"""Tests for RE:Track upgrade safety, backup generation, and schema compatibility."""

import json
from pathlib import Path
import pytest

from app import __version__
from app.services.bootstrap_service import BootstrapService
from app.services.maintenance_service import MaintenanceService


def test_upgrade_preserves_custom_settings_and_fields(tmp_path: Path):
    """Test that upgrading from older settings preserves all user customization."""
    retrack_dir = tmp_path / ".retrack"
    retrack_dir.mkdir(parents=True)

    old_settings = {
        "version": "0.0.9",
        "ollama": {
            "host": "custom-host",
            "port": 11435,
            "llm_model": "custom-llm",
            "embedding_model": "custom-embed",
        },
        "custom_plugin_field": {"enabled": True, "token": "secret123"},
    }
    settings_file = retrack_dir / "settings.json"
    settings_file.write_text(json.dumps(old_settings))

    # Run bootstrap (as happens on upgrade)
    service = BootstrapService(retrack_dir=retrack_dir)
    result = service.initialize(check_provider=False)

    assert result.success is True
    assert str(settings_file) in result.preserved_files

    # Verify custom fields were not overwritten
    reloaded = json.loads(settings_file.read_text())
    assert reloaded["ollama"]["host"] == "custom-host"
    assert reloaded["ollama"]["port"] == 11435
    assert reloaded["custom_plugin_field"]["token"] == "secret123"


def test_automatic_backup_creation_and_integrity(tmp_path: Path):
    """Test that maintenance service creates complete and accessible backups."""
    retrack_dir = tmp_path / ".retrack"
    retrack_dir.mkdir(parents=True)

    (retrack_dir / "settings.json").write_text('{"v": 1}')
    (retrack_dir / "indexed_repos.json").write_text('[{"repo": "test"}]')

    service = MaintenanceService(retrack_dir=retrack_dir)
    backup_path = service.create_backup(prefix="test_backup")

    assert backup_path.exists()
    assert (backup_path / "settings.json").exists()
    assert (backup_path / "indexed_repos.json").exists()
    assert (backup_path / "settings.json").read_text() == '{"v": 1}'
