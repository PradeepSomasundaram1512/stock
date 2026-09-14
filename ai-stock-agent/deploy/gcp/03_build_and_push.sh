#!/bin/bash
#
# Build the container image with Cloud Build and push it to Artifact Registry.
#
# Usage:
#   export PROJECT_ID=your-gcp-project-id
#   ./deploy/gcp/03_build_and_push.sh
#
cd "$(dirname "$0")"
source ./config.sh
cd ../..   # back to ai-stock-agent/ — the Dockerfile build context

echo "========================================="
echo "Building and pushing $IMAGE_URI"
echo "========================================="

gcloud builds submit --tag "${IMAGE_URI}:latest" .

echo ""
echo "✓ Image pushed: ${IMAGE_URI}:latest"
echo "Next: ./deploy/gcp/04_deploy_job.sh"
