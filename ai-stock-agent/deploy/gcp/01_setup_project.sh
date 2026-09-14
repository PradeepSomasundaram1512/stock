#!/bin/bash
#
# One-time GCP project setup: enable APIs, create the Artifact Registry repo,
# the GCS bucket that holds persistent state (portfolio.db, backtest.db,
# watchlist.txt, vector store), and the two service accounts the job and
# the scheduler run as.
#
# Usage:
#   export PROJECT_ID=your-gcp-project-id
#   ./deploy/gcp/01_setup_project.sh
#
cd "$(dirname "$0")"
source ./config.sh

echo "========================================="
echo "GCP Project Setup — $PROJECT_ID"
echo "========================================="

gcloud config set project "$PROJECT_ID"

echo ""
echo "Enabling required APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    cloudscheduler.googleapis.com \
    secretmanager.googleapis.com \
    storage.googleapis.com

echo ""
echo "Creating Artifact Registry repo ($REPO_NAME)..."
gcloud artifacts repositories describe "$REPO_NAME" --location="$REGION" >/dev/null 2>&1 || \
gcloud artifacts repositories create "$REPO_NAME" \
    --repository-format=docker \
    --location="$REGION" \
    --description="AI stock scanner container images"

echo ""
echo "Creating GCS bucket for persistent data ($BUCKET_NAME)..."
gsutil ls -b "gs://$BUCKET_NAME" >/dev/null 2>&1 || \
gsutil mb -l "$REGION" "gs://$BUCKET_NAME"

echo ""
echo "Creating runtime service account for the Cloud Run Job ($RUN_SA_EMAIL)..."
gcloud iam service-accounts describe "$RUN_SA_EMAIL" >/dev/null 2>&1 || \
gcloud iam service-accounts create "$RUN_SA_NAME" \
    --display-name="Stock scanner Cloud Run Job runtime"

echo "Granting it access to the data bucket..."
gsutil iam ch "serviceAccount:${RUN_SA_EMAIL}:roles/storage.objectAdmin" "gs://$BUCKET_NAME"

echo ""
echo "Creating service account for Cloud Scheduler ($SCHEDULER_SA_EMAIL)..."
gcloud iam service-accounts describe "$SCHEDULER_SA_EMAIL" >/dev/null 2>&1 || \
gcloud iam service-accounts create "$SCHEDULER_SA_NAME" \
    --display-name="Stock scanner Cloud Scheduler invoker"
# Its permission to trigger the job (roles/run.invoker, scoped to just this
# job) is granted in 04_deploy_job.sh, once the job resource exists.

echo ""
echo "✓ Project setup complete."
echo "Next: ./deploy/gcp/02_create_secrets.sh"
