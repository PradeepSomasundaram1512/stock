#!/bin/bash
#
# Create (or update) the Cloud Run Job. One job definition is reused for
# every scheduled task — Cloud Scheduler passes a different --args override
# per schedule (see 05_schedule_jobs.sh) to pick which scan/brief/report runs.
#
# The container's entrypoint.sh downloads data/ from the GCS bucket before
# the scan runs and uploads it back after, so portfolio.db, backtest.db,
# watchlist.txt and the vector store persist across executions exactly like
# they did on the EC2 instance's local disk — without mounting SQLite files
# directly on GCS FUSE (which doesn't support SQLite's random-offset writes).
#
# Usage:
#   export PROJECT_ID=your-gcp-project-id
#   ./deploy/gcp/04_deploy_job.sh
#
cd "$(dirname "$0")"
source ./config.sh
cd ../..   # back to ai-stock-agent/

ENV_FILE=".env"
if [ ! -f "$ENV_FILE" ]; then
    echo "Error: $ENV_FILE not found in $(pwd)"
    exit 1
fi

# Build --set-secrets=KEY1=KEY1:latest,KEY2=KEY2:latest,... from .env keys
SECRETS=""
while IFS='=' read -r key value; do
    [ -z "$key" ] && continue
    case "$key" in \#*) continue ;; esac
    [ -z "$value" ] && continue
    SECRETS="${SECRETS}${key}=${key}:latest,"
done < "$ENV_FILE"
SECRETS="${SECRETS%,}"

echo "========================================="
echo "Deploying Cloud Run Job: $JOB_NAME"
echo "========================================="

gcloud run jobs deploy "$JOB_NAME" \
    --image="${IMAGE_URI}:latest" \
    --region="$REGION" \
    --service-account="$RUN_SA_EMAIL" \
    --set-env-vars="DATA_BUCKET=${BUCKET_NAME}" \
    --set-secrets="$SECRETS" \
    --memory=4Gi \
    --cpu=2 \
    --task-timeout=1800 \
    --max-retries=1

echo ""
echo "Granting Cloud Scheduler's service account permission to run this job..."
gcloud run jobs add-iam-policy-binding "$JOB_NAME" \
    --region="$REGION" \
    --member="serviceAccount:${SCHEDULER_SA_EMAIL}" \
    --role="roles/run.invoker"

echo ""
echo "✓ Job deployed. Test it once manually:"
echo "  gcloud run jobs execute $JOB_NAME --region=$REGION --args=--test-discord"
echo ""
echo "Next: ./deploy/gcp/05_schedule_jobs.sh"
