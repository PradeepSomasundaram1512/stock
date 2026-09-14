#!/bin/bash
#
# Runs the full GCP deployment end to end. See GCP_DEPLOYMENT_GUIDE.md for
# what each step does and how to inspect/undo it individually.
#
# Usage:
#   export PROJECT_ID=your-gcp-project-id
#   ./deploy/gcp/deploy_all.sh
#
cd "$(dirname "$0")"

./01_setup_project.sh
./02_create_secrets.sh
./03_build_and_push.sh
./04_deploy_job.sh
./05_schedule_jobs.sh

echo ""
echo "========================================="
echo "✓ Deployment complete"
echo "========================================="
