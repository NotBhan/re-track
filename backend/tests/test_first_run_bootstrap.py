"""Tests for RE:Track first-run bootstrap and environment initialization."""

import json
from pathlib import Path
import pytest

from app import __version__
from app.services.bootstrap_service import BootstrapService, BootstrapResult


def test_bootstrap_fresh_initialization(tmp_path: Path):
    """Test first-run initialization creates required directories and files."""
    retrack_dir = tmp_path / ".retrack"
    legacy_dir = tmp_path / ".andes"

    service = BootstrapService(retrack_dir=retrack_dir, legacy_dir=legacy_dir)
    result = service.initialize(check_provider=False)

    assert result.success is True
    assert result.version == __version__
    assert retrack_dir.exists()
    assert (retrack_dir / "manifests").exists()
    assert (retrack_dir / "cache").exists()
    assert (retrack_dir / "backups").exists()
    assert (retrack_dir / "settings.json").exists()
    assert (retrack_dir / "indexed_repos.json").exists()
    assert (retrack_dir / "context_packages.json").exists()

    settings_data = json.loads((retrack_dir / "settings.json").read_text())
    assert settings_data["version"] == __version__
    assert settings_data["ollama"]["host"] == "localhost"

    repos_data = json.loads((retrack_dir / "indexed_repos.json").read_text())
    assert isinstance(repos_data, list)

    packages_data = json.loads((retrack_dir / "context_packages.json").read_text())
    assert isinstance(packages_data, dict)


def test_bootstrap_idempotent(tmp_path: Path):
    """Test that running initialization repeatedly is non-destructive and idempotent."""
    retrack_dir = tmp_path / ".retrack"
    service = BootstrapService(retrack_dir=retrack_dir)

    res1 = service.initialize(check_provider=False)
    assert len(res1.created_files) >= 3

    # Add custom setting
    settings_file = retrack_dir / "settings.json"
    settings_data = json.loads(settings_file.read_text())
    settings_data["custom_field"] = "custom_value"
    settings_file.write_text(json.dumps(settings_data))

    # Second initialization
    res2 = service.initialize(check_provider=False)
    assert res2.success is True
    assert len(res2.created_files) == 0
    assert str(settings_file) in res2.preserved_files

    # Custom setting should be preserved
    reloaded = json.loads(settings_file.read_text())
    assert reloaded["custom_field"] == "custom_value"


def test_bootstrap_legacy_detection(tmp_path: Path):
    """Test detection of legacy ~/.andes data during bootstrap."""
    retrack_dir = tmp_path / ".retrack"
    legacy_dir = tmp_path / ".andes"
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "repositories.json").write_text('[{"name": "legacy_repo"}]')

    service = BootstrapService(retrack_dir=retrack_dir, legacy_dir=legacy_dir)
    result = service.initialize(check_provider=False)

    assert result.success is True
    assert result.legacy_data_detected is True
    assert result.legacy_item_count == 1
    assert "retrack migrate" in result.message
