"""
Forward-audit analysis of the live LLM swing-trading agent (IEEE paper, AIEI 2027).

Methods (all computed from recommendations logged in real time, Jan-Sep 2026):
  1. Event study: cumulative abnormal returns (CAR) for days 0..10 after each signal.
  2. Characteristic-matched placebo: for every LLM BUY, the K nearest non-selected
     stocks on the same date in (daily RSI, 20-day momentum, ATR%) space. The
     difference isolates the LLM's contribution beyond the technical pre-screen.
  3. Block bootstrap: signals are resampled in non-overlapping 10-trading-day blocks,
     which covers both same-day cross-correlation and overlapping holding periods.
  4. Exit-policy decomposition: selection alpha (10-day hold) vs execution alpha
     under a grid of daily-ATR stop/target multiples and the as-deployed levels.
  5. Confidence calibration: reliability, ECE, Brier score, rank correlation.
  6. Portfolio simulation with transaction costs, HAC-robust alpha/beta vs SPY.
  7. Regime analysis by VIX level and SPY trend.

Run:    venv/bin/python paper_analysis.py [path/to/backtest.db]
Output: paper_results/analysis.json, ../../paper/results_macros.tex, ../../paper/figs/*.pdf
"""

import json
import sqlite3
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats

HERE = Path(__file__).parent
ROOT = HERE.parents[1]                 # folder holding the stock/ repo and the EC2 backup
DB = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / "paper/data/backtest_ec2_2026-01-06_to_2026-09-24.db"
RES = HERE / "paper_results"
PAPER = HERE.parent / "paper"
FIGS = PAPER / "figs"
for d in (RES, FIGS):
    d.mkdir(parents=True, exist_ok=True)

from audit_core import BLOCK, DATA_END, H, car_path, fixed_universe, load_panel, valid   # shared with forward_test.py
from audit_core import load_signals as _load_signals
K_MATCH = 10        # placebo neighbours per signal
K_RANDOM = 20       # random draws per signal
COST = 0.0010       # round-trip transaction cost (10 bps)
N_BOOT = 5000
rng = np.random.default_rng(2027)

plt.rcParams.update({"font.family": "serif", "font.size": 8, "axes.linewidth": 0.6,
                     "figure.dpi": 200, "savefig.bbox": "tight", "legend.frameon": False})


# ── data ──────────────────────────────────────────────────────────────────────

def load_signals():
    return _load_signals(DB)


# ── per-signal measurements ───────────────────────────────────────────────────

def replay(P, i, t, stop, target):
    """Exit replay from close[i]; returns trade return (gross). Gaps fill at the open."""
    c0 = P["C"][t].iloc[i]
    o, hi, lo, cl = (P[k][t].values for k in ("O", "H", "L", "C"))
    for k in range(1, H + 1):
        j = i + k
        if stop is not None and lo[j] <= stop:
            return (min(o[j], stop) if o[j] < stop else stop) / c0 - 1, "STOP"
        if target is not None and hi[j] >= target:
            return (max(o[j], target) if o[j] > target else target) / c0 - 1, "TARGET"
    return cl[i + H] / c0 - 1, "TIME"


# ── statistics ────────────────────────────────────────────────────────────────

def block_boot(values, pos, n=N_BOOT, stat=np.mean):
    """Mean and 95% CI via block bootstrap over non-overlapping 10-day blocks of signal dates."""
    values, blocks = np.asarray(values, float), np.asarray(pos) // BLOCK
    ub = np.unique(blocks)
    groups = [values[blocks == b] for b in ub]
    draws = np.empty(n)
    for k in range(n):
        pick = rng.integers(0, len(ub), len(ub))
        draws[k] = stat(np.concatenate([groups[p] for p in pick]))
    est = stat(values)
    p = 2 * min((draws <= 0).mean(), (draws >= 0).mean())
    return {"mean": est, "lo": np.percentile(draws, 2.5), "hi": np.percentile(draws, 97.5),
            "se": draws.std(ddof=1), "p": max(p, 1 / n)}


def hac_ols(y, x, lags=10):
    """OLS y = a + b x with Newey-West standard errors."""
    X = np.column_stack([np.ones_like(x), x])
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    u = y - X @ beta
    XtX_inv = np.linalg.inv(X.T @ X)
    S = (X * u[:, None]).T @ (X * u[:, None])
    for l in range(1, lags + 1):
        w = 1 - l / (lags + 1)
        G = (X[l:] * u[l:, None]).T @ (X[:-l] * u[:-l, None])
        S += w * (G + G.T)
    se = np.sqrt(np.diag(XtX_inv @ S @ XtX_inv))
    return beta, beta / se


def perf(daily):
    daily = pd.Series(daily).fillna(0)
    eq = (1 + daily).cumprod()
    yrs = len(daily) / 252
    return {"total": eq.iloc[-1] - 1, "cagr": eq.iloc[-1] ** (1 / yrs) - 1,
            "vol": daily.std() * np.sqrt(252),
            "sharpe": daily.mean() / daily.std() * np.sqrt(252) if daily.std() > 0 else np.nan,
            "mdd": (eq / eq.cummax() - 1).min()}


# ── main analysis ─────────────────────────────────────────────────────────────

def main():
    sig, raw_counts, n_raw = load_signals()
    fixed = fixed_universe()
    P = load_panel(sorted(set(sig["ticker"].unique()) | set(fixed)), sig["day"].min() - pd.Timedelta(days=140), DATA_END, cache_dir=RES)
    dates = P["C"].index
    universe = [t for t in fixed if t in P["C"].columns and t != "SPY"]
    sig["i"] = dates.searchsorted(sig["day"], side="right") - 1

    buys = sig[(sig.decision == "BUY")].copy()
    buys = buys[[valid(P, r.i, r.ticker) for r in buys.itertuples()]].reset_index(drop=True)
    wsell = sig[(sig.decision == "WATCH SELL")]
    wsell = wsell[[valid(P, r.i, r.ticker) for r in wsell.itertuples()]].reset_index(drop=True)
    picked = set(zip(sig.loc[sig.decision == "BUY", "i"], sig.loc[sig.decision == "BUY", "ticker"]))

    # 1+2. event study and matched placebo -----------------------------------
    rows, car_buy, car_match, car_rand, car_ws = [], [], [], [], []
    for r in buys.itertuples():
        i, t = r.i, r.ticker
        ab, raw, mkt = car_path(P, i, t)
        car_buy.append(ab)
        feats = pd.DataFrame({"rsi": P["rsi"].iloc[i], "mom": P["mom"].iloc[i], "atr": P["atr_pct"].iloc[i]})
        feats = feats.loc[[u for u in universe if (i, u) not in picked]].dropna()
        z = (feats - feats.mean()) / feats.std()
        me = (np.array([P["rsi"][t].iloc[i], P["mom"][t].iloc[i], P["atr_pct"][t].iloc[i]]) - feats.mean().values) / feats.std().values
        order = ((z.values - me) ** 2).sum(1).argsort()
        nb = [u for u in z.index[order] if valid(P, i, u)][:K_MATCH]
        m_paths = np.array([car_path(P, i, u)[0] for u in nb])
        m_raw = np.array([car_path(P, i, u)[1][H] for u in nb])
        car_match.append(m_paths.mean(0))
        pool = [u for u in rng.choice(universe, 4 * K_RANDOM, replace=False) if valid(P, i, u)][:K_RANDOM]
        car_rand.append(np.mean([car_path(P, i, u)[0] for u in pool], 0))
        rows.append({"i": i, "ticker": t, "conf": r.confidence, "rsi_d": P["rsi"][t].iloc[i],
                     "raw5": raw[5], "raw10": raw[H], "spy10": mkt[H], "ex10": raw[H] - mkt[H],
                     "car5": ab[5], "car10": ab[H], "match_raw10": m_raw.mean(),
                     "match_car10": m_paths[:, H].mean(), "rand_car10": car_rand[-1][H],
                     "entry_rec": r.entry_price, "tgt_rec": r.price_target, "stop_rec": r.stop_loss,
                     "atr": P["atr"][t].iloc[i], "vix": P["vix"].iloc[i],
                     "spy_up": bool(P["C"]["SPY"].iloc[i] > P["sma50"].iloc[i])})
    for r in wsell.itertuples():
        car_ws.append(car_path(P, r.i, r.ticker)[0])
    ev = pd.DataFrame(rows)
    ev["alpha_vs_match"] = ev["car10"] - ev["match_car10"]
    ev.to_csv(RES / "analysis_buy_signals.csv", index=False)
    car_buy, car_match, car_rand, car_ws = map(np.array, (car_buy, car_match, car_rand, car_ws))
    pos_b = ev["i"].values
    pos_ws = wsell["i"].values

    B = lambda v, p=pos_b: block_boot(v, p)
    main_tab = {
        "buy_raw10": B(ev.raw10), "buy_ex10": B(ev.ex10), "buy_car10": B(ev.car10),
        "match_car10": B(ev.match_car10), "rand_car10": B(ev.rand_car10),
        "ws_car10": block_boot(car_ws[:, H], pos_ws),
        "buy_minus_match": B(ev.alpha_vs_match), "buy_minus_rand": B(ev.car10 - ev.rand_car10),
        "match_minus_rand": B(ev.match_car10 - ev.rand_car10),
        "buy_car5": B(ev.car5), "buy_hit10": B((ev.raw10 > 0).astype(float)),
        "match_hit10": B((ev.match_raw10 > 0).astype(float)),
    }

    # 4. exit-policy decomposition -------------------------------------------
    stops = [0.5, 1.0, 1.5, 2.0, 3.0, 4.0, None]
    tgts = [2.0, 3.0, 5.0, 8.0, None]
    grid = np.zeros((len(stops), len(tgts)))
    for a, ks in enumerate(stops):
        for b, kt in enumerate(tgts):
            vals = []
            for r in ev.itertuples():
                c0 = P["C"][r.ticker].iloc[r.i]
                vals.append(replay(P, r.i, r.ticker, c0 - ks * r.atr if ks else None,
                                   c0 + kt * r.atr if kt else None)[0] - COST)
            grid[a, b] = np.mean(vals)
    dep, dep_exit = [], []
    for r in ev.itertuples():
        c0 = P["C"][r.ticker].iloc[r.i]
        ok = r.tgt_rec and r.stop_rec and r.tgt_rec > r.entry_rec > r.stop_rec
        s = c0 * r.stop_rec / r.entry_rec if ok else None
        g = c0 * r.tgt_rec / r.entry_rec if ok else None
        v, why = replay(P, r.i, r.ticker, s, g)
        dep.append(v - COST)
        dep_exit.append(why)
    ev["deployed_ret"], ev["deployed_exit"] = dep, dep_exit
    ev["deployed_stop_pct"] = (ev.entry_rec - ev.stop_rec) / ev.entry_rec
    close0 = np.array([P["C"][r.ticker].iloc[r.i] for r in ev.itertuples()])
    ev["deployed_stop_in_daily_atr"] = ev.deployed_stop_pct * close0 / ev.atr
    hold_net = ev.raw10 - COST
    exit_tab = {
        "hold_net": B(hold_net), "deployed_net": B(ev.deployed_ret),
        "deployed_minus_hold": B(ev.deployed_ret - hold_net),
        "deployed_stop_rate": float((ev.deployed_exit == "STOP").mean()),
        "deployed_target_rate": float((ev.deployed_exit == "TARGET").mean()),
        "deployed_winrate": float((ev.deployed_ret > 0).mean()),
        "hold_winrate": float((hold_net > 0).mean()),
        "median_stop_pct": float(ev.deployed_stop_pct.median()),
        "median_stop_atr": float(ev.deployed_stop_in_daily_atr.median()),
        "grid": grid.tolist(), "stops": [s or "none" for s in stops], "tgts": [t or "none" for t in tgts],
    }

    # 5. calibration -----------------------------------------------------------
    succ = (ev.deployed_exit == "TARGET").astype(float)
    win = (ev.ex10 > 0).astype(float)
    bins = [0, 0.7, 0.8, 0.85, 0.9, 1.01]
    ev["cbin"] = pd.cut(ev.conf, bins, right=False)
    calib = ev.assign(win=win, succ=succ).groupby("cbin", observed=True).agg(
        n=("conf", "size"), conf=("conf", "mean"), win=("win", "mean"), succ=("succ", "mean"),
        car10=("car10", "mean"), alpha=("alpha_vs_match", "mean")).reset_index()
    ece = float((calib.n * (calib.conf - calib.win).abs()).sum() / calib.n.sum())
    conf_v, car_v = ev.conf.values, ev.car10.values
    rho_boot = block_boot(np.arange(len(ev)), pos_b,
                          stat=lambda idx: stats.spearmanr(conf_v[idx.astype(int)], car_v[idx.astype(int)])[0])
    cal_tab = {"ece": ece, "brier": float(((ev.conf - win) ** 2).mean()),
               "brier_base": float(((win.mean() - win) ** 2).mean()),
               "mean_conf": float(ev.conf.mean()), "win_rate": float(win.mean()),
               "spearman": rho_boot, "table": calib.astype({"cbin": str}).to_dict("records")}

    # 6. portfolio simulation --------------------------------------------------
    T = len(dates)

    def port(entries):
        """entries: list of (i, ticker, weight, exit_offset). Daily signal-weighted returns."""
        num, den = np.zeros(T), np.zeros(T)
        R = P["ret"]
        for i, t, w, k_exit in entries:
            rr = R[t].values[i + 1:i + k_exit + 1].copy()
            rr[0] -= COST / 2
            rr[-1] -= COST / 2
            num[i + 1:i + k_exit + 1] += w * rr
            den[i + 1:i + k_exit + 1] += w
        return pd.Series(np.where(den > 0, num / np.maximum(den, 1e-12), 0.0), index=dates)

    llm_entries = [(r.i, r.ticker, 1.0, H) for r in ev.itertuples()]
    match_entries = []
    for r in ev.itertuples():
        i, t = r.i, r.ticker
        feats = pd.DataFrame({"rsi": P["rsi"].iloc[i], "mom": P["mom"].iloc[i], "atr": P["atr_pct"].iloc[i]})
        feats = feats.loc[[u for u in universe if (i, u) not in picked]].dropna()
        z = (feats - feats.mean()) / feats.std()
        me = (np.array([P["rsi"][t].iloc[i], P["mom"][t].iloc[i], P["atr_pct"][t].iloc[i]]) - feats.mean().values) / feats.std().values
        nb = [u for u in z.index[((z.values - me) ** 2).sum(1).argsort()] if valid(P, i, u)][:K_MATCH]
        match_entries += [(i, u, 1.0 / K_MATCH, H) for u in nb]
    rule_entries = []
    for i in range(ev.i.min(), ev.i.max() + 1):
        low = P["rsi"].iloc[i].drop("SPY")
        rule_entries += [(i, u, 1.0, H) for u in low[low < 25].index if valid(P, i, u)]

    start, end = ev.i.min() + 1, ev.i.max() + H + 1
    series = {"LLM agent": port(llm_entries), "Matched placebo": port(match_entries),
              "RSI<25 rule": port(rule_entries), "SPY": P["ret"]["SPY"]}
    series = {k: v.iloc[start:end] for k, v in series.items()}
    port_tab = {}
    for k, v in series.items():
        pr = perf(v)
        (a, b), (ta, tb) = hac_ols(v.values, series["SPY"].values)
        pr.update({"alpha_ann": a * 252, "alpha_t": ta, "beta": b})
        port_tab[k] = pr
    ls = series["LLM agent"] - series["Matched placebo"]
    port_tab["LLM minus placebo"] = {**perf(ls), "alpha_ann": ls.mean() * 252,
                                    "alpha_t": hac_ols(ls.values, series["SPY"].values)[1][0], "beta": np.nan}

    # 7. regimes ---------------------------------------------------------------
    ev["vix_bucket"] = pd.cut(ev.vix, [0, 16, 20, 100], labels=["VIX<16", "16-20", "VIX>20"])
    reg = []
    for name, g in list(ev.groupby("vix_bucket", observed=True)) + [("SPY>SMA50", ev[ev.spy_up]), ("SPY<SMA50", ev[~ev.spy_up])]:
        bb = block_boot(g.alpha_vs_match, g.i)
        reg.append({"regime": str(name), "n": len(g), "car10": g.car10.mean(), "alpha": bb["mean"],
                    "lo": bb["lo"], "hi": bb["hi"], "p": bb["p"]})

    # robustness: horizons and next-open entry --------------------------------
    rob = {}
    for h in (1, 3, 5, 10):
        rob[f"h{h}"] = B([car_buy[j][h] - car_match[j][h] for j in range(len(ev))])
    nxt = []
    for r in ev.itertuples():
        o1 = P["O"][r.ticker].iloc[r.i + 1]
        s0, s1 = P["O"]["SPY"].iloc[r.i + 1], P["C"]["SPY"].iloc[r.i + H]
        nxt.append(P["C"][r.ticker].iloc[r.i + H] / o1 - 1 - (s1 / s0 - 1))
    rob["next_open_ex"] = B(nxt)
    rob["excl_top_decile_rsi"] = block_boot(ev.alpha_vs_match[ev.rsi_d > ev.rsi_d.quantile(0.1)],
                                            ev.i[ev.rsi_d > ev.rsi_d.quantile(0.1)])

    # descriptive --------------------------------------------------------------
    info = {
        "n_raw": n_raw, "raw_counts": raw_counts, "n_buy_unique": int((sig.decision == "BUY").sum()),
        "n_buy_eval": len(ev), "n_ws_eval": len(wsell), "n_tickers_buy": int(ev.ticker.nunique()),
        "n_days_buy": int(ev.i.nunique()), "universe": len(universe),
        "first": str(dates[ev.i.min()].date()), "last": str(dates[ev.i.max()].date()),
        "eval_end": str(dates[min(ev.i.max() + H, T - 1)].date()),
        "median_rsi_buy": float(ev.rsi_d.median()), "mean_conf": float(ev.conf.mean()),
        "spy_total": float(series["SPY"].add(1).prod() - 1),
        "signals_per_day": float(len(ev) / ev.i.nunique()),
    }
    out = {"info": info, "main": main_tab, "exit": exit_tab, "calibration": cal_tab,
           "portfolio": port_tab, "regimes": reg, "robustness": rob}
    json.dump(out, open(RES / "analysis.json", "w"), indent=2, default=float)

    figures(car_buy, car_match, car_rand, car_ws, series, exit_tab, calib)
    macros(out)
    print(json.dumps(out, indent=1, default=lambda x: round(float(x), 4)))


# ── figures ───────────────────────────────────────────────────────────────────

def figures(car_buy, car_match, car_rand, car_ws, series, exit_tab, calib):
    x = np.arange(H + 1)
    fig, ax = plt.subplots(figsize=(3.4, 2.2))
    for arr, lab, c, ls in [(car_buy, "LLM BUY", "#1f4e79", "-"), (car_match, "Matched placebo", "#c55a11", "--"),
                            (car_rand, "Random, same date", "#7f7f7f", ":"), (car_ws, "Overbought (WATCH SELL)", "#548235", "-.")]:
        m = 100 * arr.mean(0)
        se = 100 * arr.std(0, ddof=1) / np.sqrt(len(arr))
        ax.plot(x, m, ls, color=c, lw=1.2, label=lab)
        ax.fill_between(x, m - 1.96 * se, m + 1.96 * se, color=c, alpha=0.12, lw=0)
    ax.axhline(0, color="k", lw=0.4)
    ax.set_xlabel("Trading days after signal")
    ax.set_ylabel("Mean beta-adjusted CAR (%)")
    ax.legend(fontsize=6.5, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2)
    fig.savefig(FIGS / "event_study.pdf")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(3.4, 2.1))
    for (k, v), c, ls in zip(series.items(), ["#1f4e79", "#c55a11", "#548235", "k"], ["-", "--", "-.", ":"]):
        ax.plot(v.index, 100 * ((1 + v).cumprod() - 1), ls, color=c, lw=1.1, label=k)
    ax.set_ylabel("Cumulative return (%)")
    ax.legend(fontsize=6.5, loc="upper left")
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b"))
    ax.tick_params(axis="x", labelsize=7)
    fig.savefig(FIGS / "equity.pdf")
    plt.close(fig)

    g = 100 * np.array(exit_tab["grid"])
    fig, ax = plt.subplots(figsize=(3.4, 2.3))
    lim = np.abs(g).max()
    im = ax.imshow(g, cmap="RdBu", vmin=-lim, vmax=lim, aspect="auto")
    ax.set_xticks(range(len(exit_tab["tgts"])), [f"{t}" if t != "none" else "none" for t in exit_tab["tgts"]])
    ax.set_yticks(range(len(exit_tab["stops"])), [f"{s}" if s != "none" else "none" for s in exit_tab["stops"]])
    ax.set_xlabel("Target (x daily ATR)")
    ax.set_ylabel("Stop (x daily ATR)")
    for a in range(g.shape[0]):
        for b in range(g.shape[1]):
            ax.text(b, a, f"{g[a, b]:.2f}", ha="center", va="center", fontsize=6.5,
                    color="white" if abs(g[a, b]) > 0.6 * lim else "black")
    fig.colorbar(im, ax=ax, label="Mean net trade return (%)", shrink=0.9)
    fig.savefig(FIGS / "exit_grid.pdf")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(3.4, 2.2))
    ax.plot([0.5, 1], [0.5, 1], "k:", lw=0.6, label="Perfect calibration")
    ax.plot(calib.conf, calib.win, "o-", color="#1f4e79", ms=3, lw=1, label="P(beat SPY, 10d)")
    ax.plot(calib.conf, calib.succ, "s--", color="#c55a11", ms=3, lw=1, label="P(target before stop)")
    for r in calib.itertuples():
        ax.annotate(f"n={r.n}", (r.conf, r.win), fontsize=5.5, xytext=(2, 3), textcoords="offset points")
    ax.set_xlabel("Stated LLM confidence")
    ax.set_ylabel("Empirical frequency")
    ax.set_ylim(0, 1.02)
    ax.legend(fontsize=6.5, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3)
    fig.savefig(FIGS / "calibration.pdf")
    plt.close(fig)


# ── LaTeX macros so the paper stays in sync with the data ─────────────────────

def macros(o):
    pc = lambda v, d=2: f"{100 * v:+.{d}f}"
    pu = lambda v, d=1: f"{100 * v:.{d}f}"
    ci = lambda b: f"[{100 * b['lo']:+.2f}, {100 * b['hi']:+.2f}]"
    pv = lambda b: f"{b['p']:.3f}" if b["p"] >= 0.001 else "$<$0.001"
    I, M, E, C, Pf = o["info"], o["main"], o["exit"], o["calibration"], o["portfolio"]
    m = {
        "nRaw": f"{I['n_raw']:,}", "nBuy": f"{I['n_buy_eval']:,}", "nWS": f"{I['n_ws_eval']:,}",
        "nTick": I["n_tickers_buy"], "nDays": I["n_days_buy"], "nUniv": I["universe"],
        "dFirst": I["first"], "dLast": I["last"], "dEvalEnd": I["eval_end"],
        "medRSI": f"{I['median_rsi_buy']:.1f}", "meanConf": f"{I['mean_conf']:.2f}",
        "sigPerDay": f"{I['signals_per_day']:.1f}", "spyTotal": pc(I["spy_total"], 1),
    }
    for k, b in M.items():
        key = "".join(p.capitalize() for p in k.replace("10", "Ten").replace("5", "Five").split("_"))
        m["m" + key] = pc(b["mean"]) if "hit" not in k else pu(b["mean"])
        m["m" + key + "CI"] = ci(b)
        m["m" + key + "P"] = pv(b)
    m.update({"holdNet": pc(E["hold_net"]["mean"]), "holdNetCI": ci(E["hold_net"]),
              "depNet": pc(E["deployed_net"]["mean"]), "depNetCI": ci(E["deployed_net"]),
              "depGap": pc(E["deployed_minus_hold"]["mean"]), "depGapCI": ci(E["deployed_minus_hold"]),
              "depGapP": pv(E["deployed_minus_hold"]),
              "depStopRate": pu(E["deployed_stop_rate"]), "depTgtRate": pu(E["deployed_target_rate"]),
              "depWin": pu(E["deployed_winrate"]), "holdWin": pu(E["hold_winrate"]),
              "medStopPct": pu(E["median_stop_pct"], 2), "medStopATR": f"{E['median_stop_atr']:.2f}",
              "gridBest": pc(np.max(E["grid"])), "gridWorst": pc(np.min(E["grid"])),
              "ece": f"{C['ece']:.3f}", "brier": f"{C['brier']:.3f}", "brierBase": f"{C['brier_base']:.3f}",
              "calConf": f"{C['mean_conf']:.2f}", "calWin": pu(C["win_rate"]),
              "rhoConf": f"{C['spearman']['mean']:+.3f}",
              "rhoConfCI": f"[{C['spearman']['lo']:+.3f}, {C['spearman']['hi']:+.3f}]"})
    for k, v in Pf.items():
        key = {"LLM agent": "Llm", "Matched placebo": "Match", "RSI<25 rule": "Rule",
               "SPY": "Spy", "LLM minus placebo": "LS"}[k]
        m[f"p{key}Tot"] = pc(v["total"], 1)
        m[f"p{key}Vol"] = pu(v["vol"], 1)
        m[f"p{key}Sh"] = f"{v['sharpe']:.2f}"
        m[f"p{key}Mdd"] = pc(v["mdd"], 1)
        m[f"p{key}Alpha"] = pc(v["alpha_ann"], 1)
        m[f"p{key}AlphaT"] = "--" if key == "Spy" else f"{v['alpha_t']:.2f}"
        if key == "Spy":
            m[f"p{key}Alpha"] = "--"
        m[f"p{key}Beta"] = "--" if np.isnan(v["beta"]) else f"{v['beta']:.2f}"
    R = o["robustness"]
    for k, b in R.items():
        key = "".join(p.capitalize() for p in k.replace("1", "One").replace("3", "Three").replace("5", "Five")
                      .replace("0", "Zero").split("_"))
        m["r" + key] = pc(b["mean"])
        m["r" + key + "CI"] = ci(b)
    m["gridHalfNoTgt"] = pc(E["grid"][0][-1])
    with open(PAPER / "results_macros.tex", "w") as f:
        f.write("% Auto-generated by paper_analysis.py -- do not edit by hand\n")
        for k, v in m.items():
            f.write(f"\\newcommand{{\\{k}}}{{{v}}}\n")
        # regime and calibration tables as ready-made rows
        f.write("\\newcommand{\\regimeRows}{%\n")
        for r in o["regimes"]:
            f.write(f"{r['regime'].replace('<', '$<$').replace('>', '$>$')} & {r['n']} & {pc(r['car10'])} & "
                    f"{pc(r['alpha'])} & [{100 * r['lo']:+.2f}, {100 * r['hi']:+.2f}] & {pv(r)} \\\\\n")
        f.write("}\n\\newcommand{\\calibRows}{%\n")
        for r in C["table"]:
            f.write(f"${r['cbin'].replace('1.01)', '1.0]')}$ & {r['n']} & {r['conf']:.2f} & {pu(r['win'])} & "
                    f"{pu(r['succ'])} & {pc(r['alpha'])} \\\\\n")
        f.write("}\n")


if __name__ == "__main__":
    main()
