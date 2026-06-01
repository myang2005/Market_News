"""News and macro calendar data collection."""

import os
import requests
from datetime import date, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env", override=True)


def _news_api_key() -> str:
    """Read key at call time so dotenv always has a chance to load first."""
    return os.getenv("NEWS_API_KEY", "")

NEWS_QUERIES = [
    "Federal Reserve interest rates inflation",
    "S&P 500 stock market earnings",
    "Treasury yields oil gold geopolitics",
    "economy GDP jobs data",
]


# ── NewsAPI headlines ─────────────────────────────────────────────────────────

def fetch_newsapi_headlines(api_key: str, query: str, from_date: date, page_size: int = 5) -> list[dict]:
    if not api_key:
        return []
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "from": str(from_date),
        "sortBy": "relevancy",
        "language": "en",
        "pageSize": page_size,
        "apiKey": api_key,
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            return r.json().get("articles", [])
    except Exception:
        pass
    return []


def get_top_headlines(prior_day: date, max_per_category: int = 3) -> list[dict]:
    """Fetch top market headlines from NewsAPI across multiple queries."""
    NEWS_API_KEY = _news_api_key()
    if not NEWS_API_KEY:
        return []
    seen_titles = set()
    headlines = []
    from_date = prior_day
    for query in NEWS_QUERIES:
        articles = fetch_newsapi_headlines(NEWS_API_KEY, query, from_date, page_size=max_per_category)
        for a in articles:
            title = a.get("title", "")
            if title and title not in seen_titles:
                seen_titles.add(title)
                headlines.append({
                    "title": title,
                    "source": a.get("source", {}).get("name", ""),
                    "url": a.get("url", ""),
                    "published": str(a.get("publishedAt") or "")[:10],
                    "description": a.get("description", ""),
                })
    return headlines


# ── Macro calendar (Investing.com as primary source) ─────────────────────────

def get_macro_calendar(report_date: date) -> list[dict]:
    """
    Live economic calendar for report_date.
<<<<<<< HEAD
    Returns only high-impact events plus a curated set of medium-impact ones.
    Falls back to a minimal stub if scraping fails.
    """
    try:
        from scrapers import scrape_investing_calendar, MEDIUM_KEEP_KEYWORDS
        events = scrape_investing_calendar(report_date)
        if events:
            filtered = []
            for e in events:
                imp = e.get("importance", "")
                if imp == "🔴 High":
                    filtered.append(e)
                elif imp == "🟡 Medium":
                    name_lower = e.get("event", "").lower()
                    if any(kw in name_lower for kw in MEDIUM_KEEP_KEYWORDS):
                        filtered.append(e)
            return filtered if filtered else events
    except Exception as e:
        print(f"Calendar scrape failed: {e}")

    return [{"time (ET)": "—", "event": "Economic calendar unavailable",
             "importance": "—", "note": "—", "previous": "—"}]
=======
    Primary source: Investing.com (same underlying data as MarketWatch calendar).
    Falls back to a minimal stub if scraping fails.
    """
    try:
        from scrapers import scrape_investing_calendar
        events = scrape_investing_calendar(report_date)
        if events:
            return events
    except Exception as e:
        print(f"Calendar scrape failed: {e}")

    # Fallback stub
    return [{"time (ET)": "—", "event": "Economic calendar unavailable", "period": "—",
             "actual": "—", "forecast": "—", "previous": "—", "importance": "—"}]
>>>>>>> 81638a08212eb30308f3bcd357044f7983b43bc2


# ── Week ahead calendar (Mondays) ─────────────────────────────────────────────

def get_week_ahead_calendar(monday: date) -> list[dict]:
    """
    Live week-ahead economic calendar for Monday morning reports.
<<<<<<< HEAD
    Scrapes Mon–Fri from Investing.com, filtering to HIGH importance only.
=======
    Scrapes Mon–Fri from Investing.com, filtering to medium+ importance.
>>>>>>> 81638a08212eb30308f3bcd357044f7983b43bc2
    Falls back to a structured stub on failure.
    """
    try:
        from scrapers import scrape_week_investing_calendar
        events = scrape_week_investing_calendar(monday)
<<<<<<< HEAD
        filtered = [e for e in events if e.get("importance", "") == "🔴 High"]
=======
        # Filter to medium importance and above for the week-ahead view
        filtered = [e for e in events if e.get("importance", "") in ("🔴 High", "🟡 Medium")]
>>>>>>> 81638a08212eb30308f3bcd357044f7983b43bc2
        if filtered:
            return filtered
    except Exception as e:
        print(f"Week ahead calendar scrape failed: {e}")

<<<<<<< HEAD
    # Fallback stub — high-impact anchors only
    mon, wed, thu, fri = [monday + timedelta(days=i) for i in [0, 2, 3, 4]]
    return [
        {"date": mon.strftime("%a %b %d"), "event": "Markets open",
         "importance": "🔴 High", "note": "Watch overnight futures and any weekend geopolitical news", "previous": "—"},
        {"date": wed.strftime("%a %b %d"), "event": "ADP Employment Change",
         "importance": "🔴 High", "note": "Private payrolls preview ahead of NFP Friday", "previous": "—"},
        {"date": thu.strftime("%a %b %d"), "event": "Initial Jobless Claims",
         "importance": "🔴 High", "note": "Weekly new unemployment filings; real-time labor signal", "previous": "—"},
        {"date": fri.strftime("%a %b %d"), "event": "Nonfarm Payrolls",
         "importance": "🔴 High", "note": "Monthly jobs report; most watched labor market data", "previous": "—"},
=======
    # Fallback stub
    mon, tue, wed, thu, fri = [monday + timedelta(days=i) for i in range(5)]
    return [
        {"date": mon.strftime("%a %b %d"), "event": "Markets open — watch futures and weekend news", "importance": "—"},
        {"date": tue.strftime("%a %b %d"), "event": "JOLTS Job Openings (if scheduled); Fed speakers", "importance": "🟡 Medium"},
        {"date": wed.strftime("%a %b %d"), "event": "ADP Employment; ISM Services PMI; Fed Minutes (if applicable)", "importance": "🟡 Medium"},
        {"date": thu.strftime("%a %b %d"), "event": "Initial Jobless Claims (8:30 AM ET)", "importance": "🟡 Medium"},
        {"date": fri.strftime("%a %b %d"), "event": "Nonfarm Payrolls (first Friday); UMich Sentiment", "importance": "🔴 High"},
>>>>>>> 81638a08212eb30308f3bcd357044f7983b43bc2
    ]
