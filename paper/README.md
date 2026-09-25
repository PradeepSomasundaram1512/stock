# AIEI 2027 paper — Does the LLM Add Alpha? A Forward Audit of a Deployed Multi-Agent LLM Trading System

Every number in the paper is generated from data; never edit `results_*.tex` by hand.

## Reproduce

```bash
cd ../ai-stock-agent
venv/bin/python paper_universe.py   # fixed S&P 500 placebo pool on 2026-01-01 -> paper_results/sp500_universe.csv (network; result is committed)
venv/bin/python paper_analysis.py   # daily-horizon audit  -> ../paper/results_macros.tex, figs/
venv/bin/python paper_intraday.py   # intraday audit       -> ../paper/results_intraday.tex
venv/bin/python paper_ops.py        # ops, power, lineage  -> ../paper/results_ops.tex (needs the two above)
cd ../paper
pdflatex main && bibtex main && pdflatex main && pdflatex main
```

## Data

* `data/backtest_ec2_2026-01-06_to_2026-09-24.db` — the production recommendation database (3,507 rows) from the retired AWS instance. Prices come from Yahoo Finance at run time.
* The 560 MB production scanner log used by `paper_ops.py` is not in git. It is archived (gzip) at `gs://project-0c776d86-067e-4f37-9ca-stock-scanner-archive/ec2-2026-09-25/logs.tar.gz`; extract it and pass its path as the second argument to `paper_ops.py`.
* `paper_results/prev_universe/` holds the results from before the placebo pool was fixed, kept so the paper can quote the before/after difference.
* From 2026-09-25 the live scanner also writes every analysed candidate (HOLDs and fallbacks included, with the news/fundamentals inputs) to the `llm_decisions` table; future audits should use that instead of reconstructing from logs.
