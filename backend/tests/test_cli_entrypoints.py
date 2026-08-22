"""Tests for RE:Track CLI commands and entrypoint consistency."""

import json
from pathlib import Path
import pytest
from typer.testing import CliRunner

from app import __version__
from app.cli.main import app


@pytest.fixture
def runner():
    return CliRunner()


def test_cli_version_flag(runner: CliRunner):
    """Test retrack --version outputs correct version string."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"RE:Track v{__version__}" in result.stdout


def test_cli_init_command(runner: CliRunner, tmp_path: Path, monkeypatch):
    """Test retrack init command initializes storage structure."""
    fake_home = tmp_path / "user_home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))

    result = runner.invoke(app, ["init", "--no-check-provider"])
    assert result.exit_code == 0
    assert "RE:Track Initialization" in result.stdout
    assert (fake_home / ".retrack").exists()
    assert (fake_home / ".retrack" / "settings.json").exists()


def test_cli_reset_command_cache(runner: CliRunner, tmp_path: Path, monkeypatch):
    """Test retrack reset --cache clears cache successfully."""
    fake_home = tmp_path / "user_home"
    cache_dir = fake_home / ".retrack" / "cache"
    cache_dir.mkdir(parents=True)
    (cache_dir / "test.cache").write_text("data")
    monkeypatch.setenv("HOME", str(fake_home))

    result = runner.invoke(app, ["reset", "--cache"])
    assert result.exit_code == 0
    assert "Cache cleared successfully" in result.stdout
    assert not (cache_dir / "test.cache").exists()


def test_cli_reset_command_state_aborted_without_confirm(runner: CliRunner, tmp_path: Path, monkeypatch):
    """Test retrack reset --state aborts if user declines prompt."""
    fake_home = tmp_path / "user_home"
    (fake_home / ".retrack").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(fake_home))

    # Respond 'n' to interactive prompt
    result = runner.invoke(app, ["reset", "--state"], input="n\n")
    assert result.exit_code == 0
    assert "Operation aborted" in result.stdout


def test_cli_reset_command_state_confirmed(runner: CliRunner, tmp_path: Path, monkeypatch):
    """Test retrack reset --state --confirm resets state without prompt."""
    fake_home = tmp_path / "user_home"
    retrack_dir = fake_home / ".retrack"
    retrack_dir.mkdir(parents=True)
    (retrack_dir / "indexed_repos.json").write_text('[{"repo": "test"}]')
    monkeypatch.setenv("HOME", str(fake_home))

    result = runner.invoke(app, ["reset", "--state", "--confirm"])
    assert result.exit_code == 0
    assert "Application state reset complete" in result.stdout
    assert json.loads((retrack_dir / "indexed_repos.json").read_text()) == []


def test_cli_migrate_dry_run(runner: CliRunner, tmp_path: Path, monkeypatch):
    """Test retrack migrate --dry-run prints items without copying."""
    fake_home = tmp_path / "user_home"
    legacy_dir = fake_home / ".andes"
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "repositories.json").write_text('[{"repo": "legacy"}]')
    monkeypatch.setenv("HOME", str(fake_home))

    result = runner.invoke(app, ["migrate", "--dry-run"])
    assert result.exit_code == 0
    assert "Migration Dry Run" in result.stdout
    assert not (fake_home / ".retrack").exists()
