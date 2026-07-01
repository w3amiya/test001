from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path

from .config import HelperConfig, expand_path


def setup_logger(config: HelperConfig) -> logging.Logger:
    log_dir_override = os.environ.get("TABLEAU_WPS_HELPER_LOG_DIR", "").strip()
    log_dir = expand_path(log_dir_override or config.default_log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"tableau_plugin_{datetime.now():%Y%m%d}.log"

    logger = logging.getLogger("tableau_wps_helper")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def log_path_for(config: HelperConfig) -> Path:
    return expand_path(config.default_log_dir) / f"tableau_plugin_{datetime.now():%Y%m%d}.log"
