"""Architectural boundary tests for RE:Track Application and Use-Case layer.

Verifies:
1. Direct use case execution with constructor-injected dependencies.
2. Application container factory wiring and dependency injection.
3. AST static verification enforcing that app.application does NOT import inbound adapters (FastAPI, CLI, server) or infrastructure persistence drivers.
"""

import ast
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.api.schemas import (
    CognifyRequest,
    ContextPackageAppendRequest,
    ContextPackageSaveRequest,
    ContextResponse,
    ErrorResponse,
    ForgetDatasetRequest,
    GenerateContextRequest,
    IndexRepositoryRequest,
    RepositoryCreateRequest,
)
from app.application.container import ApplicationContainer
from app.application.use_cases.benchmarks import BenchmarkUseCases
from app.application.use_cases.context import ContextUseCases
from app.application.use_cases.context_packages import PackageUseCases
from app.application.use_cases.indexing import IndexingUseCases
from app.application.use_cases.memory import MemoryUseCases
from app.application.use_cases.repositories import RepositoryUseCases
from app.application.use_cases.system import SystemUseCases
from app.config.settings import Settings
from app.models.repository import Repository
from app.models.responses import (
    ContextPackage,
    IndexingProgress,
    PackageMetadata,
    PackageSection,
)
from app.services.context_cache import ContextCacheEngine
from app.services.repository_summary import RepositorySummaryGenerator


@pytest.fixture
def mock_container(tmp_path):
    settings = Settings(settings_store_path=tmp_path / "settings.json")
    container = ApplicationContainer(settings=settings)
    container.cognee_service = AsyncMock()
    container.cognee_service.is_initialized = True
    container.indexing_service = MagicMock()
    container.context_service = MagicMock()
    container.llm_provider = AsyncMock()
    container.intent_parser = MagicMock()
    container.cgc_service = MagicMock()
    return container


# --- 1. Use Case Unit & Boundary Tests ---


class TestContextUseCases:
    @pytest.mark.asyncio
    async def test_generate_context_success(self, tmp_path):
        mock_ctx_svc = MagicMock()
        mock_meta = PackageMetadata(
            package_version="1.0",
            repository_summary_version="1.0",
            generated_at="2026-08-20T00:00:00Z",
            datasets_used=["my-repo"],
            retrieved_memory_count=5,
            deduplicated_count=4,
            compressed_count=4,
            compression_ratio=1.25,
            estimated_tokens=150,
            pipeline_version="1.0",
            retrieval_time_ms=20,
            total_time_ms=50,
        )
        mock_pkg = ContextPackage(
            task="Add feature",
            objective="Add test feature",
            markdown="# Feature Context\nDetails",
            sections=[PackageSection(section_type="architecture", heading="Arch", content="Content")],
            metadata=mock_meta,
            source_count=2,
            dataset="my-repo",
        )
        mock_ctx_svc.generate_context_package = AsyncMock(return_value=mock_pkg)

        use_case = ContextUseCases(
            context_service=mock_ctx_svc,
            cognee_service=AsyncMock(),
            indexing_service=MagicMock(),
            intent_parser=MagicMock(),
            llm_provider=AsyncMock(),
            cgc_service=MagicMock(),
            summary_generator=RepositorySummaryGenerator(),
            context_cache=ContextCacheEngine(),
            context_gen_lock=asyncio.Lock(),
            ensure_services_fn=lambda: None,
        )

        req = GenerateContextRequest(task="Add feature", datasets=["my-repo"])
        res = await use_case.generate_context(req)

        assert isinstance(res, ContextResponse)
        assert res.success is True
        assert res.task == "Add feature"
        assert res.objective == "Add test feature"
        assert res.retrieved_memories == 5

    @pytest.mark.asyncio
    async def test_generate_context_validation_empty_task(self):
        use_case = ContextUseCases(
            context_service=MagicMock(),
            cognee_service=AsyncMock(),
            indexing_service=MagicMock(),
            intent_parser=MagicMock(),
            llm_provider=AsyncMock(),
            cgc_service=MagicMock(),
            summary_generator=RepositorySummaryGenerator(),
            context_cache=ContextCacheEngine(),
            context_gen_lock=asyncio.Lock(),
            ensure_services_fn=lambda: None,
        )

        with pytest.raises(ValueError, match="must not be empty"):
            await use_case.generate_context(GenerateContextRequest(task="   ", datasets=["repo"]))


class TestIndexingUseCases:
    @pytest.mark.asyncio
    async def test_indexing_concurrency_rejection(self, tmp_path):
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        lock = asyncio.Lock()
        await lock.acquire()  # Simulate ongoing indexing job

        use_case = IndexingUseCases(
            indexing_service=MagicMock(),
            indexing_lock=lock,
            ensure_services_fn=lambda: None,
            summary_generator=RepositorySummaryGenerator(),
            repo_store_path=tmp_path / "store.json",
        )

        req = IndexRepositoryRequest(repository_path=str(repo_dir), dataset_name="repo")
        res = await use_case.index_repository(req)

        assert isinstance(res, ErrorResponse)
        assert res.error == "ConcurrencyError"

        lock.release()

    @pytest.mark.asyncio
    async def test_indexing_success(self, tmp_path):
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "main.py").write_text("print('hello')")

        mock_idx = MagicMock()
        mock_idx.index_repository = AsyncMock(return_value=IndexingProgress(
            total_files=1,
            processed_files=1,
            failed_files=0,
            total_batches=1,
            failed_paths=[],
        ))
        mock_idx.discover_files.return_value = [repo_dir / "main.py"]
        mock_idx.filter_files.return_value = [repo_dir / "main.py"]

        use_case = IndexingUseCases(
            indexing_service=mock_idx,
            indexing_lock=asyncio.Lock(),
            ensure_services_fn=lambda: None,
            summary_generator=RepositorySummaryGenerator(),
            repo_store_path=tmp_path / "store.json",
        )

        req = IndexRepositoryRequest(repository_path=str(repo_dir), dataset_name="repo")
        res = await use_case.index_repository(req)

        assert res.success is True
        assert res.processed_files == 1


class TestRepositoryUseCases:
    @pytest.mark.asyncio
    async def test_repository_crud(self, tmp_path):
        mock_mgr = MagicMock()
        repo_obj = Repository(
            id="repo-123",
            name="demo-repo",
            source_type="local",
            local_path=str(tmp_path),
            status="registered",
        )
        mock_mgr.list_repositories.return_value = [repo_obj]
        mock_mgr.import_repo.return_value = repo_obj
        mock_mgr.delete.return_value = True

        use_case = RepositoryUseCases(
            repository_manager=mock_mgr,
            indexing_service=MagicMock(),
            llm_provider=AsyncMock(),
            summary_generator=RepositorySummaryGenerator(),
            repo_store_path=tmp_path / "store.json",
        )

        # List
        list_res = await use_case.list_repositories()
        assert list_res.success is True
        assert list_res.total_count == 1

        # Create
        create_res = await use_case.create_repository(RepositoryCreateRequest(
            name="demo-repo",
            source_type="local",
            local_path=str(tmp_path),
        ))
        assert create_res.name == "demo-repo"

        # Delete
        del_res = await use_case.delete_repository("repo-123")
        assert del_res["success"] is True


class TestPackageUseCases:
    @pytest.mark.asyncio
    async def test_package_crud_and_append(self, tmp_path):
        from app.services.context_package_repository import JsonContextPackageRepository
        pkg_repo = JsonContextPackageRepository(store_path=tmp_path / "pkgs.json")

        use_case = PackageUseCases(package_repository=pkg_repo)

        # Save
        save_res = await use_case.save_context_package(ContextPackageSaveRequest(
            name="My Package",
            task="Optimize query",
            objective="Index columns",
            markdown="# Package Markdown",
        ))
        assert save_res.name == "My Package"
        pkg_id = save_res.id

        # Get
        get_res = await use_case.get_context_package(pkg_id)
        assert get_res is not None
        assert get_res.name == "My Package"

        # Append
        app_res = await use_case.append_context_package(
            pkg_id,
            ContextPackageAppendRequest(
                additional_task="Add tests",
                additional_markdown="## Tests\nTest notes",
            )
        )
        assert app_res is not None
        assert "Add tests" in app_res.task

        # List
        list_res = await use_case.list_context_packages()
        assert list_res.total_count == 1

        # Delete
        del_res = await use_case.delete_context_package(pkg_id)
        assert del_res["success"] is True


class TestSystemUseCases:
    @pytest.mark.asyncio
    async def test_system_telemetry(self, tmp_path):
        settings = Settings(settings_store_path=tmp_path / "settings.json")
        mock_cognee = AsyncMock()
        mock_cognee.is_initialized = True
        mock_provider = AsyncMock()
        mock_provider.check_health.return_value = MagicMock(is_reachable=True, active_model="phi4-mini")

        use_case = SystemUseCases(
            settings_getter=lambda: settings,
            cognee_service_getter=lambda: mock_cognee,
            llm_provider_getter=lambda: mock_provider,
            provider_updater_fn=AsyncMock(return_value={"success": True}),
        )

        health = await use_case.health()
        assert health.status == "ok"
        assert health.ollama_reachable is True
        assert health.cognee_initialized is True
        assert health.ram_total_gb > 0


# --- 2. Container Factory Wiring Tests ---


class TestApplicationContainerWiring:
    def test_container_instantiates_use_cases(self, mock_container):
        assert isinstance(mock_container.get_context_use_cases(), ContextUseCases)
        assert isinstance(mock_container.get_indexing_use_cases(), IndexingUseCases)
        assert isinstance(mock_container.get_repository_use_cases(), RepositoryUseCases)
        assert isinstance(mock_container.get_memory_use_cases(), MemoryUseCases)
        assert isinstance(mock_container.get_package_use_cases(), PackageUseCases)
        assert isinstance(mock_container.get_system_use_cases(), SystemUseCases)
        assert isinstance(mock_container.get_benchmark_use_cases(), BenchmarkUseCases)


# --- 3. AST Architectural Boundary Invariant Checks ---


class TestArchitecturalBoundaryInvariants:
    """Verifies that app.application strictly depends inward on models/services, never outward on server/CLI."""

    FORBIDDEN_IMPORTS = {
        "fastapi",
        "app.server",
        "app.cli",
        "kuzu",
        "lancedb",
        "cognee.api.v1",
    }

    def test_application_layer_ast_purity(self):
        app_dir = Path(__file__).resolve().parent.parent / "app" / "application"
        py_files = list(app_dir.rglob("*.py"))
        assert len(py_files) >= 7, "Expected at least 7 Python files under app/application"

        for file_path in py_files:
            tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for forbidden in self.FORBIDDEN_IMPORTS:
                            assert not alias.name.startswith(forbidden), (
                                f"Boundary violation in {file_path.name}: "
                                f"forbidden import '{alias.name}'"
                            )
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    for forbidden in self.FORBIDDEN_IMPORTS:
                        assert not mod.startswith(forbidden), (
                            f"Boundary violation in {file_path.name}: "
                            f"forbidden 'from {mod} import ...'"
                        )
