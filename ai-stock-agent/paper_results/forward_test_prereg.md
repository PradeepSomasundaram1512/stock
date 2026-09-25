# Pre-registered forward test

Written and committed **before** any signal from the evaluation window has a measurable outcome,
so the tests below cannot be tuned to the results. Any change to this file after the freeze date
must be visible in git history and reported.

- **Freeze date:** 2026-09-25 (UTC). Only signals dated on or after it count as forward data.
  Everything before it is the development sample and is never re-used as evidence.
- **Outcome:** 10-trading-day beta-adjusted cumulative abnormal return (CAR) vs SPY, the same metric as
  the paper (`paper_analysis.py`). A signal is scored only once 10 trading days have elapsed.
- **Unit and inference:** one row per BUY signal; 95% CI from a block bootstrap over non-overlapping
  10-trading-day blocks of signal dates (3,000 resamples). "Detectable" means the 95% CI excludes 0.
  The minimum detectable effect is reported as 2.80 x the bootstrap standard error.
- **Minimum sample before any verdict:** 300 matured signals AND at least 20 distinct 10-day blocks.
  Below that the report says "insufficient data" and states no conclusion.

## Hypotheses (fixed now)

1. **H1, confidence gate.** BUY signals with stated confidence >= 0.85 have a higher mean CAR than
   all BUY signals. Threshold fixed at 0.85 (the top ~quarter of the development sample); it is not tuned.
   Development-sample expectation: no difference (rank correlation of confidence and CAR was 0.008).
2. **H2, confidence ranking.** Spearman correlation between stated confidence and CAR is > 0.
3. **H3, reversal rule.** On each date with LLM BUYs, the rule "pick the same number of stocks with the
   lowest daily RSI from the fixed S&P 500 pool" has a higher mean CAR than the equal-weight universe.
   Development-sample estimate was +1.19 percentage points with a CI spanning zero.
4. **H4, LLM vs reversal rule.** Mean CAR of the LLM's BUYs minus the reversal rule's picks (paired by date).

All four are two-sided; no other hypothesis will be reported as a finding. Anything else run on this
data is exploratory and must be labelled that way.

## Walk-forward check on the development sample

Chronological split at 60% of the distinct BUY dates. The same fixed hypotheses (no re-tuning) are
evaluated separately on the early and late windows. An effect present only in the early window is
reported as not persisting.

## Addendum, 2026-09-25 (added after the freeze date, but before any forward outcome could be measured)

No forward signal had matured when this was written; nothing above was changed. What is added:

- **H5, lowest-RSI third.** Among BUY signals, those in the lowest 30% of daily RSI (within the evaluated window) have a *lower*
  mean 10-day CAR than all BUY signals (two-sided, same bootstrap, same minimum sample). **Origin:** the meta-labeling study
  (`meta_label.py`) found the lowest-RSI third of BUYs under-performing their matched placebos in the development sample
  (Holm-adjusted p = 0.05 across 9 tests, the only one to survive at all). H5 was therefore suggested by development data, the
  development windows are exploratory for it, and only forward data can confirm it.
- **Input ablation** (`ablation.py outcomes`) is descriptive/exploratory: it reports the 10-day CAR of BUYs that removing an input
  drops, adds or keeps, and no verdict is drawn below 30 matured candidates.
- **No meta-model is pre-registered as a trading rule:** none had out-of-sample skill (AUC 0.43 to 0.51, LLM outputs added nothing).
