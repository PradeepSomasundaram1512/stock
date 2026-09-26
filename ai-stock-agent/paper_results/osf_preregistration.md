# Pre-registration for external registration (OSF / AsPredicted format)

Purpose: the pre-registration in `forward_test_prereg.md` is a file in the author's own git repository, so its timestamps are the author's own.
Copy the text below into an external registry (OSF Registries "Pre-Registration in Social Sciences Template" or AsPredicted) and cite the
resulting DOI in the paper. Registering now still precedes every forward outcome (none had matured on 2026-09-25); it cannot pre-date the
freeze itself, and the entry should say so.

## 1. Data collection status
Registration is made after the freeze date (2026-09-25) and after analysis of a development sample (2026-01-09 to 2026-09-10, 1,399 BUY signals).
No forward signal (dated on or after 2026-09-25) had a measurable 10-trading-day outcome when the hypotheses below were written and committed
to the project repository (commit history: `ai-stock-agent/paper_results/forward_test_prereg.md`, addenda 1, 2 and 3). H3 and H5 were suggested by
the development sample, H5 was redefined once (addendum 2), and H6 was added (addendum 3), each before any forward outcome existed; all three facts are disclosed.

## 2. Hypotheses (all two-sided)
Outcome for every hypothesis: the 10-trading-day beta-adjusted cumulative abnormal return (CAR) against SPY, per BUY signal, using the
production system's BUY signals on or after 2026-09-25, scored only once 10 trading days have elapsed.
- H1: BUY signals with stated confidence >= 0.85 have a different mean CAR than all BUY signals.
- H2: the Spearman correlation between stated confidence and CAR differs from 0.
- H3: on each date with LLM BUYs, the rule "pick the same number of stocks with the lowest daily RSI-14 from the fixed S&P 500 pool of 2026-01-01"
  has a different mean CAR than the equal-weighted pool.
- H4: the mean CAR of the LLM's BUYs differs from that of the rule in H3 (paired by date).
- H5: the mean alpha over the matched placebo (CAR minus the mean CAR of the 10 nearest non-selected pool stocks in RSI / 20-day momentum / ATR%
  space) of the lowest 30% of BUYs by daily RSI (within the evaluated window) is lower than that of all BUYs.
- H6 (primary test of ten-day selection skill, addendum 3): let alpha_i be as in H5 and let b be the mean alpha earned by 200 seeded no-skill fake pickers evaluated on
  the SAME dates of the evaluated window (on each date with real BUYs, the same number of stocks drawn at random from the 50 lowest daily-RSI pool stocks, compared with
  the identical placebo). The mean of (alpha_i - b) differs from 0. Rationale (`paper_power.py`): the ten-day placebo is biased by about +0.27 pp for oversold picks, so
  the right zero is not zero. Stated limitation: b depends on the fake-picker pool, which only approximates the real pre-screen.


## 3. Analysis
One row per signal; 95% intervals and p-values from a block bootstrap over non-overlapping 10-trading-day blocks of signal dates (3,000 resamples),
seeded (`forward_test.py`). "Detectable" means the 95% interval excludes 0. All six hypotheses are reported, together with Holm-adjusted p-values
across the six. (A Monte-Carlo check, `paper_power.py`, found this block-bootstrap procedure conservative at the current number of blocks.)

## 4. Sample size and stopping rule
No verdict below 300 matured signals AND 20 independent blocks: below that the report says "insufficient data". At ~12 signals per active day the
signal count is reached in about 5 weeks and the block count in about 10 months. Data is analysed at fixed checkpoints (weekly, automated), and
interim results are not used to change the hypotheses, the analysis or the stopping rule.

## 5. Known changes after the freeze (disclosed)
- 2026-09-25: the scan universe changed from a hand-typed list of 469 tickers to the live S&P 500 (503), then refreshed weekly (log: `universe_changes.jsonl`).
  Signals therefore come from a slightly different set of stocks before and after that date; the comparison pool of the test is unchanged.
- The model is called by the alias `gpt-4o-mini`; the served snapshot is logged from 2026-09-26 on (it was `gpt-4o-mini-2024-07-18` on 2026-09-25).

## 6. Other
Exploratory, not confirmatory: the input ablation, meta-labeling, regime splits and horizon variants. No meta-model is registered as a trading rule.

## 7. How to file (needs an account, which only you can create)
1. Create a free account at https://osf.io and open Registries > New registration, or use https://aspredicted.org.
2. Paste sections 1-6 above; attach `forward_test_prereg.md` (with its three addenda) as a supporting file.
3. Submit, copy the DOI/URL, and add it to the paper's availability paragraph and to `paper_results/forward_test_prereg.md`.
An external registry timestamps the entry independently of the author's own repository, which is the point.
