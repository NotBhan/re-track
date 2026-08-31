from typing import Any, Optional, Protocol

from app.application.domain.memory import (
    MemoryDataItemRecord,
    MemoryDatasetRecord,
    MemoryGraphRecord,
    MemoryVectorStatsRecord,
    SemanticMemoryGenerationResult,
    SemanticMemoryRecord,
)


class MemoryLifecyclePort(Protocol):
    """Port for memory backend initialization and readiness verification."""

    @property
    def is_initialized(self) -> bool:
        """Return True if memory backend is configured and initialized."""
        ...

    async def initialize(self) -> None:
        """Initialize and validate connection to the memory engine."""
        ...


class MemoryIngestionPort(Protocol):
    """Port for ingesting documents, code, and text into persistent memory."""

    async def add(
        self,
        data: Any,
        dataset_name: str = "default",
        **kwargs: Any,
    ) -> Any:
        """Add data into memory without immediate graph extraction."""
        ...

    async def remember(
        self,
        data: Any,
        dataset_name: str = "default",
        **kwargs: Any,
    ) -> Any:
        """Ingest data into persistent memory."""
        ...


class MemoryRetrievalPort(Protocol):
    """Port for semantic search and contextual memory recall."""

    async def recall(
        self,
        query_text: str,
        datasets: list[str],
        top_k: int = 15,
        **kwargs: Any,
    ) -> Any:
        """Retrieve semantically relevant context from specified datasets."""
        ...


class MemoryDatasetPort(MemoryLifecyclePort, Protocol):
    """Port for managing memory datasets and their individual data items."""

    async def list_datasets(self) -> list[MemoryDatasetRecord] | list[dict[str, Any]]:
        """List all datasets stored in persistent memory."""
        ...

    async def get_dataset_data(self, dataset_id: str) -> list[MemoryDataItemRecord] | list[dict[str, Any]]:
        """List all ingested data items belonging to a dataset."""
        ...

    async def forget(
        self,
        dataset: Optional[str] = None,
        dataset_id: Optional[str] = None,
        data_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Remove a dataset or data item from persistent memory."""
        ...

    async def forget_data_item(self, data_id: str) -> None:
        """Remove a specific data item by its unique ID."""
        ...


class MemoryTopologyPort(Protocol):
    """Port for inspecting graph topology, vector stats, and running extraction pipelines."""

    async def cognify(self, dataset_name: Optional[str] = None) -> Any:
        """Run graph and knowledge extraction pipeline on a dataset."""
        ...

    async def get_stats(self) -> dict[str, Any]:
        """Retrieve aggregated memory statistics (dataset count, items, storage)."""
        ...

    async def get_graph(self) -> MemoryGraphRecord | dict[str, Any]:
        """Retrieve knowledge graph nodes and edges for visualization."""
        ...

    async def get_vectors(self) -> MemoryVectorStatsRecord | dict[str, Any]:
        """Retrieve vector index metadata and embeddings distribution."""
        ...


class MemoryPort(
    MemoryIngestionPort,
    MemoryRetrievalPort,
    MemoryDatasetPort,
    MemoryTopologyPort,
    Protocol,
):
    """Unified composite memory port combining all memory capabilities."""
    ...


class SemanticMemoryRepositoryPort(Protocol):
    """Port for durable persistence and repository-isolated retrieval of SemanticMemoryRecord entities.

    Invariants:
    - Persists ONLY records that pass provenance validation.
    - Maintains repository isolation (cross-repo isolation and validation).
    - Preserves derived-only invariants (generated_by='cognee_pipeline', is_derived=True, is_authoritative=False).
    - Revalidates records against active manifest on load without silently repairing stale records.
    """

    def save(self, record: SemanticMemoryRecord, manifest: Optional[Any] = None) -> tuple[bool, str]:
        """Persist a single validated SemanticMemoryRecord."""
        ...

    def save_all(self, records: list[SemanticMemoryRecord], manifest: Optional[Any] = None) -> tuple[int, list[str]]:
        """Persist a batch of validated SemanticMemoryRecords."""
        ...

    def upsert(self, record: SemanticMemoryRecord, manifest: Optional[Any] = None) -> tuple[bool, str]:
        """Upsert a single validated SemanticMemoryRecord."""
        ...

    def get(self, memory_id: str, repository_id: Optional[str] = None, manifest: Optional[Any] = None) -> Optional[SemanticMemoryRecord]:
        """Retrieve a record by ID, optionally validating against manifest."""
        ...

    def get_by_repository(self, repository_id: str, manifest: Optional[Any] = None, include_stale: bool = False) -> list[SemanticMemoryRecord]:
        """Retrieve all records for a repository, optionally validating against manifest."""
        ...

    def load_all(self, manifest: Optional[Any] = None, include_stale: bool = False) -> list[SemanticMemoryRecord]:
        """Retrieve all persisted records across all repositories."""
        ...

    def delete(self, memory_id: str, repository_id: Optional[str] = None) -> bool:
        """Delete a record by its memory ID."""
        ...

    def delete_by_repository(self, repository_id: str) -> int:
        """Delete all records associated with a repository."""
        ...

    def clear(self) -> None:
        """Clear all stored semantic memory records."""
        ...


class SemanticMemoryGeneratorPort(Protocol):
    """Port for generating structured semantic memory records from verified repository evidence."""

    async def generate_semantic_memory(
        self,
        repository_id: str,
        manifest: Any,
        file_filter: Optional[list[str]] = None,
        source_snippets: Optional[dict[str, str]] = None,
        task_intent: Optional[str] = None,
        frameworks: Optional[list[str]] = None,
        model_config: Optional[dict[str, Any]] = None,
        persist: bool = True,
    ) -> SemanticMemoryGenerationResult:
        """Generate, validate, and optionally persist semantic memory records from verified repository evidence."""
        ...

    async def cognify_repository(
        self,
        repository_id: str,
        manifest: Any,
        delta: Optional[Any] = None,
        existing_manifest: Optional[Any] = None,
        source_snippets: Optional[dict[str, str]] = None,
        frameworks: Optional[list[str]] = None,
        task_intent: Optional[str] = None,
        model_config: Optional[dict[str, Any]] = None,
        cognee_service: Optional[Any] = None,
    ) -> SemanticMemoryGenerationResult:
        """Perform end-to-end repository cognification and incremental semantic memory lifecycle."""
        ...


class CognificationPort(SemanticMemoryGeneratorPort, Protocol):
    """Alias protocol for repository cognification lifecycle."""
    ...

