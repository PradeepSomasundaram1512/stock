#!/bin/bash
#
# Cloud Run Job entrypoint: pull persisted state from GCS, run the requested
# script, push whatever changed back — regardless of whether it succeeded,
# so partial state (e.g. a logged recommendation before a later failure)
# isn't lost. The script's own exit code is what Cloud Run Job's retry
# logic sees.
#
# --swing-trade runs swing_trader.py's live paper-trading cycle instead of
# the default ultimate_market_scanner.py; every other arg (or none) goes to
# ultimate_market_scanner.py as before.
#
set -uo pipefail

python deploy/gcp/sync_data.py --download

if [ "${1:-}" = "--swing-trade" ]; then
    shift
    python swing_trader.py "$@"
else
    python ultimate_market_scanner.py "$@"
fi
STATUS=$?

python deploy/gcp/sync_data.py --upload

exit $STATUS
