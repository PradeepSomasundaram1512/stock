# 🚀 GCP Deployment Guide — Cloud Run Jobs + Cloud Scheduler

This replaces the [AWS EC2 setup](AWS_DEPLOYMENT_GUIDE.md) with a serverless
GCP deployment: instead of one VM running 24/7, each scheduled task
(pre-market brief, hourly scan, stop-loss check, etc.) runs as a short-lived
**Cloud Run Job** execution, triggered by **Cloud Scheduler**. You only pay
for the seconds each job actually runs.

---

## 🏗 Architecture

```
Cloud Scheduler (7 cron schedules, America/New_York)
        │  each fires a different --args override
        ▼
Cloud Run Job "stock-scanner"  (one container image, many executions)
        │
        ├─> entrypoint.sh: download data/ from GCS, run the scan, upload
        │     data/ back to GCS (portfolio.db, backtest.db, watchlist.txt,
        │     vector store) — this is what makes state survive between
        │     executions, without mounting SQLite files on GCS FUSE
        │
        ├─> Secret Manager  (API keys, injected as env vars)
        │
        ├─> Yahoo Finance, OpenAI, NewsAPI, Finnhub, ...
        └─> Discord webhook
```

Why Jobs instead of a Compute Engine VM: the workload is inherently
scheduled (nothing needs to run between scans), so a 24/7 VM is mostly idle
capacity you're paying for. Cloud Run Jobs bill per-second of actual
execution — a handful of scans a day costs cents, not a monthly VM bill.

Why download/upload instead of a live GCS FUSE mount: SQLite writes its
rollback journal (and WAL, if enabled) at random offsets, which GCS FUSE's
streaming writes don't support — mounting the DB directly threw repeated
`BufferedWriteHandler.OutOfOrderError`s in testing. `entrypoint.sh` instead
pulls `data/` down to local disk before the scan and pushes it back after
(`deploy/gcp/sync_data.py`), so SQLite gets a normal local filesystem and the
bucket only ever sees whole-file object writes.

Executions DO overlap in practice (the 15-minute stop-loss check runs alongside
scans and the swing trader), and a plain download-everything/upload-everything
cycle is last-writer-wins: a slow run silently overwrote a faster run's
results with its stale copy (this lost the 9/24 swing-trade exits before it
was caught). Two guards prevent that: a lock object in the bucket
(`_locks/data.lock`) makes executions take turns (a lock older than 15 min is
treated as abandoned by a killed run), and `--upload` writes only files that
changed since `--download`. If you later need true concurrent writers, migrate
`tools/db_manager.py` and `portfolio/manager.py` to Cloud SQL instead.

---

## 💰 Cost

| Component | Cost/month | Notes |
|---|---|---|
| Cloud Run Jobs execution time | ~$1-5 | Pay per vCPU-second/GB-second actually used, roughly a dozen runs/day at a few minutes each |
| Cloud Build (image builds) | $0 | 120 free build-minutes/day, plenty for occasional deploys |
| Artifact Registry storage | ~$0.10 | One container image, a few hundred MB |
| GCS bucket (data/) | ~$0.02 | A few MB of SQLite files |
| Secret Manager | $0.06/secret/month after first 6 free | ~$1-2 for ~25 keys |
| **Total** | **~$3-8/month** | Scales with how often you schedule scans, not a flat VM fee |

New GCP accounts also get a $300 / 90-day free credit, and Cloud Run/Cloud
Build both have standing always-free monthly quotas this workload will
likely stay under entirely.

---

## 📋 Prerequisites

- A GCP account with billing enabled (`console.cloud.google.com`)
- `gcloud` CLI installed — you already have it (`/opt/homebrew/bin/gcloud`)
- Your existing `.env` file with API keys, filled in as usual
- Docker is **not** required locally — Cloud Build builds the image for you

---

## 🚀 Step-by-Step

### Phase 1: Create and authenticate a GCP project (5 minutes)

```bash
# Log in (opens a browser)
gcloud auth login

# Create a new project (id must be globally unique) — or reuse an existing one
gcloud projects create YOUR_PROJECT_ID --name="Stock Scanner"

# Link billing — list your billing accounts, then link one
gcloud billing accounts list
gcloud billing projects link YOUR_PROJECT_ID --billing-account=YOUR_BILLING_ACCOUNT_ID

gcloud config set project YOUR_PROJECT_ID
```

### Phase 2: Run the deploy scripts (10-15 minutes, mostly waiting on builds)

From `ai-stock-agent/`:

```bash
export PROJECT_ID=YOUR_PROJECT_ID

./deploy/gcp/deploy_all.sh
```

This runs, in order (you can also run each individually — see the header
comment in each script):

1. **`01_setup_project.sh`** — enables the required APIs, creates the
   Artifact Registry repo, the GCS data bucket, and two service accounts
   (one for the job runtime, one for Cloud Scheduler). Also grants Cloud
   Scheduler's own service agent permission to mint OAuth tokens as the
   scheduler SA — the Console does this automatically when you create an
   HTTP+OAuth job through the UI, but the CLI doesn't, so without it every
   scheduled trigger fails silently (no error anywhere, no execution ever
   created).
2. **`02_create_secrets.sh`** — reads your local `.env` and pushes each key
   into Secret Manager as its own secret (values are piped straight to
   `gcloud`, never printed or logged).
3. **`03_build_and_push.sh`** — builds the container image with Cloud Build
   and pushes it to Artifact Registry.
4. **`04_deploy_job.sh`** — creates the Cloud Run Job, wires up the secrets
   as env vars, sets `DATA_BUCKET` for `entrypoint.sh`'s sync, and grants
   Cloud Scheduler's service account `roles/run.developer` (scoped to just
   this job) so it can run it. This has to be `run.developer`, not the more
   obvious `run.invoker`: `05_schedule_jobs.sh`'s requests include
   `overrides.containerOverrides` to pick which scheduled task runs, which
   needs the `run.jobs.runWithOverrides` permission — `run.invoker` only has
   plain `run.jobs.run` and gets a 403 on any request with overrides.
5. **`05_schedule_jobs.sh`** — creates the 7 Cloud Scheduler jobs that
   replace the old `--monitor` loop's internal schedule.

### Phase 3: Verify (5 minutes)

```bash
# Manually run one execution to confirm the container works end-to-end
gcloud run jobs execute stock-scanner --region=us-central1 --args=--test-discord

# Watch it
gcloud run jobs executions list --job=stock-scanner --region=us-central1

# Check logs for the most recent execution
gcloud logging read \
  'resource.type=cloud_run_job AND resource.labels.job_name=stock-scanner' \
  --limit=50 --format='value(textPayload)'
```

You should see a Discord test notification, same as the old
`python ultimate_market_scanner.py --test-discord`.

Trigger a real scan the same way:

```bash
gcloud run jobs execute stock-scanner --region=us-central1 --args=--hourly-scan
```

---

## 🎛 Managing It

### Update the code

```bash
./deploy/gcp/03_build_and_push.sh   # rebuild image
./deploy/gcp/04_deploy_job.sh       # point the job at the new image
```

### Rotate an API key

Edit `.env`, then:

```bash
./deploy/gcp/02_create_secrets.sh
```

(No redeploy needed — the job reads `:latest` for each secret on every
execution.)

### View logs

```bash
gcloud logging read \
  'resource.type=cloud_run_job AND resource.labels.job_name=stock-scanner' \
  --limit=100 --freshness=1d

# Or in the console:
# https://console.cloud.google.com/run/jobs/details/us-central1/stock-scanner/executions
```

### Pause / resume a schedule

```bash
gcloud scheduler jobs pause stock-scanner-hourly-scan --location=us-central1
gcloud scheduler jobs resume stock-scanner-hourly-scan --location=us-central1
```

### List everything that was created

```bash
gcloud run jobs list --region=us-central1
gcloud scheduler jobs list --location=us-central1
gcloud secrets list
gsutil ls gs://YOUR_PROJECT_ID-stock-scanner-data
```

---

## ⚡ Performance, cost and failure alerts (measured)

**Why every run takes ~1.5-2.5 minutes.** Cloud Run Jobs have a fixed startup
cost. A no-op `echo` job takes ~73 s even on Google's tiny sample image, and
neither our image size nor the 28 Secret Manager env vars changed that
(measured with throwaway probe jobs: slim image, with/without secrets, all
~1m43s at 2 CPU/4 GiB and ~71 s at 1 CPU/1 GiB). Machine size does add to it, so:

- `stock-scanner` (2 CPU / 4 GiB) runs the scans, briefs and swing trader.
- `stock-scanner-light` (1 CPU / 1 GiB) runs only the 15-minute stop-loss
  check (~84 runs/day), which just reads a few prices.
- The container image dropped from 1.4 GB to 390 MB by installing
  `requirements-cloud.txt` (no TensorFlow/xgboost/scikit-learn/scipy/
  matplotlib/plotly — only offline analysis code imports them).
- `entrypoint.sh` warms the scanner import in the background (it takes ~20 s
  on Cloud Run's slow sandbox filesystem vs 1.6 s on a laptop) so it overlaps
  the lock wait/state download instead of extending how long the lock is held.

If alert latency ever matters more than simplicity, the next step is serving
the stop-loss check from a Cloud Run *service* (seconds to cold-start, not
~70 s) instead of a job.

**Cost.** Stop-loss runs use roughly 185k vCPU-seconds/month on the light job,
which falls inside Cloud Run's free tier (240k vCPU-s and 450k GiB-s per
month); everything else adds ~80k vCPU-s. Compute is effectively $0-2/month —
the OpenAI/news API calls are the real spend, so duplicate senders (see the
AWS decommission note below) cost far more than the infrastructure.

**Failure alerts.** Any failed run — the job itself, the state sync/lock, or
the final upload — posts a Discord message with the exit code, attempt number
and a link to that execution's logs (`deploy/gcp/notify_failure.py`, called
from `entrypoint.sh`). A second alert catches what a crash alert cannot: if 10% or more of a run's
decisions were exception fallbacks (the agent answers HOLD at confidence 0.5
when the model call fails and the job still exits 0), it posts "LLM fallback
rate high". This exists because production ran for two months with an
exhausted OpenAI quota — 71% of all logged decisions were fallbacks — and
nothing looked broken. Failures inside the container are covered; failures
before the container runs (image pull, OOM-kill) are not, so still glance at
`gcloud run jobs executions list` if the channel goes quiet.

**Archive.** Data from the retired AWS instance (3,507 recommendations from
2026-01-06 to 2026-09-24, plus its logs) and the pre-merge GCP database live
in `gs://<project>-stock-scanner-archive/`, deliberately outside the synced
data bucket. The live `backtest.db` already contains the merged history.

## 🧪 Shadow model (forward model comparison)

A second LLM answers the *same prompt on the same stored inputs* as the production
model for every candidate of the hourly scan, and its answer is only logged
(`shadow_decisions` table, joined to `llm_decisions` on `scan_id, ticker`). It never
reaches alerts, rankings or trading. It exists to answer, forward and cleanly, whether
a newer/stronger model chooses better than the deployed 2024 one.

It shares an OpenAI account with production, which once ran out of quota (see the
fallback-alert section), so it is built to be unable to hurt it and to stay cheap:

| Guard | Behaviour |
|---|---|
| Off switch | disabled unless `SHADOW_MODEL` is set; a model with no known price is refused |
| Daily cap | `SHADOW_DAILY_BUDGET_USD` (default **$0.25**), summed from actual token usage already logged today, so it holds across separate job executions |
| Never delays alerts | runs after the production Discord alert has been sent |
| Health check | skipped for a scan if >=10% of production calls failed |
| Circuit breaker | stops for the scan after 3 consecutive failures |

Measured on real prompts (about 1,300 input / 450-520 output tokens including hidden
reasoning; official prices, Sept 2026):

| Model | Per decision | ~240 decisions/day | Per month |
|---|---|---|---|
| gpt-6-luna (default) | ~$0.0004 | ~$0.10 | ~$2 |
| gpt-6-sol | ~$0.007 | ~$1.70 | ~$37 |
| gpt-6-astra | ~$0.036 | ~$8.60 | ~$190 |

Change or disable it at deploy time (`SHADOW_MODEL= ./deploy/gcp/04_deploy_job.sh`
disables; raise `SHADOW_DAILY_BUDGET_USD` if you pick a pricier model or the cap will
bind). GPT-6 models reject a non-default temperature, so the shadow agent omits it.
Read results with `venv/bin/python shadow_report.py <backtest.db>`.

## 🆘 Troubleshooting

**Job execution fails immediately** — check logs (above). Most common cause:
a secret referenced in the job spec doesn't exist yet — re-run
`02_create_secrets.sh` before `04_deploy_job.sh`.

**"Permission denied" (403) calling the Cloud Run Jobs API from Cloud
Scheduler** — check `gcloud logging read 'logName:"cloudscheduler.googleapis.com"'`
for the actual `AttemptFinished` error; `gcloud scheduler jobs run` itself
always returns success (it only confirms Scheduler *accepted* the trigger,
not that the downstream call succeeded), so this failure mode is otherwise
silent. Two distinct causes, both need the fix to have run before
`05_schedule_jobs.sh` (already the order in `deploy_all.sh`):
- The scheduler service account needs `roles/run.developer` (not
  `run.invoker` — see the `04_deploy_job.sh` note above) on the specific job.
- Cloud Scheduler's own service agent needs `roles/iam.serviceAccountTokenCreator`
  on the scheduler service account, or it can't mint the OAuth token it
  sends — `01_setup_project.sh` grants this.

**Executions stuck "waiting" / a run seems slow to start its work** — runs
take turns on the bucket lock, so a run queues behind whichever one holds
it (each execution spends ~2.5 min mostly on cold-start imports; the actual
work is seconds). Look for `Acquired data lock` / `Released data lock` in the
execution logs. A run that can't get the lock within 20 min exits with an
error, and a lock left by a killed run is taken over after 15 min. To clear a
stuck lock manually: `gsutil rm gs://<bucket>/_locks/data.lock`.

**Saved state looks stale or missing recent trades** — check that every
execution log shows `Uploaded N changed object(s)` after the job's own output;
if a run died before upload, its changes for that run are lost (the
scheduled jobs are idempotent, so the next run recomputes them).

**Out of memory / slow scans** — bump `--memory` and `--cpu` in
`04_deploy_job.sh` (currently 4Gi/2 vCPU, matching the AWS guide's
recommended t3.medium) and re-run it.

---

## Rolling back to AWS

Nothing about this migration deletes the AWS setup — `AWS_DEPLOYMENT_GUIDE.md`
and `deploy/*.sh` (the EC2 scripts) are untouched. The only code change is
additive: new `--hourly-scan` / `--premarket-brief` / `--gap-scan` /
`--go-no-go` / `--stop-loss-check` / `--weekly-report` / `--closing-recap`
flags on `ultimate_market_scanner.py` alongside the existing `--scan-now` and
`--monitor`, so the EC2 systemd service keeps working unmodified if you ever
want to go back.

## Daily health digest

`stock-scanner-daily-digest` (16:20 ET, Mon-Fri, light job) runs `daily_digest.py` via `entrypoint.sh --digest`
and posts one Discord message per day: scans run, candidates analysed, how many were answered by the model vs.
fell back to HOLD, BUY count, top ranked signals, and the shadow model's agreement and cost. The title is
✅ under a 10% fallback rate, ⚠️ above it, ℹ️ on days with no decisions (market holidays). Run it by hand with
`python daily_digest.py --print` against a downloaded `backtest.db`.

## Rule baselines

`paper_baselines.py` compares the LLM's BUY signals with momentum, reversal, low-volatility and equal-weight
rules that pick the same number of stocks on the same dates from the fixed S&P 500 pool (`paper_results/baselines.json`).

## Dashboard

`./deploy/gcp/06_deploy_dashboard.sh` deploys `stock-dashboard`, a read-only Cloud Run service (scales to zero,
~$0 when idle). It reads `backtest.db`, `paper_trades.json` and `swing_trades.json` from the data bucket (cached
2 minutes) and shows: today's model health, the latest scan's candidates with the production and shadow
decisions and the model's reasoning, per-day health and BUY-count charts, the paper account, and swing trades, with open positions marked to the last Yahoo price (60 s cache; falls back to
cost if a quote is unavailable).
It runs as its own service account with `objectViewer` only.

## Dashboard sign-in

Cloud Run's built-in IAP cannot be used for personal Gmail testers: its default Google-managed sign-in
only admits identities inside the Google Cloud organization, so an invited `@gmail.com` account gets
"You don't have access" even with the accessor role (verified: the IAM Policy Troubleshooter reports the
grant as matched). So the dashboard does its own **invite-only Google sign-in** (`dashboard/auth.py`):

1. The browser gets a Google ID token; the server verifies it (signature, expiry, audience, verified email).
2. The email must be on the invite list, `gs://<project>-stock-dashboard-config/allowed_emails.json`.
3. The server sets its own signed, HttpOnly, Secure, SameSite cookie (12 h). Every request re-checks the
   list, so a revoked person loses access within about a minute. It fails closed on any misconfiguration.
4. The service is public at the network level, so *every* page and API route except `/healthz` checks the
   session first. `python dashboard/test_auth.py` covers forged, tampered, expired and revoked sessions.

**One-time setup (needs the console; only the client ID is needed, never a secret):**

1. Open <https://console.cloud.google.com/auth/overview?project=PROJECT_ID> and click *Get started*: app name
   "Scanner Dashboard", your support email, audience **External**, contact email.
2. *Audience*: leave publishing status **Testing** and add each invited person under *Test users*.
3. *Clients* > *Create client* > **Web application**. Under *Authorized JavaScript origins* add the service URL
   (`gcloud run services describe stock-dashboard --region=us-central1 --format="value(status.url)"`).
   No redirect URI is needed. Copy the **Client ID** (`...apps.googleusercontent.com`).
4. `GOOGLE_CLIENT_ID=<that id> ./deploy/gcp/06_deploy_dashboard.sh` (this also removes IAP and makes the URL public).

Invite or revoke testers (also add them as Test users in step 2 while the app is in Testing):

    ./deploy/gcp/dashboard_access.sh list
    ./deploy/gcp/dashboard_access.sh invite tester@example.com
    ./deploy/gcp/dashboard_access.sh revoke tester@example.com

Local development: `DATA_DIR=/path/to/copies DASHBOARD_DEV_NO_AUTH=1 python dashboard/server.py`
(the auth bypass only works together with `DATA_DIR`, which Cloud Run never sets).

### Dashboard tabs

- **Overview**: freshness badge (red if the market is open and no scan for 90 minutes), SPY/VIX, model spend vs. cap, today's health, latest scan, charts, paper account.
- **History**: any past scan, or one ticker's full decision and outcome history; CSV export.
- **Scoreboard**: the forward-audit result (LLM vs. matched placebo, random stocks and rule baselines, with confidence intervals), a confidence-calibration chart, and live exit outcomes. The audit numbers come from `dashboard/scoreboard.json`; regenerate with `python dashboard/build_scoreboard.py` after re-running `paper_analysis.py`/`paper_baselines.py`, then redeploy.
- **Model arena**: production vs. shadow model: agreement matrix, every disagreement, and the move since each call (unmatured, early evidence only).

## Weekly forward test

`stock-scanner-forward-test` (Saturdays 09:00 ET, main job, `entrypoint.sh --forward-test`) runs `forward_test.py forward`
on the live database, writes `data/forward_test.json` (shown on the dashboard's Scoreboard tab) and posts a short status to
Discord. The hypotheses, thresholds and minimum sample (300 matured signals and 20 independent 10-day blocks) are fixed in
`paper_results/forward_test_prereg.md`, committed before any outcome existed; below the minimum it reports "insufficient data".
`forward_test.py` and `audit_core.py` need only pandas/numpy/yfinance, so they run in the cloud image (no scipy/matplotlib).
The placebo universe list lives in `audit/sp500_universe.csv`.

## Public track-record page and tamper-evident log

`/public` needs no sign-in. Its allowlist is exact (`PUBLIC_FILES`, `PUBLIC_ROUTES` in `dashboard/server.py`) and it reads no row
from the live decision tables, only `scoreboard.json`, `forward_test.json` and the chain files, so it cannot leak a current signal.

`track_record.py` (run by the daily digest) hashes each completed day's decisions (SHA-256), chains the days
(`hash_n = sha256(hash_{n-1} | day | digest | rows)`), stores `data/track_record_chain.json`, and releases the raw decisions only
after 45 days as `data/public_revealed.csv`. The chain head is posted to Discord daily as an outside timestamp. Anyone can run
`python verify_chain.py verify chain.json revealed.csv` (stdlib only, served at `/public/verify_chain.py`). It proves released
decisions were not edited after commit; it cannot prove a day's list was complete when committed. Tests: `python tests/test_track_record.py`,
`python dashboard/test_auth.py`.

## Cost

Measured (2026-09-25): about $7-12/month on GCP and $4-9/month on OpenAI. Cloud Run jobs are billed at $0.000018 per vCPU-second and
$0.000002 per GiB-second (us-central1). The stop-loss check was the biggest line (~150 s per run); it now runs every 15 minutes instead
of every 5, cutting that part by two thirds. A budget alert ("Stock scanner monthly", $25, alerts at 50/90/100%) emails the billing
account admins; it warns but does not stop spending. List it with
`gcloud billing budgets list --billing-account=<id>`. The shadow model has its own daily cap (`SHADOW_DAILY_BUDGET_USD`, default $0.25).

## Live dashboard, heatmap and phone use

- **Live bar:** `/api/pulse` (polled every 30 s while the page is visible) drives the market-session clock, countdown to the next scheduled run
  (`dashboard/market_clock.py`, which mirrors `05_schedule_jobs.sh`; its 2026 NYSE holiday list must be updated each year), the age of the last
  scan, SPY/VIX, and position prices. A newly landed scan triggers a toast and refreshes the data.
- **Heatmap:** `stock-scanner-market-snapshot` (every 30 min, 09:00-16:59 ET weekdays, light job) runs `market_snapshot.py`: one batched download of
  the whole scan universe into `data/market_snapshot.json`; sectors come from `dashboard/sectors.json` (`python dashboard/build_sectors.py`).
  Tile size is dollar volume (market cap is not available from the source), colour is 1-day/5-day change or RSI.
- **Charts:** `/api/chart` returns candles (Yahoo, ~15 min delayed) plus the model's own recommendations and decisions for that ticker; the chart is
  hand-written SVG (`dashboard/charts.js`), so no third-party charting licence applies.
- **iPhone:** open the site in Safari, sign in, then Share > Add to Home Screen. The Home Screen app has separate cookie storage on iOS, so it
  signs in again, and uses a redirect-style Google sign-in: add `<service URL>/auth/google` under *Authorized redirect URIs* of the OAuth client
  (Google Auth Platform > Clients). Browsing in Safari works without that. Regenerate icons with `python dashboard/make_icons.py`.

## Scan universe (S&P 500)

The hand-typed scan list drifted from the index (83 members missing, 49 non-members present), so it is now refreshed weekly:
`stock-scanner-refresh-universe` (Sunday 08:00 ET, light job, `entrypoint.sh --refresh-universe`) runs `scan_universe.py refresh`. It fetches the
S&P 500 constituents (Wikipedia's list), validates them (count, symbol shape, table layout, size of change) and rewrites
`data/scan_universe.json`; **on any doubt it keeps the old file**. Existing tickers keep their position (the quick scan uses the first 100),
leavers drop out, joiners are appended, and every change is logged to `data/universe_changes.jsonl` and posted to Discord.
The scanner and `market_snapshot.py` use the refreshed list when it is valid and less than 45 days old, otherwise the list built into
`ultimate_market_scanner.py`. To scan names beyond the index, list them in `audit/scan_extras.txt` (one per line). Because the universe change alters where
forward-test signals come from, it is recorded in `paper_results/forward_test_deviations.md`. Tests: `python tests/test_scan_universe.py`.

## Backups and restoring a file

The data and dashboard-config buckets have **object versioning** on (old versions expire after 30 days; the frequently rewritten lock file's
after 1 day), on top of Google's default 7-day soft delete. To recover from a bad write or an accidental delete:

    gcloud storage ls -a gs://<project>-stock-scanner-data/backtest.db          # lists generations: ...backtest.db#1790371076961913
    gcloud storage cp "gs://<project>-stock-scanner-data/backtest.db#<generation>" gs://<project>-stock-scanner-data/backtest.db

(The restore was drilled on a throwaway object: overwrite, list, copy the old generation back, verified.) Do this while no job is running, or
the next upload will overwrite the restored file.

## Automated checks

- **CI** (`.github/workflows/tests.yml`) runs on every push: Python/shell/JavaScript syntax, and the dashboard (sign-in, endpoints), market-clock,
  track-record, scan-universe and digest-check test suites.
- **Daily digest** (Discord, 16:20 ET) now also verifies the machinery: scan-list size and age, heatmap snapshot age and missing tickers, and
  the age of the latest scan; any problem turns the message to a warning.
- **Sign-in** is rate limited (10 attempts per address per 5 minutes), and responses carry HSTS and a permissions policy. A strict
  Content-Security-Policy was deliberately not added: it could not be tested against real Google sign-in and could lock everyone out.

## "How similar past calls did"

`/api/similar` (shown under each ticker's latest call) reports, from the logged history of closed calls, the win rate of past calls with the same
decision in a similar setup (RSI within 8, same trend), at about the same confidence, and overall, each with a 95% Wilson interval, and it says
"too few" below 20 examples. It describes the past; it is not a forecast.

## Reproducing the paper's numbers

`paper_results/daily_panel_*.pkl.gz` is the frozen raw price download used by `paper_analysis.py`, `paper_baselines.py` and
`forward_test.py walkforward` (`audit_core.load_panel(..., cache_dir=...)`). Yahoo revises adjusted prices slightly between downloads, which
used to make the portfolio-rule row wobble between runs; with the frozen file two runs are byte-identical. The live forward test never uses a cache.

## Validating the audit, and the model snapshot

- `paper_power.py` validates the paper's inference by Monte Carlo on the real price panel: 500 fake LLMs pick random oversold stocks (no skill) and are
  compared with the same matched placebo, giving false-positive rates and power for the percentile bootstrap, a cluster-robust t and a sign-flip test.
  It also measures the placebo's bias for oversold picks (about +0.27 pp). `paper_sensitivity.py` repeats the comparison under six placebo designs.
  Both write LaTeX for the paper (`paper/results_power.tex`, `paper/results_sensitivity.tex`).
- `llm_decisions.model_snapshot` now records the exact model snapshot the API served (the alias `gpt-4o-mini` can point to different snapshots over
  time; on 2026-09-25 it resolved to `gpt-4o-mini-2024-07-18`). The column is added automatically by `migrate_schema()`.
- `ablation.py` also replays the two key ablations with different replacement wording, so an effect can be told apart from an artifact of the words.
- `paper_results/osf_preregistration.md` is ready to paste into an external registry (OSF / AsPredicted) for an independent timestamp.

## Forward test: H6 and paper status

- `forward_test.py` now includes **H6, the primary test of ten-day selection skill** (pre-registered in addendum 3 before it was implemented): the alpha over
  the matched placebo minus the placebo's bias, the bias measured each run by 200 seeded no-skill fake pickers on the same dates (`audit_core.null_bias`,
  numpy only, so it runs in the cloud image). The Holm family is H1 to H6.
- `paper_power_intraday.py` validates the intraday result the same way as the ten-day one (size, power, placebo bias, six placebo designs).
- `python paper_forward_status.py` pulls the latest `forward_test.json` from the bucket and writes `paper/results_forward_status.tex`: until the
  pre-registered minimum sample is met the paper says how far along it is; afterwards it adds a results table (H1 to H6 with Holm p). Then rebuild the paper.
