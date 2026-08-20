"""Architectural boundary tests for RE:Track Application and Use-Case layer.

Verifies:
1. Direct use case execution with constructor-injected dependencies.
2. Application container factory wiring and dependency injection.
3. AST static verification enforcing that app.application does NOT import:
   - app.api
   - fastapi / starlette
   - app.server
   - app.cli
   - kuzu / lancedb / cognee.api.v1
4. AST static verification enforcing that use_cases/ do NOT import concrete service adapters from app.services.
5. Ports and Domain purity: no infrastructure/framework imports.
6. Domain entity round-trip serialization/deserialization.
7. LocalFileSystemAdapter and LocalHardwareTelemetryAdapter port contracts.
8. Execution of use cases with fake ports without live infrastructure.
"""

import ast
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.application.container import ApplicationContainer
from app.application.domain.repository import IndexedRepositoryRecord
from app.application.dto import (
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
from app.application.ports import (
    FileSystemPort,
    HardwareTelemetryPort,
    MemoryPort,
    RepositoryMetadataPort,
)
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
from app.services.hardware_telemetry import LocalHardwareTelemetryAdapter
from app.services.local_filesystem import LocalFileSystemAdapter
from app.services.repository_metadata_store import JsonRepositoryMetadataStore
from app.services.repository_summary import RepositorySummaryGenerator
from app.services.source_search_service import SourceSearchService


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
    container.metadata_store = JsonRepositoryMetadataStore(store_path=tmp_path / "store.json")
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
            summary_generator=MagicMock(),
            context_cache=ContextCacheEngine(),
            context_gen_lock=asyncio.Lock(),
            ensure_services_fn=lambda: None,
        )

        req = GenerateContextRequest(task="Add feature", datasets=["my-repo"], top_k=10)
        res = await use_case.generate_context(req)

        assert isinstance(res, ContextResponse)
        assert res.success is True
        assert res.task == "Add feature"
        assert res.markdown == "# Feature Context\nDetails"
        assert res.section_count == 1

    @pytest.mark.asyncio
    async def test_generate_context_validation_empty_task(self):
        use_case = ContextUseCases(
            context_service=MagicMock(),
            cognee_service=AsyncMock(),
            indexing_service=MagicMock(),
            intent_parser=MagicMock(),
            llm_provider=AsyncMock(),
            cgc_service=MagicMock(),
            summary_generator=MagicMock(),
            context_cache=ContextCacheEngine(),
            context_gen_lock=asyncio.Lock(),
            ensure_services_fn=lambda: None,
        )
        req = GenerateContextRequest(task="   ", datasets=["my-repo"])
        with pytest.raises(ValueError, match="Task must not be empty"):
            await use_case.generate_context(req)


class TestIndexingUseCases:
    @pytest.mark.asyncio
    async def test_indexing_orchestration(self, tmp_path):
        repo_dir = tmp_path / "test_repo"
        repo_dir.mkdir()
        (repo_dir / "main.py").write_text("print('hello')")

        mock_indexing_service = MagicMock()
        mock_indexing_service.index_repository = AsyncMock(
            return_value=IndexingProgress(
                total_files=1,
                processed_files=1,
                failed_files=0,
                total_batches=1,
                failed_paths=[],
            )
        )
        mock_indexing_service.discover_files.return_value = [repo_dir / "main.py"]
        mock_indexing_service.filter_files.return_value = [repo_dir / "main.py"]

        store = JsonRepositoryMetadataStore(store_path=tmp_path / "store.json")
        summary_gen = RepositorySummaryGenerator()

        use_case = IndexingUseCases(
            indexing_service=mock_indexing_service,
            indexing_lock=asyncio.Lock(),
            ensure_services_fn=lambda: None,
            summary_generator=summary_gen,
            metadata_store=store,
        )

        req = IndexRepositoryRequest(repository_path=str(repo_dir), dataset_name="test_dataset")
        res = await use_case.index_repository(req)

        assert res.success is True
        assert res.processed_files == 1

        summaries_res = await use_case.get_repository_summaries()
        assert summaries_res.success is True
        assert summaries_res.total_count == 1
        assert summaries_res.repositories[0].name == "test_dataset"


class TestRepositoryUseCases:
    @pytest.mark.asyncio
    async def test_repository_crud(self, tmp_path):
        repo_dir = tmp_path / "my_project"
        repo_dir.mkdir()

        mock_manager = MagicMock()
        mock_repo = Repository(
            id="rep-123",
            name="my_project",
            source_type="local",
            local_path=str(repo_dir),
            languages=["Python"],
            frameworks=[],
            file_count=5,
            size_bytes=1024,
            status="ready",
        )
        mock_manager.list_repositories.return_value = [mock_repo]
        mock_manager.import_repo.return_value = mock_repo
        mock_manager.delete.return_value = True

        store = JsonRepositoryMetadataStore(store_path=tmp_path / "store.json")

        use_case = RepositoryUseCases(
            repository_manager=mock_manager,
            indexing_service=MagicMock(),
            llm_provider=AsyncMock(),
            summary_generator=RepositorySummaryGenerator(),
            cognee_service=AsyncMock(),
            metadata_store=store,
        )

        list_res = await use_case.list_repositories()
        assert list_res.success is True
        assert list_res.total_count == 1
        assert list_res.repositories[0].name == "my_project"

        del_res = await use_case.delete_repository("rep-123")
        assert del_res["success"] is True


class TestMemoryUseCases:
    @pytest.mark.asyncio
    async def test_list_and_forget_datasets(self, tmp_path):
        mock_cognee = AsyncMock()
        mock_cognee.list_datasets.return_value = [
            {"id": "ds-1", "name": "repo_dataset", "file_count": 10, "created_at": "2026-08-20"}
        ]
        mock_cognee.get_stats.return_value = {
            "total_datasets": 1,
            "total_data_items": 10,
            "total_size_bytes": 4096,
            "storage_directory": "/tmp",
            "vector_db": "lancedb",
            "graph_db": "kuzu",
            "status": "ready",
        }

        store = JsonRepositoryMetadataStore(store_path=tmp_path / "store.json")
        settings = Settings(settings_store_path=tmp_path / "settings.json")

        use_case = MemoryUseCases(
            cognee_service=mock_cognee,
            settings_getter=lambda: settings,
            ensure_services_fn=lambda: None,
            metadata_store=store,
        )

        list_res = await use_case.list_datasets()
        assert list_res.success is True
        assert list_res.total_count == 1
        assert list_res.datasets[0].name == "repo_dataset"

        stats_res = await use_case.get_memory_stats()
        assert stats_res.success is True
        assert stats_res.dataset_count == 1

        forget_res = await use_case.forget_dataset(ForgetDatasetRequest(dataset="repo_dataset"))
        assert forget_res is None


class TestPackageUseCases:
    @pytest.mark.asyncio
    async def test_package_lifecycle(self, tmp_path):
        from app.services.context_package_repository import JsonContextPackageRepository

        pkg_repo = JsonContextPackageRepository(store_path=tmp_path / "pkgs.json")
        use_case = PackageUseCases(package_repository=pkg_repo)

        save_req = ContextPackageSaveRequest(
            name="Auth Context",
            task="Add authentication",
            objective="OAuth implementation",
            markdown="# Auth context",
            total_time_ms=120,
        )

        saved = await use_case.save_context_package(save_req)
        assert saved.id is not None
        assert saved.name == "Auth Context"

        listed = await use_case.list_context_packages()
        assert listed.total_count == 1
        assert listed.packages[0].name == "Auth Context"

        appended = await use_case.append_context_package(
            saved.id,
            ContextPackageAppendRequest(
                additional_task="Add refresh tokens",
                additional_markdown="\n## Refresh Token Details",
            ),
        )
        assert "Refresh Token" in appended.markdown

        del_res = await use_case.delete_context_package(saved.id)
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


# --- 3. Domain Entity & Port Adapter Tests ---


class TestDomainEntitiesAndAdapters:
    def test_indexed_repository_record_roundtrip(self):
        rec = IndexedRepositoryRecord(
            id="repo-1",
            name="test-repo",
            path="/path/to/test-repo",
            languages=["Python", "TypeScript"],
            file_count=42,
            memory_size="168 KB",
            last_indexed="2026-08-20T12:00:00Z",
            purpose="Testing domain entity",
            architecture=[{"icon": "Layers", "label": "Modular"}],
            components=[{"path": "core", "centrality": "core"}],
            call_graph_status="ready",
            call_graph_error=None,
        )
        d = rec.to_dict()
        assert d["id"] == "repo-1"
        assert d["languages"] == ["Python", "TypeScript"]

        rec2 = IndexedRepositoryRecord.from_dict(d)
        assert rec2.id == rec.id
        assert rec2.name == rec.name
        assert rec2.languages == rec.languages
        assert rec2.file_count == rec.file_count

    def test_local_filesystem_adapter(self, tmp_path):
        adapter = LocalFileSystemAdapter()
        test_file = tmp_path / "hello.txt"
        test_file.write_text("Hello World\nLine 2", encoding="utf-8")

        assert adapter.exists(test_file) is True
        assert adapter.is_dir(tmp_path) is True
        assert adapter.is_dir(test_file) is False
        assert adapter.get_file_size(test_file) > 0
        assert "Hello World" in adapter.read_text(test_file)

    def test_local_hardware_telemetry_adapter(self):
        adapter = LocalHardwareTelemetryAdapter()
        telem = adapter.get_telemetry()
        assert telem.ram_total_gb >= 0.0
        assert telem.cpu_percent >= 0.0


# --- 4. AST Architectural Boundary Invariant Checks ---


class TestArchitecturalBoundaryInvariants:
    """Verifies that app.application strictly depends inward on models/ports, never outward on API, server, or CLI."""

    FORBIDDEN_IMPORTS = {
        "app.api",
        "fastapi",
        "starlette",
        "app.server",
        "app.cli",
        "kuzu",
        "lancedb",
        "cognee.api.v1",
    }

    CONCRETE_SERVICES = {
        "app.services.cognee_service",
        "app.services.indexing_service",
        "app.services.repository_manager",
        "app.services.llm_provider_service",
        "app.services.cgc_service",
        "app.services.repository_summary",
        "app.services.context_service",
        "app.services.context_cache",
        "app.services.context_package_repository",
        "app.services.repository_metadata_store",
        "app.services.benchmark_service",
        "app.services.hardware_telemetry",
    }

    def test_application_layer_ast_purity(self):
        """Verify no Python file in app/application imports any forbidden package."""
        app_dir = Path(__file__).resolve().parent.parent / "app" / "application"
        py_files = list(app_dir.rglob("*.py"))
        assert len(py_files) >= 15, f"Expected at least 15 Python files under app/application, found {len(py_files)}"

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

    def test_use_cases_do_not_import_concrete_services(self):
        """Verify that use cases import only from app.application.ports/dto/domain, not concrete services."""
        use_cases_dir = Path(__file__).resolve().parent.parent / "app" / "application" / "use_cases"
        for file_path in use_cases_dir.glob("*.py"):
            tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert not any(alias.name.startswith(svc) for svc in self.CONCRETE_SERVICES), (
                            f"Use case {file_path.name} imports concrete service: {alias.name}"
                        )
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    assert not any(mod.startswith(svc) for svc in self.CONCRETE_SERVICES), (
                        f"Use case {file_path.name} imports from concrete service: {mod}"
                    )

    def test_ports_layer_ast_purity(self):
        """Verify ports contain no dependencies on app.services, API frameworks, or databases."""
        ports_dir = Path(__file__).resolve().parent.parent / "app" / "application" / "ports"
        for file_path in ports_dir.glob("*.py"):
            tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert not alias.name.startswith("app.services"), f"Port {file_path.name} imports {alias.name}"
                        assert not any(alias.name.startswith(f) for f in self.FORBIDDEN_IMPORTS), f"Port {file_path.name} imports {alias.name}"
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    assert not mod.startswith("app.services"), f"Port {file_path.name} imports from {mod}"
                    assert not any(mod.startswith(f) for f in self.FORBIDDEN_IMPORTS), f"Port {file_path.name} imports from {mod}"

    def test_domain_layer_ast_purity(self):
        """Verify domain entities contain zero infrastructure dependencies."""
        domain_dir = Path(__file__).resolve().parent.parent / "app" / "application" / "domain"
        for file_path in domain_dir.glob("*.py"):
            tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert not alias.name.startswith("app.services")
                        assert not any(alias.name.startswith(f) for f in self.FORBIDDEN_IMPORTS)
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    assert not mod.startswith("app.services")
                    assert not any(mod.startswith(f) for f in self.FORBIDDEN_IMPORTS)

    def test_no_direct_persistence_in_use_cases(self):
        """Verify use cases do not perform raw JSON file operations."""
        use_cases_dir = Path(__file__).resolve().parent.parent / "app" / "application" / "use_cases"
        for file_path in use_cases_dir.glob("*.py"):
            content = file_path.read_text(encoding="utf-8")
            assert "write_text" not in content, (
                f"Direct filesystem write found in use case {file_path.name}"
            )
            assert "_load_repo_store" not in content, (
                f"Legacy raw persistence helper found in use case {file_path.name}"
            )

    def test_no_inline_context_service_construction(self):
        """Verify ContextUseCases does not instantiate ContextService inline."""
        ctx_file = Path(__file__).resolve().parent.parent / "app" / "application" / "use_cases" / "context.py"
        tree = ast.parse(ctx_file.read_text(encoding="utf-8"), filename=str(ctx_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "ContextService":
                    pytest.fail("Inline construction of ContextService found in context.py use case!")

    def test_dto_isolation_and_independence(self):
        """Verify application DTOs can be imported in isolation without importing app.api."""
        import importlib
        dto_mod = importlib.import_module("app.application.dto")
        assert hasattr(dto_mod, "ContextResponse")
        assert hasattr(dto_mod, "IndexRepositoryRequest")
        assert hasattr(dto_mod, "BenchmarkSuiteResponse")
        assert hasattr(dto_mod, "HealthResponse")
