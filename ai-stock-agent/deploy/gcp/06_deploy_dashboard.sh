#!/bin/bash
#
# Build and deploy the read-only dashboard as a Cloud Run service (scales to zero).
#
# Runs as its own service account: read-only on the data bucket and on the invite list.
#
# Access control, two modes:
#   * No GOOGLE_CLIENT_ID given and none already configured: the service is NOT public. Cloud Run IAP guards it, but IAP's
#     built-in sign-in only admits accounts inside the Google Cloud organization, so personal Gmail
#     accounts are refused. Safe, but unusable for invited testers.
#   * GOOGLE_CLIENT_ID set: the service is public and the app itself enforces invite-only Google
#     sign-in (dashboard/auth.py). Every page and API route except /healthz needs a valid session.
#     Get a client ID: see "Dashboard sign-in" in GCP_DEPLOYMENT_GUIDE.md.
#
# Usage:  export PROJECT_ID=...; [GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com] ./deploy/gcp/06_deploy_dashboard.sh
cd "$(dirname "$0")"
source ./config.sh
cd ../..   # ai-stock-agent/ (build context)

SERVICE="stock-dashboard"
DASH_SA_NAME="stock-dashboard"
DASH_SA="${DASH_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
DASH_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${SERVICE}"
CONFIG_BUCKET="${PROJECT_ID}-stock-dashboard-config"
CLIENT_ID="${GOOGLE_CLIENT_ID:-}"
# A redeploy must not silently undo sign-in: with no ID given, keep the one already configured.
if [ -z "$CLIENT_ID" ]; then
    CLIENT_ID=$(gcloud run services describe "$SERVICE" --region="$REGION" --format=json 2>/dev/null | python3 -c "
import json,sys
try:
    env = json.load(sys.stdin)['spec']['template']['spec']['containers'][0].get('env', [])
    print(next((e.get('value','') for e in env if e['name']=='GOOGLE_CLIENT_ID'), ''))
except Exception:
    print('')")
    [ -n "$CLIENT_ID" ] && echo "Keeping the existing GOOGLE_CLIENT_ID (${CLIENT_ID%%-*}-…)"
fi

gcloud iam service-accounts describe "$DASH_SA" >/dev/null 2>&1 || \
    gcloud iam service-accounts create "$DASH_SA_NAME" --display-name="Stock dashboard (read-only)"
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
    --member="serviceAccount:${DASH_SA}" --role="roles/storage.objectViewer" >/dev/null

# invite list (private bucket, no public access) and the session-signing secret
gcloud storage buckets describe "gs://${CONFIG_BUCKET}" >/dev/null 2>&1 || \
    gcloud storage buckets create "gs://${CONFIG_BUCKET}" --location="$REGION" --uniform-bucket-level-access --public-access-prevention
gcloud storage buckets add-iam-policy-binding "gs://${CONFIG_BUCKET}" \
    --member="serviceAccount:${DASH_SA}" --role="roles/storage.objectViewer" >/dev/null
gcloud secrets describe dashboard-session-secret >/dev/null 2>&1 || \
    python3 -c "import secrets;print(secrets.token_urlsafe(48),end='')" | gcloud secrets create dashboard-session-secret --data-file=-
gcloud secrets add-iam-policy-binding dashboard-session-secret \
    --member="serviceAccount:${DASH_SA}" --role="roles/secretmanager.secretAccessor" >/dev/null

gcloud builds submit --config=dashboard/cloudbuild.yaml --substitutions=_IMAGE="${DASH_IMAGE}" .

if [ -n "$CLIENT_ID" ]; then ACCESS_FLAG="--allow-unauthenticated"; else ACCESS_FLAG="--no-allow-unauthenticated"; fi
gcloud run deploy "$SERVICE" \
    --image="${DASH_IMAGE}:latest" \
    --region="$REGION" \
    --service-account="$DASH_SA" \
    --set-env-vars="DATA_BUCKET=${BUCKET_NAME},ACCESS_BUCKET=${CONFIG_BUCKET},GOOGLE_CLIENT_ID=${CLIENT_ID}" \
    --set-secrets="SESSION_SECRET=dashboard-session-secret:latest" \
    $ACCESS_FLAG \
    --cpu=1 --memory=512Mi \
    --min-instances=0 --max-instances=2 --concurrency=20 --timeout=60

if [ -n "$CLIENT_ID" ]; then
    # App-level sign-in replaces IAP: drop the IAP annotation, otherwise IAP would still intercept.
    gcloud run services describe "$SERVICE" --region="$REGION" --format=export > /tmp/dash_noiap.yaml
    python3 - <<'PY'
import re
s = open("/tmp/dash_noiap.yaml").read()
s = re.sub(r"^\s*run\.googleapis\.com/iap-enabled:.*\n", "", s, flags=re.M)
open("/tmp/dash_noiap.yaml", "w").write(s)
PY
    gcloud run services replace /tmp/dash_noiap.yaml --region="$REGION"
    gcloud run services add-iam-policy-binding "$SERVICE" --region="$REGION" \
        --member=allUsers --role=roles/run.invoker >/dev/null
fi

echo ""
echo "✓ Dashboard deployed. URL:"
gcloud run services describe "$SERVICE" --region="$REGION" --format="value(status.url)"
if [ -n "$CLIENT_ID" ]; then
    echo "Public URL, invite-only Google sign-in. Manage the list: ./deploy/gcp/dashboard_access.sh invite EMAIL"
else
    echo "No GOOGLE_CLIENT_ID given: still behind IAP (in-organization accounts only)."
fi
