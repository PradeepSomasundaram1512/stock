import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import market_clock as mc

ET = mc.ET
dt = lambda *a: datetime(*a, tzinfo=ET)


class SessionTests(unittest.TestCase):
    def test_states_on_a_normal_day(self):          # Fri 2026-09-25
        for (h, m), want in {(3, 0): "closed", (4, 0): "premarket", (9, 29): "premarket", (9, 30): "open", (15, 59): "open",
                             (16, 0): "afterhours", (19, 59): "afterhours", (20, 0): "closed"}.items():
            self.assertEqual(mc.session(dt(2026, 9, 25, h, m))["state"], want, (h, m))

    def test_weekend_and_next_open(self):
        s = mc.session(dt(2026, 9, 26, 12, 0))      # Saturday
        self.assertEqual((s["state"], s["next_change_at"][:16]), ("closed", "2026-09-28T09:30"))

    def test_holiday(self):
        s = mc.session(dt(2026, 11, 26, 11, 0))     # Thanksgiving (Thu)
        self.assertEqual(s["state"], "holiday")
        self.assertIn("Thanksgiving", s["label"])
        self.assertEqual(s["next_change_at"][:10], "2026-11-27")

    def test_early_close(self):
        self.assertEqual(mc.session(dt(2026, 11, 27, 12, 59))["state"], "open")
        self.assertEqual(mc.session(dt(2026, 11, 27, 13, 0))["state"], "afterhours")

    def test_friday_after_close_points_to_monday(self):
        self.assertEqual(mc.session(dt(2026, 9, 25, 17, 0))["next_change_at"][:10], "2026-09-28")

    def test_holiday_before_a_long_weekend(self):
        # Fri 2026-07-03 is the observed holiday, so Thursday after close -> next open is Monday 07-06
        self.assertEqual(mc.session(dt(2026, 7, 2, 17, 0))["next_change_at"][:10], "2026-07-06")

    def test_dst_offsets_are_handled(self):        # March 9 is right after the spring-forward
        s = mc.session(dt(2026, 3, 9, 9, 30))
        self.assertEqual(s["state"], "open")
        self.assertTrue(s["next_change_at"].endswith("-04:00"))


class ScheduleTests(unittest.TestCase):
    def test_next_hourly_scan(self):
        ev = mc.next_events(dt(2026, 9, 25, 13, 10))
        self.assertEqual([(e["name"], e["at"][11:16]) for e in ev if e["name"] == "Hourly scan"][0], ("Hourly scan", "14:00"))

    def test_rolls_over_weekend_and_skips_holiday(self):
        ev = mc.next_events(dt(2026, 9, 25, 16, 30), limit=2)          # Friday evening
        self.assertEqual(ev[0]["at"][:10], "2026-09-28")
        self.assertEqual(ev[0]["name"], "Weekly report")               # Monday 08:55 comes first
        ev = mc.next_events(dt(2026, 11, 25, 16, 30), limit=1)         # day before Thanksgiving
        self.assertEqual(ev[0]["at"][:10], "2026-11-27")

    def test_no_events_on_a_closed_day(self):
        for e in mc.next_events(dt(2026, 12, 24, 17, 0), limit=3):
            self.assertNotEqual(e["at"][:10], "2026-12-25")


if __name__ == "__main__":
    unittest.main(verbosity=2)
