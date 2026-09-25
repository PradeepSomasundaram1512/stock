"""
Tamper-evident track record.

Each completed day's model decisions are reduced to a SHA-256 digest and chained:

    hash_n = sha256(hash_{n-1} | day | digest | n_rows)

The chain (hashes only, no tickers) is public and its newest hash is posted daily to Discord, an outside
timestamp. Raw decisions are revealed only REVEAL_AFTER_DAYS later, so the page never becomes a live
signal feed, yet anyone can later recompute every digest from the revealed rows and confirm the history was
never rewritten: editing any past decision changes that day's digest and every hash after it.

    python track_record.py update [db] [chain.json] [revealed.csv]   (run daily by daily_digest.py)
    python track_record.py verify chain.json [revealed.csv]          (anyone can run this; stdlib only)

Limits, stated plainly: the chain proves decisions were not altered after being committed, not that they
were committed before the outcome was known unless the timestamps are checked against the outside anchor
(the Discord posts). It also cannot show that no decision was left out at commit time.
"""
import csv
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REVEAL_AFTER_DAYS = 45
GENESIS = "0" * 64
FIELDS = ("scan_id", "decided_at", "ticker", "decision", "confidence")


def _line(scan_id, decided_at, ticker, decision, confidence) -> str:
    conf = "" if confidence in (None, "") else f"{float(confidence):.4f}"   # "" = missing (as read back from the CSV)
    return "|".join(str(x) for x in (scan_id, decided_at, ticker, decision or "", conf))


def day_digest(lines: list) -> str:
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def link(prev: str, day: str, digest: str, n: int) -> str:
    return hashlib.sha256(f"{prev}|{day}|{digest}|{n}".encode()).hexdigest()


def verify_chain(chain: list) -> bool:
    prev = GENESIS
    for e in chain:
        if e["prev"] != prev or e["hash"] != link(prev, e["day"], e["digest"], e["n"]):
            return False
        prev = e["hash"]
    return True


def day_rows(con, day: str) -> list:
    return con.execute(
        "select scan_id, decided_at, ticker, raw_decision, raw_confidence from llm_decisions "
        "where decided_at like ? order by decided_at, ticker, scan_id", (day + "%",)).fetchall()


def update(db, chain_path, revealed_path, today: str = None) -> dict:
    """Commit every completed day (strictly before `today`, UTC) not yet in the chain; refresh the reveal file."""
    today = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    chain_path, revealed_path = Path(chain_path), Path(revealed_path)
    chain = json.loads(chain_path.read_text()) if chain_path.exists() else []
    if not verify_chain(chain):
        raise RuntimeError("the stored chain does not verify: it was modified after being written")
    con = sqlite3.connect(db)
    done = {e["day"] for e in chain}
    days = [r[0] for r in con.execute(
        "select distinct substr(decided_at,1,10) d from llm_decisions where d < ? order by d", (today,)) if r[0] not in done]
    prev = chain[-1]["hash"] if chain else GENESIS
    for day in days:
        rows = day_rows(con, day)
        digest = day_digest([_line(*r) for r in rows])
        h = link(prev, day, digest, len(rows))
        chain.append({"day": day, "n": len(rows), "digest": digest, "prev": prev, "hash": h})
        prev = h
    chain_path.write_text(json.dumps(chain, indent=1))
    cutoff = (datetime.strptime(today, "%Y-%m-%d") - timedelta(days=REVEAL_AFTER_DAYS)).strftime("%Y-%m-%d")
    n_rev = 0
    with revealed_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(("day",) + FIELDS)
        for e in chain:
            if e["day"] <= cutoff:
                for r in day_rows(con, e["day"]):
                    w.writerow((e["day"], r[0], r[1], r[2], r[3], "" if r[4] is None else f"{float(r[4]):.4f}"))
                    n_rev += 1
    return {"days": len(chain), "new_days": len(days), "head": prev, "revealed_rows": n_rev,
            "first": chain[0]["day"] if chain else None, "last": chain[-1]["day"] if chain else None}


def verify(chain_path, revealed_path=None) -> dict:
    """Recompute the chain and, if given, every revealed day's digest from its rows."""
    chain = json.loads(Path(chain_path).read_text())
    out = {"chain_ok": verify_chain(chain), "days": len(chain), "revealed_days_checked": 0, "revealed_ok": True}
    if revealed_path and Path(revealed_path).exists():
        by_day = {}
        with open(revealed_path, newline="") as f:
            for r in csv.DictReader(f):
                by_day.setdefault(r["day"], []).append(_line(*(r[k] for k in FIELDS)))
        entries = {e["day"]: e for e in chain}
        for day, lines in by_day.items():
            e = entries.get(day)
            out["revealed_days_checked"] += 1
            if e is None or e["n"] != len(lines) or e["digest"] != day_digest(lines):
                out["revealed_ok"] = False
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "update":
        d = Path(__file__).parent / "data"
        print(json.dumps(update(*(sys.argv[2:5] or [d / "backtest.db", d / "track_record_chain.json", d / "public_revealed.csv"])), indent=1))
    elif cmd == "verify" and len(sys.argv) > 2:
        r = verify(*sys.argv[2:4])
        print(json.dumps(r, indent=1))
        sys.exit(0 if r["chain_ok"] and r["revealed_ok"] else 1)
    else:
        sys.exit(__doc__)
