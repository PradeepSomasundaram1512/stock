#!/bin/bash
#
# Create the Cloud Scheduler jobs that replace the internal ET-aware loop
# from `ultimate_market_scanner.py --monitor`. Each schedule fires an HTTP
# request against the Cloud Run Jobs v2 API to run ONE execution of the job
# with different container args, then that execution exits.
#
# All schedules use --time-zone=America/New_York, so Cloud Scheduler handles
# EST/EDT for us — no manual DST bookkeeping needed.
#
# Usage:
#   export PROJECT_ID=your-gcp-project-id
#   ./deploy/gcp/05_schedule_jobs.sh
#
cd "$(dirname "$0")"
source ./config.sh

run_uri() { echo "https://${REGION}-run.googleapis.com/v2/projects/${PROJECT_ID}/locations/${REGION}/jobs/${1:-$JOB_NAME}:run"; }

create_or_update() {
    local name="$1" cron="$2" args_json="$3" job="${4:-$JOB_NAME}"
    local body="{\"overrides\":{\"containerOverrides\":[{\"args\":${args_json}}]}}"

    if gcloud scheduler jobs describe "$name" --location="$REGION" >/dev/null 2>&1; then
        echo "Updating $name ($cron ET)..."
        # `update http` takes --update-headers, not --headers (that's only
        # accepted by `create http`) — different flag name for the same thing.
        gcloud scheduler jobs update http "$name" \
            --location="$REGION" \
            --schedule="$cron" \
            --time-zone="America/New_York" \
            --uri="$(run_uri "$job")" \
            --http-method=POST \
            --oauth-service-account-email="$SCHEDULER_SA_EMAIL" \
            --update-headers="Content-Type=application/json" \
            --message-body="$body" >/dev/null
    else
        echo "Creating $name ($cron ET)..."
        gcloud scheduler jobs create http "$name" \
            --location="$REGION" \
            --schedule="$cron" \
            --time-zone="America/New_York" \
            --uri="$(run_uri "$job")" \
            --http-method=POST \
            --oauth-service-account-email="$SCHEDULER_SA_EMAIL" \
            --headers="Content-Type=application/json" \
            --message-body="$body" >/dev/null
    fi
}

echo "========================================="
echo "Scheduling Cloud Run Job executions"
echo "========================================="

create_or_update "stock-scanner-weekly-report"    "55 8 * * 1"    '["--weekly-report"]'
create_or_update "stock-scanner-premarket-brief"  "0 9 * * 1-5"   '["--premarket-brief"]'
create_or_update "stock-scanner-gap-scan"         "45 9 * * 1-5"  '["--gap-scan"]'
create_or_update "stock-scanner-go-no-go"         "50 9 * * 1-5"  '["--go-no-go"]'
create_or_update "stock-scanner-hourly-scan"      "0 10-15 * * 1-5" '["--hourly-scan"]'
create_or_update "stock-scanner-stop-loss-check"  "*/5 9-16 * * 1-5" '["--stop-loss-check"]' "$LIGHT_JOB_NAME"
create_or_update "stock-scanner-closing-recap"    "45 15 * * 1-5" '["--closing-recap"]'
create_or_update "stock-scanner-daily-digest"     "20 16 * * 1-5" '["--digest"]' "$LIGHT_JOB_NAME"
create_or_update "stock-scanner-swing-trade"      "5 10 * * 1-5"  '["--swing-trade"]'

echo ""
echo "✓ All schedules created."
echo ""
echo "The stop-loss-check schedule fires a bit outside 9:30-16:00 (9:00-9:25"
echo "and 16:00) since cron can't express half-hour boundaries cleanly — those"
echo "extra runs are harmless no-ops if there's nothing to check."
echo ""
echo "List them:   gcloud scheduler jobs list --location=$REGION"
echo "Trigger one now for testing:"
echo "  gcloud scheduler jobs run stock-scanner-premarket-brief --location=$REGION"
