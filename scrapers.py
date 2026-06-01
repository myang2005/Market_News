"""
Web scrapers for market calendar data.

Priority sources:
  1. Investing.com  — economic calendar (same data that powers MarketWatch)
  2. yfinance       — earnings dates for the priority watchlist
  3. NewsAPI        — market headlines (handled in news_data.py)
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

IMPORTANCE_MAP = {3: "🔴 High", 2: "🟡 Medium", 1: "⚪ Low", 0: "⚪ Low"}
USA_COUNTRY_CODE = "5"

# Medium-importance events worth keeping for the *daily* calendar (others filtered out)
MEDIUM_KEEP_KEYWORDS = {
    "jobless claims", "initial claims", "continuing claims",
    "retail sales", "ism", "pmi", "purchasing managers",
    "consumer confidence", "consumer sentiment", "michigan",
    "jolts", "job openings", "adp",
    "durable goods", "industrial production", "capacity utilization",
    "housing starts", "building permits", "existing home", "new home",
    "trade balance",
}

# ── Week-ahead priority scoring ───────────────────────────────────────────────
# Each tuple: (score, [keyword substrings]). First match wins. Higher = more important.
WEEK_EVENT_SCORES: list[tuple[int, list[str]]] = [
    (100, ["fomc", "federal funds rate", "interest rate decision",
           "fomc minutes", "fomc meeting minutes", "fed chair", "powell"]),
    (95,  ["cpi", "consumer price index", "core cpi",
           "ppi", "producer price", "core ppi",
           "pce price", "core pce", "personal consumption expenditure"]),
    (90,  ["nonfarm payrolls", "nonfarm payroll", "unemployment rate",
           "average hourly earnings"]),
    (85,  ["initial jobless claims", "continuing jobless claims", "jobless claims",
           "jolts", "job openings", "adp employment"]),
    (80,  ["gdp", "gross domestic product", "retail sales", "core retail"]),
    (75,  ["consumer confidence", "michigan consumer sentiment", "consumer sentiment",
           "university of michigan", "umich"]),
    (70,  ["ism services", "ism non-manufacturing", "services pmi",
           "s&p global services"]),
    (65,  ["10-year note auction", "30-year bond auction", "treasury auction",
           "note auction", "bond auction"]),
    # Manufacturing / factory — lower score so they yield to the above
    (35,  ["ism manufacturing", "s&p global manufacturing", "manufacturing pmi",
           "purchasing managers", "philly fed", "empire state", "chicago pmi",
           "richmond fed", "dallas fed"]),
]

# Keywords that identify a manufacturing-only event
MANUFACTURING_KEYWORDS: set[str] = {
    "ism manufacturing", "s&p global manufacturing", "manufacturing pmi",
    "purchasing managers", "philly fed", "empire state", "chicago pmi",
    "richmond fed", "dallas fed", "factory orders",
}


def score_week_event(event_name: str) -> int:
    """Return a priority score for a week-ahead calendar event. Higher = more important."""
    el = event_name.lower()
    for score, keywords in WEEK_EVENT_SCORES:
        if any(kw in el for kw in keywords):
            return score
    return 30


def is_manufacturing_event(event_name: str) -> bool:
    """Return True if this event is a manufacturing-only indicator."""
    el = event_name.lower()
    return any(kw in el for kw in MANUFACTURING_KEYWORDS)

# One-liner descriptions for common economic events
EVENT_DESCRIPTIONS = {
    "Nonfarm Payrolls":             "Monthly jobs added ex-farm; biggest labor market mover",
    "Unemployment Rate":            "Headline jobless rate; watched alongside NFP",
    "Average Hourly Earnings":      "Wage growth; signals inflation pressure from labor",
    "CPI":                          "Consumer inflation gauge; key Fed rate-path driver",
    "Core CPI":                     "CPI ex-food & energy; Fed's preferred inflation lens",
    "CPI m/m":                      "Month-over-month consumer price change",
    "Core CPI m/m":                 "Core month-over-month consumer price change",
    "CPI y/y":                      "Year-over-year consumer price inflation",
    "PPI":                          "Producer-level inflation; leading indicator for CPI",
    "Core PPI":                     "PPI ex-food & energy; upstream price pressure signal",
    "PCE Price Index":              "Fed's preferred inflation measure for policy decisions",
    "Core PCE Price Index":         "Fed's primary inflation target gauge",
    "PCE":                          "Fed's preferred inflation measure for policy decisions",
    "Core PCE":                     "Fed's primary inflation target; closely watched",
    "FOMC Statement":               "Fed rate decision and forward guidance; highest impact",
    "Fed Interest Rate Decision":   "Fed rate decision and forward guidance; highest impact",
    "Federal Funds Rate":           "Fed rate decision outcome",
    "FOMC Meeting Minutes":         "Detailed record of Fed debate; reveals policy thinking",
    "Fed Chair Press Conference":   "Powell explains the rate decision live",
    "GDP":                          "Broadest measure of U.S. economic output",
    "GDP Growth Rate":              "Quarter-over-quarter economic output growth",
    "GDP q/q":                      "Quarterly GDP growth rate; economy's headline number",
    "Initial Jobless Claims":       "Weekly new unemployment filings; real-time labor signal",
    "Continuing Jobless Claims":    "Workers still collecting unemployment; labor trend gauge",
    "Retail Sales":                 "Consumer spending on goods; ~70% of GDP is consumption",
    "Core Retail Sales":            "Retail sales ex-autos; cleaner consumer demand signal",
    "ISM Manufacturing PMI":        "Factory sector health; >50 = expansion",
    "ISM Non-Manufacturing PMI":    "Services sector health; dominant share of U.S. economy",
    "ISM Services PMI":             "Services sector health; dominant share of U.S. economy",
    "S&P Global Manufacturing PMI": "Private-sector factory activity gauge",
    "S&P Global Services PMI":      "Private-sector services activity gauge",
    "Consumer Confidence":          "Sentiment on jobs and economy; predicts future spending",
    "Michigan Consumer Sentiment":  "UMich forward-looking consumer confidence gauge",
    "Existing Home Sales":          "Resale activity; reflects housing demand and mortgage rates",
    "New Home Sales":               "New construction sales; leading housing demand indicator",
    "Housing Starts":               "New home construction begins; housing supply signal",
    "Building Permits":             "Authorized future construction; forward housing indicator",
    "Durable Goods Orders":         "Big-ticket manufactured goods orders; business investment proxy",
    "Core Durable Goods Orders":    "Durable goods ex-defense/aircraft; pure capex signal",
    "Trade Balance":                "Exports minus imports; impacts GDP and dollar strength",
    "Industrial Production":        "Factory, mining, and utilities output gauge",
    "Capacity Utilization":         "Share of production capacity in use; inflation signal",
    "JOLTS Job Openings":           "Unfilled jobs count; measures labor market tightness",
    "ADP Employment Change":        "Private payrolls preview ahead of NFP Friday",
    "3-Year Note Auction":          "Treasury debt sale; demand signals appetite for short rates",
    "10-Year Note Auction":         "Benchmark Treasury auction; key for yield direction",
    "30-Year Bond Auction":         "Long-end Treasury sale; fiscal and duration risk signal",
    "EIA Crude Oil Inventories":    "Weekly U.S. oil stock change; moves crude prices",
    "EIA Natural Gas Storage":      "Weekly gas inventory change; seasonal price driver",
    "Fed Chair Powell Speech":      "Powell remarks on rates and economy; very high impact",
}


def get_event_note(event_name: str) -> str:
    """Return a one-liner description for a known economic event."""
    if event_name in EVENT_DESCRIPTIONS:
        return EVENT_DESCRIPTIONS[event_name]
    el = event_name.lower()
    for key, desc in EVENT_DESCRIPTIONS.items():
        if key.lower() in el or el in key.lower():
            return desc
    return "—"

def scrape_investing_calendar(target_date: date, countries: list = None) -> list[dict]:
    """
    Scrape Investing.com economic calendar for a given date.
    Returns events with: time (ET), event, importance, note, previous.
    Falls back to empty list on any error.
    """
    if countries is None:
        countries = [USA_COUNTRY_CODE]

    # "currentTab": "custom" tells the endpoint to respect dateFrom/dateTo.
    # Previously "today" caused the endpoint to always return today's events,
    # ignoring the requested date entirely.
    data_payload = {
        "dateFrom": str(target_date),
        "dateTo":   str(target_date),
        "timeZone": "8",
        "currentTab": "custom",
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
            # Row-level date validation: each <tr> carries data-event-datetime.
            # If present and it doesn't match target_date, skip the row — this
            # catches cases where the endpoint still leaks events from other dates.
            row_dt = row.get("data-event-datetime", "")
            if row_dt:
                try:
                    row_date = date.fromisoformat(str(row_dt)[:10])
                    if row_date != target_date:
                        continue
                except ValueError:
                    pass  # unparseable — include the row rather than silently dropping it

            time_td   = row.find("td", class_="time")
            event_td  = row.find("td", class_="event")
            prev_td   = row.find("td", class_="prev")

            period_span = event_td.find("span", class_="smallGray") if event_td else None
            event_name  = event_td.get_text(strip=True) if event_td else ""
            if period_span:
                event_name = event_name.replace(period_span.get_text(strip=True), "").strip()

            bull_icons       = row.find_all("i", class_="grayFullBullishIcon")
            importance_level = len(bull_icons)
            importance       = IMPORTANCE_MAP.get(importance_level, "⚪ Low")

            events.append({
                "time (ET)":  time_td.get_text(strip=True) if time_td else "—",
                "event":      event_name,
                "importance": importance,
                "note":       get_event_note(event_name),
                "previous":   prev_td.get_text(strip=True) if prev_td else "—",
                "_level":     importance_level,
            })

        events.sort(key=lambda e: (-e["_level"], e["time (ET)"]))
        for e in events:
            e.pop("_level", None)

        return events

    except Exception as ex:
        print(f"Investing.com calendar scrape error: {ex}")
        return []


def scrape_week_investing_calendar(monday: date) -> list[dict]:
    """
    Scrape Investing.com for the full trading week (Mon–Fri).

    Includes a similarity guard: if two or more consecutive days return event
    sets that overlap by >75%, the API is almost certainly returning the same
    cached/today data for every requested date.  In that case we stop early and
    log a warning rather than stamping identical events across the whole week.
    """
    all_events: list[dict] = []
    prev_names: frozenset[str] = frozenset()
    consecutive_dupes: int = 0

    for days_offset in range(5):
        day = monday + timedelta(days=days_offset)
        events = scrape_investing_calendar(day)

        if not events:
            prev_names = frozenset()
            consecutive_dupes = 0
            continue

        curr_names = frozenset(e.get("event", "") for e in events)

        if prev_names:
            union = prev_names | curr_names
            overlap_ratio = len(prev_names & curr_names) / len(union) if union else 0
            if overlap_ratio > 0.75:
                # This day looks like a copy of the previous day — skip its events.
                # After 2 consecutive skips, stop fetching entirely.
                consecutive_dupes += 1
                print(
                    f"[week_calendar] {day.strftime('%a %b %d')}: event set "
                    f"{overlap_ratio:.0%} identical to previous day — skipping."
                )
                if consecutive_dupes >= 2:
                    print(
                        "[week_calendar] Stopping: Investing.com appears to be "
                        "returning today's events for every requested date."
                    )
                    break
                prev_names = curr_names
                continue  # do NOT add this day's events to all_events
            else:
                consecutive_dupes = 0

        prev_names = curr_names
        for e in events:
            e["date"] = day.strftime("%a %b %d")
        all_events.extend(events)

    return all_events


# ── Earnings calendar via yfinance ────────────────────────────────────────────

EARNINGS_WATCHLIST = [
    # Magnificent 7
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA",
    # Financials
    "JPM", "GS", "MS", "BAC", "WFC", "C", "BLK", "AXP",
    # Semis & hardware
    "AMD", "AVGO", "QCOM", "MU", "AMAT", "INTC", "ARM", "ASML", "TSM",
    # Enterprise tech
    "CRM", "ORCL", "NOW", "SNOW", "PLTR",
    # Consumer / retail
    "WMT", "TGT", "COST", "HD", "NKE",
    # Media / streaming
    "NFLX", "DIS", "SPOT",
    # Other large-caps
    "UBER", "V", "MA", "UNH", "LLY", "XOM", "CVX", "BA", "CAT", "RDDT",
]
# Deduplicate while preserving order
_seen = set()
EARNINGS_WATCHLIST = [x for x in EARNINGS_WATCHLIST if not (_seen.add(x) or x in _seen)]

COMPANY_NAMES = {
    "AAPL":  "Apple",
    "MSFT":  "Microsoft",
    "NVDA":  "Nvidia",
    "AMZN":  "Amazon",
    "GOOGL": "Alphabet",
    "META":  "Meta",
    "TSLA":  "Tesla",
    "JPM":   "JPMorgan Chase",
    "GS":    "Goldman Sachs",
    "MS":    "Morgan Stanley",
    "BAC":   "Bank of America",
    "WFC":   "Wells Fargo",
    "C":     "Citigroup",
    "BLK":   "BlackRock",
    "AXP":   "American Express",
    "AMD":   "AMD",
    "AVGO":  "Broadcom",
    "QCOM":  "Qualcomm",
    "MU":    "Micron Technology",
    "AMAT":  "Applied Materials",
    "INTC":  "Intel",
    "ARM":   "Arm Holdings",
    "ASML":  "ASML",
    "TSM":   "TSMC",
    "CRM":   "Salesforce",
    "ORCL":  "Oracle",
    "NOW":   "ServiceNow",
    "SNOW":  "Snowflake",
    "PLTR":  "Palantir",
    "WMT":   "Walmart",
    "TGT":   "Target",
    "COST":  "Costco",
    "HD":    "Home Depot",
    "NKE":   "Nike",
    "NFLX":  "Netflix",
    "DIS":   "Disney",
    "SPOT":  "Spotify",
    "UBER":  "Uber",
    "V":     "Visa",
    "MA":    "Mastercard",
    "UNH":   "UnitedHealth",
    "LLY":   "Eli Lilly",
    "XOM":   "ExxonMobil",
    "CVX":   "Chevron",
    "BA":    "Boeing",
    "CAT":   "Caterpillar",
    "RDDT":  "Reddit",
}


def get_earnings_this_week(monday: date) -> list[dict]:
    """Return earnings reports expected this week for the priority watchlist."""
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
            for earn_dt in earn_dates:
                earn_date = earn_dt.date() if hasattr(earn_dt, "date") else earn_dt
                if isinstance(earn_date, date) and monday <= earn_date <= friday:
                    eps_est = cal.get("Earnings Average")
                    rev_est = cal.get("Revenue Average")
                    reporting.append({
                        "company":    COMPANY_NAMES.get(ticker_sym, ticker_sym),
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
                        "company":  COMPANY_NAMES.get(ticker_sym, ticker_sym),
                        "ticker":   ticker_sym,
                        "date":     earn_date.strftime("%a %b %d"),
                        "eps_est":  f"${eps_est:.2f}" if eps_est else "—",
                        "rev_est":  _fmt_revenue(rev_est),
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
