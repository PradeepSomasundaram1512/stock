"""
Snapshot of the whole scan universe for the dashboard's heatmap: last price, 1-day and 5-day change, RSI(14)
and a dollar-volume size proxy for every ticker the scanner covers, from ONE batched daily-bar download.
Written to data/market_snapshot.json (synced to the bucket like the other state).

    python market_snapshot.py [--out data/market_snapshot.json]

Prices are Yahoo's, so about 15 minutes delayed during market hours; the dashboard shows the "as of" time.
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

HERE = Path(__file__).parent


def universe() -> list:
    """The scan universe: the refreshed list (scan_universe.py) when present and valid, else the scanner's built-in one."""
    from scan_universe import builtin_default, load_universe
    return load_universe(builtin_default())


def rsi14(close: pd.Series):
    d = close.diff()
    up, dn = d.clip(lower=0).rolling(14).mean(), (-d.clip(upper=0)).rolling(14).mean()
    if len(close) < 15 or not np.isfinite(dn.iloc[-1]):
        return None
    return float(100 - 100 / (1 + up.iloc[-1] / (dn.iloc[-1] + 1e-9)))


def build(tickers: list) -> dict:
    df = yf.download(tickers, period="3mo", interval="1d", auto_adjust=True, group_by="ticker", progress=False, threads=True)
    have = set(df.columns.get_level_values(0))
    stocks, missing = {}, []
    for t in tickers:
        if t not in have:
            missing.append(t)
            continue
        c, v = df[t]["Close"].dropna(), df[t]["Volume"].dropna()
        if len(c) < 6:
            missing.append(t)
            continue
        price = float(c.iloc[-1])
        stocks[t] = {"p": round(price, 2), "c": round(price / float(c.iloc[-2]) - 1, 5), "c5": round(price / float(c.iloc[-6]) - 1, 5),
                     "rsi": None if rsi14(c) is None else round(rsi14(c), 1),
                     "dv": float(price * v.tail(5).mean()) if len(v) else 0.0, "d": str(c.index[-1].date())}
    return {"asof": datetime.now(timezone.utc).isoformat(timespec="seconds"), "n": len(stocks), "missing": missing, "stocks": stocks}


if __name__ == "__main__":
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else HERE / "data" / "market_snapshot.json"
    snap = build(universe())
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".part")
    tmp.write_text(json.dumps(snap, separators=(",", ":")))
    tmp.replace(out)                                  # never leave a half-written file for the dashboard
    print(f"market snapshot: {snap['n']} tickers, {len(snap['missing'])} missing, as of {snap['asof']}, latest bar {max(s['d'] for s in snap['stocks'].values())}")
    if len(snap["stocks"]) < 0.8 * len(universe()):
        sys.exit("snapshot is missing more than 20% of tickers; likely a data-source problem")
