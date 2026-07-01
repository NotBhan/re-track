"""Tests for the AndesContext CLI layer.

Validates CLI commands delegate to API layer correctly.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from app.cli.main import app
from app.api.schemas import (
    BackendStatusResponse,
    ContextResponse,
    ErrorResponse,
    HealthResponse,
    IndexRepositoryResponse,
)

runner = CliRunner()


# --- health ---


class TestHealthCommand:
    def test_health_shows_ok(self):
        response = HealthResponse(
            status="ok",
            ollama_reachable=True,
            cognee_initialized=True,
            version="0.1.0",
        )
        with patch("app.cli.main._run", return_value=response):
            with patch("app.cli.main._init_backend"):
                result = runner.invoke(app, ["health"])
                assert result.exit_code == 0
                assert "ok" in result.output

    def test_health_shows_degraded(self):
        response = HealthResponse(
            status="degraded",
            ollama_reachable=False,
            cognee_initialized=True,
            version="0.1.0",
        )
        with patch("app.cli.main._run", return_value=response):
            with patch("app.cli.main._init_backend"):
                result = runner.invoke(app, ["health"])
                assert result.exit_code == 0
                assert "degraded" in result.output

    def test_health_handles_error(self):
        error = ErrorResponse(error="TestError", message="something broke")
        with patch("app.cli.main._run", return_value=error):
            with patch("app.cli.main._init_backend"):
                result = runner.invoke(app, ["health"])
                assert result.exit_code == 1
                assert "Error" in result.output


# --- status ---


class TestStatusCommand:
    def test_status_displays_config(self):
        response = BackendStatusResponse(
            status="ok",
            ollama_reachable=True,
            ollama_host="localhost",
            ollama_port=11434,
            llm_model="phi3:mini",
            embedding_model="nomic-embed-text:latest",
            vector_db="lancedb",
            graph_db="kuzu",
            relational_db="sqlite",
            data_root="/tmp/data",
            system_root="/tmp/system",
            cognee_initialized=True,
        )
        with patch("app.cli.main._run", return_value=response):
            with patch("app.cli.main._init_backend"):
                result = runner.invoke(app, ["status"])
                assert result.exit_code == 0
                assert "phi3:mini" in result.output
                assert "lancedb" in result.output


# --- index ---


class TestIndexCommand:
    def test_index_rejects_missing_path(self):
        result = runner.invoke(app, ["index", "/nonexistent/path", "-d", "test"])
        assert result.exit_code == 1
        assert "does not exist" in result.output

    def test_index_rejects_file_path(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("hello")
        result = runner.invoke(app, ["index", str(f), "-d", "test"])
        assert result.exit_code == 1
        assert "not a directory" in result.output

    def test_index_shows_results(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "test.py").write_text("print('hi')")

        response = IndexRepositoryResponse(
            success=True,
            repository_path=str(repo),
            dataset_name="my-project",
            total_files=1,
            processed_files=1,
            failed_files=0,
            total_batches=1,
            failed_paths=[],
            summary="Indexed 1/1 files",
        )
        with patch("app.cli.main._run", return_value=response):
            with patch("app.cli.main._init_backend"):
                result = runner.invoke(app, ["index", str(repo), "-d", "my-project"])
                assert result.exit_code == 0
                assert "my-project" in result.output
                assert "1" in result.output


# --- context ---


class TestContextCommand:
    def test_context_rejects_empty_query(self):
        with patch("app.cli.main._init_backend"):
            result = runner.invoke(app, ["context", "-q", "  ", "-d", "test"])
            assert result.exit_code == 1
            assert "empty" in result.output.lower()

    def test_context_renders_markdown(self):
        response = ContextResponse(
            success=True,
            task="How does auth work?",
            objective="Explain authentication mechanism",
            markdown="# Task\n\nAuth uses JWT tokens.",
            section_count=1,
            source_count=3,
            token_estimate=50,
            dataset="my-project",
        )
        with patch("app.cli.main._run", return_value=response):
            with patch("app.cli.main._init_backend"):
                result = runner.invoke(
                    app, ["context", "-q", "How does auth work?", "-d", "my-project"]
                )
                assert result.exit_code == 0
                assert "Auth uses JWT" in result.output
                assert "3" in result.output


# --- forget ---


class TestForgetCommand:
    def test_forget_requires_identifier(self):
        with patch("app.cli.main._init_backend"):
            result = runner.invoke(app, ["forget"])
            assert result.exit_code == 1
            assert "at least one" in result.output.lower()

    def test_forget_success(self):
        with patch("app.cli.main._run", return_value=None):
            with patch("app.cli.main._init_backend"):
                result = runner.invoke(app, ["forget", "-d", "old-data"])
                assert result.exit_code == 0
                assert "forgotten" in result.output.lower()

    def test_forget_handles_error(self):
        error = ErrorResponse(error="CogneeServiceError", message="forget failed")
        with patch("app.cli.main._run", return_value=error):
            with patch("app.cli.main._init_backend"):
                result = runner.invoke(app, ["forget", "-d", "bad-data"])
                assert result.exit_code == 1
                assert "Error" in result.output
