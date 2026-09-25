#!/bin/bash
#
# Build and deploy the read-only dashboard as a Cloud Run *service* (scales to zero).
#
# It has its own service account with read-only access to the data bucket, so a bug in
# the dashboard cannot touch trading state. It is deployed with no public access, and
# sign-in is Google IAP (invite-only): manage testers with ./deploy/gcp/dashboard_access.sh.
# After a redeploy, run `dashboard_access.sh list` and check the service still redirects
# to Google sign-in when signed out.
#
# Usage:  export PROJECT_ID=...; ./deploy/gcp/06_deploy_dashboard.sh
cd "$(dirname "$0")"
source ./config.sh
cd ../..   # ai-stock-agent/ (build context)

SERVICE="stock-dashboard"
DASH_SA_NAME="stock-dashboard"
DASH_SA="${DASH_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
DASH_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${SERVICE}"

gcloud iam service-accounts describe "$DASH_SA" >/dev/null 2>&1 || \
    gcloud iam service-accounts create "$DASH_SA_NAME" --display-name="Stock dashboard (read-only)"
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
    --member="serviceAccount:${DASH_SA}" --role="roles/storage.objectViewer" >/dev/null

gcloud builds submit --config=dashboard/cloudbuild.yaml --substitutions=_IMAGE="${DASH_IMAGE}" .

gcloud run deploy "$SERVICE" \
    --image="${DASH_IMAGE}:latest" \
    --region="$REGION" \
    --service-account="$DASH_SA" \
    --set-env-vars="DATA_BUCKET=${BUCKET_NAME}" \
    --no-allow-unauthenticated \
    --cpu=1 --memory=512Mi \
    --min-instances=0 --max-instances=2 --concurrency=20 --timeout=60

echo ""
echo "✓ Dashboard deployed. URL:"
gcloud run services describe "$SERVICE" --region="$REGION" --format="value(status.url)"
echo "Invite a tester: ./deploy/gcp/dashboard_access.sh invite EMAIL"
