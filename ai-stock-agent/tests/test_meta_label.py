import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
import meta_label as ml


def frame(n_days=200, per_day=3, seed=0):
    rng = np.random.default_rng(seed)
    rows = [{"i": d, "ticker": f"T{d}_{k}", "alpha": rng.normal(0, .02), "rsi": rng.normal(20, 8), "mom20": rng.normal(0, .1), "ret5": rng.normal(0, .05),
             "below_high20": -abs(rng.normal(.1, .05)), "atr_pct": abs(rng.normal(.03, .01)), "beta": rng.normal(1, .3), "vix": rng.normal(16, 3),
             "spy_up": float(rng.random() > .5), "earnings_days": rng.integers(1, 90), "conf": rng.uniform(.6, .95), "trend_bearish": float(rng.random() > .5),
             "trend_bullish": 0.0} for d in range(n_days) for k in range(per_day)]
    df = pd.DataFrame(rows)
    df["y"] = (df.alpha > 0).astype(int)
    return df


class Folds(unittest.TestCase):
    def test_training_never_overlaps_a_test_fold_and_is_purged(self):
        df = frame()
        seen = 0
        for train, test in ml.folds(df):
            seen += 1
            self.assertLessEqual(train.i.max(), test.i.min() - ml.H - ml.EMBARGO)          # 10-day outcome window + embargo are excluded
            self.assertEqual(len(set(train.index) & set(test.index)), 0)
        self.assertEqual(seen, ml.N_FOLDS)

    def test_test_folds_are_contiguous_ordered_and_skip_the_burn_in(self):
        df = frame()
        starts = [t.i.min() for _, t in ml.folds(df)]
        self.assertEqual(starts, sorted(starts))
        self.assertGreaterEqual(starts[0], int(200 * ml.BURN_IN) - 1)

    def test_imputation_uses_training_medians_only(self):
        tr = pd.DataFrame({"a": [1.0, 2.0, 3.0, np.nan]})
        te = pd.DataFrame({"a": [np.nan, 100.0]})
        Xtr, Xte = ml.impute(tr, te, ["a"])
        self.assertEqual(Xte[0, 0], 2.0)                                                    # the test row's 100 must not influence the fill


class Statistics(unittest.TestCase):
    def test_holm_matches_a_hand_computed_example(self):
        adj = ml.holm({"a": 0.01, "b": 0.04, "c": 0.03})
        self.assertAlmostEqual(adj["a"], 0.03)                                              # 3 * 0.01
        self.assertAlmostEqual(adj["c"], 0.06)                                              # 2 * 0.03
        self.assertAlmostEqual(adj["b"], 0.06)                                              # max(0.06, 1 * 0.04): monotone
        self.assertTrue(all(v <= 1 for v in ml.holm({"x": 0.9, "y": 0.8}).values()))

    def test_random_features_carry_no_signal_out_of_fold(self):
        # sanity: on pure noise, out-of-fold AUC must sit near 0.5, not above (this would catch leakage in the pipeline)
        df = frame(n_days=260, per_day=4, seed=1)
        oof = ml.oof_predictions(df, ml.PRICE_FEATURES, "lr")
        from sklearn.metrics import roc_auc_score
        self.assertLess(abs(roc_auc_score(oof.y, oof.score) - 0.5), 0.08)

    def test_a_planted_signal_is_recovered(self):
        df = frame(n_days=260, per_day=4, seed=2)
        df["y"] = (df.rsi + np.random.default_rng(3).normal(0, 4, len(df)) > df.rsi.median()).astype(int)     # y depends on rsi
        oof = ml.oof_predictions(df, ml.PRICE_FEATURES, "lr")
        from sklearn.metrics import roc_auc_score
        self.assertGreater(roc_auc_score(oof.y, oof.score), 0.7)


if __name__ == "__main__":
    unittest.main(verbosity=2)
