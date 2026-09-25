import json
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import daily_digest as dd

NOW = datetime(2026, 9, 28, 20, 20, tzinfo=timezone.utc)
iso = lambda d: (NOW - d).isoformat(timespec="seconds")


class Checks(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.old_db = dd.DB
        dd.DB = self.d / "backtest.db"
        con = sqlite3.connect(dd.DB)
        con.execute("create table llm_decisions(decided_at text)")
        con.execute("insert into llm_decisions values (?)", (iso(timedelta(hours=1, minutes=20)).replace("+00:00", ""),))
        con.commit()
        con.close()

    def tearDown(self):
        dd.DB = self.old_db

    def write(self, name, obj):
        (self.d / name).write_text(json.dumps(obj))

    def healthy(self):
        self.write("scan_universe.json", {"asof": iso(timedelta(days=3)), "n": 503})
        self.write("market_snapshot.json", {"asof": iso(timedelta(minutes=25)), "n": 503, "missing": []})

    def test_healthy_system_has_no_problems(self):
        self.healthy()
        lines, problems = dd.system_checks(self.d, NOW)
        self.assertEqual(problems, [])
        self.assertTrue(any("503 tickers" in l for l in lines))

    def test_each_failure_is_reported(self):
        self.write("scan_universe.json", {"asof": iso(timedelta(days=20)), "n": 300})
        self.write("market_snapshot.json", {"asof": iso(timedelta(hours=5)), "n": 480, "missing": ["AAA", "BBB"]})
        _, problems = dd.system_checks(self.d, NOW)
        text = " | ".join(problems)
        for needle in ("outside the expected", "not refreshed for 20 days", "5.0 h old", "2 tickers had no price data"):
            self.assertIn(needle, text)

    def test_missing_files_are_problems_not_crashes(self):
        _, problems = dd.system_checks(self.d, NOW)
        self.assertEqual(len(problems), 2)                                     # universe and snapshot; the scan itself is fine

    def test_stale_scan_is_reported(self):
        self.healthy()
        con = sqlite3.connect(dd.DB)
        con.execute("update llm_decisions set decided_at=?", (iso(timedelta(hours=9)).replace("+00:00", ""),))
        con.commit()
        con.close()
        self.assertIn("no scan for 9.0 h", " ".join(dd.system_checks(self.d, NOW)[1]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
