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

# Cloud Run Jobs have a fixed ~70 s startup cost, and the machine size adds to
# it (measured: 1 CPU/1 GiB ~71 s vs 2 CPU/4 GiB ~103 s for a no-op). Full
# scans need the big machine; the 15-minute stop-loss check only reads a few
# prices, so it gets its own small job — ~84 runs/day, faster and ~4x cheaper.
# Shadow model (see shadow.py): a second model answers the same prompt on the same inputs and is
# only logged. Cheap by construction: GPT-6 Luna ~ $0.0004/decision (~$2/month at ~240 decisions a day)
# with a hard daily cap. `SHADOW_MODEL= ./deploy/gcp/04_deploy_job.sh` (empty) turns it off;
# SHADOW_MODEL=gpt-6-sol (~$37/month for every candidate; ~$6-8 with :buys) or gpt-6-astra (~$190/month) for stronger models.
SHADOW_MODEL="${SHADOW_MODEL-gpt-6-luna,gpt-6-sol:buys}"   # ":buys" = only stocks production called BUY
SHADOW_DAILY_BUDGET_USD="${SHADOW_DAILY_BUDGET_USD:-0.60}"   # shared cap, applied per model (Sol was hitting $0.40 most afternoons; Luna never gets close)

# The ^@^ prefix in --set-env-vars below switches gcloud's list separator to "@", because SHADOW_MODEL contains commas.
deploy_job() {
    local name="$1" cpu="$2" mem="$3" timeout="$4"
    gcloud run jobs deploy "$name" \
        --image="${IMAGE_URI}:latest" \
        --region="$REGION" \
        --service-account="$RUN_SA_EMAIL" \
        --clear-volumes \
        --clear-volume-mounts \
        --set-env-vars="^@^DATA_BUCKET=${BUCKET_NAME}@SHADOW_MODEL=${SHADOW_MODEL}@SHADOW_DAILY_BUDGET_USD=${SHADOW_DAILY_BUDGET_USD}" \
        --set-secrets="$SECRETS" \
        --memory="$mem" \
        --cpu="$cpu" \
        --task-timeout="$timeout" \
        --max-retries=1
}

deploy_job "$JOB_NAME"       2 4Gi 1800
deploy_job "$LIGHT_JOB_NAME" 1 1Gi 600

echo ""
echo "Granting Cloud Scheduler's service account permission to run this job..."
# roles/run.developer, not roles/run.invoker: 05_schedule_jobs.sh's request
# body includes overrides.containerOverrides (to pick which scheduled task
# runs), which needs the run.jobs.runWithOverrides permission — invoker only
# has plain run.jobs.run and gets a 403 on any request with overrides.
for job in "$JOB_NAME" "$LIGHT_JOB_NAME"; do
    gcloud run jobs add-iam-policy-binding "$job" \
        --region="$REGION" \
        --member="serviceAccount:${SCHEDULER_SA_EMAIL}" \
        --role="roles/run.developer" >/dev/null
done

echo ""
echo "✓ Job deployed. Test it once manually:"
echo "  gcloud run jobs execute $JOB_NAME --region=$REGION --args=--test-discord"
echo ""
echo "Next: ./deploy/gcp/05_schedule_jobs.sh"
