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
# the default ultimate_market_scanner.py; --digest posts the end-of-day health
# digest (daily_digest.py); --forward-test runs the pre-registered forward test
# (forward_test.py) and posts its status; --market-snapshot writes the dashboard
# heatmap's price snapshot (market_snapshot.py); --refresh-universe rebuilds the
# scan list from the live S&P 500 (scan_universe.py); every other arg (or none) goes to
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

# Output is tee'd so the agent's silent exception fallbacks can be counted afterwards.
# (Production ran for months with an exhausted OpenAI quota: every call failed, the
# agent answered HOLD at 0.5 and the job still exited 0, so nothing looked broken.)
LOGF=$(mktemp)
if [ "${1:-}" = "--swing-trade" ]; then
    shift
    python -u swing_trader.py "$@" 2>&1 | tee "$LOGF"
    STATUS=${PIPESTATUS[0]}
elif [ "${1:-}" = "--forward-test" ]; then
    python -u forward_test.py forward data/backtest.db --out data/forward_test.json --discord 2>&1 | tee "$LOGF"
    STATUS=${PIPESTATUS[0]}
elif [ "${1:-}" = "--refresh-universe" ]; then
    python -u scan_universe.py refresh --discord 2>&1 | tee "$LOGF"
    STATUS=${PIPESTATUS[0]}
elif [ "${1:-}" = "--market-snapshot" ]; then
    python -u market_snapshot.py --out data/market_snapshot.json 2>&1 | tee "$LOGF"
    STATUS=${PIPESTATUS[0]}
elif [ "${1:-}" = "--digest" ]; then
    shift
    python -u daily_digest.py "$@" 2>&1 | tee "$LOGF"
    STATUS=${PIPESTATUS[0]}
else
    python -u ultimate_market_scanner.py "$@" 2>&1 | tee "$LOGF"
    STATUS=${PIPESTATUS[0]}
fi
[ $STATUS -ne 0 ] && notify "Job '${JOB}' failed" $STATUS

DEC=$(grep -c "✓ DECISION:" "$LOGF" || true)
ERR=$(grep -c "Error in autonomous analysis" "$LOGF" || true)
if [ "${ERR:-0}" -gt 0 ] && [ $((ERR * 10)) -ge "${DEC:-0}" ]; then
    python deploy/gcp/notify_failure.py \
        "${ERR} of ${DEC} decisions in '${JOB}' fell back to HOLD at 0.5 because the model call failed (e.g. OpenAI quota exhausted). These are not real LLM decisions." \
        "-" "⚠️ LLM fallback rate high"
fi

python deploy/gcp/sync_data.py --upload
UP=$?
if [ $UP -ne 0 ]; then
    notify "Saving state after '${JOB}' failed — its changes may be lost" $UP
    [ $STATUS -eq 0 ] && STATUS=$UP
fi

exit $STATUS
