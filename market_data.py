"""Market data collection using yfinance."""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta, date
from typing import Optional
import exchange_calendars as xcals
import pytz


# Ticker map: display name -> yfinance symbol
TICKERS = {
    # Equities
    "S&P 500":      "^GSPC",
    "Nasdaq 100":   "^NDX",
    "Dow Jones":    "^DJI",   # actual DJIA index, not DIA ETF
    "Russell 2000": "^RUT",
    "VIX":          "^VIX",
    # International
    "FTSE 100":     "^FTSE",
    "DAX":          "^GDAXI",
    "Nikkei 225":   "^N225",
    "Hang Seng":    "^HSI",
    # Rates — ^TNX/^TYX report yield * 10 (e.g. 4.455 = 4.455%); ^IRX reports yield/10
    "13-wk T-Bill": "^IRX",   # 13-week T-bill; freely available short-end proxy
    "10Y Treasury": "^TNX",
    "30Y Treasury": "^TYX",
    # FX
    "DXY":          "DX-Y.NYB",
    "EUR/USD":      "EURUSD=X",
    "USD/JPY":      "JPY=X",
    "GBP/USD":      "GBPUSD=X",
    # Commodities
    "WTI Crude":    "CL=F",
    "Brent Crude":  "BZ=F",
    "Gold":         "GC=F",
    "Natural Gas":  "NG=F",
    # Crypto
    "Bitcoin":      "BTC-USD",
}

EQUITY_NAMES = ["S&P 500", "Nasdaq 100", "Dow Jones", "Russell 2000", "VIX"]
INTL_NAMES = ["FTSE 100", "DAX", "Nikkei 225", "Hang Seng"]
RATES_NAMES = ["13-wk T-Bill", "10Y Treasury", "30Y Treasury"]
FX_NAMES = ["DXY", "EUR/USD", "USD/JPY", "GBP/USD"]
COMMODITY_NAMES = ["WTI Crude", "Brent Crude", "Gold", "Natural Gas"]
CRYPTO_NAMES = ["Bitcoin"]


def get_us_calendar():
    return xcals.get_calendar("XNYS")


def is_trading_day(check_date: date) -> bool:
    """Return True if check_date was a valid NYSE trading day."""
    cal = get_us_calendar()
    return cal.is_session(str(check_date))


def get_prior_trading_day(reference_date: date = None) -> Optional[date]:
    """Return the most recent trading day before reference_date (default: today)."""
    if reference_date is None:
        reference_date = date.today()
    cal = get_us_calendar()
    # Walk back up to 10 calendar days
    for days_back in range(1, 11):
        candidate = reference_date - timedelta(days=days_back)
        if cal.is_session(str(candidate)):
            return candidate
    return None


def fetch_prices(prior_day: date) -> dict:
    """
    Fetch prior-day closes for all tickers.
    Returns dict: name -> {close, prev_close, change, pct_change}.
    """
    # We need two trading days to compute daily change
    cal = get_us_calendar()
    sessions = cal.sessions_in_range(
        str(prior_day - timedelta(days=10)), str(prior_day)
    )
    if len(sessions) < 2:
        return {}
    prev_day = pd.Timestamp(sessions[-2])
    target_day = pd.Timestamp(sessions[-1])

    all_symbols = list(TICKERS.values())
    results = {}

    try:
        raw = yf.download(
            all_symbols,
            start=prev_day - timedelta(days=1),
            end=target_day + timedelta(days=1),
            auto_adjust=True,
            progress=False,
            threads=True,
        )
        close_df = raw["Close"] if "Close" in raw else raw

        for name, symbol in TICKERS.items():
            try:
                series = close_df[symbol] if symbol in close_df.columns else close_df
                series = series.dropna()
                if len(series) < 2:
                    continue
                close = float(series.iloc[-1])
                prev_close = float(series.iloc[-2])
                change = close - prev_close
                pct = (change / prev_close) * 100 if prev_close else 0
                results[name] = {
                    "close": close,
                    "prev_close": prev_close,
                    "change": change,
                    "pct_change": pct,
                }
            except Exception:
                continue
    except Exception as e:
        print(f"yfinance bulk download error: {e}")

    return results


def get_yield_spread(prices: dict) -> Optional[float]:
    """
    Compute approximate short-end vs 10Y spread in basis points.
    ^IRX (13-week T-bill) is already in percent (e.g. 4.45 = 4.45%).
    ^TNX (10Y) is also in percent (e.g. 4.455 = 4.455%).
    Spread = 10Y minus short-end, expressed in bps.
    """
    y_short = prices.get("13-wk T-Bill", {}).get("close")
    y10 = prices.get("10Y Treasury", {}).get("close")
    if y_short is not None and y10 is not None:
        return round((y10 - y_short) * 100, 1)
    return None


def format_value(name: str, value: float) -> str:
    """Format a price value for display — always use comma notation, never scientific."""
    if "Treasury" in name or "T-Bill" in name:
        return f"{value:.2f}%"
    if name == "VIX":
        return f"{value:.2f}"          # VIX is an index level, not a %
    if name == "DXY":
        return f"{value:.2f}"
    if name in ("EUR/USD", "GBP/USD"):
        return f"{value:.4f}"
    if name == "USD/JPY":
        return f"{value:.2f}"
    if name == "Bitcoin":
        return f"${value:,.0f}"
    if name in ("WTI Crude", "Brent Crude", "Gold", "Natural Gas"):
        return f"${value:,.2f}"
    if value >= 10000:
        return f"{value:,.0f}"
    if value >= 1000:
        return f"{value:,.2f}"
    return f"{value:.2f}"
