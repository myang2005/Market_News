"""Orchestrates data collection and report generation."""

import os
import json
from datetime import date, timedelta
from dotenv import load_dotenv
from pathlib import Path

import market_data
import news_data
import summarizer

load_dotenv(Path(__file__).parent / ".env", override=True)

CACHE_DIR = Path(__file__).parent / "reports"
CACHE_DIR.mkdir(exist_ok=True)


def _cache_path(report_date: date) -> Path:
    return CACHE_DIR / f"{report_date}.json"


def _save_cache(report: dict):
    """Save report to disk, converting dates to strings."""
    path = _cache_path(report["report_date"])
    serialisable = {
        k: str(v) if isinstance(v, date) else v
        for k, v in report.items()
    }
    path.write_text(json.dumps(serialisable, indent=2, default=str))
    _prune_old_reports()


def _prune_old_reports(keep_days: int = 15):
    cutoff = date.today() - timedelta(days=keep_days)
    for p in CACHE_DIR.glob("*.json"):
        try:
            if date.fromisoformat(p.stem) < cutoff:
                p.unlink()
        except ValueError:
            pass


def _load_cache(report_date: date):
    """Load today's report from disk if it exists."""
    path = _cache_path(report_date)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        # Re-parse date strings back to date objects
        for key in ("report_date", "prior_day"):
            if data.get(key) and data[key] != "None":
                data[key] = date.fromisoformat(data[key])
            elif data.get(key) == "None":
                data[key] = None
        return data
    except Exception:
        return None


def generate_report(force_date: date = None) -> dict:
    """
    Generate the full daily markets report.

    Returns a dict with keys:
      - report_date, prior_day, market_open, is_monday
      - prices, headlines, summary
      - macro_calendar       (today's economic events from Investing.com)
      - earnings_today       (watchlist companies reporting today)
      - week_ahead           (Mon only: full-week economic calendar)
      - earnings_this_week   (Mon only: watchlist earnings for the week)
    """
    today = force_date or date.today()

    # ── Disk cache: return today's report immediately if already generated ──────
    cached = _load_cache(today)
    if cached is not None:
        return cached

    prior_day = market_data.get_prior_trading_day(today)

    if prior_day is None:
        return _empty_report(today, None)

    was_open = market_data.is_trading_day(prior_day)
    if not was_open:
        return _empty_report(today, prior_day)

    is_monday = today.weekday() == 0

    # ── Collect market data ───────────────────────────────────────────────────
    prices   = market_data.fetch_prices(prior_day)
    headlines = news_data.get_top_headlines(prior_day)

    # ── Calendars ─────────────────────────────────────────────────────────────
    macro_calendar = news_data.get_macro_calendar(today)

    # Earnings for today from the priority watchlist
    try:
        from scrapers import get_earnings_today
        earnings_today = get_earnings_today(today)
    except Exception:
        earnings_today = []

    week_ahead = []
    earnings_this_week = []
    if is_monday:
        week_ahead = news_data.get_week_ahead_calendar(today)
        try:
            from scrapers import get_earnings_this_week
            earnings_this_week = get_earnings_this_week(today)
        except Exception:
            earnings_this_week = []

    # ── AI summary ────────────────────────────────────────────────────────────
    summary = summarizer.generate_summary(
        prices, headlines, today, prior_day, is_monday=is_monday
    )

    report = {
        "report_date":       today,
        "prior_day":         prior_day,
        "market_open":       True,
        "is_monday":         is_monday,
        "prices":            prices,
        "headlines":         headlines,
        "summary":           summary,
        "macro_calendar":    macro_calendar,
        "earnings_today":    earnings_today,
        "week_ahead":        week_ahead,
        "earnings_this_week": earnings_this_week,
    }
    _save_cache(report)
    return report


def _empty_report(today: date, prior_day) -> dict:
    return {
        "report_date":       today,
        "prior_day":         prior_day,
        "market_open":       False,
        "is_monday":         today.weekday() == 0,
        "prices":            {},
        "headlines":         [],
        "summary":           {},
        "macro_calendar":    [],
        "earnings_today":    [],
        "week_ahead":        [],
        "earnings_this_week": [],
    }
