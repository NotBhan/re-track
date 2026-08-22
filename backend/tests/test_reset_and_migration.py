"""Tests for RE:Track state reset and legacy ~/.andes data migration."""

import json
from pathlib import Path
import pytest

from app.services.maintenance_service import (
    MaintenanceService,
    ResetScope,
    ResetResult,
    MigrationResult,
)


def test_reset_cache_only(tmp_path: Path):
    """Test that cache reset only deletes cache files and preserves data/settings."""
    retrack_dir = tmp_path / ".retrack"
    cache_dir = retrack_dir / "cache"
    cache_dir.mkdir(parents=True)
    (cache_dir / "ast_hash_123.json").write_text('{"hash": "123"}')

    settings_file = retrack_dir / "settings.json"
    settings_file.write_text('{"key": "value"}')

    repos_file = retrack_dir / "repositories.json"
    repos_file.write_text('[{"name": "test_repo"}]')

    service = MaintenanceService(retrack_dir=retrack_dir)
    result = service.reset_data(scope=ResetScope.CACHE, confirm=False)

    assert result.success is True
    assert not (cache_dir / "ast_hash_123.json").exists()
    assert settings_file.exists()
    assert repos_file.exists()
    assert json.loads(repos_file.read_text()) == [{"name": "test_repo"}]


def test_reset_state_requires_confirmation(tmp_path: Path):
    """Test that state reset raises ValueError if confirm=False."""
    retrack_dir = tmp_path / ".retrack"
    service = MaintenanceService(retrack_dir=retrack_dir)

    with pytest.raises(ValueError, match="requires explicit confirmation"):
        service.reset_data(scope=ResetScope.STATE, confirm=False)


def test_reset_state_with_confirmation_and_backup(tmp_path: Path):
    """Test that state reset clears state, creates backup, and preserves user source files."""
    retrack_dir = tmp_path / ".retrack"
    retrack_dir.mkdir(parents=True)

    # Dummy source repo
    source_repo = tmp_path / "my_source_code"
    source_repo.mkdir()
    (source_repo / "main.py").write_text("print('hello world')")

    # Retrack state
    (retrack_dir / "indexed_repos.json").write_text(
        json.dumps([{"path": str(source_repo), "name": "my_source_code"}])
    )
    (retrack_dir / "context_packages.json").write_text('{"pkg1": {}}')
    manifests_dir = retrack_dir / "manifests"
    manifests_dir.mkdir()
    (manifests_dir / "manifest1.json").write_text('{"nodes": []}')

    service = MaintenanceService(retrack_dir=retrack_dir)
    result = service.reset_data(scope=ResetScope.STATE, confirm=True)

    assert result.success is True
    assert result.backup_path is not None
    assert Path(result.backup_path).exists()
    assert (Path(result.backup_path) / "indexed_repos.json").exists()

    # Retrack state is reset
    assert json.loads((retrack_dir / "indexed_repos.json").read_text()) == []
    assert json.loads((retrack_dir / "context_packages.json").read_text()) == {}
    assert len(list(manifests_dir.glob("*.json"))) == 0

    # User source repo is completely untouched!
    assert source_repo.exists()
    assert (source_repo / "main.py").read_text() == "print('hello world')"


def test_migration_dry_run(tmp_path: Path):
    """Test migration dry run previews items without writing to target."""
    retrack_dir = tmp_path / ".retrack"
    legacy_dir = tmp_path / ".andes"
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "repositories.json").write_text('[{"name": "legacy_repo"}]')
    (legacy_dir / "context_packages.json").write_text('{"legacy_pkg": {}}')

    service = MaintenanceService(retrack_dir=retrack_dir, legacy_dir=legacy_dir)
    result = service.migrate_legacy_data(dry_run=True)

    assert result.success is True
    assert result.dry_run is True
    assert len(result.items_migrated) == 2
    assert not retrack_dir.exists()


def test_migration_execution_preserves_legacy(tmp_path: Path):
    """Test migration copies records into canonical storage while preserving legacy files."""
    retrack_dir = tmp_path / ".retrack"
    retrack_dir.mkdir(parents=True)
    (retrack_dir / "repositories.json").write_text('[{"name": "canonical_repo"}]')

    legacy_dir = tmp_path / ".andes"
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "repositories.json").write_text('[{"name": "legacy_repo"}]')
    (legacy_dir / "context_packages.json").write_text('{"legacy_pkg": {"title": "Legacy"}}')

    service = MaintenanceService(retrack_dir=retrack_dir, legacy_dir=legacy_dir)
    result = service.migrate_legacy_data(dry_run=False)

    assert result.success is True
    assert result.dry_run is False
    assert result.backup_path is not None

    # Canonical repositories should now have both
    merged_repos = json.loads((retrack_dir / "repositories.json").read_text())
    names = {r["name"] for r in merged_repos}
    assert "canonical_repo" in names
    assert "legacy_repo" in names

    # Canonical packages should have legacy_pkg
    pkgs = json.loads((retrack_dir / "context_packages.json").read_text())
    assert "legacy_pkg" in pkgs

    # Legacy directory must remain untouched and read-only
    assert (legacy_dir / "repositories.json").read_text() == '[{"name": "legacy_repo"}]'
    assert (legacy_dir / "context_packages.json").read_text() == '{"legacy_pkg": {"title": "Legacy"}}'
