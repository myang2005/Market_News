"""
Standalone scheduler: generates and saves the daily report at 7:00 AM ET.
Run with: python3 scheduler.py
"""

import os
import json
import logging
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

from apscheduler.schedulers.blocking import BlockingScheduler
import report_generator

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

REPORTS_DIR = Path(__file__).parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

ET = ZoneInfo("America/New_York")


def run_daily_report():
    today = date.today()
    log.info(f"Running daily report for {today}")
    report = report_generator.generate_report(force_date=today)

    out_path = REPORTS_DIR / f"{today}.json"
    # Convert dates to strings for JSON serialization
    serializable = {
        k: str(v) if isinstance(v, date) else v
        for k, v in report.items()
    }
    out_path.write_text(json.dumps(serializable, indent=2, default=str))
    log.info(f"Report saved to {out_path}")

    if not report["market_open"]:
        log.info("Market was closed — no full report generated.")
    else:
        log.info("Full report generated successfully.")


if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone=ET)
    scheduler.add_job(
        run_daily_report,
        trigger="cron",
        hour=7,
        minute=0,
        id="daily_market_report",
        name="Daily Market Report at 7 AM ET",
        replace_existing=True,
    )
    log.info("Scheduler started — daily report will run at 7:00 AM ET.")
    log.info("Press Ctrl+C to stop.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler stopped.")
