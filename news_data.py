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
    Returns only high-importance (🔴) events, matching the week-ahead filter.
    Falls back to a minimal stub if scraping fails.
    """
    try:
        from scrapers import scrape_investing_calendar
        events = scrape_investing_calendar(report_date)
        if events:
            filtered = [e for e in events if e.get("importance", "") == "🔴 High"]
            return filtered if filtered else events
    except Exception as e:
        print(f"Calendar scrape failed: {e}")

    return [{"time (ET)": "—", "event": "Economic calendar unavailable",
             "importance": "—", "note": "—", "previous": "—"}]


# ── Week ahead calendar (Mondays) ─────────────────────────────────────────────

def get_week_ahead_calendar(monday: date) -> list[dict]:
    """
    Live week-ahead economic calendar for Monday morning reports.

    Filtering logic:
    - Score every event by market importance (Fed > inflation > labor > growth > services > manufacturing).
    - Keep High and Medium events that score >= 65; always keep score >= 90.
    - Deduplicate: same event name on the same day (ignoring parenthetical qualifiers) keeps only one row.
    - Cap manufacturing-only events at 1 for the whole week when >= 5 higher-priority events exist.
    - Sort within each day by score descending so the most important event leads.
    """
    import re

    def _normalize(name: str) -> str:
        return re.sub(r"\s*\(.*?\)", "", name).lower().strip()

    try:
        from scrapers import (
            scrape_week_investing_calendar,
            score_week_event,
            is_manufacturing_event,
        )
        raw = scrape_week_investing_calendar(monday)

        # Build a day-order map so we can sort chronologically (not alphabetically by day name)
        day_order = {
            (monday + timedelta(days=i)).strftime("%a %b %d"): i
            for i in range(5)
        }

        # Annotate scores
        for e in raw:
            e["_score"] = score_week_event(e.get("event", ""))
            e["_mfg"]   = is_manufacturing_event(e.get("event", ""))

        # Keep only high-importance events, consistent with Today's Economic Calendar.
        candidates = [
            e for e in raw
            if e.get("importance", "") == "🔴 High"
        ]

        # Pass 1 — same-day dedup: same normalised name + same date → keep highest-scored
        seen: dict[tuple, dict] = {}
        for e in candidates:
            key = (e.get("date", ""), _normalize(e.get("event", "")))
            if key not in seen or e["_score"] > seen[key]["_score"]:
                seen[key] = e
        deduped = list(seen.values())

        # Pass 2 — cross-day dedup guard: if the same event name appears on ≥3
        # distinct days within one week it is almost certainly an API artifact
        # (the scraper returned today's events for every requested future date and
        # stamped each copy with a different day).  Collapse each such event to its
        # single first/earliest occurrence.
        from collections import Counter
        name_day_count: Counter = Counter(
            _normalize(e.get("event", "")) for e in deduped
        )
        cross_day_repeated = {n for n, cnt in name_day_count.items() if cnt >= 3}
        if cross_day_repeated:
            seen_repeated: set[str] = set()
            clean: list[dict] = []
            for e in deduped:
                n = _normalize(e.get("event", ""))
                if n in cross_day_repeated:
                    if n not in seen_repeated:
                        seen_repeated.add(n)
                        clean.append(e)
                    # else: drop duplicate cross-day occurrence
                else:
                    clean.append(e)
            deduped = clean

        # Split manufacturing vs everything else
        non_mfg = [e for e in deduped if not e["_mfg"]]
        mfg     = [e for e in deduped if e["_mfg"]]

        # Cap manufacturing at 1 per week when enough other macro data exists
        if len(non_mfg) >= 5:
            mfg = mfg[:1]

        result = non_mfg + mfg
        result.sort(key=lambda e: (day_order.get(e.get("date", ""), 99), -e["_score"]))

        for e in result:
            e.pop("_score", None)
            e.pop("_mfg",   None)

        if result:
            return result

    except Exception as ex:
        print(f"Week ahead calendar scrape failed: {ex}")

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
    ]
