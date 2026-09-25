#!/usr/bin/env python3
"""
Syncs the local data/ directory with a GCS bucket, so Cloud Run Job
executions can persist SQLite/JSON state (portfolio.db, backtest.db,
swing_trades.json, ...) across runs without mounting the files live on
GCS FUSE (SQLite's random-offset writes break on FUSE).

Executions overlap (the 5-minute stop-loss check runs alongside scans), and a
plain "download everything / upload everything" cycle lets a slow run overwrite
a faster run's results with its stale copy. Two guards prevent that:

  1. A bucket-level lock (_locks/data.lock) serialises executions: --download
     waits for the lock, --release drops it. A lock older than LOCK_STALE_SECS
     is treated as abandoned (crashed/killed run) and taken over.
  2. --upload only writes files that actually changed since --download.

Usage:
    python deploy/gcp/sync_data.py --download   # take lock, bucket -> data/
    python deploy/gcp/sync_data.py --upload     # changed files in data/ -> bucket
    python deploy/gcp/sync_data.py --release    # drop the lock
"""
import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from google.api_core.exceptions import NotFound, PreconditionFailed
from google.cloud import storage

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
MANIFEST = Path("/tmp/sync_manifest.json")
LOCK_NAME = "_locks/data.lock"
LOCK_WAIT_SECS = 20 * 60
LOCK_STALE_SECS = 15 * 60
OWNER = os.environ.get("CLOUD_RUN_EXECUTION", f"local-{os.getpid()}")


def get_bucket():
    bucket_name = os.environ.get("DATA_BUCKET")
    if not bucket_name:
        print("DATA_BUCKET env var not set — skipping sync (local-only run)")
        return None
    return storage.Client().bucket(bucket_name)


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def acquire_lock(bucket):
    lock = bucket.blob(LOCK_NAME)
    deadline = time.time() + LOCK_WAIT_SECS
    while True:
        try:
            lock.upload_from_string(OWNER, if_generation_match=0)
            print(f"✓ Acquired data lock ({OWNER})")
            return
        except PreconditionFailed:
            pass
        try:
            lock.reload()
            age = (datetime.now(timezone.utc) - lock.updated).total_seconds()
            if age > LOCK_STALE_SECS:
                print(f"Taking over stale lock ({age:.0f}s old)")
                lock.delete(if_generation_match=lock.generation)
                continue
        except (NotFound, PreconditionFailed):
            continue
        if time.time() > deadline:
            print("ERROR: could not acquire data lock in time", file=sys.stderr)
            sys.exit(1)
        time.sleep(5)


def release_lock(bucket):
    lock = bucket.blob(LOCK_NAME)
    try:
        owner = lock.download_as_text()
        if owner == OWNER:
            lock.delete(if_generation_match=lock.generation)
            print("✓ Released data lock")
    except (NotFound, PreconditionFailed):
        pass


def download(bucket):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {}
    count = 0
    for blob in bucket.list_blobs():
        if blob.name.endswith("/") or blob.name.startswith("_locks/"):
            continue
        dest = DATA_DIR / blob.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(dest))
        manifest[blob.name] = md5(dest)
        count += 1
    MANIFEST.write_text(json.dumps(manifest))
    print(f"✓ Downloaded {count} object(s) from gs://{bucket.name} to {DATA_DIR}")


def upload(bucket):
    if not DATA_DIR.exists():
        print(f"{DATA_DIR} does not exist, nothing to upload")
        return
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    changed = 0
    for path in DATA_DIR.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(DATA_DIR).as_posix()
        if manifest.get(rel) == md5(path):
            continue
        bucket.blob(rel).upload_from_filename(str(path))
        changed += 1
        print(f"  uploaded {rel}")
    print(f"✓ Uploaded {changed} changed object(s) to gs://{bucket.name}")


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--download", action="store_true")
    group.add_argument("--upload", action="store_true")
    group.add_argument("--release", action="store_true")
    args = parser.parse_args()

    bucket = get_bucket()
    if bucket is None:
        return 0

    if args.download:
        acquire_lock(bucket)
        try:
            download(bucket)
        except BaseException:
            release_lock(bucket)
            raise
    elif args.upload:
        upload(bucket)
    else:
        release_lock(bucket)
    return 0


if __name__ == "__main__":
    sys.exit(main())
