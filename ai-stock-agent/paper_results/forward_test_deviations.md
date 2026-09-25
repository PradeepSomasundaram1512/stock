# Deviations from the pre-registered forward test

The pre-registration (`forward_test_prereg.md`, committed 2026-09-25 before any outcome existed) fixed the hypotheses,
thresholds and minimum sample. Nothing below changes those. These are changes to the *system that generates the signals*
after the freeze date; each is listed here so results can be read with them in mind.

## 2026-09-25: scan universe

1. **Dead tickers removed (commit 9a7ddad).** 24 symbols that return no price data (delisted, merged or renamed) were removed;
   BRK.B and BF.B were changed to BRK-B and BF-B. 493 -> 469 tickers. They produced no signals, so no effect on results.
2. **Universe rebuilt from the live S&P 500** (`scan_universe.py`; weekly refresh from then on). 469 -> 503 tickers:
   +83 index members that had been missing, -49 non-members. The exact tickers and timestamp of every change are in the
   bucket's `universe_changes.jsonl`. Consequences to keep in mind when reading forward results:
   - The population of stocks that can produce a BUY changed part-way through the forward window: large-cap index members
     were added (ACN, ANET, APH, AXON, BX, DASH, DELL, GEV, FSLR, ...) and a set of smaller, higher-volatility non-index names
     (SNOW, SHOP, ROKU, RBLX, DKNG, SOFI, RIVN, AFRM, UPST, ...) were removed. Signals dated before the change come from the old list.
   - The weekly refresh keeps changing the universe by whatever the index changes (typically a handful of names a quarter).
   - The placebo/comparison pool of the forward test is unchanged: the fixed list in `audit/sp500_universe.csv`.
   - Names can be kept alongside the index through `audit/scan_extras.txt` (empty at the time of writing).

Interpretation rule: the forward test is still evaluated on all BUY signals dated on/after 2026-09-25. If a verdict is close,
re-check it separately on signals before and after the change (the timestamp is in `universe_changes.jsonl`) before drawing conclusions.
