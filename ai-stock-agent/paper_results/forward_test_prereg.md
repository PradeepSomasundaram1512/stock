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

## Addendum 2, 2026-09-25 (still before any forward outcome; corrects H5's definition)

While implementing H5, the development sample showed that H5 *as written above* (raw 10-day CAR of the lowest-RSI third vs. all BUYs) has the
**opposite sign** (+0.69%, not detectable) to the finding it came from: the meta-labeling result was measured against matched placebos, and
oversold stocks simply bounce more in raw returns. H5 is therefore redefined to the measure it came from:

- **H5 (as redefined):** the mean *alpha over the matched placebo* (CAR minus the mean CAR of the 10 nearest non-selected stocks in RSI,
  momentum and ATR% space, exactly as in the paper) of the lowest 30% of BUYs by daily RSI is *lower* than that of all BUYs (two-sided).

Development estimates for the redefined H5 (exploratory): -0.10% in the early window, -0.78% in the late window, -0.30% overall (95% CI -0.92 to +0.35, not
detectable). The -0.77% seen in the meta-labeling study came from the later, out-of-fold subsample only and is not stable across windows,
so the development evidence for H5 is weak and the forward test is the real test. No forward outcome had matured when this was written.

## Addendum 3, 2026-09-25 (still before any forward outcome; adds H6, the primary test of selection skill)

Monte-Carlo validation (`paper_power.py`, `paper_sensitivity.py`) found that the ten-day matched placebo is **biased for extreme oversold picks**: fake
"LLMs" with no skill, picking at random from the 50 lowest-RSI names, earn about +0.27 percentage points over their matched placebo (SD 0.19 pp over 500
fake LLMs), so the right zero for a selection-skill test is not zero. (The intraday placebo is unbiased, +0.002%.) The forward test therefore adds a
bias-corrected primary test and fixes its definition here, before any forward outcome exists and without reference to forward data:

- **H6 (primary test of ten-day selection skill).** Let alpha_i = CAR_i minus the mean CAR of the K = 10 nearest non-selected pool stocks (RSI, 20-day
  momentum, ATR% space, as in the paper). Let b be the mean of alpha over 200 seeded no-skill fake pickers evaluated on the SAME dates of the evaluated window
  (on each date with real BUYs, the same number of stocks drawn at random from the 50 lowest daily-RSI pool stocks, compared with the identical placebo).
  H6: mean(alpha_i) - b differs from 0 (two-sided), with the same block bootstrap applied to alpha_i - b. Fake pickers are re-drawn (seeded) at every evaluation
  because the window grows. Limitation stated in advance: b depends on the fake-picker pool (50 lowest daily RSI), which only approximates the real pre-screen.
- H1 to H5 are unchanged. The family for the Holm adjustment becomes H1 to H6.
- The intraday horizon is not part of the forward test (the deployed intraday result is validated as unbiased and is reported as a development result).

## Addendum 4, 2026-09-26 (still before any forward outcome; adds H7, a secondary test of a stronger model, separate from H1 to H6)

**State of the shadow data when this was written.** The production model's decisions are logged as before. A second model has been answering the same prompts on the same
stored inputs since 2026-09-25 (`shadow.py`; answers are logged only and never reach alerts, rankings or trades). At the time of writing the table `shadow_decisions`
held 116 answers from GPT-6 Luna, all from 2026-09-25, none matured, none a BUY, and **no answer from GPT-6 Sol**, which is switched on with this addendum
(`SHADOW_MODEL=gpt-6-luna,gpt-6-sol:buys`; Sol scores only the candidates production called BUY). No shadow outcome could have been measured.

- **H7 (secondary; does a stronger model sort production's BUYs?).** Among candidates that production called BUY and that Sol answered (llm_status ok), let alpha_i be defined
  exactly as in H6 (10-day CAR minus the mean CAR of the K = 10 nearest non-selected pool stocks) and let b be the H6 bias term for the same dates. H7: the mean of
  (alpha_i - b) over those BUYs that Sol also calls BUY **differs from** the mean over those Sol does not call BUY (two-sided; same 10-day-block bootstrap on the difference).
  Minimum sample: 100 Sol-answered production BUYs matured, in at least 20 independent blocks; below that no verdict is drawn.
- **Same test for Luna, descriptive.** Luna answers every candidate, so the same comparison is computed for it on the production BUYs it answered, reported as descriptive,
  with no verdict, so as to keep the family small.
- **Family.** H7 is its own family of one; the Holm adjustment for H1 to H6 is unchanged. H7 is not part of the paper's six main hypotheses.
- **What is not claimed.** H7 is about whether Sol adds information *on top of production's BUYs*. It says nothing about whether Sol picks stocks better from the whole universe
  (it never sees non-BUY candidates), and a null would not show the stronger model is useless, only that it does not sort this slice.
- **Known limits, stated in advance.** (i) The shadow table records the model name the deployment was configured with (an alias), not a dated snapshot, so a silent model update
  during the test cannot be detected from the log; the deviation log will note the date of any provider announcement found. (ii) Sol runs under a hard daily budget
  (USD 0.40 per model) and stops for a scan after three consecutive errors, so on busy days some BUYs may be unanswered; the number answered is reported next to the result.
  (iii) The analysis code for H7 is not yet written; this addendum fixes its definition, and the code will be added and committed before the minimum sample is reached.
  (iv) Sol's access to the OpenAI account is unverified at the time of writing; if it never answers, H7 is reported as untestable rather than dropped.
