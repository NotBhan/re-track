"""Phase 9C — Track 1: Structured Persistent Logging Tests.

Verifies JSONL structured log formatting, field consistency, secret redaction,
stderr console isolation (MCP stdio safety), and log reading capabilities.
"""

import json
import logging
from pathlib import Path
import sys
import tempfile
import pytest

from app.core.logging import (
    StructuredJsonFormatter,
    log_event,
    read_recent_logs,
    sanitize_log_message,
    setup_logging,
)


def test_structured_json_formatter_basic_fields():
    """Verify that StructuredJsonFormatter emits standard ISO8601 JSON fields."""
    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=25,
        msg="Sample log message for testing",
        args=(),
        exc_info=None,
    )

    formatted = formatter.format(record)
    data = json.loads(formatted)

    assert data["level"] == "INFO"
    assert data["logger"] == "test_logger"
    assert data["message"] == "Sample log message for testing"
    assert "timestamp" in data
    assert "process_id" in data
    assert "thread_name" in data


def test_structured_json_formatter_custom_fields():
    """Verify that structured event fields (component, operation, duration_ms, error_class) are included."""
    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="app.context",
        level=logging.INFO,
        pathname=__file__,
        lineno=40,
        msg="Synthesized context package",
        args=(),
        exc_info=None,
    )
    record.structured_fields = {
        "event": "context_synthesized",
        "component": "context_engine",
        "operation": "get_agent_context",
        "duration_ms": 42.5,
        "token_estimate": 1250,
    }

    formatted = formatter.format(record)
    data = json.loads(formatted)

    assert data["event"] == "context_synthesized"
    assert data["component"] == "context_engine"
    assert data["operation"] == "get_agent_context"
    assert data["duration_ms"] == 42.5
    assert data["token_estimate"] == 1250


def test_structured_logging_secret_redaction():
    """Verify that API keys, bearer tokens, and passwords in messages or fields are redacted."""
    formatter = StructuredJsonFormatter()

    # Secret in message
    record1 = logging.LogRecord(
        name="app.provider",
        level=logging.WARNING,
        pathname=__file__,
        lineno=60,
        msg="Provider auth failed with api_key=sk-1234567890abcdef1234567890 and Bearer eyJhbGciOiJIUzI1NiJ9",
        args=(),
        exc_info=None,
    )
    data1 = json.loads(formatter.format(record1))
    assert "sk-1234567890abcdef1234567890" not in data1["message"]
    assert "[REDACTED]" in data1["message"]

    # Secret in structured fields
    record2 = logging.LogRecord(
        name="app.api",
        level=logging.INFO,
        pathname=__file__,
        lineno=75,
        msg="API call",
        args=(),
        exc_info=None,
    )
    record2.structured_fields = {
        "auth_header": "Bearer secret_token_xyz_123456",
        "database_url": "postgres://admin:super_secret_password@localhost:5432/retrack",
    }
    data2 = json.loads(formatter.format(record2))
    assert "secret_token_xyz_123456" not in str(data2)
    assert "super_secret_password" not in str(data2)


def test_structured_logging_exception_capture():
    """Verify that exception details and error class are captured and formatted cleanly."""
    formatter = StructuredJsonFormatter()
    try:
        raise ValueError("Invalid workspace parameter: sensitive_token=abc1234567")
    except ValueError:
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="app.use_cases",
        level=logging.ERROR,
        pathname=__file__,
        lineno=95,
        msg="Operation failed",
        args=(),
        exc_info=exc_info,
    )
    data = json.loads(formatter.format(record))

    assert data["level"] == "ERROR"
    assert data["error_class"] == "ValueError"
    assert "exception" in data
    assert "abc1234567" not in data["exception"]


def test_setup_logging_mcp_stdout_cleanliness(capsys):
    """Verify that setup_logging routes human-readable logs to stderr, leaving stdout untouched."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_logging(
            level=logging.INFO,
            stream=sys.stderr,
            log_dir=tmpdir,
            enable_file_logging=True,
            enable_stderr_logging=True,
        )

        test_logger = logging.getLogger("test_stdio_cleanliness")
        test_logger.info("This is a diagnostic message for MCP")

        captured = capsys.readouterr()
        # Stdout MUST be completely empty (100% clean for JSON-RPC)
        assert captured.out == "", "Stdout was polluted by logging subsystem!"
        # Stderr MUST contain the log line
        assert "This is a diagnostic message for MCP" in captured.err


def test_read_recent_logs():
    """Verify that read_recent_logs correctly parses JSONL files and tolerates corrupted lines."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "app.jsonl"
        lines = [
            json.dumps({"timestamp": "2026-08-22T10:00:00Z", "level": "INFO", "message": "Log 1"}),
            "THIS_IS_CORRUPTED_NON_JSON_LINE",
            json.dumps({"timestamp": "2026-08-22T10:01:00Z", "level": "WARNING", "message": "Log 2"}),
            "",
            json.dumps({"timestamp": "2026-08-22T10:02:00Z", "level": "ERROR", "message": "Log 3"}),
        ]
        log_file.write_text("\n".join(lines), encoding="utf-8")

        entries = read_recent_logs(max_entries=10, log_dir=tmpdir, log_file_name="app.jsonl")
        assert len(entries) == 3
        assert entries[0]["message"] == "Log 1"
        assert entries[1]["message"] == "Log 2"
        assert entries[2]["message"] == "Log 3"
