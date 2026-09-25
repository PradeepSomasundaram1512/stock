"""
Read-only dashboard for the scanner's state. Serves one page (index.html) and a few JSON
endpoints computed from the same files the scheduled jobs write to the GCS bucket:

    /api/summary   today's health, spend, totals
    /api/latest    candidates of the latest scan: production vs shadow decision
    /api/history   per-day model health and BUY counts
    /api/paper     paper-trading account and swing trades
    /api/context   freshness of the last scan, VIX/SPY, model spend vs. budget
    /api/scans     list of recent scans;  /api/latest?scan=ID  one scan's candidates
    /api/tickers   tickers seen;  /api/ticker?t=XYZ  one ticker's decision history
    /api/arena     production vs. shadow model: agreement, disagreements, moves since
    /api/scoreboard  forward-audit results (static, from scoreboard.json) + live outcomes

It only ever READS (its service account has objectViewer on the bucket), so it cannot
corrupt trading state. Files are re-downloaded at most every CACHE_TTL seconds.
Access is invite-only Google sign-in implemented in auth.py (the service itself is publicly
reachable, so EVERY page and API route except /healthz checks the session first).

Env: DATA_BUCKET (required), PORT (default 8080), CACHE_TTL (default 120)
     DATA_DIR (optional): read local files instead of the bucket, for development.
"""
import json
import os
import sqlite3
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo
from datetime import datetime, timezone

HERE = Path(__file__).parent
import sys
sys.path.insert(0, str(HERE))
import auth
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


def latest(q=None) -> dict:
    con = db()
    want = (q or {}).get("scan")
    scan = (con.execute("select scan_id, max(decided_at) t from llm_decisions where scan_id=?", (want,)).fetchone()
            if want else con.execute("select scan_id, max(decided_at) t from llm_decisions").fetchone())
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


_PRICES: dict = {}          # ticker -> (fetched_at, {"price":..., "prev":...})
PRICE_TTL = 60


def _meta(t: str, ttl: int = PRICE_TTL):
    """Last price and previous close from Yahoo's public chart endpoint; None if unavailable."""
    hit = _PRICES.get(t)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    try:
        from urllib.parse import quote
        req = urllib.request.Request(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(t)}?range=1d&interval=1d",
            headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            m = json.load(r)["chart"]["result"][0]["meta"]
        val = {"price": m["regularMarketPrice"], "prev": m.get("chartPreviousClose") or m.get("previousClose")}
    except Exception:                                   # noqa: BLE001 - a missing quote must not break the page
        return hit[1] if hit else None
    _PRICES[t] = (time.time(), val)
    return val


def _quote(t: str, ttl: int = PRICE_TTL):
    m = _meta(t, ttl)
    return m["price"] if m else None


def marks(tickers, ttl: int = PRICE_TTL) -> dict:
    tickers = sorted(set(tickers))
    with ThreadPoolExecutor(max_workers=8) as pool:
        return dict(zip(tickers, pool.map(lambda t: _quote(t, ttl), tickers)))


def paper() -> dict:
    out = {}
    for key, name in (("paper", "paper_trades.json"), ("swing", "swing_trades.json")):
        f = CACHE / name
        out[key] = json.loads(f.read_text()) if f.exists() else None
    p, sw = out["paper"], out["swing"]
    open_sw = list((sw or {}).get("open_trades", {}))
    px = marks(list((p or {}).get("positions", {})) + open_sw)
    out["marks"] = px
    if p:
        invested = sum(v.get("total_cost", 0) for v in p.get("positions", {}).values())
        market = sum(v["shares"] * (px.get(t) or v["avg_price"]) for t, v in p.get("positions", {}).items())
        out["paper_summary"] = {"starting": p["starting_balance"], "cash": p["cash"], "invested_at_cost": invested,
                                "market_value": market, "equity": p["cash"] + market,
                                "pnl": p["cash"] + market - p["starting_balance"],
                                "all_marked": all(px.get(t) for t in p.get("positions", {})),
                                "updated": p.get("last_updated")}
    return out


MODEL_PRICES = {"gpt-4o-mini": (0.15, 0.60)}       # USD per 1M tokens (in, out): production model
ET = ZoneInfo("America/New_York")


def _market_open(now=None) -> bool:
    n = (now or datetime.now(ET)).astimezone(ET)
    return n.weekday() < 5 and (9, 30) <= (n.hour, n.minute) < (16, 0)


def context(q=None) -> dict:
    con = db()
    out = {"market_open": _market_open()}
    last = con.execute("select max(decided_at) from llm_decisions").fetchone()[0]
    if last:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(last).replace(tzinfo=timezone.utc)).total_seconds() / 60
        out.update(last_scan_at=last, age_min=round(age), stale=bool(out["market_open"] and age > 90))
    for key, sym in (("spy", "SPY"), ("vix", "^VIX")):
        m = _meta(sym)
        out[key] = ({"price": m["price"], "chg": (m["price"] / m["prev"] - 1) if m.get("prev") else None} if m else None)
    r = con.execute("select market_trend from recommendations where market_trend is not null "
                    "order by recommendation_date desc limit 1").fetchone()
    out["trend"] = r[0] if r else None
    # model spend: shadow cost is logged; production cost is estimated from logged tokens
    month = (last or datetime.utcnow().isoformat())[:7]
    day = (last or "")[:10]
    prod = lambda like: sum(
        (ti or 0) * MODEL_PRICES.get(m, (0.15, 0.60))[0] / 1e6 + (to or 0) * MODEL_PRICES.get(m, (0.15, 0.60))[1] / 1e6
        for m, ti, to in con.execute(
            "select model, sum(tokens_in), sum(tokens_out) from llm_decisions where decided_at like ? group by model", (like,)))
    cost = {"prod_today": prod(day + "%"), "prod_month": prod(month + "%"), "budget": float(os.environ.get("SHADOW_DAILY_BUDGET_USD", "0.25"))}
    if _table_exists(con, "shadow_decisions"):
        sc = lambda like: con.execute("select coalesce(sum(est_cost_usd),0) from shadow_decisions where decided_at like ?", (like,)).fetchone()[0]
        cost.update(shadow_today=sc(day + "%"), shadow_month=sc(month + "%"), shadow_total=sc("%"))
    out["cost"] = cost
    return out


def scans(q=None) -> dict:
    con = db()
    return {"scans": rows(con,
        "select scan_id, max(decided_at) at, count(*) n, sum(raw_decision='BUY') buys, sum(llm_status!='ok') failed, "
        "sum(in_signal_list=1) listed from llm_decisions group by scan_id order by at desc limit 80")}


def tickers(q=None) -> dict:
    con = db()
    return {"tickers": sorted({r[0] for r in con.execute(
        "select distinct ticker from llm_decisions union select distinct ticker from recommendations")})}


def ticker(q=None) -> dict:
    t = ((q or {}).get("t") or "").upper().strip()
    con = db()
    dec = rows(con,
        "select p.decided_at, p.raw_decision decision, p.raw_confidence confidence, p.final_decision final, p.price, p.rsi, "
        "p.reasoning, s.decision shadow_decision, s.confidence shadow_confidence "
        "from llm_decisions p left join shadow_decisions s on s.scan_id=p.scan_id and s.ticker=p.ticker "
        "where p.ticker=? order by p.decided_at desc limit 60", t)
    recs = rows(con,
        "select recommendation_date date, decision, confidence, entry_price, price_target, stop_loss, outcome, "
        "profit_loss_pct, exit_reason, scan_type from recommendations where ticker=? order by recommendation_date desc limit 40", t)
    m = _meta(t) if t else None
    return {"ticker": t, "last": m["price"] if m else None, "decisions": dec, "recommendations": recs}


def arena(q=None) -> dict:
    con = db()
    if not _table_exists(con, "shadow_decisions"):
        return {"n": 0}
    j = rows(con,
        "select p.scan_id, p.decided_at at, p.ticker, p.raw_decision prod, p.raw_confidence prod_conf, p.price, "
        "s.decision shadow, s.confidence shadow_conf, s.shadow_model model "
        "from shadow_decisions s join llm_decisions p on p.scan_id=s.scan_id and p.ticker=s.ticker "
        "where s.llm_status='ok' and p.llm_status='ok' order by p.decided_at desc")
    n = len(j)
    out = {"n": n, "model": j[0]["model"] if j else None}
    if not n:
        return out
    out["agree"] = sum(1 for r in j if r["prod"] == r["shadow"]) / n
    cross = {}
    for r in j:
        cross.setdefault(r["prod"], {}).setdefault(r["shadow"], 0)
        cross[r["prod"]][r["shadow"]] += 1
    out["crosstab"] = cross
    out["buy_rate"] = {"prod": sum(r["prod"] == "BUY" for r in j) / n, "shadow": sum(r["shadow"] == "BUY" for r in j) / n}
    out["mean_conf"] = {"prod": sum(r["prod_conf"] or 0 for r in j) / n, "shadow": sum(r["shadow_conf"] or 0 for r in j) / n}
    dis = [r for r in j if r["prod"] != r["shadow"]]
    # move since the decision (price at decision -> last price): unmatured, so treat as early evidence only
    tick = sorted({r["ticker"] for r in j if r["prod"] == "BUY" or r["shadow"] == "BUY"})[:80]
    px = marks(tick, ttl=600)
    move = lambda r: (px.get(r["ticker"]) / r["price"] - 1) if px.get(r["ticker"]) and r["price"] else None
    for r in j:
        r["move"] = move(r)
    for side in ("prod", "shadow"):
        mv = [r["move"] for r in j if r[side] == "BUY" and r["move"] is not None]
        out[f"{side}_buy_move"] = {"n": len(mv), "mean": sum(mv) / len(mv) if mv else None}
    out["disagreements"] = [{k: r[k] for k in ("at", "ticker", "prod", "shadow", "prod_conf", "shadow_conf", "price", "move")}
                            for r in dis[:60]]
    out["n_disagree"] = len(dis)
    return out


def scoreboard(q=None) -> dict:
    f = HERE / "scoreboard.json"
    out = {"audit": json.loads(f.read_text()) if f.exists() else None}
    con = db()
    live = rows(con,
        "select outcome, count(*) n, avg(profit_loss_pct) avg_pl from recommendations "
        "where decision='BUY' and outcome is not null group by outcome")
    tot = sum(r["n"] for r in live)
    out["live"] = {"by_outcome": live, "n": tot,
                   "win_rate": (sum(r["n"] for r in live if r["outcome"] == "WIN") / tot) if tot else None}
    return out


ROUTES = {"/api/summary": summary, "/api/latest": latest, "/api/history": history, "/api/paper": paper,
          "/api/context": context, "/api/scans": scans, "/api/tickers": tickers, "/api/ticker": ticker,
          "/api/arena": arena, "/api/scoreboard": scoreboard}


DEV_NO_AUTH = os.environ.get("DASHBOARD_DEV_NO_AUTH") == "1" and bool(os.environ.get("DATA_DIR"))   # local only


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body: bytes, ctype: str, headers=()):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, obj, headers=()):
        self._send(code, json.dumps(obj, default=str).encode(), "application/json", headers)

    def _email(self):
        """Signed-in, still-invited email for this request, or None."""
        if DEV_NO_AUTH:
            return "dev@localhost"
        try:
            return auth.read_session(auth.token_from_cookie(self.headers.get("Cookie", "")), auth.allowed_emails())
        except RuntimeError:                       # SESSION_SECRET missing: fail closed
            return None

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/auth/logout":
            return self._json(200, {"ok": True}, [("Set-Cookie", auth.cookie_header("", 0))])
        if path != "/auth/login":
            return self._send(404, b"not found", "text/plain")
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if not 0 < n <= 8192:
                return self._json(400, {"error": "bad request"})
            cred = json.loads(self.rfile.read(n)).get("credential", "")
        except Exception:                          # noqa: BLE001
            return self._json(400, {"error": "bad request"})
        email = auth.verify_google(cred)
        if not email:
            return self._json(401, {"error": "could not verify the Google sign-in"})
        if email not in auth.allowed_emails():
            print(f"auth: refused sign-in from a non-invited account", flush=True)
            return self._json(403, {"error": "not invited"})
        try:
            token = auth.sign_session(email)
        except RuntimeError:
            return self._json(500, {"error": "server not configured"})
        print(f"auth: signed in {email}", flush=True)
        self._json(200, {"ok": True}, [("Set-Cookie", auth.cookie_header(token))])

    def do_GET(self):
        u = urlparse(self.path)
        path, query = u.path, {k: v[0] for k, v in parse_qs(u.query).items()}
        if path == "/healthz":
            return self._send(200, b"ok", "text/plain")
        me = self._email()
        if path in ("/", "/index.html"):
            if me:
                return self._send(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
            page = (HERE / "login.html").read_text().replace("__CLIENT_ID__", os.environ.get("GOOGLE_CLIENT_ID", ""))
            return self._send(200, page.encode(), "text/html; charset=utf-8")
        if not me:
            return self._json(401, {"error": "sign in required"})
        if path == "/api/me":
            return self._json(200, {"email": me})
        fn = ROUTES.get(path)
        if not fn:
            return self._send(404, b"not found", "text/plain")
        try:
            refresh()
            self._json(200, fn(query) if fn.__code__.co_argcount else fn())
        except Exception as e:                       # noqa: BLE001 - report, never crash the server
            self._json(500, {"error": f"{type(e).__name__}: {e}"})

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} {fmt % args}", flush=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    print(f"dashboard listening on :{port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
