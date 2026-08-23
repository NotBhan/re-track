"""Tests for Phase 10A Semantic Memory Ingestion and Dataset Isolation Contract."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.services.indexing_service import IndexingService
from app.services.manifest_service import ManifestService


@pytest.fixture
def temp_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "test_repo"
    repo.mkdir()
    (repo / "auth.py").write_text("""
class AuthService:
    def login(self): pass
""", encoding="utf-8")
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
async def test_semantic_memory_summary_outline_synchronization(
    temp_repo: Path, mock_cognee: MagicMock, manifest_service: ManifestService
):
    """Cognee memory receives the synthesized repository architecture outline upon incremental changes."""
    service = IndexingService(cognee_service=mock_cognee, manifest_service=manifest_service)

    # Initial indexing
    await service.index_repository(temp_repo, "test_dataset")
    assert mock_cognee.add.call_count == 1
    call_args = mock_cognee.add.call_args[1]
    assert "test_dataset" in call_args["dataset_name"]
    assert "AuthService" in call_args["data"]

    mock_cognee.add.reset_mock()

    # Re-indexing unchanged repo (NOOP) -> Cognee is NOT re-ingested
    await service.index_repository(temp_repo, "test_dataset")
    assert mock_cognee.add.call_count == 0

    # Incremental update: Add billing.py
    (temp_repo / "billing.py").write_text("""
class BillingService:
    def pay(self): pass
""", encoding="utf-8")

    await service.index_repository(temp_repo, "test_dataset")
    assert mock_cognee.add.call_count == 1
    call_args2 = mock_cognee.add.call_args[1]
    assert "BillingService" in call_args2["data"]
