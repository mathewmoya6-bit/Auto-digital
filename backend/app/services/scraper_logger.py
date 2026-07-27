"""
services/scraper_logger.py
===========================
Shared logging setup for scrapers/worker.py and the individual scraper
classes (AutochekScraper, JijiScraper, CarApiScraper, etc).

Usage:
    from services.scraper_logger import get_logger
    logger = get_logger(__name__)
    logger.info("Job finished (%s): %s", scraper_name, summary)

Design notes:
- `get_logger(name)` is idempotent: calling it multiple times for the same
  (or different) module names never attaches duplicate handlers, which
  matters because worker.py, scheduler.py, and each scraper module all
  call it independently at import time.
- Logs go to stdout (console) always, since Render captures stdout/stderr
  as your service logs - no file handler by default so the process stays
  happy on Render's ephemeral filesystem. A rotating file handler is
  available behind an env var for local debugging.
- LOG_LEVEL is read from the environment (default INFO) so you can bump
  to DEBUG locally without touching code:
      LOG_LEVEL=DEBUG python -m scrapers.worker '{"scraper": "jiji", ...}'
- Format includes a timestamp, level, logger name (so you can tell which
  scraper emitted a line), and the message.
"""
from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

_CONFIGURED_LOGGERS: set[str] = set()

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _resolve_level() -> int:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    return getattr(logging, level_name, logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger for `name` (pass __name__ from the caller).

    Safe to call repeatedly - handlers are only attached once per logger
    name, so re-importing a module (or multiple modules calling this at
    import time) won't duplicate log lines.
    """
    logger = logging.getLogger(name)

    if name in _CONFIGURED_LOGGERS:
        return logger

    logger.setLevel(_resolve_level())
    logger.propagate = False  # don't double-log via the root logger

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # Console handler - always on. This is what Render (or any stdout-based
    # log collector) picks up.
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Optional rotating file handler for local debugging. Off by default
    # since Render's filesystem is ephemeral and this isn't useful there.
    log_file = os.getenv("SCRAPER_LOG_FILE")  # e.g. "logs/scrapers.log"
    if log_file:
        os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file, maxBytes=5 * 1024 * 1024, backupCount=3
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    _CONFIGURED_LOGGERS.add(name)
    return logger
