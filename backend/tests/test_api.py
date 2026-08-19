"""Tests for the API layer — schemas, commands, and error handling."""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.api.schemas import (
    BackendStatusResponse,
    ContextResponse,
    ErrorResponse,
    ForgetDatasetRequest,
    GenerateContextRequest,
    HealthResponse,
    IndexRepositoryRequest,
    IndexRepositoryResponse,
)
from app.api.commands import (
    _ensure_services,
    forget_dataset,
    generate_context,
    get_backend_status,
    health,
    index_repository,
    initialize_backend,
)
from app.models.errors import CogneeServiceError
from app.models.responses import (
    ContextPackage,
    IndexingProgress,
    PackageSection,
    RecallResult,
    RecallResponse,
    SectionType,
)


# ─── Schema Tests ───


class TestHealthResponse:
    def test_ok(self):
        r = HealthResponse(status="ok", ollama_reachable=True, cognee_initialized=True)
        assert r.status == "ok"
        assert r.ollama_reachable is True
        assert r.version == "0.1.0"

    def test_degraded(self):
        r = HealthResponse(status="degraded", ollama_reachable=False, cognee_initialized=True)
        assert r.status == "degraded"
        assert r.ollama_reachable is False

    def test_to_dict(self):
        r = HealthResponse(status="ok", ollama_reachable=True, cognee_initialized=True)
        d = r.model_dump()
        assert d["status"] == "ok"
        assert d["ollama_reachable"] is True
        assert "version" in d


class TestBackendStatusResponse:
    def test_full_response(self):
        r = BackendStatusResponse(
            status="ok",
            ollama_reachable=True,
            ollama_host="localhost",
            ollama_port=11434,
            llm_model="phi3:mini",
            embedding_model="nomic-embed-text:latest",
            vector_db="lancedb",
            graph_db="kuzu",
            relational_db="sqlite",
            data_root="/data",
            system_root="/system",
            cognee_initialized=True,
        )
        assert r.llm_model == "phi3:mini"
        assert r.vector_db == "lancedb"


class TestIndexRepositoryRequest:
    def test_valid(self):
        r = IndexRepositoryRequest(
            repository_path="/home/user/repo",
            dataset_name="my-repo",
        )
        assert r.batch_size == 10  # default
        assert r.repository_path == "/home/user/repo"

    def test_custom_batch_size(self):
        r = IndexRepositoryRequest(
            repository_path="/repo",
            dataset_name="test",
            batch_size=25,
        )
        assert r.batch_size == 25

    def test_empty_dataset_rejected(self):
        with pytest.raises(Exception):
            IndexRepositoryRequest(
                repository_path="/repo",
                dataset_name="",
            )


class TestIndexRepositoryResponse:
    def test_from_indexing_progress(self):
        progress = IndexingProgress(
            total_files=50,
            processed_files=45,
            failed_files=5,
            total_batches=5,
            failed_paths=["/repo/bad.py"],
        )
        r = IndexRepositoryResponse(
            success=True,
            repository_path="/repo",
            dataset_name="test",
            total_files=progress.total_files,
            processed_files=progress.processed_files,
            failed_files=progress.failed_files,
            total_batches=progress.total_batches,
            failed_paths=progress.failed_paths,
            summary=progress.summary(),
        )
        assert r.success is True
        assert r.total_files == 50
        assert r.failed_paths == ["/repo/bad.py"]


class TestGenerateContextRequest:
    def test_valid(self):
        r = GenerateContextRequest(
            task="Add auth middleware",
            datasets=["repo-1", "repo-2"],
        )
        assert r.top_k == 20  # default
        assert len(r.datasets) == 2

    def test_empty_task_rejected(self):
        with pytest.raises(Exception):
            GenerateContextRequest(task="", datasets=["repo"])

    def test_empty_datasets_at_command_level(self):
        r = GenerateContextRequest(task="test", datasets=[])
        assert r.datasets == []


class TestContextResponse:
    def test_full_response(self):
        r = ContextResponse(
            success=True,
            task="test",
            objective="test objective",
            markdown="# Task\n\nhello",
            section_count=2,
            source_count=5,
            token_estimate=100,
            dataset="repo",
        )
        assert r.success is True
        assert r.token_estimate == 100
        assert r.objective == "test objective"


class TestForgetDatasetRequest:
    def test_dataset_name(self):
        r = ForgetDatasetRequest(dataset="my-dataset")
        assert r.dataset == "my-dataset"
        assert r.dataset_id is None
        assert r.data_id is None

    def test_dataset_id(self):
        r = ForgetDatasetRequest(dataset_id="550e8400-e29b-41d4-a716-446655440000")
        assert r.dataset_id is not None

    def test_all_none(self):
        r = ForgetDatasetRequest()
        assert r.dataset is None
        assert r.dataset_id is None
        assert r.data_id is None


class TestErrorResponse:
    def test_error(self):
        r = ErrorResponse(error="ValueError", message="bad input")
        assert r.success is False
        assert r.details is None

    def test_with_details(self):
        r = ErrorResponse(
            error="CogneeServiceError",
            message="init failed",
            details="Ollama not reachable",
        )
        assert r.details == "Ollama not reachable"


# ─── Command Tests (mocked services) ───


@pytest.fixture
def mock_services():
    """Set up mocked services for command tests."""
    import app.api.commands as cmd

    mock_cognee = MagicMock()
    mock_cognee.is_initialized = True
    mock_cognee.initialize = AsyncMock()
    mock_cognee.remember = AsyncMock()
    mock_cognee.recall = AsyncMock()
    mock_cognee.forget = AsyncMock()

    mock_indexing = MagicMock()
    mock_indexing.index_repository = AsyncMock()

    mock_context = MagicMock()
    mock_context.generate_context_package = AsyncMock()

    cmd._cognee_service = mock_cognee
    cmd._indexing_service = mock_indexing
    cmd._context_service = mock_context
    cmd._settings = MagicMock()
    cmd._settings.ollama.check_connection.return_value = True
    cmd._settings.ollama.host = "localhost"
    cmd._settings.ollama.port = 11434
    cmd._settings.ollama.llm_model = "phi3:mini"
    cmd._settings.ollama.embedding_model = "nomic-embed-text:latest"
    cmd._settings.storage.vector_db = "lancedb"
    cmd._settings.storage.graph_db = "kuzu"
    cmd._settings.storage.relational_db = "sqlite"
    cmd._settings.storage.data_root = Path("/data")
    cmd._settings.storage.system_root = Path("/system")

    yield cmd, mock_cognee, mock_indexing, mock_context


class TestHealthCommand:
    @pytest.mark.asyncio
    async def test_health_ok(self, mock_services):
        cmd, _, _, _ = mock_services
        result = await health()
        assert result.status == "ok"
        assert result.ollama_reachable is True
        assert result.cognee_initialized is True

    @pytest.mark.asyncio
    async def test_health_degraded_no_ollama(self, mock_services):
        cmd, _, _, _ = mock_services
        cmd._settings.ollama.check_connection.return_value = False
        result = await health()
        assert result.status == "degraded"
        assert result.ollama_reachable is False


class TestGetBackendStatus:
    @pytest.mark.asyncio
    async def test_status_ok(self, mock_services):
        result = await get_backend_status()
        assert result.status == "ok"
        assert result.llm_model == "phi3:mini"
        assert result.vector_db == "lancedb"

    @pytest.mark.asyncio
    async def test_status_degraded(self, mock_services):
        cmd, _, _, _ = mock_services
        cmd._settings.ollama.check_connection.return_value = False
        result = await get_backend_status()
        assert result.status == "degraded"


class TestIndexRepositoryCommand:
    @pytest.mark.asyncio
    async def test_index_valid_repo(self, mock_services, tmp_path):
        cmd, _, mock_indexing, _ = mock_services
        # Create a temp directory to act as a repo
        repo = tmp_path / "repo"
        repo.mkdir()

        progress = IndexingProgress(
            total_files=10,
            processed_files=10,
            failed_files=0,
            total_batches=1,
        )
        mock_indexing.index_repository.return_value = progress

        request = IndexRepositoryRequest(
            repository_path=str(repo),
            dataset_name="test-dataset",
        )
        result = await index_repository(request)
        assert result.success is True
        assert result.total_files == 10
        assert result.processed_files == 10
        assert result.failed_files == 0

    @pytest.mark.asyncio
    async def test_index_nonexistent_path(self, mock_services):
        request = IndexRepositoryRequest(
            repository_path="/nonexistent/path",
            dataset_name="test",
        )
        with pytest.raises(ValueError, match="does not exist"):
            await index_repository(request)

    @pytest.mark.asyncio
    async def test_index_file_not_dir(self, mock_services, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("hello")
        request = IndexRepositoryRequest(
            repository_path=str(f),
            dataset_name="test",
        )
        with pytest.raises(ValueError, match="not a directory"):
            await index_repository(request)


class TestGenerateContextCommand:
    @pytest.mark.asyncio
    async def test_generate_context(self, mock_services):
        _, _, _, mock_context = mock_services
        from app.models.responses import PackageMetadata, PackageReference
        meta = PackageMetadata(
            package_version="1.0", repository_summary_version="none",
            generated_at="2026-01-01T00:00:00Z", datasets_used=["repo"],
            retrieved_memory_count=10, deduplicated_count=7,
            compressed_count=7, compression_ratio=1.3,
            estimated_tokens=200, pipeline_version="1.0",
            retrieval_time_ms=500, total_time_ms=800,
        )
        refs = [PackageReference("file", "auth.py", None, 0.9, ["recall:test"])]
        package = ContextPackage(
            task="Add auth",
            objective="Add authentication middleware",
            markdown="# Task\n\nAdd auth",
            sections=[
                PackageSection(
                    section_type="architecture",
                    heading="Architecture Notes",
                    content="- Uses middleware pattern",
                )
            ],
            references=refs,
            metadata=meta,
            source_count=3,
            dataset="repo",
        )
        mock_context.generate_context_package.return_value = package

        request = GenerateContextRequest(
            task="Add auth middleware",
            datasets=["repo"],
        )
        result = await generate_context(request)
        assert result.success is True
        assert result.section_count == 1
        assert result.source_count == 3
        assert "Add auth" in result.markdown
        assert result.objective == "Add authentication middleware"
        assert result.retrieved_memories == 10
        assert result.deduplicated_memories == 7
        assert result.compression_ratio == 1.3
        assert result.retrieval_time_ms == 500
        assert result.total_time_ms == 800
        assert result.reference_count == 1
        assert result.section_headings == ["Architecture Notes"]

    @pytest.mark.asyncio
    async def test_generate_context_empty_task(self, mock_services):
        request = GenerateContextRequest(task="  ", datasets=["repo"])
        with pytest.raises(ValueError, match="must not be empty"):
            await generate_context(request)

    @pytest.mark.asyncio
    async def test_generate_context_empty_datasets(self, mock_services):
        request = GenerateContextRequest(task="test", datasets=[])
        with pytest.raises(ValueError, match="at least one dataset"):
            await generate_context(request)


class TestForgetDatasetCommand:
    @pytest.mark.asyncio
    async def test_forget_by_name(self, mock_services):
        _, mock_cognee, _, _ = mock_services
        mock_cognee.forget.return_value = None

        request = ForgetDatasetRequest(dataset="old-dataset")
        result = await forget_dataset(request)
        assert result is None
        mock_cognee.forget.assert_called_once_with(
            dataset="old-dataset", dataset_id=None, data_id=None
        )

    @pytest.mark.asyncio
    async def test_forget_no_identifiers(self, mock_services):
        request = ForgetDatasetRequest()
        result = await forget_dataset(request)
        assert isinstance(result, ErrorResponse)
        assert result.error == "ValueError"

    @pytest.mark.asyncio
    async def test_forget_failure(self, mock_services):
        _, mock_cognee, _, _ = mock_services
        mock_cognee.forget.side_effect = CogneeServiceError("forget failed")

        request = ForgetDatasetRequest(dataset="bad-dataset")
        result = await forget_dataset(request)
        assert isinstance(result, ErrorResponse)
        assert "forget failed" in result.message


class TestEnsureServices:
    def test_raises_when_not_initialized(self):
        import app.api.commands as cmd

        cmd._cognee_service = None
        cmd._indexing_service = None
        cmd._context_service = None
        with pytest.raises(CogneeServiceError, match="not initialized"):
            _ensure_services()


# ─── Serialization Tests ───


class TestSerializationRoundtrip:
    def test_health_response_json(self):
        r = HealthResponse(status="ok", ollama_reachable=True, cognee_initialized=True)
        j = r.model_dump_json()
        r2 = HealthResponse.model_validate_json(j)
        assert r2.status == "ok"

    def test_context_response_json(self):
        r = ContextResponse(
            success=True,
            task="test",
            objective="test objective",
            markdown="# hello",
            section_count=1,
            source_count=2,
            token_estimate=10,
            dataset="repo",
            retrieved_memories=5,
            deduplicated_memories=3,
            compressed_memories=3,
            compression_ratio=1.5,
            retrieval_time_ms=100,
            total_time_ms=200,
            reference_count=2,
            section_headings=["Files"],
        )
        j = r.model_dump_json()
        r2 = ContextResponse.model_validate_json(j)
        assert r2.markdown == "# hello"
        assert r2.objective == "test objective"
        assert r2.retrieved_memories == 5
        assert r2.reference_count == 2

    def test_error_response_json(self):
        r = ErrorResponse(error="TestError", message="boom")
        j = r.model_dump_json()
        r2 = ErrorResponse.model_validate_json(j)
        assert r2.success is False

    def test_index_request_json(self):
        r = IndexRepositoryRequest(repository_path="/repo", dataset_name="test")
        j = r.model_dump_json()
        r2 = IndexRepositoryRequest.model_validate_json(j)
        assert r2.repository_path == "/repo"


class TestSuggestedPrompts:
    @pytest.mark.asyncio
    async def test_generate_suggested_prompts_fallback(self):
        from app.api.commands import generate_suggested_prompts
        result = await generate_suggested_prompts("unknown-repo")
        assert result["success"] is True
        assert len(result["prompts"]) > 0
        assert "label" in result["prompts"][0]
        assert "prompt" in result["prompts"][0]


class TestSettingsAPI:
    @pytest.mark.asyncio
    async def test_get_and_update_cognee_settings(self, tmp_path):
        from app.api.commands import get_app_settings, update_cognee_settings
        from app.api.schemas import CogneeSettingsRequest
        from app.config.settings import Settings

        settings_file = tmp_path / "settings.json"
        import app.api.commands as cmd_module
        settings = Settings(settings_store_path=settings_file)
        cmd_module._settings = settings

        # Update settings
        req = CogneeSettingsRequest(
            vector_db="qdrant",
            graph_db="networkx",
            enable_kg_extraction=False,
            auto_link_entities=True,
            caching=True,
        )

        result = await update_cognee_settings(req)
        assert result.success is True
        assert result.vector_db == "qdrant"
        assert result.graph_db == "networkx"
        assert result.enable_kg_extraction is False
        assert result.auto_link_entities is True
        assert result.caching is True

        # Verify persistent file was written
        assert settings_file.exists()

        # Verify get_app_settings returns the persisted values
        get_res = await get_app_settings()
        assert get_res.success is True
        assert get_res.vector_db == "qdrant"
        assert get_res.graph_db == "networkx"


# ─── Main ───

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

