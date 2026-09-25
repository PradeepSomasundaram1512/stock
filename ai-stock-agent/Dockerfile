# Container image for running the market scanner as a Cloud Run Job.
# One execution = one scheduled job (hourly scan, pre-market brief, etc.),
# triggered by Cloud Scheduler — see deploy/gcp/GCP_DEPLOYMENT_GUIDE.md.

FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements-cloud.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements-cloud.txt

COPY . .
RUN chmod +x entrypoint.sh \
    && python -m compileall -q . >/dev/null

# data/ (portfolio.db, backtest.db, watchlist.txt, vector store) is synced
# from a GCS bucket at the start and end of every execution — see
# entrypoint.sh and deploy/gcp/sync_data.py. It is NOT mounted live via GCS
# FUSE: SQLite's random-offset journal writes are incompatible with FUSE's
# streaming writes (BufferedWriteHandler.OutOfOrderError).
RUN mkdir -p data/knowledge_base data/vector_store

ENTRYPOINT ["./entrypoint.sh"]
CMD ["--hourly-scan"]
