"""News and macro calendar data collection."""

import os
import requests
from datetime import date, timedelta
from typing import Optional


NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

NEWS_QUERIES = [
    "Federal Reserve Fed interest rates",
    "S&P 500 stock market",
    "Treasury yields bonds",
    "inflation CPI PPI",
    "oil crude gold commodities",
    "earnings quarterly results",
]


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
    if not NEWS_API_KEY:
        return []
    seen_titles = set()
    headlines = []
    from_date = prior_day - timedelta(days=1)
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
                    "published": a.get("publishedAt", "")[:10],
                    "description": a.get("description", ""),
                })
    return headlines


def get_week_ahead_stub(monday: date) -> list[dict]:
    """
    Returns the standard recurring high-importance events for the week ahead.
    In a full implementation this would pull from Econoday / Investing.com.
    Days are calculated relative to the Monday date passed in.
    """
    from datetime import timedelta
    mon, tue, wed, thu, fri = [monday + timedelta(days=i) for i in range(5)]

    return [
        {"day": mon.strftime("%A %b %d"), "event": "Markets open — watch pre-market futures and weekend news flow", "importance": "—"},
        {"day": tue.strftime("%A %b %d"), "event": "Check Fed speaker calendar; JOLTS Job Openings (if scheduled)", "importance": "Medium"},
        {"day": wed.strftime("%A %b %d"), "event": "ADP Employment Report (if scheduled); ISM Services PMI; Fed meeting minutes (if applicable)", "importance": "Medium–High"},
        {"day": thu.strftime("%A %b %d"), "event": "Initial Jobless Claims (8:30 AM ET, weekly)", "importance": "Medium"},
        {"day": fri.strftime("%A %b %d"), "event": "Nonfarm Payrolls / Jobs Report (first Friday of month); University of Michigan Sentiment", "importance": "Very High (if NFP week)"},
    ]


def get_macro_calendar_stub(report_date: date) -> list[dict]:
    """
    Returns a stub macro calendar for today.
    In a full implementation this would pull from Investing.com / Econoday / Trading Economics.
    """
    # Placeholder — real implementation would scrape or use a paid API
    return [
        {
            "time": "8:30 AM ET",
            "event": "Initial Jobless Claims",
            "consensus": "N/A",
            "prior": "N/A",
            "importance": "Medium",
        },
    ]
