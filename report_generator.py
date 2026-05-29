"""Orchestrates data collection and report generation."""

import os
from datetime import date
from dotenv import load_dotenv

import market_data
import news_data
import summarizer

load_dotenv()


def generate_report(force_date: date = None) -> dict:
    """
    Generate the full daily markets report.

    Returns a dict with keys:
      - report_date
      - prior_day
      - market_open  (bool)
      - prices       (dict)
      - headlines    (list)
      - summary      (dict from Claude)
      - macro_calendar (list)
    """
    today = force_date or date.today()
    prior_day = market_data.get_prior_trading_day(today)

    if prior_day is None:
        return {
            "report_date": today,
            "prior_day": None,
            "market_open": False,
            "prices": {},
            "headlines": [],
            "summary": {},
            "macro_calendar": [],
        }

    was_open = market_data.is_trading_day(prior_day)

    if not was_open:
        return {
            "report_date": today,
            "prior_day": prior_day,
            "market_open": False,
            "prices": {},
            "headlines": [],
            "summary": {},
            "macro_calendar": [],
        }

    is_monday = today.weekday() == 0  # Monday = 0

    # Collect data
    prices = market_data.fetch_prices(prior_day)
    headlines = news_data.get_top_headlines(prior_day)
    macro_calendar = news_data.get_macro_calendar_stub(today)
    week_ahead = news_data.get_week_ahead_stub(today) if is_monday else []
    summary = summarizer.generate_summary(prices, headlines, today, prior_day, is_monday=is_monday)

    return {
        "report_date": today,
        "prior_day": prior_day,
        "market_open": True,
        "is_monday": is_monday,
        "prices": prices,
        "headlines": headlines,
        "summary": summary,
        "macro_calendar": macro_calendar,
        "week_ahead": week_ahead,
    }
