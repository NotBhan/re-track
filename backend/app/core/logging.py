import logging
import sys
from typing import Any, Optional


def setup_logging(level: int = logging.INFO, stream: Optional[Any] = None) -> None:
    """Configure structured logging for the application.

    Directs all application logs to stderr to preserve stdout for MCP JSON-RPC framing.

    Args:
        level: Minimum log level (default: INFO).
        stream: Stream target for logs (default: sys.stderr).
    """
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    target_stream = stream or sys.stderr
    handler = logging.StreamHandler(target_stream)
    handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

    # Quiet noisy third-party loggers
    for name in ("httpx", "httpcore", "litellm", "instructor"):
        logging.getLogger(name).setLevel(logging.WARNING)
