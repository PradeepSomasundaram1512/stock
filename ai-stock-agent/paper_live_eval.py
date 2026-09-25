"""
Forward (live) evaluation of the LLM agent's recommendations for the IEEE paper.

Every recommendation in the EC2 database was generated in real time (Jan-Sep 2026),
after the LLM's training cutoff, so there is no look-ahead bias.

For each unique (ticker, day, decision) signal we:
  * enter at the recommendation-day close,
  * replay the LLM's own target/stop over the next 10 trading days using daily
    high/low (stop assumed first when both are touched in the same bar),
  * record raw and SPY-excess forward returns at 5 and 10 trading days.

Controls: WATCH SELL signals (the agent's own negative calls) and a random-entry
control drawn from the same tickers and dates.

Run: venv/bin/python paper_live_eval.py [path/to/backtest.db]
Output: paper_results/live_*.csv, paper_results/live_summary.json
"""

import json
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

HERE = Path(__file__).parent
DB = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parents[1] / "aws-ec2-backup-2026-09-25/data/backtest.db"
OUT = HERE / "paper_results"
OUT.mkdir(exist_ok=True)
HOLD = 10
RNG = np.random.default_rng(42)


def load_signals():
    con = sqlite3.connect(DB)
    df = pd.read_sql("select ticker, recommendation_date, decision, confidence, entry_price, "
                     "price_target, stop_loss, rsi, news_sentiment_score, market_vix "
                     "from recommendations where decision in ('BUY','WATCH SELL','WATCH')", con)
    df["day"] = pd.to_datetime(df["recommendation_date"].str[:10], format="mixed")
    # hourly scans repeat the same call; keep the first per ticker/day/decision
    df = df.sort_values("recommendation_date").drop_duplicates(["ticker", "day", "decision"])
    return df.reset_index(drop=True)


def fetch_prices(tickers, start, end):
    data = yf.download(sorted(set(tickers) | {"SPY"}), start=start, end=end,
                       auto_adjust=True, progress=False, group_by="ticker", threads=True)
    return {t: data[t].dropna() for t in set(tickers) | {"SPY"} if t in data.columns.get_level_values(0)}


def evaluate(row, px, spy, target=None, stop=None):
    if row.ticker not in px:
        return None
    p = px[row.ticker]
    idx = p.index.searchsorted(row.day, side="right") - 1  # rec-day close (or last close before)
    if idx < 0 or idx + HOLD >= len(p):
        return None
    entry = p["Close"].iloc[idx]
    d0 = p.index[idx]
    s_idx = spy.index.get_loc(d0) if d0 in spy.index else None
    if s_idx is None or s_idx + HOLD >= len(spy):
        return None
    fwd = {h: p["Close"].iloc[idx + h] / entry - 1 for h in (5, HOLD)}
    spy_fwd = {h: spy["Close"].iloc[s_idx + h] / spy["Close"].iloc[s_idx] - 1 for h in (5, HOLD)}

    # swing-rule replay with the LLM's own levels
    trade_ret, reason = fwd[HOLD], "TIME"
    if target and stop and target > entry > stop:
        for k in range(1, HOLD + 1):
            bar = p.iloc[idx + k]
            if bar["Low"] <= stop:
                trade_ret, reason = stop / entry - 1, "STOP"
                break
            if bar["High"] >= target:
                trade_ret, reason = target / entry - 1, "TARGET"
                break
    return {
        "ret5": fwd[5], "ret10": fwd[HOLD],
        "ex5": fwd[5] - spy_fwd[5], "ex10": fwd[HOLD] - spy_fwd[HOLD],
        "trade_ret": trade_ret, "exit": reason,
    }


def summarize(df, name):
    if df.empty:
        return {"group": name, "n": 0}
    r = df["trade_ret"]
    wins, losses = r[r > 0].sum(), -r[r < 0].sum()
    boot = [RNG.choice(df["ex10"].values, len(df)).mean() for _ in range(2000)]
    return {
        "group": name, "n": len(df),
        "win_rate_pct": round(100 * (r > 0).mean(), 1),
        "avg_trade_ret_pct": round(100 * r.mean(), 2),
        "profit_factor": round(wins / losses, 2) if losses else None,
        "avg_fwd10_pct": round(100 * df["ret10"].mean(), 2),
        "avg_excess5_pct": round(100 * df["ex5"].mean(), 2),
        "avg_excess10_pct": round(100 * df["ex10"].mean(), 2),
        "excess10_ci95": [round(100 * np.percentile(boot, 2.5), 2), round(100 * np.percentile(boot, 97.5), 2)],
        "hit_target_pct": round(100 * (df["exit"] == "TARGET").mean(), 1),
        "hit_stop_pct": round(100 * (df["exit"] == "STOP").mean(), 1),
    }


def main():
    sig = load_signals()
    px = fetch_prices(sig["ticker"].unique(), sig["day"].min() - pd.Timedelta(days=5), pd.Timestamp.today())
    spy = px["SPY"]

    rows = []
    for row in sig.itertuples():
        tgt, stp = (row.price_target, row.stop_loss) if row.decision == "BUY" else (None, None)
        res = evaluate(row, px, spy, tgt, stp)
        if res:
            rows.append({**row._asdict(), **res})
    ev = pd.DataFrame(rows).drop(columns="Index")
    ev.to_csv(OUT / "live_signals_evaluated.csv", index=False)

    # random-entry control: same tickers and dates as BUY signals, shuffled pairing
    buys = ev[ev.decision == "BUY"]
    ctrl = []
    for _ in range(5):
        shuffled = buys.assign(ticker=RNG.permutation(buys["ticker"].values))
        for row in shuffled.itertuples():
            res = evaluate(row, px, spy)
            if res:
                ctrl.append(res)
    ctrl = pd.DataFrame(ctrl)

    summary = [summarize(buys, "LLM BUY (own target/stop)"),
               summarize(buys.assign(trade_ret=buys["ret10"], exit="TIME"), "LLM BUY (10-day hold)"),
               summarize(ev[ev.decision == "WATCH"], "LLM WATCH"),
               summarize(ev[ev.decision == "WATCH SELL"], "LLM WATCH SELL"),
               summarize(ctrl, "Random entry, same dates (x5)")]

    conf = []
    for lo, hi in [(0, 0.7), (0.7, 0.8), (0.8, 0.85), (0.85, 1.01)]:
        g = buys[(buys.confidence >= lo) & (buys.confidence < hi)]
        conf.append(summarize(g, f"conf [{lo:.2f},{min(hi, 1):.2f})"))

    monthly = buys.groupby(buys["day"].dt.to_period("M")).apply(
        lambda g: pd.Series(summarize(g, "")), include_groups=False).drop(columns="group")

    spy_period = spy["Close"].loc[buys["day"].min():]
    info = {
        "period": [str(buys["day"].min().date()), str(buys["day"].max().date())],
        "unique_tickers": int(ev["ticker"].nunique()),
        "spy_return_over_period_pct": round(100 * (spy_period.iloc[-1] / spy_period.iloc[0] - 1), 2),
    }
    pd.DataFrame(summary).to_csv(OUT / "live_table_strategies.csv", index=False)
    pd.DataFrame(conf).to_csv(OUT / "live_table_confidence.csv", index=False)
    monthly.to_csv(OUT / "live_table_monthly.csv")
    json.dump({"info": info, "strategies": summary, "confidence": conf}, open(OUT / "live_summary.json", "w"), indent=2)

    pd.set_option("display.width", 200)
    print(info)
    print(pd.DataFrame(summary).to_string(index=False))
    print(pd.DataFrame(conf).to_string(index=False))
    print(monthly.to_string())


if __name__ == "__main__":
    main()
