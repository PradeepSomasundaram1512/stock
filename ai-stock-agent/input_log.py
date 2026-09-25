"""
Full-input log of every analysed candidate: the exact technical/fundamental/news/market-context/RAG inputs the model saw.

The llm_decisions table keeps a flat summary (RSI, scores, sentiment), which is not enough to REPLAY a call. Replaying with parts of the
input removed (ablation) needs the real inputs, so they are appended here, one gzip'd JSON line per candidate, one file per UTC day:

    data/inputs/YYYY-MM-DD.jsonl.gz      {"scan_id","ticker","decided_at","inputs":{...}}

Files are append-only and small (the state sync uploads only the day's file), so backtest.db does not grow.
    python input_log.py summary [file]    print counts and sizes
"""
import gzip
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

DATA = Path(__file__).parent / "data"
KEYS = ("features", "rag_context", "fundamentals", "news_analysis", "market_context")


def _default(o):
    """numpy/pandas scalars and anything else non-JSON become plain numbers/strings instead of breaking the scan."""
    try:
        return o.item()
    except Exception:            # noqa: BLE001
        return str(o)


def append(scan_id: str, results: list, data_dir: Path = DATA, now: datetime = None) -> int:
    """Append one line per candidate; returns the number written. Never raises into the caller's scan."""
    now = now or datetime.now(timezone.utc)
    path = Path(data_dir) / "inputs" / f"{now.strftime('%Y-%m-%d')}.jsonl.gz"
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with gzip.open(path, "ab") as f:                       # gzip members concatenate, so appending across runs is safe
        for r in results or []:
            if not r or not r.get("ticker"):
                continue
            row = {"scan_id": scan_id, "ticker": r["ticker"], "decided_at": now.replace(tzinfo=None).isoformat(),
                   "inputs": {k: r.get(k) for k in KEYS}}
            f.write((json.dumps(row, default=_default, separators=(",", ":")) + "\n").encode())
            n += 1
    return n


def read(path) -> list:
    with gzip.open(path, "rb") as f:
        return [json.loads(line) for line in f if line.strip()]


def read_all(data_dir: Path = DATA) -> list:
    out = []
    for p in sorted((Path(data_dir) / "inputs").glob("*.jsonl.gz")):
        out += read(p)
    return out


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "summary":
        files = [Path(sys.argv[2])] if len(sys.argv) > 2 else sorted((DATA / "inputs").glob("*.jsonl.gz"))
        for p in files:
            rows = read(p)
            print(f"{p.name}: {len(rows)} candidates, {len({r['scan_id'] for r in rows})} scans, {p.stat().st_size / 1024:.0f} KB")
    else:
        sys.exit(__doc__)
