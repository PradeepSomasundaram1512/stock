import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import scan_universe as su


def page(rows, header=("Symbol", "Security", "GICS Sector", "GICS Sub-Industry")):
    body = "".join(f"<tr><td><a>{s}</a></td><td>{s} Inc</td><td>{sec}</td><td>x</td></tr>" for s, sec in rows)
    return (f'<html><table class="other" id="x"><tr><td>AAA</td></tr></table>'
            f'<table class="wikitable" id="constituents"><tr>{"".join(f"<th>{h}</th>" for h in header)}</tr>{body}'
            f'<tr><td><table><tr><td>nested</td></tr></table></td></tr></table></html>')


class Base(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.saved = (su.MIN_N, su.MAX_N, su.INDEX_MIN, su.INDEX_MAX, su.MAX_CHANGE)
        su.MIN_N, su.MAX_N, su.INDEX_MIN, su.INDEX_MAX = 3, 12, 3, 12

    def tearDown(self):
        su.MIN_N, su.MAX_N, su.INDEX_MIN, su.INDEX_MAX, su.MAX_CHANGE = self.saved


class ParseTests(Base):
    def test_parses_only_the_constituents_table_and_normalizes(self):
        out = su.parse_constituents(page([("BRK.B", "Financials"), ("AAPL", "Information Technology")]))
        self.assertEqual(out, {"BRK-B": "Financials", "AAPL": "Information Technology"})     # not "AAA" from the other table

    def test_layout_change_is_an_error_not_a_silent_empty_list(self):
        with self.assertRaises(ValueError):
            su.parse_constituents("<html>nothing here</html>")
        with self.assertRaises(ValueError):
            su.parse_constituents(page([("AAPL", "x")], header=("Ticker", "Name", "Sector")))

    def test_junk_symbols_are_dropped(self):
        out = su.parse_constituents(page([("AAPL", "x"), ("<script>", "x"), ("TOOLONGSYMBOL", "x"), ("", "x")]))
        self.assertEqual(list(out), ["AAPL"])


class MergeTests(Base):
    def test_existing_order_kept_leavers_dropped_joiners_appended_sorted(self):
        cur = {"B": "s", "A": "s", "D": "s", "Z": "s", "C": "s"}
        self.assertEqual(su.merge(["A", "X", "B", "A", "D"], cur), ["A", "B", "D", "C", "Z"])


class LoadTests(Base):
    def write(self, doc):
        (self.d / su.FILE_NAME).write_text(json.dumps(doc))

    def good(self, **kw):
        return {"asof": datetime.now(timezone.utc).isoformat(), "tickers": ["A", "B", "C", "D"], "sectors": {}, **kw}

    def test_uses_a_valid_recent_file(self):
        self.write(self.good())
        self.assertEqual(su.load_universe(["X"], self.d), ["A", "B", "C", "D"])

    def test_falls_back_when_missing_stale_short_or_corrupt(self):
        dflt = ["X", "Y", "Z"]
        self.assertEqual(su.load_universe(dflt, self.d), dflt)                                   # missing
        self.write(self.good(asof=(datetime.now(timezone.utc) - timedelta(days=su.MAX_AGE_DAYS + 1)).isoformat()))
        self.assertEqual(su.load_universe(dflt, self.d), dflt)                                   # stale
        self.write(self.good(tickers=["A"]))
        self.assertEqual(su.load_universe(dflt, self.d), dflt)                                   # far too short
        self.write(self.good(tickers=["A", "B", "c d", "D"]))
        self.assertEqual(su.load_universe(dflt, self.d), dflt)                                   # bad symbol
        (self.d / su.FILE_NAME).write_text("{not json")
        self.assertEqual(su.load_universe(dflt, self.d), dflt)                                   # corrupt


class RefreshTests(Base):
    def rows(self, syms):
        return page([(s, "Sec") for s in syms])

    def test_first_refresh_seeds_from_the_builtin_list_and_logs(self):
        orig = su.builtin_default
        su.builtin_default = lambda: ["A", "B", "GONE"]
        try:
            r = su.refresh(self.rows(["A", "B", "NEW"]), self.d)
        finally:
            su.builtin_default = orig
        self.assertEqual((r["added"], r["removed"], r["n"]), (["NEW"], ["GONE"], 3))
        self.assertEqual(json.loads((self.d / su.FILE_NAME).read_text())["tickers"], ["A", "B", "NEW"])
        self.assertIn("NEW", (self.d / su.LOG_NAME).read_text())

    def test_bad_fetch_changes_nothing(self):
        (self.d / su.FILE_NAME).write_text(json.dumps({"asof": datetime.now(timezone.utc).isoformat(), "tickers": ["A", "B", "C", "D"], "sectors": {}}))
        before = (self.d / su.FILE_NAME).read_text()
        with self.assertRaises(ValueError):
            su.refresh(self.rows(["A"]), self.d)                       # too few parsed: wrong page / layout change
        with self.assertRaises(ValueError):
            su.refresh("<html>error 503</html>", self.d)
        self.assertEqual((self.d / su.FILE_NAME).read_text(), before)

    def test_an_implausibly_large_change_is_refused(self):
        (self.d / su.FILE_NAME).write_text(json.dumps({"asof": datetime.now(timezone.utc).isoformat(), "tickers": ["A", "B", "C", "D"], "sectors": {}}))
        su.MAX_CHANGE = 2
        with self.assertRaises(ValueError):
            su.refresh(self.rows(["P", "Q", "R", "S", "T"]), self.d)   # +5 / -4

    def test_extras_are_scanned_alongside_the_index_and_index_sector_wins(self):
        (self.d / su.FILE_NAME).write_text(json.dumps({"asof": datetime.now(timezone.utc).isoformat(), "tickers": ["A", "B", "C", "D"], "sectors": {}}))
        r = su.refresh(page([("A", "Tech"), ("B", "Tech"), ("C", "Tech"), ("D", "Tech")]), self.d, extras=["SNOW", "D", "B"])
        doc = json.loads((self.d / su.FILE_NAME).read_text())
        self.assertEqual(doc["tickers"][-1], "SNOW")
        self.assertEqual((doc["sectors"]["SNOW"], doc["sectors"]["D"]), ("Other", "Tech"))
        self.assertEqual(doc["n"], 5)

    def test_extras_file_parsing(self):
        f = self.d / "extras.txt"
        f.write_text("# comment\nsnow  # cloud\n\nBRK.B\nbad symbol!\n")
        self.assertEqual(su.read_extras(f), ["SNOW", "BRK-B"])
        self.assertEqual(su.read_extras(self.d / "missing.txt"), [])

    def test_no_change_writes_no_log_line(self):
        (self.d / su.FILE_NAME).write_text(json.dumps({"asof": datetime.now(timezone.utc).isoformat(), "tickers": ["A", "B", "C"], "sectors": {}}))
        r = su.refresh(self.rows(["A", "B", "C"]), self.d)
        self.assertEqual((r["added"], r["removed"]), ([], []))
        self.assertFalse((self.d / su.LOG_NAME).exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
