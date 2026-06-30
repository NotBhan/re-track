"""Tests for rewritten ContextService using PackageBuilder."""

import pytest
from unittest.mock import AsyncMock

from app.models.responses import RecallResult, RecallResponse
from app.services.context_service import ContextService


def _make(text: str, kind: str = "text", score: float = 0.5) -> RecallResult:
    """Helper to create a RecallResult."""
    return RecallResult(kind=kind, search_type="semantic", text=text, score=score, dataset_name="test")


@pytest.fixture
def mock_cognee():
    """Mock CogneeService returning a single file result."""
    cognee = AsyncMock()
    cognee.recall.return_value = RecallResponse(
        query="test", dataset="test",
        results=[_make("svc.py", "file", 0.9)],
    )
    return cognee


@pytest.fixture
def mock_cognee_empty():
    """Mock CogneeService returning empty results."""
    cognee = AsyncMock()
    cognee.recall.return_value = RecallResponse(query="q", dataset="d", results=[])
    return cognee


@pytest.fixture
def mock_cognee_multiple():
    """Mock CogneeService returning diverse results."""
    cognee = AsyncMock()
    cognee.recall.return_value = RecallResponse(
        query="architecture", dataset="test",
        results=[
            _make("backend/app/main.py", "file", 0.9),
            _make("The layered architecture uses service boundaries", "text", 0.8),
            _make("Follow snake_case naming convention", "text", 0.7),
        ],
    )
    return cognee


class TestContextServiceV2:
    """Integration tests for ContextService with PackageBuilder."""

    @pytest.mark.asyncio
    async def test_generate_returns_package(self, mock_cognee):
        pkg = await ContextService(mock_cognee).generate_context_package("Fix bug", ["ws"])
        assert pkg.task == "Fix bug"
        assert pkg.markdown != ""

    @pytest.mark.asyncio
    async def test_generate_has_metadata(self, mock_cognee):
        pkg = await ContextService(mock_cognee).generate_context_package("q", ["ws"])
        assert pkg.metadata is not None
        assert pkg.metadata.retrieved_memory_count == 1

    @pytest.mark.asyncio
    async def test_generate_empty_results(self, mock_cognee_empty):
        pkg = await ContextService(mock_cognee_empty).generate_context_package("q", ["ws"])
        assert pkg.task == "q"
        assert pkg.markdown != ""

    @pytest.mark.asyncio
    async def test_generate_no_summary(self, mock_cognee):
        pkg = await ContextService(mock_cognee).generate_context_package("q", ["ws"])
        assert pkg.repository_summary is None

    @pytest.mark.asyncio
    async def test_generate_multiple_sections(self, mock_cognee_multiple):
        pkg = await ContextService(mock_cognee_multiple).generate_context_package("architecture", ["ws"])
        assert pkg.section_count >= 2
        assert "Architecture" in pkg.markdown

    @pytest.mark.asyncio
    async def test_generate_files_section(self, mock_cognee):
        pkg = await ContextService(mock_cognee).generate_context_package("q", ["ws"])
        assert "`svc.py`" in pkg.markdown

    @pytest.mark.asyncio
    async def test_generate_with_datasets(self, mock_cognee):
        pkg = await ContextService(mock_cognee).generate_context_package("q", ["ws", "prod"])
        assert pkg.dataset == "ws, prod"

    @pytest.mark.asyncio
    async def test_generate_preserves_task(self, mock_cognee):
        pkg = await ContextService(mock_cognee).generate_context_package("Add auth middleware", ["ws"])
        assert pkg.task == "Add auth middleware"

    @pytest.mark.asyncio
    async def test_generate_metadata_timestamps(self, mock_cognee):
        pkg = await ContextService(mock_cognee).generate_context_package("q", ["ws"])
        assert pkg.metadata.generated_at != ""
        assert pkg.metadata.total_time_ms >= 0

    @pytest.mark.asyncio
    async def test_generate_references_present(self, mock_cognee):
        pkg = await ContextService(mock_cognee).generate_context_package("q", ["ws"])
        assert len(pkg.references) > 0

    @pytest.mark.asyncio
    async def test_generate_deduplication(self, mock_cognee):
        mock_cognee.recall.return_value = RecallResponse(
            query="q", dataset="d",
            results=[_make("same", score=0.5), _make("same", score=0.9)],
        )
        pkg = await ContextService(mock_cognee).generate_context_package("q", ["ws"])
        assert pkg.metadata.deduplicated_count == 1

    @pytest.mark.asyncio
    async def test_generate_ranking(self, mock_cognee):
        mock_cognee.recall.return_value = RecallResponse(
            query="q", dataset="d",
            results=[_make("low", score=0.3), _make("high", score=0.9)],
        )
        pkg = await ContextService(mock_cognee).generate_context_package("q", ["ws"])
        assert pkg.markdown.index("high") < pkg.markdown.index("low")

    @pytest.mark.asyncio
    async def test_generate_long_task_truncated_objective(self, mock_cognee):
        long_task = "x" * 150
        pkg = await ContextService(mock_cognee).generate_context_package(long_task, ["ws"])
        assert len(pkg.objective) <= 100

    @pytest.mark.asyncio
    async def test_generate_pipeline_version(self, mock_cognee):
        pkg = await ContextService(mock_cognee).generate_context_package("q", ["ws"])
        assert pkg.metadata.pipeline_version == "1.0"
