import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import track_record as tr


def make_db(path, rows):
    con = sqlite3.connect(path)
    con.execute("create table llm_decisions(scan_id text, decided_at text, ticker text, raw_decision text, raw_confidence real)")
    con.executemany("insert into llm_decisions values (?,?,?,?,?)", rows)
    con.commit()
    return con


class ChainTests(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.db, self.chain, self.rev = self.d / "x.db", self.d / "chain.json", self.d / "rev.csv"
        self.rows = [("s1", "2026-01-05T15:00:00", "AAA", "BUY", 0.8123456), ("s1", "2026-01-05T15:00:01", "BBB", "HOLD", 0.5),
                     ("s2", "2026-01-06T15:00:00", "AAA", "HOLD", None), ("s3", "2026-03-30T15:00:00", "CCC", "BUY", 0.9)]
        self.con = make_db(self.db, self.rows)

    def test_commits_only_completed_days_and_chains(self):
        r = tr.update(self.db, self.chain, self.rev, today="2026-03-30")
        self.assertEqual((r["days"], r["first"], r["last"]), (2, "2026-01-05", "2026-01-06"))      # 03-30 is still "today"
        ch = json.loads(self.chain.read_text())
        self.assertEqual(ch[0]["prev"], tr.GENESIS)
        self.assertEqual(ch[1]["prev"], ch[0]["hash"])
        self.assertTrue(tr.verify_chain(ch))
        r2 = tr.update(self.db, self.chain, self.rev, today="2026-03-31")
        self.assertEqual((r2["days"], r2["new_days"]), (3, 1))                                       # existing days untouched
        self.assertEqual(json.loads(self.chain.read_text())[:2], ch)

    def test_tampering_with_the_chain_file_is_detected(self):
        tr.update(self.db, self.chain, self.rev, today="2026-04-01")
        ch = json.loads(self.chain.read_text())
        ch[0]["digest"] = "f" * 64
        self.chain.write_text(json.dumps(ch))
        self.assertFalse(tr.verify(self.chain)["chain_ok"])
        with self.assertRaises(RuntimeError):
            tr.update(self.db, self.chain, self.rev, today="2026-04-02")

    def test_rewriting_history_breaks_every_later_hash(self):
        tr.update(self.db, self.chain, self.rev, today="2026-04-01")
        ch = json.loads(self.chain.read_text())
        forged = tr.day_digest([tr._line("s1", "2026-01-05T15:00:00", "AAA", "SELL", 0.81)])
        ch[0]["digest"] = forged                        # attacker edits day 1 but keeps the old hashes
        self.assertFalse(tr.verify_chain(ch))

    def test_reveal_delay_and_verification_from_revealed_rows(self):
        tr.update(self.db, self.chain, self.rev, today="2026-04-01")             # cutoff = 45 days earlier = 2026-02-15
        text = self.rev.read_text()
        self.assertIn("AAA", text)                                                # January days are revealed
        self.assertNotIn("CCC", text)                                             # 03-30 is inside the 45-day window
        v = tr.verify(self.chain, self.rev)
        self.assertTrue(v["chain_ok"] and v["revealed_ok"])
        self.assertEqual(v["revealed_days_checked"], 2)

    def test_edited_revealed_row_fails_verification(self):
        tr.update(self.db, self.chain, self.rev, today="2026-04-01")
        self.rev.write_text(self.rev.read_text().replace("BUY", "SELL"))
        self.assertFalse(tr.verify(self.chain, self.rev)["revealed_ok"])

    def test_confidence_rounding_is_stable_through_csv(self):
        tr.update(self.db, self.chain, self.rev, today="2026-04-01")
        self.assertIn("0.8123", self.rev.read_text())
        self.assertTrue(tr.verify(self.chain, self.rev)["revealed_ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
