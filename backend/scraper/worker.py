"""
worker.py
=========
Executes scraper jobs one at a time. Deliberately queue-agnostic: `run_job()`
takes a plain dict, so this same function can be driven by
    - the CLI (`python -m scrapers.worker '{"scraper": "jiji", ...}'`)
    - scrapers/scheduler.py (in-process APScheduler jobs)
    - a real task queue later (Celery/RQ/Supabase Edge Function trigger) by
      just calling `run_job(payload)` from that queue's task handler.

Job payload shape:
    {
        "scraper": "autochek" | "jiji" | "carapi",
        "max_listings": 200,             # ignored by carapi
        "kwargs": { ... constructor args for the scraper class ... }
    }

Examples:
    {"scraper": "autochek", "max_listings": 100, "kwargs": {"country": "ke"}}
    {"scraper": "jiji", "max_listings": 150, "kwargs": {"category_path": "/cars/toyota"}}
    {"scraper": "carapi", "kwargs": {"years": [2022, 2023], "makes": ["Toyota", "Mazda"]}}
"""

from __future__ import annotations

import json
import sys
import traceback
from typing import Any

from scrapers.autochek_scraper import AutochekScraper
from scrapers.jiji_scraper import JijiScraper
from scrapers.carapi_scraper import CarApiScraper
from services.scraper_logger import get_logger

logger = get_logger(__name__)

SCRAPER_REGISTRY = {
    "autochek": AutochekScraper,
    "jiji": JijiScraper,
    "carapi": CarApiScraper,
}


def run_job(payload: dict[str, Any]) -> dict:
    """Instantiate the right scraper for `payload` and execute it.
    Never raises - failures are caught, logged, and returned as part of the result
    dict so a queue worker loop can keep processing subsequent jobs."""
    scraper_name = payload.get("scraper")
    scraper_cls = SCRAPER_REGISTRY.get(scraper_name)
    if scraper_cls is None:
        msg = f"Unknown scraper '{scraper_name}'. Known: {list(SCRAPER_REGISTRY)}"
        logger.error(msg)
        return {"ok": False, "error": msg}

    kwargs = payload.get("kwargs", {})
    max_listings = payload.get("max_listings", 100)

    try:
        scraper = scraper_cls(**kwargs)
        if scraper_name == "carapi":
            summary = scraper.sync_reference_data()
        else:
            summary = scraper.run(max_listings=max_listings)
        logger.info("Job finished (%s): %s", scraper_name, summary)
        return {"ok": True, "scraper": scraper_name, "summary": summary}
    except Exception as exc:  # noqa: BLE001 - worker must never crash the process
        logger.error("Job crashed (%s): %s\n%s", scraper_name, exc, traceback.format_exc())
        return {"ok": False, "scraper": scraper_name, "error": str(exc)}


def process_jobs(jobs: list[dict]) -> list[dict]:
    """Run a batch of jobs sequentially, returning each result. Sequential (not
    concurrent) on purpose - these scrapers already rate-limit themselves per
    target site, and running two jobs against the *same* site concurrently would
    defeat that. Different-site jobs are cheap enough sequentially for typical
    batch sizes; swap to a ThreadPoolExecutor keyed by `scraper` name if you need
    true parallelism across sites."""
    results = []
    for job in jobs:
        results.append(run_job(job))
    return results


if __name__ == "__main__":
    # CLI usage: python -m scrapers.worker '{"scraper": "jiji", "max_listings": 20, "kwargs": {}}'
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    job_payload = json.loads(sys.argv[1])
    result = run_job(job_payload)
    print(json.dumps(result, indent=2, default=str))
