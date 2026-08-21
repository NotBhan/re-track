"""Abstract semantic, vector, and graph memory capability ports for RE:Track."""

from typing import Any, Optional, Protocol

from app.application.domain.memory import (
    MemoryDataItemRecord,
    MemoryDatasetRecord,
    MemoryGraphRecord,
    MemoryVectorStatsRecord,
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
