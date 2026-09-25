"""
How much does the paper's null depend on the design of its placebo?

paper_power.py showed that a picker with NO skill (random names from the 50 lowest-RSI stocks) earns about +0.27 pp over its matched placebo, so the
placebo is not an unbiased benchmark for extreme, oversold picks. Here the placebo is varied and, for every variant, the same no-skill pickers are
re-run so the real LLM can be read against the right zero:

    variant               what changes
    base (K=10)           RSI, 20-day momentum, ATR%   (the paper's placebo)
    K=5, K=20             number of matched neighbours
    richer features       + 5-day return, distance below the 20-day high, beta
    same sector           base features, neighbours restricted to the same GICS sector
    index-only signals    base placebo, but only LLM signals on S&P 500 constituents (drops the 14.7% non-index signals)

Reported per variant: the LLM's alpha over the placebo (block-bootstrap 95% CI), the no-skill picker's alpha (the placebo's bias), the LLM's alpha
minus that bias, and the share of no-skill pickers the LLM does worse than.

    python paper_sensitivity.py [--sets 150]  ->  paper_results/sensitivity.json, paper/results_sensitivity.tex
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import audit_core as core

HERE = Path(__file__).parent
RES = HERE / "paper_results"
DEV_DB = HERE.parent / "paper/data/backtest_ec2_2026-01-06_to_2026-09-24.db"
POOL, BLOCK = 50, core.BLOCK
rng = np.random.default_rng(2031)
VARIANTS = {"base (K=10)": dict(K=10, rich=False, sector=False, index_only=False),
            "K=5": dict(K=5, rich=False, sector=False, index_only=False),
            "K=20": dict(K=20, rich=False, sector=False, index_only=False),
            "richer features": dict(K=10, rich=True, sector=False, index_only=False),
            "same sector": dict(K=10, rich=False, sector=True, index_only=False),
            "index-only signals": dict(K=10, rich=False, sector=False, index_only=True)}


def load():
    sig, _, _ = core.load_signals(DEV_DB)
    fixed = core.fixed_universe()
    P = core.load_panel(sorted(set(sig.ticker.unique()) | set(fixed)), sig.day.min() - pd.Timedelta(days=140), core.DATA_END, cache_dir=RES)
    dates = P["C"].index
    universe = [t for t in fixed if t in P["C"].columns and t != "SPY"]
    sig["i"] = dates.searchsorted(sig["day"], side="right") - 1
    buys = sig[sig.decision == "BUY"]
    buys = buys[[core.valid(P, r.i, r.ticker) for r in buys.itertuples()]]
    sectors = json.loads((HERE / "dashboard" / "sectors.json").read_text())
    C = P["C"]
    hi20 = C.rolling(20).max()
    return P, buys, universe, sectors, C, hi20


def day_arrays(P, buys, universe, sectors, C, hi20, rich: bool):
    """Per real BUY date: standardized features and CARs of every valid universe stock, sectors, and where the real picks sit."""
    out = []
    for i, grp in buys.groupby("i"):
        ok = [u for u in universe if core.valid(P, i, u)]
        cols = {"rsi": P["rsi"].iloc[i][ok], "mom": P["mom"].iloc[i][ok], "atr": P["atr_pct"].iloc[i][ok]}
        if rich:
            cols.update(ret5=(C.iloc[i][ok] / C.iloc[i - 5][ok] - 1), below=(C.iloc[i][ok] / hi20.iloc[i][ok] - 1), beta=P["beta"].iloc[i][ok])
        X = pd.DataFrame(cols).dropna()
        z = ((X - X.mean()) / X.std()).to_numpy()
        car = np.array([core.car_path(P, i, u)[0][core.H] for u in X.index])
        pos = {u: k for k, u in enumerate(X.index)}
        # the real LLM's picks: in the pool (index members with data) or off-pool (non-members, matched too, but never used as placebo)
        real_pool = [pos[t] for t in grp.ticker if t in pos]
        real_off = []
        for t in grp.ticker:
            if t not in pos and t in P["C"].columns and not np.isnan(P["rsi"][t].iloc[i]):
                f = [P["rsi"][t].iloc[i], P["mom"][t].iloc[i], P["atr_pct"][t].iloc[i]]
                if rich:
                    f += [C[t].iloc[i] / C[t].iloc[i - 5] - 1, C[t].iloc[i] / hi20[t].iloc[i] - 1, P["beta"][t].iloc[i]]
                if not np.isnan(f).any():
                    mu, sd = X.mean().to_numpy(), X.std().to_numpy()
                    real_off.append(((np.array(f) - mu) / sd, core.car_path(P, i, t)[0][core.H]))
        out.append({"i": int(i), "n": len(grp), "z": z, "car": car, "sector": np.array([sectors.get(u, "Other") for u in X.index]),
                    "pool": np.argsort(X["rsi"].to_numpy())[:POOL], "real_pool": real_pool, "real_off": real_off})
    return out


def delta(d, z_pick, car_pick, excl, K, sector_pick=None):
    dist = ((d["z"] - z_pick) ** 2).sum(1)
    dist[excl] = np.inf
    if sector_pick is not None:
        same = d["sector"] == sector_pick
        if (same & ~excl).sum() >= K:
            dist[~same] = np.inf
    nn = np.argpartition(dist, K)[:K]
    return car_pick - d["car"][nn].mean()


def real_deltas(days, K, sector, index_only):
    a, b = [], []
    for d in days:
        excl = np.zeros(len(d["car"]), bool)
        excl[d["real_pool"]] = True
        for p in d["real_pool"]:
            a.append(delta(d, d["z"][p], d["car"][p], excl, K, d["sector"][p] if sector else None))
            b.append(d["i"] // BLOCK)
        if not index_only:
            for z_p, car_p in d["real_off"]:
                a.append(delta(d, z_p, car_p, excl, K))
                b.append(d["i"] // BLOCK)
    return np.array(a), np.array(b)


def fake_deltas(days, K, sector):
    a, b = [], []
    for d in days:
        n = len(d["real_pool"]) + (0 if False else len(d["real_off"]))
        picks = rng.choice(d["pool"], size=min(max(n, 1), len(d["pool"])), replace=False)
        excl = np.zeros(len(d["car"]), bool)
        excl[picks] = True
        for p in picks:
            a.append(delta(d, d["z"][p], d["car"][p], excl, K, d["sector"][p] if sector else None))
            b.append(d["i"] // BLOCK)
    return np.array(a)


def block_ci(alpha, block, reps=4000):
    ub, inv = np.unique(block, return_inverse=True)
    S, n = np.bincount(inv, weights=alpha), np.bincount(inv)
    idx = rng.integers(0, len(S), size=(reps, len(S)))
    means = S[idx].sum(1) / n[idx].sum(1)
    return float(alpha.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def main():
    n_sets = int(sys.argv[sys.argv.index("--sets") + 1]) if "--sets" in sys.argv else 150
    P, buys, universe, sectors, C, hi20 = load()
    cache, out = {}, {"n_sets": n_sets, "variants": {}}
    for name, cfg in VARIANTS.items():
        key = cfg["rich"]
        if key not in cache:
            cache[key] = day_arrays(P, buys, universe, sectors, C, hi20, cfg["rich"])
        days = cache[key]
        a, b = real_deltas(days, cfg["K"], cfg["sector"], cfg["index_only"])
        est, lo, hi = block_ci(a, b)
        fake = np.array([fake_deltas(days, cfg["K"], cfg["sector"]).mean() for _ in range(n_sets)])
        bias, sd = float(fake.mean()), float(fake.std(ddof=1))
        out["variants"][name] = {"n_signals": int(len(a)), "llm_delta": est, "lo": lo, "hi": hi, "random_picker_delta": bias, "random_picker_sd": sd,
                                 "llm_minus_bias": est - bias, "llm_below_share_of_random_pickers": float((fake >= est).mean())}
        v = out["variants"][name]
        print(f"{name:20} n={v['n_signals']:5}  LLM {est * 100:+.2f}% [{lo * 100:+.2f},{hi * 100:+.2f}]   random no-skill pickers {bias * 100:+.2f}% (sd {sd * 100:.2f})   "
              f"LLM - bias {v['llm_minus_bias'] * 100:+.2f} pp   worse than {v['llm_below_share_of_random_pickers'] * 100:.0f}% of random pickers", flush=True)
    RES.mkdir(exist_ok=True)
    (RES / "sensitivity.json").write_text(json.dumps(out, indent=1))
    write_tex(out)


def write_tex(o: dict):
    """LaTeX for the paper (paper/results_sensitivity.tex), so the table cannot drift from the code."""
    rows = []
    for name, v in o["variants"].items():
        f = lambda x: f"{x * 100:+.2f}"
        rows.append(f"{name} & ${f(v['llm_delta'])}\\;[{f(v['lo'])},{f(v['hi'])}]$ & ${f(v['random_picker_delta'])}$ & ${f(v['llm_minus_bias'])}$ & {v['llm_below_share_of_random_pickers'] * 100:.0f} \\\\ ")
    v = o["variants"]
    llm = [x["llm_delta"] * 100 for x in v.values()]
    bias = [x["random_picker_delta"] * 100 for x in v.values()]
    tex = ("% generated by paper_sensitivity.py; do not edit\n"
           f"\\newcommand{{\\sensLo}}{{{min(llm):+.2f}}}\n\\newcommand{{\\sensHi}}{{{max(llm):+.2f}}}\n"
           f"\\newcommand{{\\sensBiasLo}}{{{min(bias):+.2f}}}\n\\newcommand{{\\sensBiasHi}}{{{max(bias):+.2f}}}\n"
           f"\\newcommand{{\\sensRichWorse}}{{{v['richer features']['llm_below_share_of_random_pickers'] * 100:.0f}}}\n"
           f"\\newcommand{{\\sensAllSpan}}{{{'yes' if all(x['lo'] < 0 < x['hi'] for x in v.values()) else 'no'}}}\n"
           "\\newcommand{\\sensRows}{%\n" + "\n".join(rows) + "}\n")
    (HERE.parent / "paper" / "results_sensitivity.tex").write_text(tex)


if __name__ == "__main__":
    main()
