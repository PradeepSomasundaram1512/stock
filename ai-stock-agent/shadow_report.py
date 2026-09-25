"""
Summarise the shadow-model log: spend, coverage, and how the shadow model's decisions
compare with production's on the same prompts and inputs.

Run:  venv/bin/python shadow_report.py path/to/backtest.db
      (a live copy: gcloud storage cp gs://<project>-stock-scanner-data/backtest.db .)
"""
import sqlite3
import sys

import pandas as pd

db = sys.argv[1] if len(sys.argv) > 1 else "data/backtest.db"
con = sqlite3.connect(db)
sh = pd.read_sql("select * from shadow_decisions", con)
if sh.empty:
    sys.exit("no shadow decisions logged yet")
pr = pd.read_sql("select scan_id, ticker, raw_decision, raw_confidence, llm_status from llm_decisions", con)
j = sh.merge(pr, on=["scan_id", "ticker"], how="left")
ok = j[(j.llm_status_x == "ok") & (j.llm_status_y == "ok")]
print(f"shadow model(s): {sorted(sh.shadow_model.unique())}")
print(f"decisions logged: {len(sh):,} over {sh.decided_at.str[:10].nunique()} days | answered: {(sh.llm_status == 'ok').sum():,} "
      f"| failed: {(sh.llm_status != 'ok').sum():,}")
print(f"estimated spend: ${sh.est_cost_usd.sum():.4f} total, ${sh.groupby(sh.decided_at.str[:10]).est_cost_usd.sum().mean():.4f}/day average")
print(f"median latency: {sh.latency_s.median():.1f}s | tokens in/out (mean): {sh.tokens_in.mean():.0f} / {sh.tokens_out.mean():.0f}")
if len(ok):
    print(f"\nsame-prompt comparison on {len(ok):,} candidates where both models answered:")
    print(f"  exact agreement: {(ok.decision == ok.raw_decision).mean() * 100:.1f}%")
    print(pd.crosstab(ok.raw_decision, ok.decision, rownames=["production"], colnames=["shadow"]).to_string())
    print(f"  BUY rate: production {(ok.raw_decision == 'BUY').mean() * 100:.1f}% vs shadow {(ok.decision == 'BUY').mean() * 100:.1f}%")
    print(f"  mean stated confidence: production {ok.raw_confidence.mean():.2f} vs shadow {ok.confidence.mean():.2f}")
