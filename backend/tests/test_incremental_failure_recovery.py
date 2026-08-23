"""Tests for Phase 10A Transactional Staging and Crash / Interruption Failure Recovery."""

import json
from pathlib import Path
import time
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.models.errors import CogneeServiceError
from app.services.indexing_service import IndexingService
from app.services.manifest_service import ManifestService


@pytest.fixture
def temp_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "test_repo"
    repo.mkdir()
    (repo / "file1.py").write_text("print('hello')", encoding="utf-8")
    (repo / "file2.py").write_text("print('world')", encoding="utf-8")
    return repo


@pytest.fixture
def mock_cognee() -> MagicMock:
    mock = MagicMock()
    mock.add = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def manifest_service(tmp_path: Path) -> ManifestService:
    storage = tmp_path / "manifests"
    return ManifestService(storage_dir=storage)


@pytest.mark.asyncio
async def test_recovery_from_interrupted_initial_indexing(
    temp_repo: Path, mock_cognee: MagicMock, manifest_service: ManifestService
):
    """If initial indexing is interrupted before manifest commit, next run completes cleanly."""
    service = IndexingService(cognee_service=mock_cognee, manifest_service=manifest_service)

    # Simulate failure during Cognee add
    mock_cognee.add.side_effect = CogneeServiceError("Connection lost midway through indexing")

    progress = await service.index_repository(temp_repo, "test_dataset")
    assert progress.failed_files > 0

    # Manifest must NOT have been saved with partial state
    manifest = manifest_service.load_manifest(temp_repo)
    assert manifest is None

    # Next run succeeds and commits manifest
    mock_cognee.add.side_effect = None
    progress2 = await service.index_repository(temp_repo, "test_dataset")
    assert progress2.failed_files == 0

    manifest2 = manifest_service.load_manifest(temp_repo)
    assert manifest2 is not None
    assert len(manifest2.files) == 2


@pytest.mark.asyncio
async def test_recovery_from_corrupted_manifest_file(
    temp_repo: Path, mock_cognee: MagicMock, manifest_service: ManifestService
):
    """If manifest JSON on disk is corrupted, next index triggers full rebuild and repairs state."""
    service = IndexingService(cognee_service=mock_cognee, manifest_service=manifest_service)

    # Initial successful index
    await service.index_repository(temp_repo, "test_dataset")
    manifest_file = manifest_service._get_manifest_path(temp_repo)
    assert manifest_file.exists()

    # Corrupt manifest file
    manifest_file.write_text("{ broken JSON: ...", encoding="utf-8")

    # Next run detects corruption, triggers full rebuild, and saves valid manifest
    progress = await service.index_repository(temp_repo, "test_dataset")
    assert progress.failed_files == 0

    repaired_manifest = manifest_service.load_manifest(temp_repo)
    assert repaired_manifest is not None
    assert len(repaired_manifest.files) == 2


@pytest.mark.asyncio
async def test_recovery_from_temporary_file_orphan(
    temp_repo: Path, mock_cognee: MagicMock, manifest_service: ManifestService
):
    """An orphaned .tmp file from an uncommitted transaction is safely overwritten on next run."""
    service = IndexingService(cognee_service=mock_cognee, manifest_service=manifest_service)

    # Create orphaned .tmp file
    manifest_file = manifest_service._get_manifest_path(temp_repo)
    tmp_file = manifest_file.with_suffix(".tmp")
    tmp_file.write_text("ORPHANED_PARTIAL_WRITE", encoding="utf-8")

    # Index repository
    await service.index_repository(temp_repo, "test_dataset")

    # Target manifest exists and is valid
    manifest = manifest_service.load_manifest(temp_repo)
    assert manifest is not None
    assert len(manifest.files) == 2
