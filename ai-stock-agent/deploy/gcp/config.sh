#!/bin/bash
#
# Shared config for the GCP deploy scripts. Edit these, then source this
# file is done automatically by the other scripts — you don't run it directly.
#
set -euo pipefail

# Your GCP project ID (must already exist — see GCP_DEPLOYMENT_GUIDE.md Phase 1)
PROJECT_ID="${PROJECT_ID:-}"

REGION="${REGION:-us-central1}"
REPO_NAME="stock-scanner"
IMAGE_NAME="stock-scanner"
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}"

JOB_NAME="stock-scanner"
BUCKET_NAME="${PROJECT_ID}-stock-scanner-data"

RUN_SA_NAME="stock-scanner-run"
RUN_SA_EMAIL="${RUN_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

SCHEDULER_SA_NAME="stock-scanner-scheduler"
SCHEDULER_SA_EMAIL="${SCHEDULER_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

if [ -z "$PROJECT_ID" ]; then
    echo "Error: PROJECT_ID is not set."
    echo "Run: export PROJECT_ID=your-gcp-project-id"
    exit 1
fi
