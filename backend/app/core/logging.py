"""Structured logging subsystem for RE:Track.

Directs human-readable logs to stderr to preserve stdout for FastMCP JSON-RPC communication,
and simultaneously writes structured JSONL records to canonical persistent storage (~/.retrack/logs/app.jsonl)
with safe file rotation, retention limits, and automatic secret redaction.
"""

from datetime import datetime, timezone
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import re
import sys
import threading
from typing import Any, Optional

# Secret redaction patterns
_SENSITIVE_PATTERNS = [
    # 1. Quoted secret values: key='secret' or key="secret" or key: 'secret'
    re.compile(
        r"(?i)\b([a-zA-Z0-9_-]*(?:api[_-]?key|token|password|secret|auth|session[_-]?id))\b\s*[:=]\s*(['\"][^'\"]*['\"])"
    ),
    # 2. Unquoted secret values: key=secret_val or key: secret_val
    re.compile(
        r"(?i)\b([a-zA-Z0-9_-]*(?:api[_-]?key|token|password|secret|auth|session[_-]?id))\b\s*[:=]\s*([^\s'\",;]{6,})"
    ),
    # Bearer tokens (with space)
    re.compile(r"(?i)\b(bearer)\s+(?:'[^']*'|\"[^\"]*\"|[a-zA-Z0-9_\-\.]{10,})"),
    # API key patterns (OpenAI sk-..., Anthropic sk-ant-..., etc.)
    re.compile(r"\bsk-[a-zA-Z0-9_\-]{15,}"),
    # GitHub / Personal tokens
    re.compile(r"\b(ghp|gho|ghu|ghs|ghr)_[a-zA-Z0-9]{20,}"),
    # Database and HTTP connection strings with credentials: postgres://user:pass@host or http://user:pass@host
    re.compile(r"(?i)\b(postgres|postgresql|mysql|sqlite|mongodb|redis|http|https)://([^:]+):([^@]+)@"),
]


def sanitize_log_message(msg: str) -> str:
    """Redact sensitive patterns (API keys, tokens, passwords) from a log string."""
    if not isinstance(msg, str):
        return str(msg)

    sanitized = msg
    for pat in _SENSITIVE_PATTERNS:
        if "postgres|postgresql" in pat.pattern or "http|https" in pat.pattern:
            sanitized = pat.sub(r"\1://\2:[REDACTED]@", sanitized)
        elif pat.pattern.startswith("(?i)\\b(bearer)"):
            sanitized = pat.sub(r"\1 [REDACTED]", sanitized)
        elif pat.groups >= 1:
            sanitized = pat.sub(r"\1=[REDACTED]", sanitized)
        else:
            sanitized = pat.sub("[REDACTED]", sanitized)
    return sanitized


class StructuredJsonFormatter(logging.Formatter):
    """Formats LogRecord objects into sanitized, single-line JSON records."""

    def format(self, record: logging.LogRecord) -> str:
        # Extract basic fields
        created_dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        raw_msg = record.getMessage()
        sanitized_msg = sanitize_log_message(raw_msg)

        log_data: dict[str, Any] = {
            "timestamp": created_dt.isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": sanitized_msg,
            "process_id": os.getpid(),
            "thread_name": threading.current_thread().name,
        }

        # Include structured extra fields if provided
        structured_fields = getattr(record, "structured_fields", None)
        if isinstance(structured_fields, dict):
            for k, v in structured_fields.items():
                if k not in log_data:
                    # Sanitize any string values
                    if isinstance(v, str):
                        log_data[k] = sanitize_log_message(v)
                    elif isinstance(v, (int, float, bool)) or v is None:
                        log_data[k] = v
                    elif isinstance(v, dict):
                        log_data[k] = {
                            dk: sanitize_log_message(str(dv)) if isinstance(dv, str) else dv
                            for dk, dv in v.items()
                        }
                    else:
                        log_data[k] = str(v)

        # Include exception details if present
        if record.exc_info and record.exc_info[0]:
            exc_type = record.exc_info[0]
            log_data["error_class"] = exc_type.__name__
            if record.exc_text:
                log_data["exception"] = sanitize_log_message(record.exc_text)
            elif record.exc_info[1]:
                log_data["exception"] = sanitize_log_message(str(record.exc_info[1]))

        return json.dumps(log_data)


class SafeRotatingFileHandler(RotatingFileHandler):
    """RotatingFileHandler that fails gracefully without crashing RE:Track if filesystem errors occur."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            super().emit(record)
        except (OSError, PermissionError) as e:
            # Degrade gracefully to stderr warning without crashing
            try:
                sys.stderr.write(f"[RE:Track Log Handler Warning] Failed to write log file: {e}\n")
            except Exception:
                pass
        except Exception:
            self.handleError(record)


def setup_logging(
    level: int = logging.INFO,
    stream: Optional[Any] = None,
    log_dir: Optional[Path | str] = None,
    log_file_name: str = "app.jsonl",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB default
    backup_count: int = 5,
    enable_file_logging: bool = True,
    enable_stderr_logging: bool = True,
) -> None:
    """Configure structured logging for RE:Track.

    Directs human-readable logs to stderr to preserve stdout for FastMCP JSON-RPC protocol,
    and optionally writes structured JSONL logs with rotation to log_dir.

    Args:
        level: Minimum log severity level (default: logging.INFO).
        stream: Stream target for console logs (default: sys.stderr).
        log_dir: Directory for structured persistent log files (default: ~/.retrack/logs/).
        log_file_name: Filename for structured log stream (default: 'app.jsonl').
        max_bytes: Maximum size in bytes before rotating log file (default: 10MB).
        backup_count: Number of rotated backup files to retain (default: 5).
        enable_file_logging: Whether to enable persistent file logging (default: True).
        enable_stderr_logging: Whether to enable human-readable console logging (default: True).
    """
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    # 1. Console / Stderr handler (Human-Readable)
    if enable_stderr_logging:
        target_stream = stream or sys.stderr
        console_fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        console_datefmt = "%Y-%m-%d %H:%M:%S"

        console_handler = logging.StreamHandler(target_stream)
        console_handler.setFormatter(logging.Formatter(console_fmt, datefmt=console_datefmt))
        console_handler.setLevel(level)
        root.addHandler(console_handler)

    # 2. Structured Persistent File Handler (JSONL with rotation)
    if enable_file_logging:
        target_dir = Path(log_dir) if log_dir is not None else Path.home() / ".retrack" / "logs"
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            log_path = target_dir / log_file_name

            file_handler = SafeRotatingFileHandler(
                filename=str(log_path),
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
                delay=True,
            )
            file_handler.setFormatter(StructuredJsonFormatter())
            file_handler.setLevel(level)
            root.addHandler(file_handler)
        except Exception as e:
            if stream or enable_stderr_logging:
                sys.stderr.write(f"[RE:Track Logging Warning] Could not initialize file logging at {target_dir}: {e}\n")

    # Quiet noisy third-party loggers
    for name in ("httpx", "httpcore", "litellm", "instructor", "urllib3"):
        logging.getLogger(name).setLevel(logging.WARNING)


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    component: Optional[str] = None,
    operation: Optional[str] = None,
    duration_ms: Optional[float] = None,
    error_class: Optional[str] = None,
    request_id: Optional[str] = None,
    **extra_fields: Any,
) -> None:
    """Emit a structured event log entry with standard fields.

    Args:
        logger: Target logger instance.
        level: Log severity level (e.g. logging.INFO).
        event: Short event name or human-readable description.
        component: High-level system component (e.g. 'mcp', 'context_engine', 'ast', 'storage').
        operation: Specific operation (e.g. 'get_agent_context', 'scan_repository').
        duration_ms: Elapsed execution time in milliseconds if applicable.
        error_class: Exception class name if logging an error.
        request_id: Optional request / task correlation ID.
        **extra_fields: Additional contextual fields to include in JSON record.
    """
    fields: dict[str, Any] = {
        "event": event,
    }
    if component is not None:
        fields["component"] = component
    if operation is not None:
        fields["operation"] = operation
    if duration_ms is not None:
        fields["duration_ms"] = round(duration_ms, 2)
    if error_class is not None:
        fields["error_class"] = error_class
    if request_id is not None:
        fields["request_id"] = request_id

    fields.update(extra_fields)

    logger.log(level, event, extra={"structured_fields": fields})


def read_recent_logs(
    max_entries: int = 100,
    log_dir: Optional[Path | str] = None,
    log_file_name: str = "app.jsonl",
) -> list[dict[str, Any]]:
    """Read recent structured log records from the persistent log file.

    Args:
        max_entries: Maximum number of recent log entries to return.
        log_dir: Log directory (defaults to ~/.retrack/logs/).
        log_file_name: Log filename (defaults to 'app.jsonl').

    Returns:
        List of parsed JSON log record dictionaries in chronological order.
    """
    target_dir = Path(log_dir) if log_dir is not None else Path.home() / ".retrack" / "logs"
    log_path = target_dir / log_file_name

    if not log_path.exists() or not log_path.is_file():
        return []

    entries: list[dict[str, Any]] = []
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        # Take the last max_entries lines
        recent_lines = lines[-max_entries:] if len(lines) > max_entries else lines
        for line in recent_lines:
            line_str = line.strip()
            if not line_str:
                continue
            try:
                parsed = json.loads(line_str)
                if isinstance(parsed, dict):
                    entries.append(parsed)
            except Exception:
                # Skip corrupted or unparseable lines gracefully
                continue
    except Exception:
        return []

    return entries
