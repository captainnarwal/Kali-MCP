"""Console + rotating file logging for the Kali MCP client."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(
    *,
    log_dir: Path,
    level: str = "INFO",
    max_bytes: int = 5_000_000,
    backup_count: int = 5,
    logger_name: str = "kali_mcp_client",
) -> logging.Logger:
    """Configure root logging with stderr and a rotating log file."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "client.log"

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    logger = logging.getLogger(logger_name)
    logger.info("Logging to %s (max %s bytes, %s backups)", log_file, max_bytes, backup_count)
    return logger
