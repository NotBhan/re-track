"""Structured logging configuration for RE:Track (RefinedEngine Track) backend."""

import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """Configure structured logging for the application.

    Args:
        level: Minimum log level (default: INFO).
    """
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

    # Quiet noisy third-party loggers
    for name in ("httpx", "httpcore", "litellm", "instructor"):
        logging.getLogger(name).setLevel(logging.WARNING)
