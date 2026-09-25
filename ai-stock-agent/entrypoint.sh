#!/bin/bash
#
# Cloud Run Job entrypoint: take the bucket lock and pull persisted state
# from GCS, run the requested script, push changed files back, release the
# lock — regardless of whether the script succeeded, so partial state isn't
# lost. The script's own exit code is what Cloud Run Job's retry logic sees.
# See deploy/gcp/sync_data.py for why the lock exists (overlapping runs).
#
# Any failure (state sync, the job itself, or the final upload) posts a
# Discord alert via deploy/gcp/notify_failure.py so it can't go unnoticed.
#
# --swing-trade runs swing_trader.py's live paper-trading cycle instead of
# the default ultimate_market_scanner.py; every other arg (or none) goes to
# ultimate_market_scanner.py as before.
#
set -uo pipefail

JOB="${*:-hourly-scan (default)}"

# Importing the scanner takes ~20 s on Cloud Run's slow sandbox filesystem (1.6 s
# on a laptop). Warm it in the background so it overlaps the lock wait and state
# download instead of running while the lock is held and other runs queue.
python -c "import ultimate_market_scanner" >/dev/null 2>&1 &
notify() { python deploy/gcp/notify_failure.py "$1" "$2"; }

python deploy/gcp/sync_data.py --download
RC=$?
if [ $RC -ne 0 ]; then
    notify "State sync/lock failed before '${JOB}' could run" $RC
    exit $RC
fi
trap 'python deploy/gcp/sync_data.py --release' EXIT

if [ "${1:-}" = "--swing-trade" ]; then
    shift
    python swing_trader.py "$@"
else
    python ultimate_market_scanner.py "$@"
fi
STATUS=$?
[ $STATUS -ne 0 ] && notify "Job '${JOB}' failed" $STATUS

python deploy/gcp/sync_data.py --upload
UP=$?
if [ $UP -ne 0 ]; then
    notify "Saving state after '${JOB}' failed — its changes may be lost" $UP
    [ $STATUS -eq 0 ] && STATUS=$UP
fi

exit $STATUS
