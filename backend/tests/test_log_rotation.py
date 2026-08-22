"""Phase 9C — Track 2: Safe Log Rotation & Retention Tests.

Verifies bounded persistent log file rotation, retention limits,
and safe non-fatal degradation if filesystem errors occur.
"""

import json
import logging
import os
from pathlib import Path
import stat
import tempfile
import pytest

from app.core.logging import (
    SafeRotatingFileHandler,
    StructuredJsonFormatter,
    setup_logging,
)


def test_log_rotation_triggers_on_size_limit():
    """Verify that SafeRotatingFileHandler rotates the log file once max_bytes is reached."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir)
        log_path = log_dir / "test_rotate.jsonl"

        # Max 500 bytes per file, up to 3 backup files
        handler = SafeRotatingFileHandler(
            filename=str(log_path),
            maxBytes=500,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(StructuredJsonFormatter())

        logger = logging.getLogger("test_rotation_logger")
        logger.setLevel(logging.INFO)
        logger.handlers.clear()
        logger.addHandler(handler)

        # Write enough log records to exceed 500 bytes multiple times
        for i in range(25):
            logger.info("Log rotation event message iteration number %d", i)

        handler.close()

        # Verify that rotated files exist
        assert log_path.exists(), "Primary log file must exist"
        backup1 = log_dir / "test_rotate.jsonl.1"
        assert backup1.exists(), "First backup log file must exist"


def test_log_retention_bounded_growth():
    """Verify that backup files never exceed backup_count."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir)
        log_path = log_dir / "test_bounded.jsonl"

        # Max 200 bytes, max 2 backups
        handler = SafeRotatingFileHandler(
            filename=str(log_path),
            maxBytes=200,
            backupCount=2,
            encoding="utf-8",
        )
        handler.setFormatter(StructuredJsonFormatter())

        logger = logging.getLogger("test_bounded_logger")
        logger.setLevel(logging.INFO)
        logger.handlers.clear()
        logger.addHandler(handler)

        # Write many lines
        for i in range(50):
            logger.info("Writing record %d with enough padding to trigger multiple rotations", i)

        handler.close()

        files = list(log_dir.glob("test_bounded.jsonl*"))
        # Should be at most test_bounded.jsonl, test_bounded.jsonl.1, test_bounded.jsonl.2 (<= 3 files total)
        assert len(files) <= 3, f"Expected at most 3 log files (1 active + 2 backups), found {len(files)}"
        assert not (log_dir / "test_bounded.jsonl.3").exists(), "Backup count exceeded!"


def test_unwritable_directory_fails_gracefully_without_crashing(monkeypatch):
    """Verify that logging setup and emission do not crash if the log directory is unwritable."""
    with tempfile.TemporaryDirectory() as tmpdir:
        unwritable_dir = Path(tmpdir) / "no_write"
        unwritable_dir.mkdir(parents=True, exist_ok=True)
        # Make directory read-only
        unwritable_dir.chmod(stat.S_IREAD | stat.S_IEXEC)

        try:
            # Should not raise exception
            setup_logging(
                level=logging.INFO,
                log_dir=unwritable_dir / "nested",
                enable_file_logging=True,
                enable_stderr_logging=False,
            )

            test_logger = logging.getLogger("test_unwritable_logger")
            test_logger.info("This should not raise an unhandled exception")
        finally:
            # Restore permissions for cleanup
            unwritable_dir.chmod(stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
