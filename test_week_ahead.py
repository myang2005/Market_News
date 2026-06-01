"""
Verification: week-ahead calendar does not repeat today's events across all five days.

Mocks scrape_investing_calendar to always return the same event set regardless of
the requested date (replicating the broken-API behaviour), then confirms that
get_week_ahead_calendar collapses the duplicates rather than showing them five times.

Run with:  python3 test_week_ahead.py
"""
from collections import Counter
from datetime import date
from unittest.mock import patch

# The exact events that were appearing repeated in the cached report
_FAKE_TODAY_EVENTS = [
    {"event": "Atlanta Fed GDPNow",    "importance": "🔴 High",   "time (ET)": "10:00", "note": "—", "previous": "—"},
    {"event": "Fed Waller Speaks",     "importance": "🟡 Medium", "time (ET)": "14:00", "note": "—", "previous": "—"},
    {"event": "Construction Spending", "importance": "🟡 Medium", "time (ET)": "10:00", "note": "—", "previous": "—"},
]


def _always_today(target_date, countries=None):
    """Simulates the broken API: returns the same events for every requested date."""
    return [dict(e) for e in _FAKE_TODAY_EVENTS]


def test_no_cross_day_repeats():
    monday = date(2026, 6, 1)

    # Patch at the scrapers module level so scrape_week_investing_calendar picks it up
    with patch("scrapers.scrape_investing_calendar", side_effect=_always_today):
        from news_data import get_week_ahead_calendar
        result = get_week_ahead_calendar(monday)

    event_names = [r["event"] for r in result]
    counts = Counter(event_names)
    repeated = {n: c for n, c in counts.items() if c > 1}

    assert not repeated, (
        f"Events repeated across days (should have been collapsed):\n"
        + "\n".join(f"  {n!r}: {c}x" for n, c in repeated.items())
    )

    # Each of the fake events should appear at most once in the output
    for fake in _FAKE_TODAY_EVENTS:
        occurrences = event_names.count(fake["event"])
        assert occurrences <= 1, f"{fake['event']!r} appeared {occurrences} times"

    print(f"PASS — {len(result)} row(s) returned, no event repeated across days")
    for r in result:
        print(f"  [{r.get('date', '?')}] {r.get('importance', '?')} | {r.get('event', '?')}")


def test_similarity_guard_stops_early():
    """
    The similarity guard in scrape_week_investing_calendar should stop fetching
    after detecting 2+ consecutive identical-ish day results and log a warning.
    """
    monday = date(2026, 6, 1)
    call_log: list[date] = []

    def _logged_today(target_date, countries=None):
        call_log.append(target_date)
        return [dict(e) for e in _FAKE_TODAY_EVENTS]

    with patch("scrapers.scrape_investing_calendar", side_effect=_logged_today):
        import scrapers
        result = scrapers.scrape_week_investing_calendar(monday)

    # With identical events for every day the guard should have stopped before
    # all 5 days were fetched (stops after 3 calls: day1 ok, day2 dupe#1, day3 dupe#2→stop)
    assert len(call_log) < 5, (
        f"Similarity guard did not stop early: scrape_investing_calendar called "
        f"{len(call_log)} times (expected < 5)"
    )
    print(f"PASS — similarity guard stopped after {len(call_log)} day(s) fetched")


if __name__ == "__main__":
    test_no_cross_day_repeats()
    test_similarity_guard_stops_early()
    print("\nAll tests passed.")
