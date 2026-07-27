"""
scheduler.py
============
Periodic scheduler for scraper jobs, built on APScheduler's BlockingScheduler.

Run it as a long-lived process (e.g. its own Docker container / systemd unit):
    python -m scrapers.scheduler

Each job below calls scrapers.worker.run_job(), so the exact same job payload
shape is shared between "run this once by hand" (worker.py CLI) and
"run this every N hours forever" (this file).

Adjust SCHEDULE to fit your rate-limit/coverage tradeoff - scraping too
aggressively is both rude to the target sites and more likely to get you
blocked, so intervals here default to a conservative multi-hour cadence.
"""

from __future__ import annotations

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from scrapers.worker import run_job
from services.scraper_logger import get_logger

logger = get_logger(__name__)

# Each entry: (job_id, trigger, payload)
SCHEDULE = [
    (
        "autochek_ke_hourly",
        IntervalTrigger(hours=4),
        {"scraper": "autochek", "max_listings": 200, "kwargs": {"country": "ke"}},
    ),
    (
        "jiji_ke_cars_hourly",
        IntervalTrigger(hours=4),
        {"scraper": "jiji", "max_listings": 300, "kwargs": {"category_path": "/cars"}},
    ),
    (
        # Reference data changes rarely - once a week is plenty.
        "carapi_reference_weekly",
        CronTrigger(day_of_week="sun", hour=3, minute=0),
        {
            "scraper": "carapi",
            "kwargs": {"years": list(range(2015, 2026))},
        },
    ),
]


def _make_job_fn(payload: dict):
    def _job():
        logger.info("Scheduler triggering job: %s", payload)
        result = run_job(payload)
        if not result.get("ok"):
            logger.error("Scheduled job failed: %s", result)

    return _job


def build_scheduler() -> BlockingScheduler:
    scheduler = BlockingScheduler(timezone="UTC")
    for job_id, trigger, payload in SCHEDULE:
        scheduler.add_job(
            _make_job_fn(payload),
            trigger=trigger,
            id=job_id,
            name=job_id,
            replace_existing=True,
            max_instances=1,  # never let a slow run overlap with the next tick
            misfire_grace_time=3600,
        )
        logger.info("Registered job '%s' (trigger=%s)", job_id, trigger)
    return scheduler


def main():
    scheduler = build_scheduler()
    logger.info("Scheduler starting with %d job(s). Ctrl+C to stop.", len(SCHEDULE))
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
