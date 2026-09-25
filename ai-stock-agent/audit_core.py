"""
Shared, light-weight pieces of the forward audit (no matplotlib/scipy, so it runs in the cloud image):
the fixed S&P 500 placebo universe, signal loading, the price panel with the derived columns, and the
10-day beta-adjusted cumulative abnormal return (CAR). paper_analysis.py and forward_test.py both use
these, so the paper and the ongoing forward test measure exactly the same thing.
"""
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

HERE = Path(__file__).parent
UNIVERSE_CSV = HERE / "audit" / "sp500_universe.csv"

H = 10              # holding horizon (trading days)
BLOCK = 10          # bootstrap block length in trading days
# Price data is cut off here (exclusive) so results do not change from run to run: downloading
# "through today" leaked a half-finished trading day into the panel and shifted the numbers.
DATA_END = pd.Timestamp("2026-09-25")


def fixed_universe():
    """S&P 500 constituents on the first day of the study (see paper_universe.py).

    The placebo pool must not depend on which tickers later appeared in the log, so it
    is this fixed list, in Yahoo Finance symbol style, rather than the log's tickers."""
    u = pd.read_csv(UNIVERSE_CSV)
    return sorted(u.loc[u.in_universe_at_start, "symbol"])


def load_signals(db):
    con = sqlite3.connect(db)
    df = pd.read_sql("select ticker, recommendation_date, decision, confidence, entry_price, "
                     "price_target, stop_loss from recommendations", con)
    df["day"] = pd.to_datetime(df["recommendation_date"].str[:10], format="mixed")
    raw_counts = df["decision"].value_counts().to_dict()
    df = df.sort_values("recommendation_date").drop_duplicates(["ticker", "day", "decision"])
    return df.reset_index(drop=True), raw_counts, len(con.execute("select 1 from recommendations").fetchall())


def load_panel(tickers, start, end, cache_dir=None):
    """Price panel with derived columns. With `cache_dir`, the raw download is frozen on first use and reused afterwards, keyed by the
    exact tickers and dates: Yahoo revises adjusted prices slightly between downloads, which made the paper's numbers wobble from run to
    run (the portfolio-rule row moved between +8.6% and +8.9%). The paper uses a cache; the live forward test never does."""
    import hashlib
    tick = sorted(set(tickers) | {"SPY"})
    raw, path = None, None
    if cache_dir is not None:
        key = hashlib.sha1(f"{','.join(tick)}|{pd.Timestamp(start).date()}|{pd.Timestamp(end).date()}".encode()).hexdigest()[:10]
        path = Path(cache_dir) / f"daily_panel_{key}.pkl.gz"
        if path.exists():
            raw = pd.read_pickle(path)
    if raw is None:
        raw = yf.download(tick + ["^VIX"], start=start, end=end, auto_adjust=True,
                          progress=False, group_by="ticker", threads=True)
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            raw.to_pickle(path, compression="gzip")
    spy_idx = raw["SPY"].dropna().index
    get = lambda f: pd.DataFrame({t: raw[t][f] for t in tick if t in raw.columns.get_level_values(0)}).reindex(spy_idx)
    C, O, Hh, L = get("Close"), get("Open"), get("High"), get("Low")
    C = C.loc[:, C.notna().sum() > 60]
    O, Hh, L = O[C.columns], Hh[C.columns], L[C.columns]
    delta = C.diff()
    rsi = 100 - 100 / (1 + delta.clip(lower=0).rolling(14).mean() / ((-delta.clip(upper=0)).rolling(14).mean() + 1e-9))
    pc = C.shift(1)
    tr = np.maximum(Hh - L, np.maximum((Hh - pc).abs(), (L - pc).abs()))
    atr = tr.rolling(14).mean()
    ret = C.pct_change()
    beta = ret.rolling(60, min_periods=40).cov(ret["SPY"]).div(ret["SPY"].rolling(60, min_periods=40).var(), axis=0)
    vix = raw["^VIX"]["Close"].reindex(spy_idx).ffill()
    return dict(C=C, O=O, H=Hh, L=L, rsi=rsi, atr_pct=atr / C, atr=atr, mom=C / C.shift(20) - 1,
                ret=ret, beta=beta.clip(-1, 3), vix=vix, sma50=C["SPY"].rolling(50).mean())


def car_path(P, i, t):
    """Beta-adjusted cumulative abnormal return path for days 0..H."""
    c, s = P["C"][t].values, P["C"]["SPY"].values
    b = P["beta"][t].iloc[i]
    b = 1.0 if np.isnan(b) else b
    r = c[i:i + H + 1] / c[i] - 1
    rm = s[i:i + H + 1] / s[i] - 1
    return r - b * rm, r, rm


def valid(P, i, t):
    return (t in P["C"].columns and i + H < len(P["C"]) and
            not np.isnan(P["C"][t].values[i:i + H + 1]).any() and not np.isnan(P["rsi"][t].iloc[i]))
