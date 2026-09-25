"""
Operational audit, statistical power and rationale audit for the IEEE paper.

Reads the production scanner log and the recommendation database and writes only
generated results (never edit them by hand):

  * decision coverage: how many logged decisions were real LLM outputs versus the
    agent's exception fallback (HOLD at confidence 0.5), by cause and by month;
  * end-to-end analysis latency and API status counts for real decisions;
  * statistical power: minimum detectable effect from the bootstrap SEs in
    paper_results/analysis.json and intraday.json (run paper_analysis.py and
    paper_intraday.py first);
  * a split of the 10-day result by period (Feb--Mar quota outage vs full coverage);
  * lineage and rationale audit: database BUYs traced to logged LLM BUYs, and the
    factors the LLM cited checked against the stored measurements.

Attribution caveat: deep analysis ran tickers in parallel threads, so unlabelled log
lines (fundamentals, news, the bare "DECISION:" line) cannot be assigned to a ticker
by position. Only ticker-labelled lines are used; per-decision news/fundamentals
inputs are deliberately NOT recovered from the log for that reason.

Run:    venv/bin/python paper_ops.py [backtest.db] [scanner.log]
Output: paper_results/ops.json, ops_real_decisions.csv, ops_fallbacks.csv,
        ../../paper/results_ops.tex
"""

import json
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
RES = HERE / "paper_results"
PAPER = HERE.parent / "paper"
DB = Path(sys.argv[1]) if len(sys.argv) > 1 else PAPER / "data/backtest_ec2_2026-01-06_to_2026-09-24.db"
LOG = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "aws-ec2-backup-2026-09-25/logs/scanner.log"

TS = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d),(\d{3}) - (\w+) - (.*)$")
RE_ANALYZ = re.compile(r"^Analyzing ([A-Z0-9.\-]+)\.\.\.$")
RE_FUND = re.compile(r"Fundamentals: Valuation=([\d.]+) Health=([\d.]+) Growth=([\d.]+)")
RE_NEWS = re.compile(r"Found (\d+) news items, sentiment: (\w+)")
RE_MKT = re.compile(r"Market: (\w+), VIX: ([\d.]+)")
RE_LAB = re.compile(r"Autonomous decision for ([A-Z0-9.\-]+): ([A-Z ]+) \(([\d.]+)% confidence\)")
RE_DEC = re.compile(r"DECISION: ([A-Z ]+) at ([\d.]+)% confidence")
RE_PRE = re.compile(r"Pre-screen: (\d+)/(\d+) returned data, (\d+) flagged interesting \S+ (\d+) selected")
Z_ALPHA, Z_POWER = 1.959964, 0.841621          # two-sided 5% test, 80% power


def parse_log():
    """Stream the log once.

    Deep analysis ran tickers in parallel threads for most of the deployment, so
    unlabelled lines (fundamentals, news, the bare "DECISION:" line) cannot be
    attributed to a ticker by position. Two kinds of line are safe anchors:
      * "Autonomous decision for T: D (C% confidence)" -- printed only when the LLM
        returned a parsable answer, and carries the ticker;
      * "Error in autonomous analysis" -- printed when the call failed; the agent then
        returns its fallback (HOLD, confidence 0.5) and prints no labelled line.
    Real decisions + fallbacks therefore add up to the number of "DECISION:" lines.
    """
    real, errs, scans = [], [], []
    started = {}                       # ticker -> latest "Analyzing T..." timestamp
    n_dec_lines = n_429 = n_200 = n_retry = n_embed = 0
    scan_id, t_scan0 = 0, None
    with open(LOG, errors="replace") as fh:
        for line in fh:
            if "HTTP Request: POST" in line:
                if "chat/completions" in line:
                    n_200 += "HTTP/1.1 200" in line
                    n_429 += "HTTP/1.1 429" in line
                elif "embeddings" in line and "HTTP/1.1 200" in line:
                    n_embed += 1
                continue
            m = TS.match(line)
            if not m:
                continue
            ts = datetime.strptime(m.group(1) + "." + m.group(2), "%Y-%m-%d %H:%M:%S.%f")
            msg = m.group(4)
            if (d := RE_LAB.search(msg)):
                t0 = started.get(d.group(1))
                real.append({"ts": ts, "ticker": d.group(1), "decision": d.group(2).strip(), "conf": float(d.group(3)) / 100,
                             "lat_s": (ts - t0).total_seconds() if t0 else np.nan, "scan": scan_id})
            elif (a := RE_ANALYZ.match(msg)):
                started[a.group(1)] = ts
            elif "Error in autonomous analysis" in msg:
                errs.append({"ts": ts, "kind": "quota" if "exceeded your current quota" in msg else ("json" if "JSON" in msg else "other")})
            elif "DECISION:" in msg and RE_DEC.search(msg):
                n_dec_lines += 1
            elif msg.startswith("Retrying request to /chat/completions"):
                n_retry += 1
            elif "DAY-TRADE SCAN STARTING" in msg:
                scan_id, t_scan0 = scan_id + 1, ts
                scans.append({"scan": scan_id, "t0": ts, "dur": np.nan, "selected": np.nan})
            elif msg.startswith("Pre-screen:") and (p := RE_PRE.search(msg)) and scans:
                scans[-1]["selected"] = int(p.group(4))
            elif "Scan completed" in msg and scans and t_scan0 is not None:
                scans[-1]["dur"] = (ts - t_scan0).total_seconds()
    return (pd.DataFrame(real), pd.DataFrame(errs), pd.DataFrame(scans),
            dict(n_200=n_200, n_429=n_429, n_retry=n_retry, n_embed=n_embed, n_dec_lines=n_dec_lines))


def power_section():
    """Minimum detectable effect (two-sided 5%, 80% power) from the bootstrap SEs."""
    a = json.load(open(RES / "analysis.json"))
    i = json.load(open(RES / "intraday.json"))
    k = Z_ALPHA + Z_POWER
    out = {"intraday": {"se": i["alpha"]["se"], "mde": k * i["alpha"]["se"], "hi": i["alpha"]["hi"]}}
    for h in ("h1", "h3", "h5", "h10"):
        out[h] = {"se": a["robustness"][h]["se"], "mde": k * a["robustness"][h]["se"], "hi": a["robustness"][h]["hi"]}
    return out


def period_robustness():
    """10-day LLM-minus-placebo alpha split by whether the LLM was reachable (quota) that month."""
    import yfinance as yf
    import paper_analysis as pa
    ev = pd.read_csv(RES / "analysis_buy_signals.csv")
    sig, _, _ = pa.load_signals()
    spy = yf.download("SPY", start=sig["day"].min() - pd.Timedelta(days=140), end=pa.DATA_END,
                      auto_adjust=True, progress=False)
    dates = spy.dropna().index
    ev["date"] = dates[ev["i"].values]
    out = {}
    for name, mask in (("all", ev.date >= "2000-01-01"), ("quota_era", ev.date < "2026-04-01"),
                       ("full_coverage", ev.date >= "2026-04-01")):
        g = ev[mask]
        b = pa.block_boot(g.alpha_vs_match.values, g["i"].values)
        out[name] = {"n": int(len(g)), "mean": b["mean"], "lo": b["lo"], "hi": b["hi"], "p": b["p"], "se": b["se"],
                     "mde": (Z_ALPHA + Z_POWER) * b["se"]}
    return out


def audit_rationale(real):
    """Trace database BUYs to logged LLM decisions and check the rationale they cite."""
    db = pd.read_sql("select ticker, recommendation_date, decision, confidence, rsi, trend, key_factors from recommendations",
                     sqlite3.connect(DB))
    db["ts"] = pd.to_datetime(db.recommendation_date, format="mixed")
    buys = db[db.decision == "BUY"].sort_values("ts").reset_index(drop=True)
    rb = real[real.decision == "BUY"].sort_values("ts")[["ticker", "ts", "conf"]].rename(columns={"ts": "t_log", "conf": "log_conf"})
    # the database row is written when the scan finishes, about a minute after the decision
    j = pd.merge_asof(buys, rb, left_on="ts", right_on="t_log", by="ticker", direction="backward",
                      tolerance=pd.Timedelta("20min"))
    tr = j.log_conf.notna()
    o = {"n_buys": len(j), "traced_pct": float(tr.mean() * 100),
         "trace_offset_med_min": float(((j.ts - j.t_log).dt.total_seconds() / 60)[tr].median()),
         "stage3_conf_changed_pct": float(((j.confidence - j.log_conf).abs() > 0.005)[tr].mean() * 100),
         "stage3_conf_mean_shift": float((j.confidence - j.log_conf)[tr].mean())}
    j["factors"] = j.key_factors.map(lambda s: [x.lower() for x in json.loads(s)] if s else [])
    cites = lambda kw: j.factors.map(lambda f: any(kw in x for x in f))
    over, bear = cites("oversold"), cites("bearish trend")
    o["cite_oversold_pct"] = float(over.mean() * 100)
    o["oversold_but_rsi_ge_35_pct"] = float((j.rsi[over] >= 35).mean() * 100)
    o["cite_bearish_trend_pct"] = float(bear.mean() * 100)
    o["bearish_trend_but_field_bullish_pct"] = float((j.trend[bear] == "bullish").mean() * 100)
    o["median_rsi_of_buys"] = float(j.rsi.median())
    pe = pd.read_sql("select exit_reason, profit_loss_pct from recommendations where decision='BUY' and exit_reason is not null",
                     sqlite3.connect(DB))
    o["prod_n"] = int(len(pe))
    o["prod_eod_pct"] = float((pe.exit_reason == "end_of_day").mean() * 100)
    o["prod_stop_n"] = int((pe.exit_reason == "stop_loss_hit").sum())
    o["prod_mean_pl"] = float(pe.profit_loss_pct.mean())
    allf = pd.Series([x for f in j.factors for x in f])
    o["distinct_factor_strings"] = int(allf.nunique())
    o["top_factors"] = allf.value_counts().head(5).to_dict()
    o["top3_share_pct"] = float(allf.value_counts().head(3).sum() / len(allf) * 100)
    return o


def main():
    real, errs, scans, http = parse_log()
    real.to_csv(RES / "ops_real_decisions.csv", index=False)
    errs.to_csv(RES / "ops_fallbacks.csv", index=False)
    n_real, n_err = len(real), len(errs)
    ops = {
        "decisions": http["n_dec_lines"], "real": n_real, "fallback": n_err,
        "reconciles": bool(abs(http["n_dec_lines"] - n_real - n_err) <= 0.001 * http["n_dec_lines"]),
        "fallback_quota": int((errs.kind == "quota").sum()), "fallback_json": int((errs.kind == "json").sum()),
        "fallback_other": int((errs.kind == "other").sum()),
        "first": str(min(real.ts.min(), errs.ts.min()).date()), "last": str(max(real.ts.max(), errs.ts.max()).date()),
        "quota_first": str(errs.ts.min().date()), "quota_last": str(errs.ts.max().date()),
        "quota_days": int(errs.ts.dt.date.nunique()),
        "active_days": int(pd.concat([real.ts, errs.ts]).dt.date.nunique()),
        "lat_median_s": float(real.lat_s[real.lat_s.between(0, 600)].median()),
        "lat_p95_s": float(real.lat_s[real.lat_s.between(0, 600)].quantile(.95)),
        "scans": len(scans), "scan_median_min": float(scans.dur.median() / 60), "selected_median": float(scans.selected.median()),
        **http,
    }
    real["month"], errs["month"] = real.ts.dt.strftime("%Y-%m"), errs.ts.dt.strftime("%Y-%m")
    rm, em = real.groupby("month").size(), errs.groupby("month").size()
    months = sorted(set(rm.index) | set(em.index))
    ops["months"] = {}
    for mo in months:
        r, e = int(rm.get(mo, 0)), int(em.get(mo, 0))
        ops["months"][mo] = {"n": r + e, "real": r, "real_pct": 100 * r / (r + e), "fallback_pct": 100 * e / (r + e)}
    ops["real_decision_mix"] = (real.decision.value_counts(normalize=True) * 100).round(1).to_dict()
    ops["real_buy_share_apr_sep"] = float((real[real.ts >= "2026-04-01"].decision == "BUY").mean() * 100)
    ops["power"] = power_section()
    ops["period"] = period_robustness()
    ops["audit"] = audit_rationale(real)
    # how much of the traded universe is actually S&P 500 (the scanner's list is broader)
    u = pd.read_csv(RES / "sp500_universe.csv")
    start = set(u.loc[u.in_universe_at_start, "symbol"])
    logt = {t.replace(".", "-") for (t,) in sqlite3.connect(DB).execute("select distinct ticker from recommendations")}
    buys_ev = pd.read_csv(RES / "analysis_buy_signals.csv")
    ops["universe"] = {"index_at_start": len(start), "log_tickers": len(logt), "non_index": len(logt - start),
                       "buy_share_non_index_pct": float((~buys_ev.ticker.str.replace(".", "-").isin(start)).mean() * 100)}
    json.dump(ops, open(RES / "ops.json", "w"), indent=2, default=float)

    f = lambda v, d=1: f"{v:.{d}f}"
    m = {"opDecisions": f"{ops['decisions']:,}", "opReal": f"{ops['real']:,}", "opFallback": f"{ops['fallback']:,}",
         "opFallbackPct": f(100 * ops["fallback"] / ops["decisions"]), "opRealPct": f(100 * ops["real"] / ops["decisions"]),
         "opQuota": f"{ops['fallback_quota']:,}", "opQuotaDays": ops["quota_days"], "opActiveDays": ops["active_days"],
         "opQuotaFirst": ops["quota_first"], "opQuotaLast": ops["quota_last"], "opScans": f"{ops['scans']:,}",
         "opLatMed": f(ops["lat_median_s"]), "opLatPtf": f(ops["lat_p95_s"]), "opHttpOk": f"{ops['n_200']:,}",
         "opHttpLimited": f"{ops['n_429']:,}", "opJsonErr": ops["fallback_json"], "opScanMedMin": f(ops["scan_median_min"]),
         "opSelMed": f"{ops['selected_median']:.0f}", "opBuyShare": f(ops["real_buy_share_apr_sep"])}
    P = ops["power"]
    for key, name in (("intraday", "Intra"), ("h1", "One"), ("h3", "Three"), ("h5", "Five"), ("h10", "Ten")):
        d = 3 if key == "intraday" else 2
        m["mdeSe" + name] = f(100 * P[key]["se"], 3)
        m["mde" + name] = f(100 * P[key]["mde"], d)
        m["mdeUpper" + name] = f"{100 * P[key]['hi']:+.{d}f}"
    pr = ops["period"]
    for key, name in (("all", "All"), ("quota_era", "Quota"), ("full_coverage", "Full")):
        m["per" + name + "N"] = f"{pr[key]['n']:,}"
        m["per" + name + "Mean"] = f"{100 * pr[key]['mean']:+.2f}"
        m["per" + name + "CI"] = f"[{100 * pr[key]['lo']:+.2f}, {100 * pr[key]['hi']:+.2f}]"
        m["per" + name + "P"] = f"{pr[key]['p']:.3f}" if pr[key]["p"] >= 0.001 else "$<$0.001"
        m["per" + name + "Mde"] = f"{100 * pr[key]['mde']:.2f}"
    import ast
    tree = ast.parse((HERE / "ultimate_market_scanner.py").read_text())
    lit = next(n for n in tree.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "SP500_ALL"
               and isinstance(n.value, ast.List))
    ops["universe"]["scanner_unique"] = len({e.value for e in lit.value.elts})
    prev = json.load(open(RES / "prev_universe" / "analysis.json"))
    pv = next(r for r in prev["regimes"] if r["regime"] == "VIX>20")
    ops["prev_vix_hi"] = {"alpha": pv["alpha"], "lo": pv["lo"], "hi": pv["hi"], "p": pv["p"]}
    prev_macros = (RES / "prev_universe" / "results_macros.tex").read_text()
    prev_match_sh = re.search(r"\\newcommand\{\\pMatchSh\}\{([^}]*)\}", prev_macros).group(1)
    U = ops["universe"]
    m.update({"prevMatchSh": prev_match_sh})
    m.update({"nIndexStart": U["index_at_start"], "nLogTick": U["log_tickers"], "nNonIndex": U["non_index"],
              "nBuyNonIndexPct": f(U["buy_share_non_index_pct"]),
              "nScannerUniv": U["scanner_unique"], "prevVixHi": f"{100 * ops['prev_vix_hi']['alpha']:+.2f}",
              "prevVixHiCI": f"[{100 * ops['prev_vix_hi']['lo']:+.2f}, {100 * ops['prev_vix_hi']['hi']:+.2f}]"})
    A = ops["audit"]
    m.update({"auBuys": f"{A['n_buys']:,}", "auTraced": f(A["traced_pct"]), "auOffset": f(A["trace_offset_med_min"]),
              "auStageChanged": f(A["stage3_conf_changed_pct"]), "auCiteOversold": f(A["cite_oversold_pct"]),
              "auOversoldBad": f(A["oversold_but_rsi_ge_35_pct"]), "auMedRsi": f(A["median_rsi_of_buys"]),
              "auDistinct": A["distinct_factor_strings"], "auTopShare": f(A["top3_share_pct"])})
    i = json.load(open(RES / "intraday.json"))
    assert i["hit"] + i["ece"] < 1 and abs((i["hit"] + i["ece"]) - 0.815) < 0.02, "intraday confidence reconstruction"
    m.update({"iEce": f(i["ece"], 3), "iConf": f(i["hit"] + i["ece"], 2),
              "prodN": f"{A['prod_n']:,}", "prodEod": f(A["prod_eod_pct"]), "prodStopN": A["prod_stop_n"],
              "prodMeanPl": f"{A['prod_mean_pl']:+.2f}"})
    rows = "".join(f"{mo} & {v['n']:,} & {v['real_pct']:.0f}\\% & {v['fallback_pct']:.0f}\\% \\\\\n" for mo, v in ops["months"].items())
    with open(PAPER / "results_ops.tex", "w") as fh:
        fh.write("% Auto-generated by paper_ops.py -- do not edit by hand\n")
        for k, v in m.items():
            fh.write(f"\\newcommand{{\\{k}}}{{{v}}}\n")
        fh.write("\\newcommand{\\opMonthRows}{%\n" + rows + "}\n")
    print(json.dumps(ops, indent=1, default=lambda x: round(float(x), 4)))


if __name__ == "__main__":
    main()
