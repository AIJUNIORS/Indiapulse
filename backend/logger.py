#!/usr/bin/env python3
"""
IndiaPulse - Logger

Central logging configuration used across the backend.
"""

import logging
import sys

from backend.config import LOG_DIR, LOGGING


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        # Already configured (avoid duplicate handlers on repeated imports)
        return logger

    level = getattr(logging, LOGGING.get("level", "INFO").upper(), logging.INFO)
    logger.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    log_file = LOG_DIR / LOGGING.get("file", "docs/logs/indiapulse.log").split("/")[-1]
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger
