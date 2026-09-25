"""
Condense the paper's forward-audit results into dashboard/scoreboard.json (what the
dashboard's Scoreboard tab shows). Re-run after paper_analysis.py / paper_baselines.py,
then redeploy the dashboard:

    python dashboard/build_scoreboard.py && ./deploy/gcp/06_deploy_dashboard.sh
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
a = json.loads((ROOT / "paper_results/analysis.json").read_text())
b = json.loads((ROOT / "paper_results/baselines.json").read_text())
ci = lambda d: {k: d[k] for k in ("mean", "lo", "hi")}
m, c, info = a["main"], a["calibration"], a["info"]

out = {
    "period": {"first": info["first"], "last": info["last"], "eval_end": info["eval_end"]},
    "n_signals": info["n_buy_eval"], "n_days": info["n_days_buy"], "n_tickers": info["n_tickers_buy"],
    "horizon_days": 10,
    "spy_total_return": info.get("spy_total"),
    # 10-day beta-adjusted cumulative abnormal return, 95% block-bootstrap CI
    "car10": [
        {"name": "LLM BUY signals", **ci(m["buy_car10"])},
        {"name": "Matched placebo (same RSI/momentum/ATR)", **ci(m["match_car10"])},
        {"name": "Random S&P 500 stocks", **ci(m["rand_car10"])},
        *[{"name": {"momentum": "Top momentum rule", "reversal": "Lowest-RSI rule", "low_vol": "Lowest-volatility rule",
                    "universe": "Whole universe, equal weight"}[k], **ci(v["car10"])} for k, v in b["rules"].items()],
    ],
    "llm_minus_matched": ci(m["buy_minus_match"]),
    # per-signal share with a positive 10-day raw return. (The placebo's hit rate is not shown: it is the
    # hit rate of a 10-stock average, which is positive more often than any single stock, so not comparable.)
    "hit_rate": m["buy_hit10"]["mean"],
    "calibration": {
        "mean_confidence": c["mean_conf"], "win_rate": c["win_rate"], "ece": c["ece"],
        "brier": c["brier"], "brier_baseline": c["brier_base"], "spearman": ci(c["spearman"]),
        "bins": [{k: r[k] for k in ("cbin", "n", "conf", "win", "car10")} for r in c["table"]],
    },
}
(Path(__file__).parent / "scoreboard.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: out[k] for k in ("n_signals", "hit_rate", "llm_minus_matched")}, indent=1))
print(f"{len(out['calibration']['bins'])} calibration bins; wrote dashboard/scoreboard.json")
