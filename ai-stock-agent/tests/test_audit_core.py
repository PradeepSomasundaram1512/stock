import sys
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
