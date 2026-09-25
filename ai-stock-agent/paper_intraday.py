"""
Native-horizon (intraday) audit of the live LLM agent for the IEEE paper.

The production scanner invoked the LangGraph pipeline with the intraday prompt on
60-minute bars ("trade for TODAY ONLY"), so the agent's native horizon is entry ->
same-day close. For every BUY:
  * entry  = close of the 60-minute bar that contains the signal timestamp (UTC log),
  * exit   = 16:00 ET close of the same day, or the deployed stop/target if touched first,
  * placebo = K nearest non-selected stocks at the same bar in the prescreen's own
              feature space (hourly RSI-14, 5-bar momentum, hourly ATR%, volume ratio).

Run:    venv/bin/python paper_intraday.py [path/to/backtest.db]
Output: paper_results/intraday.json, ../../paper/results_intraday.tex
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

import paper_analysis as pa

K = 10
COST = pa.COST
pa.BLOCK = 1  # cluster by trading day: intraday holdings never overlap across days


def load_hourly(tickers, start):
    cache = pa.RES / "hourly_cache_universe.pkl"
    if cache.exists():
        raw = pd.read_pickle(cache)
    else:
        raw = yf.download(sorted(set(tickers) | {"SPY"}), start=start, interval="60m", auto_adjust=True,
                          progress=False, group_by="ticker", threads=True)
        raw.to_pickle(cache)
    idx = raw["SPY"].dropna().index
    lv = raw.columns.get_level_values(0)
    get = lambda f: pd.DataFrame({t: raw[t][f] for t in set(lv)}).reindex(idx)
    C, Hh, L, V = get("Close"), get("High"), get("Low"), get("Volume")
    keep = C.columns[C.notna().sum() > 200]
    C, Hh, L, V = C[keep], Hh[keep], L[keep], V[keep]
    d = C.diff()
    rsi = 100 - 100 / (1 + d.clip(lower=0).rolling(14).mean() / ((-d.clip(upper=0)).rolling(14).mean() + 1e-9))
    pc = C.shift(1)
    tr = np.maximum(Hh - L, np.maximum((Hh - pc).abs(), (L - pc).abs()))
    feats = {"rsi": rsi, "mom": C / C.shift(5) - 1, "atr": tr.rolling(14).mean() / C,
             "vol": V / V.rolling(20).mean()}
    return C, Hh, L, feats


def main():
    sig, _, _ = pa.load_signals()
    buys = sig[sig.decision == "BUY"].copy()
    buys["ts"] = pd.to_datetime(buys.recommendation_date, format="mixed").dt.tz_localize("UTC").dt.tz_convert("America/New_York")
    buys = buys[(buys.ts.dt.time >= pd.Timestamp("09:30").time()) & (buys.ts.dt.time < pd.Timestamp("16:00").time())]

    fixed = pa.fixed_universe()
    C, Hh, L, F = load_hourly(sorted(set(buys.ticker.unique()) | set(fixed)), buys.ts.min().normalize() - pd.Timedelta(days=10))
    bars = C.index.as_unit("ns")
    buys["ts"] = buys.ts.dt.as_unit("ns").dt.tz_convert(bars.tz)
    day = bars.normalize()
    udays = np.unique(day)
    universe = [t for t in fixed if t in C.columns and t != "SPY"]
    picked_day = set(zip(buys.ts.dt.normalize(), buys.ticker))

    rows = []
    for r in buys.itertuples():
        t = r.ticker
        if t not in C.columns:
            continue
        b = bars.searchsorted(r.ts, side="right") - 1          # bar containing the signal
        if b < 1 or day[b] != r.ts.normalize():
            continue
        last = np.where(day == day[b])[0][-1]                   # 15:30 bar of that day
        if b >= last:
            continue
        path = C[t].values[b:last + 1]
        if np.isnan(path).any():
            continue
        e0, spy0, spy1 = path[0], C["SPY"].values[b], C["SPY"].values[last]
        raw = path[-1] / e0 - 1
        ex = raw - (spy1 / spy0 - 1)

        # deployed stop/target replay on the following bars
        ok = r.price_target and r.stop_loss and r.price_target > r.entry_price > r.stop_loss
        dep, why = raw, "CLOSE"
        if ok:
            s, g = e0 * r.stop_loss / r.entry_price, e0 * r.price_target / r.entry_price
            for k in range(b + 1, last + 1):
                if L[t].values[k] <= s:
                    dep, why = s / e0 - 1, "STOP"
                    break
                if Hh[t].values[k] >= g:
                    dep, why = g / e0 - 1, "TARGET"
                    break

        # placebo on the prescreen's feature space, measured at the last completed bar
        X = pd.DataFrame({k: v.iloc[b - 1] for k, v in F.items()})
        X = X.loc[[u for u in universe if (day[b], u) not in picked_day]].dropna()
        X = X[np.isfinite(X).all(1)]
        mu, sd = X.mean(), X.std()
        me = (np.array([F[k][t].iloc[b - 1] for k in F]) - mu.values) / sd.values
        if np.isnan(me).any():
            continue
        nb = []
        for u in ((X - mu) / sd).pipe(lambda z: z.index[((z.values - me) ** 2).sum(1).argsort()]):
            pu = C[u].values[b:last + 1]
            if not np.isnan(pu).any():
                nb.append(pu[-1] / pu[0] - 1 - (spy1 / spy0 - 1))
            if len(nb) == K:
                break
        rng = pa.rng
        rnd = []
        for u in rng.choice(universe, 40, replace=False):
            pu = C[u].values[b:last + 1]
            if not np.isnan(pu).any():
                rnd.append(pu[-1] / pu[0] - 1 - (spy1 / spy0 - 1))
        rows.append({"day_i": int(np.searchsorted(udays, day[b])), "ticker": t, "conf": r.confidence,
                     "hours_left": int(last - b), "raw": raw, "ex": ex, "dep": dep - COST, "exit": why,
                     "match_ex": np.mean(nb), "rand_ex": np.mean(rnd[:20]),
                     "hold_net": raw - COST})
    ev = pd.DataFrame(rows)
    ev["alpha"] = ev.ex - ev.match_ex
    ev.to_csv(pa.RES / "intraday_buy_signals.csv", index=False)
    B = lambda v: pa.block_boot(np.asarray(v, float), ev.day_i.values)

    res = {
        "n": len(ev), "days": int(ev.day_i.nunique()),
        "raw": B(ev.raw), "ex": B(ev.ex), "match_ex": B(ev.match_ex), "rand_ex": B(ev.rand_ex),
        "alpha": B(ev.alpha), "alpha_rand": B(ev.ex - ev.rand_ex),
        "hold_net": B(ev.hold_net), "dep": B(ev.dep), "dep_gap": B(ev.dep - ev.hold_net),
        "stop_rate": float((ev.exit == "STOP").mean()), "tgt_rate": float((ev.exit == "TARGET").mean()),
        "hit": float((ev.ex > 0).mean()), "match_hit": float((ev.match_ex > 0).mean()),
        "dep_win": float((ev.dep > 0).mean()),
        "ece": float(abs(ev.conf.mean() - (ev.ex > 0).mean())),
    }
    json.dump(res, open(pa.RES / "intraday.json", "w"), indent=2, default=float)

    pc = lambda v: f"{100 * v:+.2f}"
    ci = lambda b: f"[{100 * b['lo']:+.2f}, {100 * b['hi']:+.2f}]"
    pv = lambda b: f"{b['p']:.3f}" if b["p"] >= 0.001 else "$<$0.001"
    m = {"iN": f"{res['n']:,}", "iDays": res["days"], "iStop": f"{100 * res['stop_rate']:.1f}",
         "iTgt": f"{100 * res['tgt_rate']:.1f}", "iHit": f"{100 * res['hit']:.1f}",
         "iMatchHit": f"{100 * res['match_hit']:.1f}", "iDepWin": f"{100 * res['dep_win']:.1f}"}
    for k in ("raw", "ex", "match_ex", "rand_ex", "alpha", "alpha_rand", "hold_net", "dep", "dep_gap"):
        key = "i" + "".join(p.capitalize() for p in k.split("_"))
        m[key], m[key + "CI"], m[key + "P"] = pc(res[k]["mean"]), ci(res[k]), pv(res[k])
    with open(pa.PAPER / "results_intraday.tex", "w") as f:
        f.write("% Auto-generated by paper_intraday.py -- do not edit by hand\n")
        for k, v in m.items():
            f.write(f"\\newcommand{{\\{k}}}{{{v}}}\n")
    print(json.dumps(res, indent=1, default=lambda x: round(float(x), 5)))


if __name__ == "__main__":
    main()
