# pylint: disable=invalid-name
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
import logging

from src.logging_setup import configure as _configure_logging
from src.alert_service import run_daily_search_and_alert

# Configure logging once for CLI context.
_configure_logging()
logger = logging.getLogger(__name__)

def main():
    eastern = pytz.timezone("US/Eastern")
    scheduler = BlockingScheduler(timezone=eastern)
    trigger = CronTrigger(hour=8, minute=0, timezone=eastern)
    scheduler.add_job(run_daily_search_and_alert, trigger, name="daily_alert")
    logger.info("Alert scheduler started – will run daily at 08:00 US/Eastern")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    main() 