"""
Does the paper's inference procedure work? A Monte-Carlo validation of the audit itself, on the REAL price panel.

The audit compares an LLM's BUY picks with characteristic-matched placebo stocks and infers from ~15 independent ten-day blocks. Two questions a
reviewer must ask, and that the paper never answered:

  1. SIZE.  If the "LLM" has NO edge, how often does each procedure still report one?  We build many FAKE LLMs: on every date that had real BUYs, pick the
     same number of stocks AT RANDOM from the 50 lowest-RSI names (mimicking the pre-screen), then run the identical placebo comparison.
     By construction their true alpha is zero, so a 95% procedure should reject about 5% of the time.
  2. POWER.  Add a known edge delta to each fake LLM's returns and count how often each procedure finds it; the smallest delta found 80% of the time is
     the EMPIRICAL minimum detectable effect (the paper's 2.8 x SE is a formula, not a measurement).

Procedures compared (all on the same per-signal alpha vs. the matched placebo, blocks of 10 trading days):
     percentile block bootstrap   (what the paper used)
     cluster-robust t             (CR1 variance over blocks, t with B-1 degrees of freedom)
     sign-flip permutation        (randomly flips the sign of each block's total: exact under symmetry, valid for few clusters)

    python paper_power.py [--sets 300]   ->  paper_results/power.json, paper/results_power.tex
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
K, POOL, BLOCK = 10, 50, core.BLOCK
DELTAS = (0.0, 0.005, 0.010, 0.015, 0.020)
rng = np.random.default_rng(2030)


def prepare():
    """Per real BUY date: the standardized feature matrix, CARs of every valid universe stock, and how many picks the real LLM made."""
    sig, _, _ = core.load_signals(DEV_DB)
    fixed = core.fixed_universe()
    P = core.load_panel(sorted(set(sig.ticker.unique()) | set(fixed)), sig.day.min() - pd.Timedelta(days=140), core.DATA_END, cache_dir=RES)
    dates = P["C"].index
    universe = [t for t in fixed if t in P["C"].columns and t != "SPY"]
    sig["i"] = dates.searchsorted(sig["day"], side="right") - 1
    buys = sig[sig.decision == "BUY"]
    buys = buys[[core.valid(P, r.i, r.ticker) for r in buys.itertuples()]]
    per_date = buys.groupby("i").size()
    days = []
    for i, n in per_date.items():
        ok = [u for u in universe if core.valid(P, i, u)]
        X = pd.DataFrame({"rsi": P["rsi"].iloc[i][ok], "mom": P["mom"].iloc[i][ok], "atr": P["atr_pct"].iloc[i][ok]}).dropna()
        z = ((X - X.mean()) / X.std()).to_numpy()
        car = np.array([core.car_path(P, i, u)[0][core.H] for u in X.index])
        pool = np.argsort(X["rsi"].to_numpy())[:POOL]                      # the pre-screen's oversold candidates
        days.append({"i": int(i), "n": int(n), "z": z, "car": car, "pool": pool})
    return days


def fake_llm(days: list):
    """One fake LLM: random picks from the oversold pool on every date; returns per-signal alpha vs. the matched placebo and block ids."""
    alpha, block = [], []
    for d in days:
        picks = rng.choice(d["pool"], size=min(d["n"], len(d["pool"])), replace=False)
        excl = np.zeros(len(d["car"]), bool)
        excl[picks] = True
        for p in picks:
            dist = ((d["z"] - d["z"][p]) ** 2).sum(1)
            dist[excl] = np.inf                                            # placebo names exclude the day's picks, as in the paper
            nn = np.argpartition(dist, K)[:K]
            alpha.append(d["car"][p] - d["car"][nn].mean())
            block.append(d["i"] // BLOCK)
    return np.array(alpha), np.array(block)


def block_sums(alpha, block):
    ub, inv = np.unique(block, return_inverse=True)
    S = np.bincount(inv, weights=alpha)
    n = np.bincount(inv)
    return S, n


def percentile_boot(S, n, reps=1000):
    B = len(S)
    idx = rng.integers(0, B, size=(reps, B))
    means = S[idx].sum(1) / n[idx].sum(1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    return lo > 0 or hi < 0


def cluster_t(S, n):
    from scipy import stats
    B, N = len(S), n.sum()
    m = S.sum() / N
    se = np.sqrt(B / (B - 1) * ((S - n * m) ** 2).sum()) / N
    return abs(m / se) > stats.t.ppf(0.975, B - 1) if se > 0 else False


def sign_flip(S, n, reps=2000):
    obs = abs(S.sum())
    flips = rng.choice([-1.0, 1.0], size=(reps, len(S)))
    return (np.abs(flips @ S) >= obs).mean() < 0.05


PROCS = {"percentile block bootstrap": percentile_boot, "cluster-robust t": cluster_t, "sign-flip permutation": sign_flip}


def main():
    n_sets = int(sys.argv[sys.argv.index("--sets") + 1]) if "--sets" in sys.argv else 300
    days = prepare()
    n_blocks = len({d["i"] // BLOCK for d in days})
    print(f"{sum(d['n'] for d in days)} signals on {len(days)} dates in {n_blocks} blocks; {n_sets} fake LLMs; K={K}, pool={POOL}", flush=True)
    sets = [fake_llm(days) for _ in range(n_sets)]                        # fake LLMs with zero true skill
    means = np.array([a.mean() for a, _ in sets])
    bias = float(means.mean())                                           # what a no-skill picker earns "over" its placebo: the placebo is not unbiased
    real = json.loads((RES / "analysis.json").read_text())["main"]["buy_minus_match"]["mean"]
    rej = {p: {dl: 0 for dl in DELTAS} for p in PROCS}
    for alpha, block in sets:
        for dl in DELTAS:
            S, n = block_sums(alpha - bias + dl, block)                   # centred: the null is now exactly true, so rejections = procedure error
            for name, f in PROCS.items():
                rej[name][dl] += bool(f(S, n))
    sd = float(means.std(ddof=1))
    out = {"n_sets": n_sets, "n_blocks": n_blocks, "n_signals": int(sum(d["n"] for d in days)), "placebo_bias_of_random_oversold_picks": bias,
           "sd_of_mean_alpha_under_null": sd, "empirical_mde_2p8sd": 2.8 * sd, "real_llm_delta": real,
           "real_llm_percentile_among_random_pickers": float((means <= real).mean()),
           "rejection_rate_centred": {p: {str(dl): rej[p][dl] / n_sets for dl in DELTAS} for p in PROCS}}
    RES.mkdir(exist_ok=True)
    (RES / "power.json").write_text(json.dumps(out, indent=1))
    write_tex(out)
    print(f"\nrandom no-skill pickers earn {bias * 100:+.3f}% over their matched placebo (sampling SD {sd * 100:.2f} pp); the real LLM earned {real * 100:+.3f}%, "
          f"which is below {100 * (1 - out['real_llm_percentile_among_random_pickers']):.0f}% of random pickers")
    print(f"empirical minimum detectable effect ~ {2.8 * sd * 100:.2f} pp")
    print(f"{'procedure (centred, so 0.0 = exact null)':44}" + "".join(f"{'delta=' + format(dl * 100, '.1f') + '%':>12}" for dl in DELTAS))
    for p in PROCS:
        print(f"{p:44}" + "".join(f"{out['rejection_rate_centred'][p][str(dl)] * 100:11.1f}%" for dl in DELTAS))


def write_tex(o: dict):
    """LaTeX for the paper (paper/results_power.tex), so the table cannot drift from the code."""
    rows = []
    for p, r in o["rejection_rate_centred"].items():
        cells = " & ".join(f"{r[str(dl)] * 100:.1f}" for dl in DELTAS)
        rows.append(f"{p} & {cells} \\\\ ")
    tex = ("% generated by paper_power.py; do not edit\n"
           f"\\newcommand{{\\powSets}}{{{o['n_sets']}}}\n\\newcommand{{\\powBlocks}}{{{o['n_blocks']}}}\n"
           f"\\newcommand{{\\powSD}}{{{o['sd_of_mean_alpha_under_null'] * 100:.2f}}}\n\\newcommand{{\\powMDE}}{{{o['empirical_mde_2p8sd'] * 100:.2f}}}\n"
           f"\\newcommand{{\\powBias}}{{{o['placebo_bias_of_random_oversold_picks'] * 100:+.2f}}}\n\\newcommand{{\\powRealPct}}{{{o['real_llm_percentile_among_random_pickers'] * 100:.0f}}}\n"
           + "".join(f"\\newcommand{{\\{n}}}{{{v:.1f}}}\n" for n, v in (
               ("powSizeBoot", o["rejection_rate_centred"]["percentile block bootstrap"]["0.0"] * 100), ("powSizeT", o["rejection_rate_centred"]["cluster-robust t"]["0.0"] * 100),
               ("powSizePerm", o["rejection_rate_centred"]["sign-flip permutation"]["0.0"] * 100),
               ("powPwrHalf", o["rejection_rate_centred"]["percentile block bootstrap"]["0.005"] * 100), ("powPwrOne", o["rejection_rate_centred"]["percentile block bootstrap"]["0.01"] * 100)))
           + "\\newcommand{\\powRows}{%\n" + "\n".join(rows) + "}\n")
    (HERE.parent / "paper" / "results_power.tex").write_text(tex)


if __name__ == "__main__":
    main()
