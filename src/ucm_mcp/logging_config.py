"""Console and rotating-file logging with EST timestamps."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from zoneinfo import ZoneInfo

EST = ZoneInfo("America/New_York")


class EstFormatter(logging.Formatter):
    """Formatter that renders timestamps in America/New_York."""

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        from datetime import datetime

        dt = datetime.fromtimestamp(record.created, tz=EST)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime("%Y-%m-%d %H:%M:%S %Z")


def setup_logging(log_dir: str = "logs", level: str = "INFO") -> logging.Logger:
    """Configure root logger for console + rotating file (1 MB, 3 backups)."""
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_path = os.path.join(log_dir, "ucm-mcp.log")

    fmt = EstFormatter(
        fmt="%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(funcName)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S %Z",
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    logging.getLogger("zeep").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    logger = logging.getLogger("ucm_mcp")
    logger.info("Logging initialized (dir=%s, level=%s)", log_dir, level)
    return logger
