import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
import audit_core as core


class Holm(unittest.TestCase):
    def test_matches_a_hand_computed_example_and_is_monotone_and_capped(self):
        adj = core.holm({"a": 0.01, "b": 0.04, "c": 0.03})
        self.assertAlmostEqual(adj["a"], 0.03)        # 3 x 0.01
        self.assertAlmostEqual(adj["c"], 0.06)        # 2 x 0.03
        self.assertAlmostEqual(adj["b"], 0.06)        # max(0.06, 1 x 0.04): step-down keeps adjusted p monotone
        self.assertTrue(all(v <= 1 for v in core.holm({"x": 0.9, "y": 0.8}).values()))
        self.assertEqual(core.holm({}), {})


class NullBias(unittest.TestCase):
    def days(self, car_of_z, n_days=60, n_names=120, per_date=5, seed=0):
        rng = np.random.default_rng(seed)
        out = []
        for i in range(n_days):
            z = rng.normal(size=(n_names, 3))
            rsi = z[:, 0]
            car = car_of_z(z, rng)
            out.append({"i": i, "n": per_date, "z": z, "car": car, "pool": np.argsort(rsi)[:50]})
        return out

    def test_no_skill_and_no_structure_means_no_bias(self):
        days = self.days(lambda z, rng: rng.normal(0, 0.02, len(z)))
        b, sd = core.null_bias(days, n_sets=60, seed=1)
        self.assertLess(abs(b), 0.0015)
        self.assertGreater(sd, 0)

    def test_a_planted_edge_effect_is_reported_as_bias(self):
        # returns rise the lower the first feature is: the lowest-RSI picks are extreme, their less extreme neighbours earn less, so a no-skill picker looks skilled
        days = self.days(lambda z, rng: -0.02 * z[:, 0] + rng.normal(0, 0.005, len(z)))
        b, _ = core.null_bias(days, n_sets=60, seed=1)
        self.assertGreater(b, 0.002)

    def test_deterministic_given_the_seed(self):
        days = self.days(lambda z, rng: rng.normal(0, 0.02, len(z)))
        self.assertEqual(core.null_bias(days, n_sets=10, seed=5), core.null_bias(days, n_sets=10, seed=5))


if __name__ == "__main__":
    unittest.main(verbosity=2)
