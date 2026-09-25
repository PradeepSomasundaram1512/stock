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
    /api/pulse     cheap live poll: market session, next scans, last scan, position prices
    /api/quotes?t=A,B  batch quotes;  /api/chart?t=X&range=6mo  candles + the model's calls
    /api/heatmap   whole-universe snapshot by sector (from market_snapshot.json)
    /api/scoreboard  forward-audit results (static, from scoreboard.json) + live outcomes

PUBLIC (no sign-in; an explicit allowlist, aggregate/delayed data only, never the live decision database):
    /public  /api/public  /public/chain.json  /public/revealed.csv  /public/verify_chain.py  /charts.js

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
import market_clock
CACHE = Path(os.environ.get("DATA_DIR") or "/tmp/dashboard-data")
CACHE_TTL = int(os.environ.get("CACHE_TTL", "60"))
FILES = ("backtest.db", "paper_trades.json", "swing_trades.json", "forward_test.json",
         "track_record_chain.json", "public_revealed.csv", "market_snapshot.json", "scan_universe.json")
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


def _latest_scan_id(con):
    r = con.execute("select scan_id from llm_decisions order by decided_at desc limit 1").fetchone()
    return r[0] if r else None


def summary() -> dict:
    """Describes the most recent scan only (never a whole day or several scans added together)."""
    con = db()
    sid = _latest_scan_id(con)
    out = {"as_of": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(_fetched or time.time())), "scan_id": sid}
    if sid:
        out["scan"] = dict(con.execute(
            "select max(decided_at) at, count(*) decisions, sum(llm_status='ok') ok, sum(llm_status='fallback_error') fallbacks, "
            "sum(raw_decision='BUY' and llm_status='ok') buys, sum(in_signal_list=1) signals from llm_decisions where scan_id=?", (sid,)).fetchone())
        if _table_exists(con, "shadow_decisions"):
            out["shadow_scan"] = dict(con.execute(
                "select count(*) n, sum(s.llm_status='ok') ok, coalesce(sum(s.est_cost_usd),0) cost, "
                "sum(s.llm_status='ok' and p.llm_status='ok' and s.decision=p.raw_decision) agree, "
                "sum(s.llm_status='ok' and p.llm_status='ok') both "
                "from shadow_decisions s left join llm_decisions p on p.scan_id=s.scan_id and p.ticker=s.ticker where s.scan_id=?", (sid,)).fetchone())
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


TICKER_RE = __import__("re").compile(r"^[A-Z0-9.\-^]{1,10}$")


def _clean_tickers(raw: str, limit: int = 40) -> list:
    out = []
    for t in (raw or "").upper().split(","):
        t = t.strip()
        if TICKER_RE.match(t) and t not in out:
            out.append(t)
    return out[:limit]


def pulse(q=None) -> dict:
    """Cheap poll for the live feel: market session, next scheduled runs, latest scan, position prices."""
    con = db()
    last = con.execute("select max(decided_at) from llm_decisions").fetchone()[0]
    day = (last or "")[:10]
    scans_today = con.execute("select count(distinct scan_id) from llm_decisions where decided_at like ?", (day + "%",)).fetchone()[0] if last else 0
    held = []
    for name, key in (("paper_trades.json", "positions"), ("swing_trades.json", "open_trades")):
        f = CACHE / name
        if f.exists():
            held += list((json.loads(f.read_text()).get(key) or {}))
    px = marks(held + ["SPY", "^VIX"], ttl=15)
    metas = {t: _meta(t, 15) for t in set(held) | {"SPY", "^VIX"}}
    return {"now": datetime.now(timezone.utc).isoformat(timespec="seconds"), "session": market_clock.session(),
            "next": market_clock.next_events(limit=4), "last_scan_at": last, "scans_today": scans_today,
            "marks": {t: ({"price": m["price"], "prev": m.get("prev")} if m else None) for t, m in metas.items()}}


def quotes(q=None) -> dict:
    ts = _clean_tickers((q or {}).get("t", ""))
    with ThreadPoolExecutor(max_workers=8) as pool:
        metas = dict(zip(ts, pool.map(lambda t: _meta(t, 15), ts)))
    return {"quotes": {t: ({"price": m["price"], "prev": m.get("prev")} if m else None) for t, m in metas.items()}}


_CHARTS: dict = {}          # (ticker, range) -> (fetched_at, candles)
RANGES = {"5d": "15m", "1mo": "60m", "3mo": "1d", "6mo": "1d", "1y": "1d"}


def _candles(t: str, rng: str):
    hit = _CHARTS.get((t, rng))
    if hit and time.time() - hit[0] < 300:
        return hit[1]
    from urllib.parse import quote
    try:
        req = urllib.request.Request(f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(t)}?range={rng}&interval={RANGES[rng]}",
                                     headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            res = json.load(r)["chart"]["result"][0]
        q0 = res["indicators"]["quote"][0]
        rows = [[ts * 1000, o, h, l, c, v] for ts, o, h, l, c, v in zip(res["timestamp"], q0["open"], q0["high"], q0["low"], q0["close"], q0["volume"])
                if None not in (o, h, l, c)]
    except Exception:                                   # noqa: BLE001 - a missing chart must not break the page
        return hit[1] if hit else None
    _CHARTS[(t, rng)] = (time.time(), rows)
    return rows


def chart(q=None) -> dict:
    q = q or {}
    t = (_clean_tickers(q.get("t", ""), 1) or [""])[0]
    rng = q.get("range", "6mo")
    if not t or rng not in RANGES:
        return {"error": "bad ticker or range"}
    con = db()
    out = {"ticker": t, "range": rng, "interval": RANGES[rng], "candles": _candles(t, rng) or []}
    if q.get("cmp") == "1":
        out["spy"] = _candles("SPY", rng) or []
    start = (out["candles"][0][0] / 1000) if out["candles"] else 0
    from datetime import datetime as _dt
    since = _dt.utcfromtimestamp(start).strftime("%Y-%m-%d") if start else "1970-01-01"
    out["recommendations"] = rows(con,
        "select recommendation_date at, decision, confidence, entry_price, price_target, stop_loss, outcome, exit_date, exit_price "
        "from recommendations where ticker=? and recommendation_date>=? order by recommendation_date", t, since)
    out["decisions"] = rows(con,
        "select scan_id, decided_at at, raw_decision decision, raw_confidence confidence, price, price_target, stop_loss from llm_decisions "
        "where ticker=? and decided_at>=? order by decided_at", t, since)
    out["latest_scan_id"] = _latest_scan_id(con)
    m = _meta(t)
    out["last"] = m["price"] if m else None
    return out


def heatmap(q=None) -> dict:
    snap_f, sec_f = CACHE / "market_snapshot.json", HERE / "sectors.json"
    if not snap_f.exists():
        return {"stocks": [], "sectors": [], "note": "No snapshot yet: it is written every 30 minutes while the market is open."}
    snap = json.loads(snap_f.read_text())
    uni_f = CACHE / "scan_universe.json"       # refreshed weekly with the universe; the static file is the fallback
    sectors = (json.loads(uni_f.read_text()).get("sectors") if uni_f.exists() else None) or (json.loads(sec_f.read_text()) if sec_f.exists() else {})
    con = db()
    latest = con.execute("select scan_id from llm_decisions order by decided_at desc limit 1").fetchone()
    called = ({r[0]: r[1] for r in con.execute("select ticker, raw_decision from llm_decisions where scan_id=?", (latest[0],))} if latest else {})
    stocks = [{"t": t, "sector": sectors.get(t, "Other"), "p": v["p"], "c": v["c"], "c5": v["c5"], "rsi": v["rsi"], "dv": v["dv"],
               "analysed": t in called, "call": called.get(t)} for t, v in snap["stocks"].items()]
    agg = {}
    for x in stocks:
        a = agg.setdefault(x["sector"], {"name": x["sector"], "n": 0, "c": 0.0, "c5": 0.0})
        a["n"] += 1
        a["c"] += x["c"]
        a["c5"] += x["c5"]
    secs = sorted(({"name": a["name"], "n": a["n"], "c": a["c"] / a["n"], "c5": a["c5"] / a["n"]} for a in agg.values()), key=lambda a: -a["c"])
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(snap["asof"])).total_seconds() / 60
    return {"asof": snap["asof"], "age_min": round(age), "n": snap["n"], "stocks": stocks, "sectors": secs}


def _wilson(k: int, n: int, z: float = 1.96):
    """95% Wilson score interval for a proportion (well behaved for small n and rates near 0 or 1)."""
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return max(0.0, c - h), min(1.0, c + h)


def _cohort(con, sql: str, args: tuple) -> dict:
    r = con.execute("select count(*), sum(outcome='WIN'), avg(profit_loss_pct) from recommendations where outcome is not null and " + sql, args).fetchone()
    n, wins = r[0] or 0, r[1] or 0
    ci = _wilson(wins, n)
    return {"n": n, "win_rate": (wins / n) if n else None, "lo": ci[0] if ci else None, "hi": ci[1] if ci else None, "avg_pl": r[2]}


MIN_COHORT = 20


def similar(q=None) -> dict:
    """How did past calls like this one turn out? Built only from the logged history (as-deployed exit outcomes, not a forecast)."""
    t = ((q or {}).get("t") or "").upper().strip()
    con = db()
    cur = con.execute("select raw_decision, raw_confidence, rsi, trend, decided_at from llm_decisions where ticker=? order by decided_at desc limit 1", (t,)).fetchone()
    if not cur or not cur["raw_decision"]:
        return {"available": False, "reason": "no logged call for this ticker"}
    dec, conf, rsi, trend = cur["raw_decision"], cur["raw_confidence"], cur["rsi"], cur["trend"]
    out = {"available": True, "decision": dec, "confidence": conf, "rsi": rsi, "trend": trend, "min_n": MIN_COHORT,
           "all_same_decision": _cohort(con, "decision=?", (dec,))}
    if rsi is not None:
        args = [dec, rsi - 8, rsi + 8]
        sql = "decision=? and rsi between ? and ?"
        if trend:
            sql, args = sql + " and trend=?", args + [trend]
        out["similar"] = dict(_cohort(con, sql, tuple(args)), rsi_range=[round(rsi - 8), round(rsi + 8)], trend=trend)
    if conf is not None:
        out["same_confidence"] = dict(_cohort(con, "decision=? and confidence between ? and ?", (dec, conf - 0.05, conf + 0.05)), range=[round(conf - 0.05, 2), round(conf + 0.05, 2)])
    f = HERE / "scoreboard.json"
    if f.exists():
        sp = json.loads(f.read_text()).get("calibration", {}).get("spearman")
        if sp:
            out["confidence_informative"] = not (sp["lo"] <= 0 <= sp["hi"])      # False = confidence has not predicted outcomes
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
    sid = _latest_scan_id(con)
    newest = rows(con,
        "select p.scan_id, p.decided_at at, p.raw_decision decision, p.raw_confidence confidence, p.final_decision final, p.price, "
        "p.price_target, p.stop_loss, p.reasoning, s.decision shadow_decision, s.confidence shadow_confidence "
        "from llm_decisions p left join shadow_decisions s on s.scan_id=p.scan_id and s.ticker=p.ticker "
        "where p.ticker=? order by p.decided_at desc limit 1", t)
    call = dict(newest[0], in_latest_scan=(newest[0]["scan_id"] == sid)) if newest else None
    return {"ticker": t, "last": m["price"] if m else None, "latest_call": call, "latest_scan_id": sid,
            "decisions": dec, "recommendations": recs}


def arena(q=None) -> dict:
    con = db()
    if not _table_exists(con, "shadow_decisions"):
        return {"n": 0}
    j = rows(con,
        "select p.scan_id, p.decided_at at, p.ticker, p.raw_decision prod, p.raw_confidence prod_conf, p.price, "
        "s.decision shadow, s.confidence shadow_conf, s.shadow_model model "
        "from shadow_decisions s join llm_decisions p on p.scan_id=s.scan_id and p.ticker=s.ticker "
        "where s.llm_status='ok' and p.llm_status='ok' order by p.decided_at desc")
    scope = "all" if (q or {}).get("scope") == "all" else "latest"        # default: only the latest scan
    sid = _latest_scan_id(con)
    if scope == "latest":
        j = [r for r in j if r["scan_id"] == sid]
    n = len(j)
    out = {"n": n, "model": j[0]["model"] if j else None, "scope": scope, "scan_id": sid, "scan_at": j[0]["at"] if j else None}
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
    ft = CACHE / "forward_test.json"           # written weekly by the forward-test job
    out["forward"] = (json.loads(ft.read_text()) or [None])[0] if ft.exists() else None
    out["forward_needs"] = {"signals": 300, "blocks": 20}
    con = db()
    live = rows(con,
        "select outcome, count(*) n, avg(profit_loss_pct) avg_pl from recommendations "
        "where decision='BUY' and outcome is not null group by outcome")
    tot = sum(r["n"] for r in live)
    out["live"] = {"by_outcome": live, "n": tot,
                   "win_rate": (sum(r["n"] for r in live if r["outcome"] == "WIN") / tot) if tot else None}
    return out


def public(q=None) -> dict:
    """Everything the world-readable page shows: audited aggregates, forward-test progress, chain status.
    Deliberately reads NO row from the live decision tables, so it can never leak a current signal."""
    out = {"audit": json.loads((HERE / "scoreboard.json").read_text()) if (HERE / "scoreboard.json").exists() else None}
    ft = CACHE / "forward_test.json"
    out["forward"] = (json.loads(ft.read_text()) or [None])[0] if ft.exists() else None
    out["forward_needs"] = {"signals": 300, "blocks": 20}
    ch = CACHE / "track_record_chain.json"
    chain = json.loads(ch.read_text()) if ch.exists() else []
    out["chain"] = {"days": len(chain), "first": chain[0]["day"] if chain else None, "last": chain[-1]["day"] if chain else None,
                    "head": chain[-1]["hash"] if chain else None, "rows": sum(e["n"] for e in chain)}
    rv = CACHE / "public_revealed.csv"
    out["revealed_rows"] = max(0, rv.read_text().count("\n") - 1) if rv.exists() else 0
    return out


ROUTES = {"/api/summary": summary, "/api/latest": latest, "/api/history": history, "/api/paper": paper,
          "/api/context": context, "/api/scans": scans, "/api/tickers": tickers, "/api/ticker": ticker,
          "/api/arena": arena, "/api/scoreboard": scoreboard,
          "/api/similar": similar, "/api/pulse": pulse, "/api/quotes": quotes, "/api/chart": chart, "/api/heatmap": heatmap}
PUBLIC_ROUTES = {"/api/public": public}
PUBLIC_FILES = {"/manifest.webmanifest": ("manifest.webmanifest", "application/manifest+json"),
                "/apple-touch-icon.png": ("icon-180.png", "image/png"), "/icon-192.png": ("icon-192.png", "image/png"), "/icon-512.png": ("icon-512.png", "image/png"),
                "/public": ("public.html", "text/html; charset=utf-8"), "/charts.js": ("charts.js", "application/javascript"), "/live.js": ("live.js", "application/javascript"),
                "/public/verify_chain.py": ("verify_chain.py", "text/x-python; charset=utf-8")}
PUBLIC_CACHE_FILES = {"/public/chain.json": ("track_record_chain.json", "application/json"), "/public/revealed.csv": ("public_revealed.csv", "text/csv; charset=utf-8")}


LOGIN_LIMIT = auth.RateLimiter(limit=10, window=300)     # sign-in attempts per address per 5 minutes
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
        self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
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
        if path in ("/auth/login", "/auth/google"):
            ip = auth.client_ip(self.headers.get("X-Forwarded-For", ""), self.client_address[0])
            if not LOGIN_LIMIT.allow(ip):
                print("auth: rate limit hit", flush=True)
                return self._send(429, b"too many attempts, try again in a few minutes", "text/plain", [("Retry-After", "300")])
        if path == "/auth/logout":
            return self._json(200, {"ok": True}, [("Set-Cookie", auth.cookie_header("", 0))])
        if path == "/auth/google":
            return self._google_redirect_login()
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

    def _google_redirect_login(self):
        """Sign-in for the iOS Home Screen app (popups are unreliable there): Google POSTs a form with the ID token.
        Google's own CSRF protection applies: the g_csrf_token cookie must equal the g_csrf_token form field."""
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if not 0 < n <= 16384:
                return self._send(400, b"bad request", "text/plain")
            form = {k: v[0] for k, v in parse_qs(self.rfile.read(n).decode()).items()}
        except Exception:                          # noqa: BLE001
            return self._send(400, b"bad request", "text/plain")
        cookies = dict(p.strip().partition("=")[::2] for p in self.headers.get("Cookie", "").split(";") if "=" in p)
        csrf = form.get("g_csrf_token", "")
        if not csrf or csrf != cookies.get("g_csrf_token"):
            return self._send(400, b"bad request", "text/plain")
        email = auth.verify_google(form.get("credential", ""))
        if not email or email not in auth.allowed_emails():
            print("auth: refused redirect sign-in", flush=True)
            return self._send(303, b"", "text/plain", [("Location", "/?denied=1")])
        try:
            token = auth.sign_session(email)
        except RuntimeError:
            return self._send(500, b"server not configured", "text/plain")
        print(f"auth: signed in {email} (redirect)", flush=True)
        self._send(303, b"", "text/plain", [("Location", "/"), ("Set-Cookie", auth.cookie_header(token))])

    def do_GET(self):
        u = urlparse(self.path)
        path, query = u.path, {k: v[0] for k, v in parse_qs(u.query).items()}
        if path == "/healthz":
            return self._send(200, b"ok", "text/plain")
        if path in PUBLIC_FILES:
            name, ctype = PUBLIC_FILES[path]
            try:
                return self._send(200, (HERE / name).read_bytes(), ctype)
            except OSError:
                return self._send(404, b"not found", "text/plain")
        if path in PUBLIC_CACHE_FILES:
            name, ctype = PUBLIC_CACHE_FILES[path]
            try:
                refresh()
                return self._send(200, (CACHE / name).read_bytes(), ctype)
            except Exception:                     # noqa: BLE001 - not published yet
                return self._send(404, b"not published yet", "text/plain")
        if path in PUBLIC_ROUTES:
            try:
                refresh()
                return self._json(200, PUBLIC_ROUTES[path]())
            except Exception as e:                # noqa: BLE001
                return self._json(500, {"error": f"{type(e).__name__}"})
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
