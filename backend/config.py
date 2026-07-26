#!/usr/bin/env python3
"""
IndiaPulse - Configuration Loader

Loads config.yaml once and exposes convenient paths/settings to the
rest of the backend.
"""

from pathlib import Path
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"


def _load_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"config.yaml not found at {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


CONFIG = _load_config()

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

UNIVERSE_DIR = PROJECT_ROOT / CONFIG["paths"]["universe_dir"]
HISTORICAL_DIR = PROJECT_ROOT / CONFIG["paths"]["historical_dir"]
JSON_DIR = PROJECT_ROOT / CONFIG["paths"]["json_dir"]
LOG_DIR = PROJECT_ROOT / CONFIG["paths"]["log_dir"]

for _dir in (UNIVERSE_DIR, HISTORICAL_DIR, JSON_DIR, LOG_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------
# Download settings
# ---------------------------------------------------------------------

DOWNLOAD = CONFIG["download"]
DEFAULT_PERIOD = DOWNLOAD["default_period"]
DEFAULT_INTERVAL = DOWNLOAD["default_interval"]
MAX_RETRIES = DOWNLOAD["max_retries"]
RETRY_BACKOFF = DOWNLOAD["retry_backoff_seconds"]
REQUEST_TIMEOUT = DOWNLOAD["request_timeout"]
RATE_LIMIT_SLEEP = DOWNLOAD["rate_limit_sleep"]

# ---------------------------------------------------------------------
# Indicators / Scoring
# ---------------------------------------------------------------------

INDICATORS = CONFIG["indicators"]
OPPORTUNITY_WEIGHTS = CONFIG["opportunity_weights"]
SEASONALITY = CONFIG["seasonality"]
LOGGING = CONFIG["logging"]
