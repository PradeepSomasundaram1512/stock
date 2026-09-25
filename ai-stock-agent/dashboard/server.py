"""
Read-only dashboard for the scanner's state. Serves one page (index.html) and a few JSON
endpoints computed from the same files the scheduled jobs write to the GCS bucket:

    /api/summary   today's health, spend, totals
    /api/latest    candidates of the latest scan: production vs shadow decision
    /api/history   per-day model health and BUY counts
    /api/paper     paper-trading account and swing trades

It only ever READS (its service account has objectViewer on the bucket), so it cannot
corrupt trading state. Files are re-downloaded at most every CACHE_TTL seconds.
Access is controlled by Cloud Run IAM (deployed without public access).

Env: DATA_BUCKET (required), PORT (default 8080), CACHE_TTL (default 120)
     DATA_DIR (optional): read local files instead of the bucket, for development.
"""
import json
import os
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).parent
CACHE = Path(os.environ.get("DATA_DIR") or "/tmp/dashboard-data")
CACHE_TTL = int(os.environ.get("CACHE_TTL", "120"))
FILES = ("backtest.db", "paper_trades.json", "swing_trades.json")
_lock = threading.Lock()
_fetched = 0.0


def refresh() -> None:
    """Download the state files if the local copy is older than CACHE_TTL."""
    global _fetched
    if os.environ.get("DATA_DIR"):
        return
    with _lock:
        if time.time() - _fetched < CACHE_TTL:
            return
        from google.cloud import storage
        bucket = storage.Client().bucket(os.environ["DATA_BUCKET"])
        CACHE.mkdir(parents=True, exist_ok=True)
        for name in FILES:
            blob = bucket.blob(name)
            if blob.exists():
                tmp = CACHE / (name + ".part")
                blob.download_to_filename(str(tmp))
                tmp.replace(CACHE / name)      # never serve a half-written file
        _fetched = time.time()


def db() -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{CACHE / 'backtest.db'}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def rows(con, sql, *args):
    return [dict(r) for r in con.execute(sql, args).fetchall()]


def _table_exists(con, name) -> bool:
    return bool(con.execute("select 1 from sqlite_master where name=?", (name,)).fetchone())


def summary() -> dict:
    con = db()
    day = con.execute("select max(substr(decided_at,1,10)) from llm_decisions").fetchone()[0]
    out = {"day": day, "as_of": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(_fetched or time.time()))}
    if day:
        out["today"] = dict(con.execute(
            "select count(distinct scan_id) scans, count(*) decisions, sum(llm_status='ok') ok, "
            "sum(llm_status='fallback_error') fallbacks, sum(raw_decision='BUY' and llm_status='ok') buys, "
            "sum(in_signal_list=1) signals from llm_decisions where decided_at like ?", (day + "%",)).fetchone())
        if _table_exists(con, "shadow_decisions"):
            out["shadow_today"] = dict(con.execute(
                "select count(*) n, sum(s.llm_status='ok') ok, coalesce(sum(s.est_cost_usd),0) cost, "
                "sum(s.llm_status='ok' and p.llm_status='ok' and s.decision=p.raw_decision) agree, "
                "sum(s.llm_status='ok' and p.llm_status='ok') both "
                "from shadow_decisions s left join llm_decisions p on p.scan_id=s.scan_id and p.ticker=s.ticker "
                "where s.decided_at like ?", (day + "%",)).fetchone())
            out["shadow_total_cost"] = con.execute("select coalesce(sum(est_cost_usd),0) from shadow_decisions").fetchone()[0]
    r = con.execute("select count(*), min(recommendation_date), max(recommendation_date) from recommendations").fetchone()
    out["recommendations"] = {"total": r[0], "first": (r[1] or "")[:10], "last": (r[2] or "")[:10]}
    return out


def latest() -> dict:
    con = db()
    scan = con.execute("select scan_id, max(decided_at) t from llm_decisions").fetchone()
    if not scan or not scan["scan_id"]:
        return {"scan_id": None, "candidates": []}
    cands = rows(con,
        "select p.ticker, p.raw_decision decision, p.raw_confidence confidence, p.llm_status status, "
        "p.in_signal_list in_list, p.final_decision final, p.price, p.rsi, p.trend, p.risk_level, p.price_target, "
        "p.stop_loss, p.reasoning, s.decision shadow_decision, s.confidence shadow_confidence, s.shadow_model "
        "from llm_decisions p left join shadow_decisions s on s.scan_id=p.scan_id and s.ticker=p.ticker "
        "where p.scan_id=? order by p.in_signal_list desc, p.raw_confidence desc", scan["scan_id"])
    return {"scan_id": scan["scan_id"], "at": scan["t"], "candidates": cands}


def history() -> dict:
    con = db()
    health = rows(con,
        "select substr(decided_at,1,10) day, count(*) decisions, sum(llm_status='ok') ok, "
        "sum(llm_status='fallback_error') fallbacks from llm_decisions group by day order by day")
    recs = rows(con,
        "select substr(recommendation_date,1,10) day, count(*) n, sum(decision='BUY') buys "
        "from recommendations group by day order by day")
    return {"health": health, "recommendations": recs}


def paper() -> dict:
    out = {}
    for key, name in (("paper", "paper_trades.json"), ("swing", "swing_trades.json")):
        f = CACHE / name
        out[key] = json.loads(f.read_text()) if f.exists() else None
    p = out["paper"]
    if p:
        invested = sum(v.get("total_cost", 0) for v in p.get("positions", {}).values())
        out["paper_summary"] = {"starting": p["starting_balance"], "cash": p["cash"], "invested_at_cost": invested,
                                "book_value": p["cash"] + invested, "updated": p.get("last_updated")}
    return out


ROUTES = {"/api/summary": summary, "/api/latest": latest, "/api/history": history, "/api/paper": paper}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/healthz":
            return self._send(200, b"ok", "text/plain")
        if path in ("/", "/index.html"):
            return self._send(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
        fn = ROUTES.get(path)
        if not fn:
            return self._send(404, b"not found", "text/plain")
        try:
            refresh()
            self._send(200, json.dumps(fn(), default=str).encode(), "application/json")
        except Exception as e:                       # noqa: BLE001 - report, never crash the server
            self._send(500, json.dumps({"error": f"{type(e).__name__}: {e}"}).encode(), "application/json")

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} {fmt % args}", flush=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    print(f"dashboard listening on :{port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
