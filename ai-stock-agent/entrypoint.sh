#!/bin/bash
#
# Cloud Run Job entrypoint: take the bucket lock and pull persisted state
# from GCS, run the requested script, push changed files back, release the
# lock — regardless of whether the script succeeded, so partial state isn't
# lost. The script's own exit code is what Cloud Run Job's retry logic sees.
# See deploy/gcp/sync_data.py for why the lock exists (overlapping runs).
#
# --swing-trade runs swing_trader.py's live paper-trading cycle instead of
# the default ultimate_market_scanner.py; every other arg (or none) goes to
# ultimate_market_scanner.py as before.
#
set -uo pipefail

python deploy/gcp/sync_data.py --download || exit 1
trap 'python deploy/gcp/sync_data.py --release' EXIT

if [ "${1:-}" = "--swing-trade" ]; then
    shift
    python swing_trader.py "$@"
else
    python ultimate_market_scanner.py "$@"
fi
STATUS=$?

python deploy/gcp/sync_data.py --upload

exit $STATUS
