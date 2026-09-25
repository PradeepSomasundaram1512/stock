import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import input_log as il


class NpLike:                     # stands in for numpy scalars, which json cannot serialize
    def item(self):
        return 3.5


class Tests(unittest.TestCase):
    def test_append_read_roundtrip_and_multiple_runs_append(self):
        d, now = Path(tempfile.mkdtemp()), datetime(2026, 9, 28, 15, 0, tzinfo=timezone.utc)
        r1 = [{"ticker": "AAA", "features": {"rsi": NpLike(), "trend": "up"}, "rag_context": "ctx", "fundamentals": {"pe": 20}, "news_analysis": {"summary": "s"}, "market_context": {"vix": 15}},
              {"ticker": None}, None]
        self.assertEqual(il.append("s1", r1, d, now), 1)                              # blank/None candidates skipped
        self.assertEqual(il.append("s2", [{"ticker": "BBB", "features": {}}], d, now), 1)   # a second run appends to the same day's file
        rows = il.read_all(d)
        self.assertEqual([(r["scan_id"], r["ticker"]) for r in rows], [("s1", "AAA"), ("s2", "BBB")])
        self.assertEqual(rows[0]["inputs"]["features"], {"rsi": 3.5, "trend": "up"})       # numpy-like scalars survive
        self.assertEqual(rows[0]["inputs"]["rag_context"], "ctx")
        self.assertEqual(set(rows[0]["inputs"]), set(il.KEYS))
        self.assertTrue((d / "inputs" / "2026-09-28.jsonl.gz").exists())

    def test_one_file_per_utc_day(self):
        d = Path(tempfile.mkdtemp())
        il.append("a", [{"ticker": "X"}], d, datetime(2026, 9, 28, 23, 59, tzinfo=timezone.utc))
        il.append("b", [{"ticker": "Y"}], d, datetime(2026, 9, 29, 0, 1, tzinfo=timezone.utc))
        self.assertEqual(sorted(p.name for p in (d / "inputs").glob("*.gz")), ["2026-09-28.jsonl.gz", "2026-09-29.jsonl.gz"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
