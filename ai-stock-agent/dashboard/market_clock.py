"""
US equity market session state and the scanner's own schedule, for the dashboard's live countdowns.

Times are America/New_York. The 2026 NYSE holiday and early-close lists are hard-coded (verify them
against the exchange calendar each year). The scan schedule mirrors deploy/gcp/05_schedule_jobs.sh.
"""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
HOLIDAYS_2026 = {date(2026, 1, 1): "New Year's Day", date(2026, 1, 19): "Martin Luther King Jr. Day", date(2026, 2, 16): "Presidents' Day",
                 date(2026, 4, 3): "Good Friday", date(2026, 5, 25): "Memorial Day", date(2026, 6, 19): "Juneteenth",
                 date(2026, 7, 3): "Independence Day (observed)", date(2026, 9, 7): "Labor Day", date(2026, 11, 26): "Thanksgiving",
                 date(2026, 12, 25): "Christmas"}
EARLY_CLOSE_2026 = {date(2026, 11, 27): time(13, 0), date(2026, 12, 24): time(13, 0)}

# (label, weekday set, list of (hour, minute)); weekdays: Mon=0
WEEKDAYS = {0, 1, 2, 3, 4}
SCHEDULE = [
    ("Weekly report", {0}, [(8, 55)]),
    ("Pre-market brief", WEEKDAYS, [(9, 0)]),
    ("Gap scan", WEEKDAYS, [(9, 45)]),
    ("Go / no-go", WEEKDAYS, [(9, 50)]),
    ("Hourly scan", WEEKDAYS, [(h, 0) for h in range(10, 16)]),
    ("Swing trade", WEEKDAYS, [(10, 5)]),
    ("Closing recap", WEEKDAYS, [(15, 45)]),
]


def _et(now: datetime = None) -> datetime:
    return (now or datetime.now(ET)).astimezone(ET)


def is_trading_day(d: date) -> bool:
    return d.weekday() < 5 and d not in HOLIDAYS_2026


def session(now: datetime = None) -> dict:
    """{state: premarket|open|afterhours|closed|holiday, label, next_change_at, next_change_label}"""
    n = _et(now)
    d = n.date()
    close_t = EARLY_CLOSE_2026.get(d, time(16, 0))
    at = lambda day, t: datetime.combine(day, t, tzinfo=ET)

    def next_trading_day(after: date) -> date:
        x = after + timedelta(days=1)
        while not is_trading_day(x):
            x += timedelta(days=1)
        return x

    if not is_trading_day(d):
        nxt = next_trading_day(d)
        why = HOLIDAYS_2026.get(d)
        return {"state": "holiday" if why else "closed", "label": f"Closed: {why}" if why else "Closed (weekend)",
                "next_change_at": at(nxt, time(9, 30)).isoformat(), "next_change_label": "Market opens"}
    if n < at(d, time(4, 0)):
        return {"state": "closed", "label": "Closed", "next_change_at": at(d, time(9, 30)).isoformat(), "next_change_label": "Market opens"}
    if n < at(d, time(9, 30)):
        return {"state": "premarket", "label": "Pre-market", "next_change_at": at(d, time(9, 30)).isoformat(), "next_change_label": "Market opens"}
    if n < at(d, close_t):
        return {"state": "open", "label": "Market open" + (" (early close)" if d in EARLY_CLOSE_2026 else ""),
                "next_change_at": at(d, close_t).isoformat(), "next_change_label": "Market closes"}
    if n < at(d, time(20, 0)):
        nxt = next_trading_day(d)
        return {"state": "afterhours", "label": "After hours", "next_change_at": at(nxt, time(9, 30)).isoformat(), "next_change_label": "Market opens"}
    nxt = next_trading_day(d)
    return {"state": "closed", "label": "Closed", "next_change_at": at(nxt, time(9, 30)).isoformat(), "next_change_label": "Market opens"}


def next_events(now: datetime = None, limit: int = 4) -> list:
    """The next scheduled scanner runs (label, ISO time), skipping market holidays."""
    n = _et(now)
    found = []
    for offset in range(0, 8):
        d = n.date() + timedelta(days=offset)
        if not is_trading_day(d):
            continue
        for label, days, times in SCHEDULE:
            if d.weekday() not in days:
                continue
            for h, m in times:
                t = datetime.combine(d, time(h, m), tzinfo=ET)
                if t > n:
                    found.append((t, label))
        if len(found) >= limit and offset >= 0:
            break
    found.sort()
    return [{"name": label, "at": t.isoformat()} for t, label in found[:limit]]
