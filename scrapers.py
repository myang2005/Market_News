"""
Web scrapers for market calendar data.

Priority sources:
  1. Investing.com  — economic calendar (same data that powers MarketWatch)
  2. yfinance       — earnings dates for the priority watchlist
  3. NewsAPI        — market headlines (handled in news_data.py)

Note: MarketWatch requires captcha-verified JS rendering and blocks all
automated access. Seeking Alpha's earnings API is behind a login wall.
Both sites source their calendar data from the same underlying vendors
(Refinitiv / LSEG) that Investing.com uses, so Investing.com gives us
equivalent coverage without the restrictions.
"""

import requests
import yfinance as yf
from bs4 import BeautifulSoup
from datetime import date, timedelta
from typing import Optional


# ── Investing.com economic calendar ──────────────────────────────────────────

INVESTING_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.investing.com/economic-calendar/",
}

# Importance: number of bull icons on Investing.com (3 = high impact)
IMPORTANCE_MAP = {3: "🔴 High", 2: "🟡 Medium", 1: "⚪ Low", 0: "⚪ Low"}

# Only show USA events (country code 5) by default
USA_COUNTRY_CODE = "5"


def scrape_investing_calendar(target_date: date, countries: list = None) -> list[dict]:
    """
    Scrape Investing.com economic calendar for a given date.
    Returns list of event dicts: time, event, period, actual, forecast, previous, importance.
    Falls back to empty list on any error.
    """
    if countries is None:
        countries = [USA_COUNTRY_CODE]

    data_payload = {
        "dateFrom": str(target_date),
        "dateTo":   str(target_date),
        "timeZone": "8",           # ET offset
        "currentTab": "today",
        "limit_from": 0,
    }
    for c in countries:
        data_payload.setdefault("country[]", [])
        if isinstance(data_payload["country[]"], list):
            data_payload["country[]"].append(c)
        else:
            data_payload["country[]"] = [data_payload["country[]"], c]

    try:
        r = requests.post(
            "https://www.investing.com/economic-calendar/Service/getCalendarFilteredData",
            headers=INVESTING_HEADERS,
            data=data_payload,
            timeout=15,
        )
        if r.status_code != 200:
            return []

        html = r.json().get("data", "")
        soup = BeautifulSoup(html, "html.parser")
        rows = soup.find_all("tr", class_="js-event-item")

        events = []
        for row in rows:
            time_td    = row.find("td", class_="time")
            event_td   = row.find("td", class_="event")
            actual_td  = row.find("td", class_="actual")
            fore_td    = row.find("td", class_="forecast")
            prev_td    = row.find("td", class_="prev")

            # Period lives inside the event cell as a smaller span
            period_span = event_td.find("span", class_="smallGray") if event_td else None

            event_name = event_td.get_text(strip=True) if event_td else ""
            if period_span:
                event_name = event_name.replace(period_span.get_text(strip=True), "").strip()

            # Importance = count of filled bull icons
            bull_icons = row.find_all("i", class_="grayFullBullishIcon")
            importance_level = len(bull_icons)

            events.append({
                "time (ET)":  time_td.get_text(strip=True) if time_td else "—",
                "event":      event_name,
                "period":     period_span.get_text(strip=True) if period_span else "—",
                "actual":     actual_td.get_text(strip=True) if actual_td else "—",
                "forecast":   fore_td.get_text(strip=True) if fore_td else "—",
                "previous":   prev_td.get_text(strip=True) if prev_td else "—",
                "importance": IMPORTANCE_MAP.get(importance_level, "⚪ Low"),
                "_level":     importance_level,
            })

        # Sort by importance desc, then time
        events.sort(key=lambda e: (-e["_level"], e["time (ET)"]))
        # Remove internal sort key
        for e in events:
            e.pop("_level", None)

        return events

    except Exception as ex:
        print(f"Investing.com calendar scrape error: {ex}")
        return []


def scrape_week_investing_calendar(monday: date) -> list[dict]:
    """Scrape Investing.com for the full trading week (Mon–Fri)."""
    all_events = []
    for days_offset in range(5):
        day = monday + timedelta(days=days_offset)
        events = scrape_investing_calendar(day)
        for e in events:
            e["date"] = day.strftime("%a %b %d")
        all_events.extend(events)
    return all_events


# ── Earnings calendar via yfinance ────────────────────────────────────────────

EARNINGS_WATCHLIST = [
    # Magnificent 7
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA",
    # Financials
    "JPM", "GS", "MS", "BAC", "WFC", "C",
    # Semis
    "AMD", "AVGO", "QCOM", "MU", "AMAT", "INTC",
    # Energy
    "XOM", "CVX", "COP",
    # Retail / Consumer
    "WMT", "TGT", "COST", "HD", "NKE",
    # Other major names
    "NFLX", "DIS", "RDDT", "CRM", "ORCL",
]


def get_earnings_this_week(monday: date) -> list[dict]:
    """
    Return earnings reports expected this week for the priority watchlist.
    Uses yfinance .calendar to get the next earnings date per ticker.
    """
    friday = monday + timedelta(days=4)
    reporting = []

    for ticker_sym in EARNINGS_WATCHLIST:
        try:
            t = yf.Ticker(ticker_sym)
            cal = t.calendar
            if not cal:
                continue
            earn_dates = cal.get("Earnings Date", [])
            if not earn_dates:
                continue
            # earn_dates is a list; take the nearest upcoming date
            for earn_dt in earn_dates:
                earn_date = earn_dt.date() if hasattr(earn_dt, "date") else earn_dt
                if isinstance(earn_date, date) and monday <= earn_date <= friday:
                    eps_est = cal.get("Earnings Average")
                    rev_est = cal.get("Revenue Average")
                    reporting.append({
                        "ticker":     ticker_sym,
                        "date":       earn_date.strftime("%a %b %d"),
                        "eps_est":    f"${eps_est:.2f}" if eps_est else "—",
                        "rev_est":    _fmt_revenue(rev_est),
                        "_sort_date": earn_date,
                    })
                    break
        except Exception:
            continue

    reporting.sort(key=lambda x: x["_sort_date"])
    for r in reporting:
        r.pop("_sort_date", None)
    return reporting


def get_earnings_today(report_date: date) -> list[dict]:
    """Return earnings reports expected today for the priority watchlist."""
    reporting = []
    for ticker_sym in EARNINGS_WATCHLIST:
        try:
            t = yf.Ticker(ticker_sym)
            cal = t.calendar
            if not cal:
                continue
            earn_dates = cal.get("Earnings Date", [])
            for earn_dt in earn_dates:
                earn_date = earn_dt.date() if hasattr(earn_dt, "date") else earn_dt
                if isinstance(earn_date, date) and earn_date == report_date:
                    eps_est = cal.get("Earnings Average")
                    rev_est = cal.get("Revenue Average")
                    reporting.append({
                        "ticker":  ticker_sym,
                        "date":    earn_date.strftime("%a %b %d"),
                        "eps_est": f"${eps_est:.2f}" if eps_est else "—",
                        "rev_est": _fmt_revenue(rev_est),
                    })
                    break
        except Exception:
            continue
    return reporting


def _fmt_revenue(rev: Optional[float]) -> str:
    if rev is None:
        return "—"
    if rev >= 1e9:
        return f"${rev/1e9:.1f}B"
    if rev >= 1e6:
        return f"${rev/1e6:.0f}M"
    return f"${rev:,.0f}"
