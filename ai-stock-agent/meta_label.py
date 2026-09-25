"""
Meta-labeling: can anything known at decision time predict WHICH of the LLM's BUY calls will beat their matched placebo?

Target: the signal's selection alpha, y = CAR10(signal) - CAR10(matched placebo), and its sign (paper_results/analysis_buy_signals.csv).

Two feature sets, so the LLM's own outputs are tested for INCREMENTAL information:
    A  price context only:  daily RSI, 20-day momentum, 5-day return, distance below the 20-day high, ATR%, beta, VIX, SPY trend, days to earnings
    B  A + what the LLM said:  stated confidence, trend label
(The historical log recorded fundamentals/news/market fields for only ~10 of 1,493 BUYs, so they cannot be used; the new input log will allow it later.)

Models, fixed in advance (no tuning on the test folds): L2 logistic regression (portable to numpy, so it could be frozen and scored in the cloud) and a
shallow gradient-boosted tree (exploratory). Evaluation is PURGED walk-forward: expanding training window, test folds in time order, training signals
whose 10-day outcome window overlaps the test fold (plus a 5-day embargo) are dropped. Reported on the pooled out-of-fold predictions:
AUC, Spearman(pred, alpha), and the "selective alpha": mean alpha of the top 30% by predicted score minus the mean of all out-of-fold signals,
with block-bootstrap intervals and Holm-adjusted p-values across the three primary tests. Comparators: top 30% by LLM confidence alone, by lowest RSI, random.

    python meta_label.py            -> paper_results/meta_label.json
"""
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import audit_core as core

HERE = Path(__file__).parent
RES = HERE / "paper_results"
DEV_DB = HERE.parent / "paper/data/backtest_ec2_2026-01-06_to_2026-09-24.db"
H, EMBARGO, N_FOLDS, BURN_IN, TOP = core.H, 5, 4, 0.40, 0.30
N_BOOT = 4000
rng = np.random.default_rng(2029)
PRICE_FEATURES = ["rsi", "mom20", "ret5", "below_high20", "atr_pct", "beta", "vix", "spy_up", "earnings_days"]
LLM_FEATURES = ["conf", "trend_bearish", "trend_bullish"]


def build() -> pd.DataFrame:
    """One row per evaluated BUY signal (same rows, same order as the paper's per-signal file) with features known at decision time."""
    sig, _, _ = core.load_signals(DEV_DB)
    fixed = core.fixed_universe()
    P = core.load_panel(sorted(set(sig.ticker.unique()) | set(fixed)), sig.day.min() - pd.Timedelta(days=140), core.DATA_END, cache_dir=RES)
    dates = P["C"].index
    sig["i"] = dates.searchsorted(sig["day"], side="right") - 1
    buys = sig[sig.decision == "BUY"]
    buys = buys[[core.valid(P, r.i, r.ticker) for r in buys.itertuples()]].reset_index(drop=True)
    ev = pd.read_csv(RES / "analysis_buy_signals.csv")
    assert len(ev) == len(buys) and (ev.ticker.values == buys.ticker.values).all() and (ev.i.values == buys.i.values).all(), "row alignment with the paper's file broke"

    extra = pd.read_sql("select ticker, recommendation_date, decision, trend, earnings_days from recommendations", sqlite3.connect(DEV_DB))
    extra["day"] = pd.to_datetime(extra["recommendation_date"].str[:10], format="mixed")
    extra = extra.sort_values("recommendation_date").drop_duplicates(["ticker", "day", "decision"])
    m = buys.merge(extra[["ticker", "day", "decision", "trend", "earnings_days"]], on=["ticker", "day", "decision"], how="left")
    assert len(m) == len(buys)

    C = P["C"]
    hi20 = C.rolling(20).max()
    rows = []
    for r, e in zip(m.itertuples(), ev.itertuples()):
        t, i = r.ticker, r.i
        rows.append({"i": i, "day": str(dates[i].date()), "ticker": t, "alpha": e.alpha_vs_match, "car10": e.car10,
                     "rsi": P["rsi"][t].iloc[i], "mom20": P["mom"][t].iloc[i], "ret5": C[t].iloc[i] / C[t].iloc[i - 5] - 1,
                     "below_high20": C[t].iloc[i] / hi20[t].iloc[i] - 1, "atr_pct": P["atr_pct"][t].iloc[i], "beta": P["beta"][t].iloc[i],
                     "vix": P["vix"].iloc[i], "spy_up": float(P["C"]["SPY"].iloc[i] > P["sma50"].iloc[i]),
                     "earnings_days": r.earnings_days, "conf": r.confidence, "trend": r.trend})
    df = pd.DataFrame(rows)
    df["trend_bearish"] = (df.trend == "bearish").astype(float)
    df["trend_bullish"] = (df.trend == "bullish").astype(float)
    df["y"] = (df.alpha > 0).astype(int)
    return df


def make_model(kind: str):
    if kind == "lr":
        return make_pipeline(StandardScaler(), LogisticRegression(C=0.05, max_iter=1000))
    return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=120, l2_regularization=1.0, random_state=0)


def impute(train: pd.DataFrame, test: pd.DataFrame, cols: list):
    med = train[cols].median()                       # medians from TRAINING data only
    return train[cols].fillna(med).to_numpy(float), test[cols].fillna(med).to_numpy(float)


def folds(df: pd.DataFrame):
    """Purged expanding walk-forward: test folds are contiguous in time; training ends H + EMBARGO days before a fold starts."""
    days = np.sort(df.i.unique())
    start = int(len(days) * BURN_IN)
    edges = np.array_split(days[start:], N_FOLDS)
    for e in edges:
        lo, hi = e[0], e[-1]
        train = df[df.i <= lo - H - EMBARGO]
        test = df[(df.i >= lo) & (df.i <= hi)]
        if len(train) >= 100 and len(test):
            yield train, test


def oof_predictions(df: pd.DataFrame, cols: list, kind: str) -> pd.DataFrame:
    parts = []
    for train, test in folds(df):
        Xtr, Xte = impute(train, test, cols)
        mdl = make_model(kind).fit(Xtr, train.y)
        thr = np.quantile(mdl.predict_proba(Xtr)[:, 1], 1 - TOP)          # threshold from the TRAINING predictions only
        p = mdl.predict_proba(Xte)[:, 1]
        parts.append(test.assign(score=p, selected=(p >= thr)))
    return pd.concat(parts)


def block_boot(oof: pd.DataFrame, stat, n=N_BOOT):
    blocks = [g for _, g in oof.groupby(oof.i // core.BLOCK)]
    draws = np.array([stat(pd.concat([blocks[k] for k in rng.integers(0, len(blocks), len(blocks))])) for _ in range(n)])
    draws = draws[np.isfinite(draws)]
    est = stat(oof)
    p = max(2 * min((draws <= 0).mean(), (draws >= 0).mean()), 1 / len(draws))
    return {"est": float(est), "lo": float(np.percentile(draws, 2.5)), "hi": float(np.percentile(draws, 97.5)), "p": float(p), "se": float(draws.std(ddof=1))}


def evaluate(oof: pd.DataFrame, sel_col: str = "selected") -> dict:
    sel = lambda d: d.loc[d[sel_col], "alpha"].mean() - d["alpha"].mean()
    out = {"n_oof": int(len(oof)), "n_blocks": int(oof.i.floordiv(core.BLOCK).nunique()), "n_selected": int(oof[sel_col].sum()),
           "selective_alpha": block_boot(oof, sel)}
    if "score" in oof:
        out["auc"] = float(roc_auc_score(oof.y, oof.score))
        out["spearman"] = block_boot(oof, lambda d: d.score.rank().corr(d.alpha.rank()))
    return out


def holm(pvals: dict) -> dict:
    order = sorted(pvals, key=pvals.get)
    m, adj, run = len(order), {}, 0.0
    for k, name in enumerate(order):
        run = max(run, min(1.0, (m - k) * pvals[name]))
        adj[name] = run
    return adj


def write_tex(res: dict):
    """LaTeX for the paper (paper/results_meta.tex), so the table cannot drift from the code."""
    ci = lambda r: f"${r['est'] * 100:+.2f}\\;[{r['lo'] * 100:+.2f},{r['hi'] * 100:+.2f}]$"
    lab = {"LR_price": "Logistic, price context", "LR_price+LLM": "Logistic, + LLM outputs", "GBM_price": "Boosted trees, price context", "GBM_price+LLM": "Boosted trees, + LLM outputs"}
    rows = []
    for k, name in lab.items():
        m = res["models"][k]
        inc = ci(m["incremental"]) if "incremental" in m else "---"
        rows.append(f"{name} & {m['auc']:.3f} & {ci(m['selective_alpha'])} & {inc} \\\\ ")
    for k, name in (("top30_by_LLM_confidence", "Top 30\\% by LLM confidence"), ("lowest30_RSI", "Lowest 30\\% by RSI")):
        r = res["comparators"][k]
        rows.append(f"{name} & --- & {ci(r['selective_alpha'])} & --- \\\\ ")
    holm = res["holm_family"]["holm_adjusted_p"]
    tex = ("% generated by meta_label.py; do not edit\n"
           f"\\newcommand{{\\metaOof}}{{{res['models']['LR_price']['n_oof']}}}\n\\newcommand{{\\metaBlocks}}{{{res['models']['LR_price']['n_blocks']}}}\n"
           f"\\newcommand{{\\metaMDE}}{{{res['mde_selective_alpha'] * 100:.1f}}}\n\\newcommand{{\\metaTests}}{{{res['holm_family']['n_tests']}}}\n"
           f"\\newcommand{{\\metaLowRsiHolm}}{{{holm['lowest30_RSI: selective alpha']:.2f}}}\n"
           "\\newcommand{\\metaRows}{%\n" + "\n".join(rows) + "}\n")
    (HERE.parent / "paper" / "results_meta.tex").write_text(tex)


def main():
    df = build()
    print(f"{len(df)} BUY signals, {df.i.nunique()} dates; base rate of beating the placebo: {df.y.mean():.3f}; features missing: "
          + ", ".join(f"{c} {df[c].isna().mean():.0%}" for c in PRICE_FEATURES + LLM_FEATURES if df[c].isna().mean() > 0))
    models = {"LR_price": (PRICE_FEATURES, "lr"), "LR_price+LLM": (PRICE_FEATURES + LLM_FEATURES, "lr"),
              "GBM_price": (PRICE_FEATURES, "gbm"), "GBM_price+LLM": (PRICE_FEATURES + LLM_FEATURES, "gbm")}
    pairs = {"LR_price+LLM": "LR_price", "GBM_price+LLM": "GBM_price"}       # like with like: same model family, with vs. without the LLM's outputs
    result = {"n_signals": int(len(df)), "base_rate": float(df.y.mean()), "top_share": TOP, "models": {}, "comparators": {}}
    oofs = {n: oof_predictions(df, cols, kind) for n, (cols, kind) in models.items()}
    for name, oof in oofs.items():
        result["models"][name] = evaluate(oof)
        if name in pairs:
            both = oof.merge(oofs[pairs[name]][["i", "ticker", "score", "selected"]], on=["i", "ticker"], suffixes=("", "_ref"))
            result["models"][name]["incremental_over"] = pairs[name]
            result["models"][name]["incremental"] = block_boot(
                both, lambda x: x.loc[x.selected, "alpha"].mean() - x.loc[x.selected_ref, "alpha"].mean())
    base = oofs["LR_price"].copy()                                # comparators on the same out-of-fold rows
    thr = lambda s, low: s <= s.quantile(TOP) if low else s >= s.quantile(1 - TOP)
    result["comparators"]["top30_by_LLM_confidence"] = evaluate(base.assign(sel=thr(base.conf, False)), "sel")
    result["comparators"]["lowest30_RSI"] = evaluate(base.assign(sel=thr(base.rsi, True)), "sel")
    result["comparators"]["random30"] = evaluate(base.assign(sel=rng.random(len(base)) < TOP), "sel")
    # one Holm family over EVERY test reported here: 4 selective-alpha tests, 2 incremental tests, 3 comparators
    fam = {f"{n}: selective alpha": r["selective_alpha"]["p"] for n, r in result["models"].items()}
    fam.update({f"{n}: incremental over {r['incremental_over']}": r["incremental"]["p"] for n, r in result["models"].items() if "incremental" in r})
    fam.update({f"{n}: selective alpha": r["selective_alpha"]["p"] for n, r in result["comparators"].items()})
    result["holm_family"] = {"n_tests": len(fam), "raw_p": fam, "holm_adjusted_p": holm(fam)}
    result["mde_selective_alpha"] = 2.8 * result["models"]["LR_price+LLM"]["selective_alpha"]["se"]
    RES.mkdir(exist_ok=True)
    (RES / "meta_label.json").write_text(json.dumps(result, indent=1))
    write_tex(result)
    pc = lambda r: f"{r['est'] * 100:+.2f}% [{r['lo'] * 100:+.2f}, {r['hi'] * 100:+.2f}]"
    adj = result["holm_family"]["holm_adjusted_p"]
    print(f"\nout-of-fold rows: {result['models']['LR_price']['n_oof']} in {result['models']['LR_price']['n_blocks']} independent blocks; "
          f"minimum detectable selective alpha ~ {result['mde_selective_alpha'] * 100:.1f} pp;  Holm family of {len(fam)} tests")
    for n, r in result["models"].items():
        print(f"  {n:15} AUC {r['auc']:.3f}  Spearman {r['spearman']['est']:+.3f}  selective alpha {pc(r['selective_alpha'])}  raw p {r['selective_alpha']['p']:.3f} -> Holm {adj[n + ': selective alpha']:.2f}")
        if "incremental" in r:
            print(f"{'':17}LLM outputs add (vs {r['incremental_over']}): {pc(r['incremental'])}  raw p {r['incremental']['p']:.3f} -> Holm {adj[n + ': incremental over ' + r['incremental_over']]:.2f}")
    for n, r in result["comparators"].items():
        print(f"  {n:24} selective alpha {pc(r['selective_alpha'])}  raw p {r['selective_alpha']['p']:.3f} -> Holm {adj[n + ': selective alpha']:.2f}")


if __name__ == "__main__":
    main()
