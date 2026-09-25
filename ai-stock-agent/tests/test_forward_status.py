import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import paper_forward_status as fs


def est(e, lo, hi):
    return {"est": e, "lo": lo, "hi": hi, "p": 0.5}


FULL = {"n_signals": 320, "n_blocks": 21, **{k: est(0.001, -0.01, 0.012) for k, _, _ in fs.HYP}, "holm_adjusted_p": {k: 0.9 for k, _, _ in fs.HYP}}


class Status(unittest.TestCase):
    def test_below_the_minimum_reports_progress_and_no_results(self):
        t = fs.render({"n_signals": 40, "n_blocks": 3, "verdict": "insufficient data"}, "2026-10-09")
        self.assertIn("40 of the 300", t)
        self.assertIn("3 of the 20", t)
        self.assertIn("no forward result is reported", t)
        self.assertIn("\\newcommand{\\fwdStatusTable}{}", t)                       # no table before the pre-registered minimum

    def test_a_large_sample_with_too_few_blocks_still_reports_no_result(self):
        self.assertIn("no forward result is reported", fs.render({**FULL, "n_signals": 5000, "n_blocks": 19}, "2027-01-01"))

    def test_minimum_met_adds_a_table_with_all_six_hypotheses_and_holm_p(self):
        t = fs.render(FULL, "2027-07-01")
        self.assertIn("meet the pre-registered minimum", t)
        self.assertIn("\\label{tab:fwdresults}", t)
        for h in ("H1", "H2", "H3", "H4", "H5", "H6"):
            self.assertIn(h + ":", t)
        self.assertEqual(t.count("0.90"), 6)

    def test_empty_forward_file_is_handled(self):
        t = fs.render({"n_signals": 0, "n_blocks": 0, "verdict": "insufficient data (0 signals)"}, "2026-09-26")
        self.assertIn("0 of the 300", t)


if __name__ == "__main__":
    unittest.main(verbosity=2)
