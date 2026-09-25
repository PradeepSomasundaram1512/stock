"""
Runs the pre-registered tests in paper_results/forward_test_prereg.md.

    python forward_test.py walkforward [path/to/paper.db]     early vs. late window of the development sample
    python forward_test.py forward path/to/live_backtest.db   signals on/after the freeze date, matured only

The hypotheses, thresholds and minimum sample are fixed in the pre-registration and repeated as
constants here; change them only with a visible git diff. Output: paper_results/forward_<mode>.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

import paper_analysis as pa

# paper_analysis reads sys.argv[1] as its DB path at import, so this script names the DB explicitly
DEV_DB = Path(__file__).parent.parent / "paper/data/backtest_ec2_2026-01-06_to_2026-09-24.db"
FREEZE = pd.Timestamp("2026-09-25")
TAU = 0.85                  # H1 confidence gate
MIN_SIGNALS, MIN_BLOCKS = 300, 20
N_BOOT = 3000
SPLIT = 0.60                # walk-forward: share of BUY dates in the early window
rng = np.random.default_rng(2028)


def build(db: str, end: pd.Timestamp) -> pd.DataFrame:
    """One row per matured BUY signal with its CAR and the per-date rule/universe CARs."""
    pa.DB = Path(db)
    sig, _, _ = pa.load_signals()
    fixed = pa.fixed_universe()
    P = pa.load_panel(sorted(set(sig.ticker.unique()) | set(fixed)), sig.day.min() - pd.Timedelta(days=140), end)
    dates = P["C"].index
    universe = [t for t in fixed if t in P["C"].columns and t != "SPY"]
    sig["i"] = dates.searchsorted(sig["day"], side="right") - 1
    buys = sig[sig.decision == "BUY"]
    buys = buys[[pa.valid(P, r.i, r.ticker) for r in buys.itertuples()]]
    rows = []
    for i, grp in buys.groupby("i"):
        ok = [u for u in universe if pa.valid(P, i, u)]
        rev = P["rsi"].iloc[i][ok].nsmallest(min(len(grp), len(ok))).index
        cars = {u: pa.car_path(P, i, u)[0][pa.H] for u in ok}
        uni, revc = np.mean(list(cars.values())), np.mean([cars[u] for u in rev])
        for r in grp.itertuples():
            rows.append({"i": i, "day": str(dates[i].date()), "ticker": r.ticker, "conf": r.confidence,
                         "car": pa.car_path(P, i, r.ticker)[0][pa.H], "rev": revc, "uni": uni})
    return pd.DataFrame(rows)


def boot(df: pd.DataFrame, stat):
    """Block bootstrap (10-trading-day blocks of signal dates) of stat(df); returns mean, CI, SE, MDE."""
    blocks = [g for _, g in df.groupby(df["i"] // pa.BLOCK)]
    draws = np.array([stat(pd.concat([blocks[k] for k in rng.integers(0, len(blocks), len(blocks))]))
                      for _ in range(N_BOOT)])
    draws = draws[np.isfinite(draws)]
    est = stat(df)
    se = draws.std(ddof=1)
    return {"est": float(est), "lo": float(np.percentile(draws, 2.5)), "hi": float(np.percentile(draws, 97.5)),
            "se": float(se), "mde": float(2.8 * se), "detectable": bool(np.percentile(draws, 2.5) > 0 or np.percentile(draws, 97.5) < 0)}


def analyse(df: pd.DataFrame, label: str) -> dict:
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
    out["H2_spearman_conf_car"] = boot(df, lambda d: stats.spearmanr(d.conf, d.car)[0])
    out["H3_reversal_minus_universe"] = boot(df, lambda d: (d.rev - d.uni).mean())
    out["H4_llm_minus_reversal"] = boot(df, lambda d: (d.car - d.rev).mean())
    return out


def show(o: dict):
    print(f"\n[{o['window']}] {o['n_signals']} signals, {o['n_blocks']} blocks, {o.get('first')} to {o.get('last')}")
    if "verdict" in o:
        print("  ", o["verdict"])
    for k, lab, pc in (("H1_gated_minus_all", "H1 conf>=0.85 minus all BUY (CAR)", 1), ("H2_spearman_conf_car", "H2 Spearman(conf, CAR)", 0),
                       ("H3_reversal_minus_universe", "H3 reversal rule minus universe (CAR)", 1), ("H4_llm_minus_reversal", "H4 LLM minus reversal rule (CAR)", 1)):
        if k in o:
            r, f = o[k], (lambda v: f"{v*100:+.2f}%") if pc else (lambda v: f"{v:+.3f}")
            print(f"   {lab:42} {f(r['est'])} [{f(r['lo'])}, {f(r['hi'])}]  MDE {f(r['mde']).lstrip('+')}  {'DETECTABLE' if r['detectable'] else 'not detectable'}")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "walkforward"
    if mode == "walkforward":
        db = sys.argv[2] if len(sys.argv) > 2 else str(DEV_DB)
        df = build(db, pa.DATA_END)
        cut = sorted(df.i.unique())[int(SPLIT * df.i.nunique())]
        res = [analyse(df[df.i < cut], "early (first 60% of dates)"), analyse(df[df.i >= cut], "late (last 40% of dates)"), analyse(df, "all development data")]
    elif mode == "forward":
        db = sys.argv[2]
        df = build(db, pd.Timestamp.today().normalize() + pd.Timedelta(days=1))
        df = df[pd.to_datetime(df.day) >= FREEZE]
        res = [analyse(df, "forward (on/after 2026-09-25, matured only)")] if len(df) else [{"window": "forward", "n_signals": 0, "n_blocks": 0, "verdict": "no matured signals yet"}]
    else:
        sys.exit(__doc__)
    for r in res:
        show(r)
    (pa.RES / f"forward_{mode}.json").write_text(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
