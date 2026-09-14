#!/bin/bash
#
# Cloud Run Job entrypoint: pull persisted state from GCS, run the scanner,
# push whatever changed back — regardless of whether the scan succeeded, so
# partial state (e.g. a logged recommendation before a later failure) isn't
# lost. The scanner's own exit code is what Cloud Run Job's retry logic sees.
#
set -uo pipefail

python deploy/gcp/sync_data.py --download

python ultimate_market_scanner.py "$@"
STATUS=$?

python deploy/gcp/sync_data.py --upload

exit $STATUS
