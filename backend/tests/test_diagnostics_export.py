"""Phase 9C — Track 3: Diagnostics Bundle & Export Tests.

Verifies diagnostic report generation, atomic file bundle export, CLI commands,
and inclusion of operational health, configuration, and recent logs.
"""

import json
from pathlib import Path
import tempfile
import pytest
from typer.testing import CliRunner

from app.cli.main import app
from app.config.settings import Settings
from app.services.diagnostics_service import DiagnosticsService

runner = CliRunner()


def test_generate_diagnostics_structure():
    """Verify that DiagnosticsService produces a complete sanitized dictionary."""
    with tempfile.TemporaryDirectory() as tmpdir:
        settings = Settings()
        settings.logging.log_dir = Path(tmpdir) / "logs"

        service = DiagnosticsService(settings=settings)
        report = service.generate_diagnostics(
            include_logs=True,
            include_config=True,
            include_health=True,
        )

        assert "metadata" in report
        assert report["metadata"]["product"] == "RE:Track"
        assert "version" in report["metadata"]
        assert "python_version" in report["metadata"]
        assert "platform" in report["metadata"]

        assert "configuration" in report
        assert "storage" in report["configuration"]
        assert "ollama" in report["configuration"]
        assert "logging" in report["configuration"]

        assert "health" in report
        assert "overall_status" in report["health"]
        assert "provider" in report["health"]
        assert "storage" in report["health"]
        assert "workspaces" in report["health"]
        assert "concurrency" in report["health"]
        assert "mcp_runtime" in report["health"]

        assert "recent_logs" in report
        assert isinstance(report["recent_logs"], list)


def test_export_diagnostic_bundle_file():
    """Verify that export_bundle atomically creates a valid JSON file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        settings = Settings()
        settings.logging.log_dir = Path(tmpdir) / "logs"
        out_file = Path(tmpdir) / "diag_export.json"

        service = DiagnosticsService(settings=settings)
        exported_path = service.export_bundle(output_path=out_file)

        assert exported_path == out_file
        assert out_file.exists()

        content = json.loads(out_file.read_text(encoding="utf-8"))
        assert content["metadata"]["product"] == "RE:Track"
        assert "health" in content


def test_cli_diagnostics_command(monkeypatch):
    """Verify that `retrack diagnostics` CLI command runs successfully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("HOME", tmpdir)
        target_out = Path(tmpdir) / "cli_diag.json"

        res = runner.invoke(app, ["diagnostics", "--output", str(target_out), "--no-include-logs"])
        assert res.exit_code == 0
        assert "Diagnostic bundle successfully exported" in res.stdout
        assert target_out.exists()

        data = json.loads(target_out.read_text(encoding="utf-8"))
        assert data["metadata"]["product"] == "RE:Track"


def test_cli_diagnostics_json_stdout(monkeypatch):
    """Verify that `retrack diagnostics --json` outputs valid raw JSON to stdout."""
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("HOME", tmpdir)

        res = runner.invoke(app, ["diagnostics", "--json", "--no-include-logs"])
        assert res.exit_code == 0

        # Output should be valid JSON
        data = json.loads(res.stdout)
        assert data["metadata"]["product"] == "RE:Track"
        assert "configuration" in data
