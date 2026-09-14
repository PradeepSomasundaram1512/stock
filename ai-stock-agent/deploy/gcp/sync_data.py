#!/usr/bin/env python3
"""
Syncs the local data/ directory with a GCS bucket, so Cloud Run Job
executions can persist SQLite state (portfolio.db, backtest.db,
watchlist.txt, vector store) across runs without mounting the database
files directly on GCS FUSE.

SQLite does random-offset writes (journal/WAL files), which GCS FUSE's
streaming writes don't support — mounting the DB live on FUSE throws
BufferedWriteHandler.OutOfOrderError. Downloading to local disk before the
job runs and uploading the changes back after avoids that entirely: SQLite
gets a normal local filesystem, and the bucket only ever sees whole-file
GCS object writes.

Usage:
    python deploy/gcp/sync_data.py --download   # bucket -> local data/
    python deploy/gcp/sync_data.py --upload     # local data/ -> bucket
"""
import argparse
import os
import sys
from pathlib import Path

from google.cloud import storage

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def get_bucket():
    bucket_name = os.environ.get("DATA_BUCKET")
    if not bucket_name:
        print("DATA_BUCKET env var not set — skipping sync (local-only run)")
        return None
    client = storage.Client()
    return client.bucket(bucket_name)


def download(bucket):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    for blob in bucket.list_blobs():
        if blob.name.endswith("/"):
            continue
        dest = DATA_DIR / blob.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(dest))
        count += 1
    print(f"✓ Downloaded {count} object(s) from gs://{bucket.name} to {DATA_DIR}")


def upload(bucket):
    if not DATA_DIR.exists():
        print(f"{DATA_DIR} does not exist, nothing to upload")
        return
    count = 0
    for path in DATA_DIR.rglob("*"):
        if path.is_file():
            rel = path.relative_to(DATA_DIR).as_posix()
            bucket.blob(rel).upload_from_filename(str(path))
            count += 1
    print(f"✓ Uploaded {count} object(s) from {DATA_DIR} to gs://{bucket.name}")


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--download", action="store_true")
    group.add_argument("--upload", action="store_true")
    args = parser.parse_args()

    bucket = get_bucket()
    if bucket is None:
        return 0

    if args.download:
        download(bucket)
    else:
        upload(bucket)
    return 0


if __name__ == "__main__":
    sys.exit(main())
