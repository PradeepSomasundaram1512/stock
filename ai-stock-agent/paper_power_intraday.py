"""
The same validation as paper_power.py / paper_sensitivity.py, for the INTRADAY result (the paper's sharpest claim).

The intraday audit (paper_intraday.py) enters at the close of the 60-minute bar containing the signal, exits at 16:00 ET, and builds its placebo from the
K nearest non-selected stocks in the pre-screen's own hourly feature space (RSI-14, 5-bar momentum, ATR%, volume ratio) at the last completed bar.
Blocks are trading days (about 119 of them). Here, exactly as before:

  * FAKE LLMs (no skill): on every (day, bar) with real BUYs, pick the same number of stocks at random from the 50 lowest-hourly-RSI names, compare each
    with the same placebo, and measure how often each inference procedure reports an edge (size), and how often it finds an injected one (power);
  * the placebo's BIAS for such picks is the average alpha of a no-skill fake LLM;
  * the placebo is varied (K, richer features, same sector, index-only) and the real LLM is read against the no-skill picker under each design.

Standardisation uses all universe names valid at the bar (the real code excludes the day's picks): a small approximation, stated in the paper.

    python paper_power_intraday.py [--sets 300]  ->  paper_results/power_intraday.json, paper/results_power_intraday.tex
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import audit_core as core
import paper_intraday as pi
import paper_power as pp

pa = pi.pa
HERE = Path(__file__).parent
RES = pa.RES
POOL = 50
rng = np.random.default_rng(2032)
DELTAS = (0.0, 0.0003, 0.0005, 0.0008, 0.0012)       # true edges added to each signal's return, as fractions (0.03% ... 0.12%)
VARIANTS = {"base (K=10)": dict(K=10, rich=False, sector=False, index_only=False), "K=5": dict(K=5, rich=False, sector=False, index_only=False),
            "K=20": dict(K=20, rich=False, sector=False, index_only=False), "richer features": dict(K=10, rich=True, sector=False, index_only=False),
            "same sector": dict(K=10, rich=False, sector=True, index_only=False), "index-only signals": dict(K=10, rich=False, sector=False, index_only=True)}


def load():
    sig, _, _ = core.load_signals(pp.DEV_DB)          # explicit path: paper_analysis would read sys.argv[1] as the database
    buys = sig[sig.decision == "BUY"].copy()
    buys["ts"] = pd.to_datetime(buys.recommendation_date, format="mixed").dt.tz_localize("UTC").dt.tz_convert("America/New_York")
    buys = buys[(buys.ts.dt.time >= pd.Timestamp("09:30").time()) & (buys.ts.dt.time < pd.Timestamp("16:00").time())]
    fixed = pa.fixed_universe()
    C, Hh, L, F = pi.load_hourly(sorted(set(buys.ticker.unique()) | set(fixed)), buys.ts.min().normalize() - pd.Timedelta(days=10))
    bars = C.index.as_unit("ns")
    buys["ts"] = buys.ts.dt.as_unit("ns").dt.tz_convert(bars.tz)
    return buys, C, F, bars, [t for t in fixed if t in C.columns and t != "SPY"]


def groups(buys, C, F, bars, universe, sectors, rich):
    """{day_index: [group per (day, bar) with real BUYs]}: standardised features and window excess returns of every valid universe stock."""
    day = bars.normalize()
    udays = np.unique(day)
    feats = dict(F)
    if rich:
        feats["ret3"] = C / C.shift(3) - 1
        feats["below20"] = C / C.rolling(20).max() - 1
    keys = list(feats)
    fixed_set = set(universe)
    ev = {}
    for r in buys.itertuples():
        t = r.ticker
        if t not in C.columns:
            continue
        b = bars.searchsorted(r.ts, side="right") - 1
        if b < 1 or day[b] != r.ts.normalize():
            continue
        last = np.where(day == day[b])[0][-1]
        if b >= last or np.isnan(C[t].values[b:last + 1]).any():
            continue
        ev.setdefault((int(np.searchsorted(udays, day[b])), int(b), int(last)), []).append(t)
    out = {}
    for (di, b, last), picks in ev.items():
        spy = C["SPY"].values[last] / C["SPY"].values[b] - 1
        X = pd.DataFrame({k: v.iloc[b - 1] for k, v in feats.items()}).reindex(universe + [p for p in picks if p not in fixed_set])
        ok = X.notna().all(axis=1).to_numpy() & np.isfinite(X.to_numpy()).all(axis=1)
        path_ok = np.array([not np.isnan(C[u].values[b:last + 1]).any() if u in C.columns else False for u in X.index])
        ex = np.array([(C[u].values[last] / C[u].values[b] - 1 - spy) if k else np.nan for u, k in zip(X.index, path_ok)])
        ok &= path_ok
        uni_mask = np.array([u in fixed_set for u in X.index])
        base = X[ok & uni_mask]
        mu, sd = base.mean(), base.std().replace(0, np.nan)
        Z = ((X - mu) / sd).to_numpy()
        names = np.array(list(X.index))
        out.setdefault(di, []).append({"b": b, "names": names, "Z": Z, "ex": ex, "ok": ok, "uni": uni_mask, "sector": np.array([sectors.get(u, "Other") for u in names]),
                                       "real": [p for p in picks if p in set(names[ok])], "pool_rank": np.argsort(np.where(ok & uni_mask, X["rsi"].to_numpy(), np.inf))[:POOL]})
    return out


def alpha_of(g, name, excl_names, K, sector):
    k = int(np.where(g["names"] == name)[0][0])
    cand = g["ok"] & g["uni"] & ~np.isin(g["names"], list(excl_names))
    d = ((g["Z"] - g["Z"][k]) ** 2).sum(1)
    d = np.where(cand, d, np.inf)
    if sector:
        same = g["sector"] == g["sector"][k]
        if (cand & same).sum() >= K:
            d = np.where(same, d, np.inf)
    nn = np.argpartition(d, K)[:K]
    return g["ex"][k] - np.nanmean(g["ex"][nn])


def real_alphas(gs, cfg, universe_set):
    a, blk = [], []
    for di, lst in gs.items():
        day_picks = {p for g in lst for p in g["real"]}
        for g in lst:
            for p in g["real"]:
                if cfg["index_only"] and p not in universe_set:
                    continue
                a.append(alpha_of(g, p, day_picks, cfg["K"], cfg["sector"]))
                blk.append(di)
    return np.array(a), np.array(blk)


def fake_alphas(gs, cfg, universe_set):
    a, blk = [], []
    for di, lst in gs.items():
        chosen = []
        for g in lst:
            n = len([p for p in g["real"] if not (cfg["index_only"] and p not in universe_set)])
            if n == 0:
                chosen.append([])
                continue
            pick = rng.choice(g["pool_rank"], size=min(n, len(g["pool_rank"])), replace=False)
            chosen.append([g["names"][i] for i in pick])
        day_picks = {p for c in chosen for p in c}
        for g, c in zip(lst, chosen):
            for p in c:
                a.append(alpha_of(g, p, day_picks, cfg["K"], cfg["sector"]))
                blk.append(di)
    return np.array(a), np.array(blk)


def main():
    n_sets = int(sys.argv[sys.argv.index("--sets") + 1]) if "--sets" in sys.argv else 300
    buys, C, F, bars, universe = load()
    sectors = json.loads((HERE / "dashboard" / "sectors.json").read_text())
    uset = set(universe)
    out = {"n_sets": n_sets, "variants": {}}
    base_gs = None
    for name, cfg in VARIANTS.items():
        gs = groups(buys, C, F, bars, universe, sectors, cfg["rich"])
        if name == "base (K=10)":
            base_gs = gs
        ra, rb = real_alphas(gs, cfg, uset)
        est, lo, hi = pp_ci(ra, rb)
        n_fake = n_sets if name == "base (K=10)" else max(100, n_sets // 3)
        fakes = [fake_alphas(gs, cfg, uset) for _ in range(n_fake)]
        means = np.array([f[0].mean() for f in fakes])
        v = {"n_signals": int(len(ra)), "n_blocks": int(len(np.unique(rb))), "llm_delta": est, "lo": lo, "hi": hi, "random_picker_delta": float(means.mean()),
             "random_picker_sd": float(means.std(ddof=1)), "llm_minus_bias": est - float(means.mean()), "llm_below_share_of_random_pickers": float((means >= est).mean())}
        if name == "base (K=10)":                               # size and power: only for the paper's own design
            bias = float(means.mean())
            rej = {p: {dl: 0 for dl in DELTAS} for p in pp.PROCS}
            for alpha, blk in fakes:
                for dl in DELTAS:
                    S, n = pp.block_sums(alpha - bias + dl, blk)
                    for pn, f in pp.PROCS.items():
                        rej[pn][dl] += bool(f(S, n))
            v["rejection_rate_centred"] = {pn: {str(dl): rej[pn][dl] / len(fakes) for dl in DELTAS} for pn in pp.PROCS}
            v["sd_of_mean_alpha_under_null"] = float(means.std(ddof=1))
            v["empirical_mde_2p8sd"] = 2.8 * v["sd_of_mean_alpha_under_null"]
        out["variants"][name] = v
        print(f"{name:20} n={v['n_signals']:5} blocks={v['n_blocks']:3}  LLM {est * 100:+.3f}% [{lo * 100:+.3f},{hi * 100:+.3f}]  no-skill {v['random_picker_delta'] * 100:+.3f}% "
              f"(sd {v['random_picker_sd'] * 100:.3f})  LLM-bias {v['llm_minus_bias'] * 100:+.3f} pp  worse than {v['llm_below_share_of_random_pickers'] * 100:.0f}%", flush=True)
    RES.mkdir(exist_ok=True)
    (RES / "power_intraday.json").write_text(json.dumps(out, indent=1))
    write_tex(out)
    b = out["variants"]["base (K=10)"]
    print(f"\nsize / power (centred), intraday, {b['n_blocks']} day-blocks:")
    print(f"{'procedure':30}" + "".join(f"{'d=' + format(dl * 100, '.2f') + '%':>10}" for dl in DELTAS))
    for pn in pp.PROCS:
        print(f"{pn:30}" + "".join(f"{b['rejection_rate_centred'][pn][str(dl)] * 100:9.1f}%" for dl in DELTAS))


def pp_ci(alpha, block, reps=4000):
    ub, inv = np.unique(block, return_inverse=True)
    S, n = np.bincount(inv, weights=alpha), np.bincount(inv)
    idx = rng.integers(0, len(S), size=(reps, len(S)))
    means = S[idx].sum(1) / n[idx].sum(1)
    return float(alpha.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def write_tex(o: dict):
    """LaTeX for the paper (paper/results_power_intraday.tex), so the tables cannot drift from the code."""
    f = lambda x: f"{x * 100:+.3f}"
    v = o["variants"]
    b = v["base (K=10)"]
    prow = [f"{pn} & " + " & ".join(f"{b['rejection_rate_centred'][pn][str(dl)] * 100:.1f}" for dl in DELTAS) + " \\\\ " for pn in pp.PROCS]
    srow = [f"{n} & ${f(x['llm_delta'])}\\;[{f(x['lo'])},{f(x['hi'])}]$ & ${f(x['random_picker_delta'])}$ & ${f(x['llm_minus_bias'])}$ & {x['llm_below_share_of_random_pickers'] * 100:.0f} \\\\ "
            for n, x in v.items()]
    llm = [x["llm_delta"] * 100 for x in v.values()]
    bias = [x["random_picker_delta"] * 100 for x in v.values()]
    rr = b["rejection_rate_centred"]
    tex = ("% generated by paper_power_intraday.py; do not edit\n"
           f"\\newcommand{{\\ipBlocks}}{{{b['n_blocks']}}}\n\\newcommand{{\\ipBias}}{{{b['random_picker_delta'] * 100:+.3f}}}\n\\newcommand{{\\ipSD}}{{{b['random_picker_sd'] * 100:.3f}}}\n"
           f"\\newcommand{{\\ipMDE}}{{{b['empirical_mde_2p8sd'] * 100:.3f}}}\n"
           f"\\newcommand{{\\ipSizeBoot}}{{{rr['percentile block bootstrap']['0.0'] * 100:.1f}}}\n\\newcommand{{\\ipSizeT}}{{{rr['cluster-robust t']['0.0'] * 100:.1f}}}\n"
           f"\\newcommand{{\\ipSizePerm}}{{{rr['sign-flip permutation']['0.0'] * 100:.1f}}}\n"
           f"\\newcommand{{\\ipLo}}{{{min(llm):+.3f}}}\n\\newcommand{{\\ipHi}}{{{max(llm):+.3f}}}\n\\newcommand{{\\ipBiasLo}}{{{min(bias):+.3f}}}\n\\newcommand{{\\ipBiasHi}}{{{max(bias):+.3f}}}\n"
           f"\\newcommand{{\\ipAllSpan}}{{{'yes' if all(x['lo'] < 0 < x['hi'] for x in v.values()) else 'no'}}}\n"
           f"\\newcommand{{\\ipWorseBase}}{{{b['llm_below_share_of_random_pickers'] * 100:.0f}}}\n"
           "\\newcommand{\\ipPowRows}{%\n" + "\n".join(prow) + "}\n\\newcommand{\\ipSensRows}{%\n" + "\n".join(srow) + "}\n")
    (HERE.parent / "paper" / "results_power_intraday.tex").write_text(tex)


if __name__ == "__main__":
    main()
