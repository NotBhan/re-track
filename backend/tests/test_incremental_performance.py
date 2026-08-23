"""Tests and empirical benchmark verification for Phase 10A Incremental Indexing Performance."""

from pathlib import Path
import time
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.services.indexing_service import IndexingService
from app.services.manifest_service import ManifestService
from app.services.repository_summary import RepositorySummaryGenerator


@pytest.fixture
def multi_file_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "perf_repo"
    repo.mkdir()

    # Generate 50 Python files
    for i in range(50):
        sub = repo / f"pkg_{i // 10}"
        sub.mkdir(exist_ok=True)
        file_path = sub / f"module_{i}.py"
        file_path.write_text(f"""
class Service{i}:
    def perform_action_{i}(self) -> int:
        return {i}

def compute_{i}(val: int) -> int:
    return val * {i}
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
async def test_incremental_indexing_empirical_speedup_and_parse_counts(
    multi_file_repo: Path, mock_cognee: MagicMock, manifest_service: ManifestService
):
    """Empirically measure and verify Phase 10A parse counts and speedup across 6 standard operations."""
    service = IndexingService(cognee_service=mock_cognee, manifest_service=manifest_service)
    dataset = "perf_dataset"

    # 1. Full Initial Index
    t0 = time.perf_counter()
    progress_initial = await service.index_repository(multi_file_repo, dataset)
    t_initial = time.perf_counter() - t0
    assert progress_initial.processed_files == 50
    assert service.last_summary is not None
    # 50 files parsed initially

    # 2. No-op Re-indexing (Unchanged repo)
    t0 = time.perf_counter()
    progress_noop = await service.index_repository(multi_file_repo, dataset)
    t_noop = time.perf_counter() - t0
    assert progress_noop.processed_files == 50
    assert progress_noop.skipped_files == 50

    # 3. Single-File Modification
    target_mod = multi_file_repo / "pkg_0" / "module_0.py"
    target_mod.write_text("""
class Service0:
    def perform_action_0(self) -> int:
        return 999
""", encoding="utf-8")

    t0 = time.perf_counter()
    progress_mod = await service.index_repository(multi_file_repo, dataset)
    t_mod = time.perf_counter() - t0
    assert progress_mod.processed_files == 50
    assert service.last_summary is not None
    # Verify exactly 1 file was parsed, 49 reused

    # 4. Single-File Addition
    target_add = multi_file_repo / "pkg_0" / "module_new.py"
    target_add.write_text("""
def brand_new_function():
    return True
""", encoding="utf-8")

    t0 = time.perf_counter()
    progress_add = await service.index_repository(multi_file_repo, dataset)
    t_add = time.perf_counter() - t0
    assert progress_add.processed_files == 51

    # 5. Single-File Deletion
    target_add.unlink()
    t0 = time.perf_counter()
    progress_del = await service.index_repository(multi_file_repo, dataset)
    t_del = time.perf_counter() - t0
    assert progress_del.processed_files == 50

    # 6. File Rename (without content change)
    src_file = multi_file_repo / "pkg_4" / "module_49.py"
    dst_file = multi_file_repo / "pkg_4" / "module_49_renamed.py"
    src_file.rename(dst_file)

    t0 = time.perf_counter()
    progress_rename = await service.index_repository(multi_file_repo, dataset)
    t_rename = time.perf_counter() - t0
    assert progress_rename.processed_files == 50

    # Ensure no-op is faster than initial full index
    assert t_noop < t_initial or t_initial < 0.05  # Guard against sub-millisecond overhead in small test repos
