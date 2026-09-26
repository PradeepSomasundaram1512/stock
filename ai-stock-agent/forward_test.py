"""
Runs the pre-registered tests in paper_results/forward_test_prereg.md.

    python forward_test.py walkforward [path/to/paper.db]     early vs. late window of the development sample
    python forward_test.py forward path/to/live_backtest.db   signals on/after the freeze date, matured only
        options:  --out FILE   write the JSON there (default paper_results/forward_<mode>.json)
                  --discord    post a short status to the Discord webhook (used by the weekly cloud job)

The hypotheses, thresholds and minimum sample are fixed in the pre-registration and repeated as
constants here; change them only with a visible git diff. Output: paper_results/forward_<mode>.json
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import audit_core as pa    # light-weight (no matplotlib/scipy): runs in the cloud image too

DEV_DB = Path(__file__).parent.parent / "paper/data/backtest_ec2_2026-01-06_to_2026-09-24.db"
FREEZE = pd.Timestamp("2026-09-25")
TAU = 0.85                  # H1 confidence gate
MIN_SIGNALS, MIN_BLOCKS = 300, 20
N_BOOT = 3000
K_MATCH = 10                # placebo neighbours per signal (same as the paper)
N_NULL_SETS, NULL_SEED = 200, 2033   # H6: seeded no-skill fake pickers used to measure the placebo's bias
SPLIT = 0.60                # walk-forward: share of BUY dates in the early window
rng = np.random.default_rng(2028)


def build(db: str, end: pd.Timestamp, cache_dir=None):
    """(signals, null_days): one row per matured BUY signal with its CAR and the per-date rule/universe CARs, and the per-date data for the no-skill pickers."""
    sig, _, _ = pa.load_signals(db)
    fixed = pa.fixed_universe()
    P = pa.load_panel(sorted(set(sig.ticker.unique()) | set(fixed)), sig.day.min() - pd.Timedelta(days=140), end, cache_dir=cache_dir)
    dates = P["C"].index
    universe = [t for t in fixed if t in P["C"].columns and t != "SPY"]
    sig["i"] = dates.searchsorted(sig["day"], side="right") - 1
    buys = sig[sig.decision == "BUY"]
    buys = buys[[pa.valid(P, r.i, r.ticker) for r in buys.itertuples()]]
    rows = []
    picked = set(zip(buys.i, buys.ticker))
    for i, grp in buys.groupby("i"):
        ok = [u for u in universe if pa.valid(P, i, u)]
        rev = P["rsi"].iloc[i][ok].nsmallest(min(len(grp), len(ok))).index
        cars = {u: pa.car_path(P, i, u)[0][pa.H] for u in ok}
        uni, revc = np.mean(list(cars.values())), np.mean([cars[u] for u in rev])
        feats = pd.DataFrame({"rsi": P["rsi"].iloc[i], "mom": P["mom"].iloc[i], "atr": P["atr_pct"].iloc[i]})
        feats = feats.loc[[u for u in universe if (i, u) not in picked]].dropna()
        z = (feats - feats.mean()) / feats.std()
        for r in grp.itertuples():
            # characteristic-matched placebo, exactly as in paper_analysis.py: K nearest non-selected stocks in (RSI, momentum, ATR%) space
            me = (np.array([P["rsi"][r.ticker].iloc[i], P["mom"][r.ticker].iloc[i], P["atr_pct"][r.ticker].iloc[i]]) - feats.mean().values) / feats.std().values
            order = ((z.values - me) ** 2).sum(1).argsort()
            nb = [u for u in z.index[order] if pa.valid(P, i, u)][:K_MATCH]
            match = float(np.mean([pa.car_path(P, i, u)[0][pa.H] for u in nb])) if nb else float("nan")
            rows.append({"i": i, "day": str(dates[i].date()), "ticker": r.ticker, "conf": r.confidence,
                         "rsi": P["rsi"][r.ticker].iloc[i], "car": pa.car_path(P, i, r.ticker)[0][pa.H], "match": match, "rev": revc, "uni": uni})
    df = pd.DataFrame(rows)
    # null data for H6: on each date with matured BUYs, the pool of oversold stocks a no-skill picker would draw from
    per_date = df.groupby("i").size().to_dict()
    return df, pa.null_days(P, per_date, universe)


def boot(df: pd.DataFrame, stat):
    """Block bootstrap (10-trading-day blocks of signal dates) of stat(df); returns mean, CI, SE, MDE."""
    blocks = [g for _, g in df.groupby(df["i"] // pa.BLOCK)]
    draws = np.array([stat(pd.concat([blocks[k] for k in rng.integers(0, len(blocks), len(blocks))]))
                      for _ in range(N_BOOT)])
    draws = draws[np.isfinite(draws)]
    est = stat(df)
    se = draws.std(ddof=1)
    p = max(2 * min((draws <= 0).mean(), (draws >= 0).mean()), 1 / len(draws))
    return {"est": float(est), "lo": float(np.percentile(draws, 2.5)), "hi": float(np.percentile(draws, 97.5)),
            "se": float(se), "mde": float(2.8 * se), "p": float(p), "detectable": bool(np.percentile(draws, 2.5) > 0 or np.percentile(draws, 97.5) < 0)}


def analyse(df: pd.DataFrame, label: str, days: list = None) -> dict:
    n, nb = len(df), df["i"].floordiv(pa.BLOCK).nunique()
    out = {"window": label, "n_signals": n, "n_blocks": int(nb),
           "first": df.day.min() if n else None, "last": df.day.max() if n else None}
    if n < MIN_SIGNALS or nb < MIN_BLOCKS:
        out["verdict"] = f"insufficient data ({n} signals, {nb} blocks; need {MIN_SIGNALS} and {MIN_BLOCKS})"
        if n < 30:
            return out
    gated = lambda d: d.loc[d.conf >= TAU, "car"].mean() - d["car"].mean()
    out["n_gated"] = int((df.conf >= TAU).sum())
    out["mean_car_all"] = float(df.car.mean())
    out["H1_gated_minus_all"] = boot(df, gated)
    # Spearman = Pearson on average ranks (pandas' own spearman needs scipy, which the cloud image omits)
    out["H2_spearman_conf_car"] = boot(df, lambda d: d.conf.rank().corr(d.car.rank()))
    out["H3_reversal_minus_universe"] = boot(df, lambda d: (d.rev - d.uni).mean())
    out["H4_llm_minus_reversal"] = boot(df, lambda d: (d.car - d.rev).mean())
    # H5 (see the addendum in forward_test_prereg.md): alpha over the matched placebo of the lowest 30% of BUYs by daily RSI minus that of all BUYs
    def h5(d):
        a = (d["car"] - d["match"])
        ok = a.notna()
        return a[ok & (d.rsi <= d.rsi.quantile(0.30))].mean() - a[ok].mean()
    out["H5_lowrsi30_minus_all"] = boot(df, h5)
    # H6 (addendum 3): selection alpha over the placebo MINUS the placebo's bias, measured with seeded no-skill fake pickers on the same dates
    if days:
        have = set(df.i.unique())
        b, b_sd = pa.null_bias([d for d in days if d["i"] in have], K=K_MATCH, n_sets=N_NULL_SETS, seed=NULL_SEED)
        out["placebo_bias"], out["placebo_bias_sd"] = b, b_sd

        def h6(d):
            a = d["car"] - d["match"]
            return a[a.notna()].mean() - b
        out["H6_biascorrected_alpha"] = boot(df, h6)
    fam = {k: out[k]["p"] for k in ("H1_gated_minus_all", "H2_spearman_conf_car", "H3_reversal_minus_universe", "H4_llm_minus_reversal", "H5_lowrsi30_minus_all", "H6_biascorrected_alpha") if k in out}
    out["holm_adjusted_p"] = pa.holm(fam)                    # across the five pre-registered hypotheses
    return out


def show(o: dict):
    print(f"\n[{o['window']}] {o['n_signals']} signals, {o['n_blocks']} blocks, {o.get('first')} to {o.get('last')}")
    if "verdict" in o:
        print("  ", o["verdict"])
    for k, lab, pc in (("H1_gated_minus_all", "H1 conf>=0.85 minus all BUY (CAR)", 1), ("H2_spearman_conf_car", "H2 Spearman(conf, CAR)", 0),
                       ("H3_reversal_minus_universe", "H3 reversal rule minus universe (CAR)", 1), ("H4_llm_minus_reversal", "H4 LLM minus reversal rule (CAR)", 1),
                       ("H5_lowrsi30_minus_all", "H5 lowest-RSI third minus all BUYs (alpha vs placebo)", 1),
                       ("H6_biascorrected_alpha", "H6 bias-corrected selection alpha (PRIMARY)", 1)):
        if k in o:
            r, f = o[k], (lambda v: f"{v*100:+.2f}%") if pc else (lambda v: f"{v:+.3f}")
            print(f"   {lab:42} {f(r['est'])} [{f(r['lo'])}, {f(r['hi'])}]  MDE {f(r['mde']).lstrip('+')}  {'DETECTABLE' if r['detectable'] else 'not detectable'}")


def write_paper_tex(res: list):
    """LaTeX for the paper (paper/results_forward.tex) from the walk-forward run, so numbers cannot drift from the code."""
    early, late, allv = res
    pc = lambda r: f"${r['est'] * 100:+.2f}\\;[{r['lo'] * 100:+.2f},{r['hi'] * 100:+.2f}]$"
    rho = lambda r: f"${r['est']:+.3f}\\;[{r['lo']:+.3f},{r['hi']:+.3f}]$"
    spec = [("H1_gated_minus_all", "H1: conf.\\ $\\geq 0.85$ vs.\\ all", pc), ("H2_spearman_conf_car", "H2: rank corr.\\ conf.--CAR", rho),
            ("H3_reversal_minus_universe", "H3: low-RSI vs.\\ universe", pc), ("H4_llm_minus_reversal", "H4: LLM vs.\\ low-RSI", pc), ("H5_lowrsi30_minus_all", "H5: lowest-RSI third vs.\\ all (placebo alpha)", pc),
            ("H6_biascorrected_alpha", "H6: bias-corrected alpha (primary)", pc)]
    rows = [f"{lab} & {fmt(early[k])} & {fmt(late[k])} \\\\" for k, lab, fmt in spec]
    tex = ("% generated by forward_test.py walkforward; do not edit\n"
           f"\\newcommand{{\\fwdEarlyN}}{{{early['n_signals']:,}}}\n\\newcommand{{\\fwdLateN}}{{{late['n_signals']:,}}}\n"
           f"\\newcommand{{\\fwdEarlyB}}{{{early['n_blocks']}}}\n\\newcommand{{\\fwdLateB}}{{{late['n_blocks']}}}\n"
           f"\\newcommand{{\\fwdAllB}}{{{allv['n_blocks']}}}\n"
           f"\\newcommand{{\\fwdMDE}}{{{allv['H3_reversal_minus_universe']['mde'] * 100:.1f}}}\n"
           f"\\newcommand{{\\fwdNeedS}}{{{MIN_SIGNALS}}}\n\\newcommand{{\\fwdNeedB}}{{{MIN_BLOCKS}}}\n"
           f"\\newcommand{{\\hSixEst}}{{{allv['H6_biascorrected_alpha']['est'] * 100:+.2f}}}\n"
           f"\\newcommand{{\\hSixCI}}{{[{allv['H6_biascorrected_alpha']['lo'] * 100:+.2f}, {allv['H6_biascorrected_alpha']['hi'] * 100:+.2f}]}}\n"
           "\\newcommand{\\forwardRows}{%\n" + "\n".join(rows) + "}\n")
    (Path(__file__).parent.parent / "paper" / "results_forward.tex").write_text(tex)


def discord_status(res: list):
    """One short message: how much forward data has matured and, once enough, each hypothesis."""
    import requests
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook:
        return
    o = res[0]
    lines = [f"Matured signals: **{o['n_signals']}** of {MIN_SIGNALS} needed, {o['n_blocks']} of {MIN_BLOCKS} independent 10-day blocks."]
    lines.append(o.get("verdict") or "Minimum sample reached: results below are reportable.")
    for k, lab in (("H1_gated_minus_all", "H1 confidence gate"), ("H2_spearman_conf_car", "H2 confidence rank"),
                   ("H3_reversal_minus_universe", "H3 reversal rule"), ("H4_llm_minus_reversal", "H4 LLM vs reversal"),
                   ("H5_lowrsi30_minus_all", "H5 lowest-RSI third"), ("H6_biascorrected_alpha", "H6 bias-corrected alpha")):
        if k in o:
            r = o[k]
            lines.append(f"{lab}: {r['est']:+.4f} [{r['lo']:+.4f}, {r['hi']:+.4f}] " + ("**detectable**" if r["detectable"] else "not detectable"))
    body = {"embeds": [{"title": "Weekly forward-test status", "description": "\n".join(lines), "color": 0x5865F2}]}
    try:
        requests.post(webhook, json=body, timeout=10)
    except Exception as exc:   # noqa: BLE001 - a failed post must not fail the job
        print(f"discord post failed: {exc}", file=sys.stderr)


def main():
    argv = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = sys.argv[1:]
    out_path = Path(opts[opts.index("--out") + 1]) if "--out" in opts else None
    if out_path is not None:
        argv = [a for a in argv if a != str(out_path)]
    mode = argv[0] if argv else "walkforward"
    if mode == "walkforward":
        db = argv[1] if len(argv) > 1 else str(DEV_DB)
        df, days = build(db, pa.DATA_END, cache_dir=Path(__file__).parent / "paper_results")   # frozen prices: the development sample never changes
        cut = sorted(df.i.unique())[int(SPLIT * df.i.nunique())]
        res = [analyse(df[df.i < cut], "early (first 60% of dates)", days), analyse(df[df.i >= cut], "late (last 40% of dates)", days), analyse(df, "all development data", days)]
    elif mode == "forward":
        db = argv[1]
        df, days = build(db, pd.Timestamp.today().normalize() + pd.Timedelta(days=1))
        df = df[pd.to_datetime(df.day) >= FREEZE]
        res = [analyse(df, "forward (on/after 2026-09-25, matured only)", days)] if len(df) else [
            {"window": "forward", "n_signals": 0, "n_blocks": 0, "verdict": f"insufficient data (0 signals, 0 blocks; need {MIN_SIGNALS} and {MIN_BLOCKS})"}]
    else:
        sys.exit(__doc__)
    for r in res:
        show(r)
    out_path = out_path or (Path(__file__).parent / "paper_results" / f"forward_{mode}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(res, indent=1, default=float))
    if mode == "walkforward" and len(res) == 3 and "H1_gated_minus_all" in res[0]:
        write_paper_tex(res)
    if "--discord" in opts:
        discord_status(res)


if __name__ == "__main__":
    main()
