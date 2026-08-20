"""Abstract semantic and graph memory port for RE:Track."""

from typing import Any, Optional, Protocol


class MemoryPort(Protocol):
    """Port for semantic, vector, and graph memory operations."""

    @property
    def is_initialized(self) -> bool:
        """Return True if memory backend is configured and initialized."""
        ...

    async def initialize(self) -> None:
        """Initialize and validate connection to the memory engine."""
        ...

    async def list_datasets(self) -> list[dict[str, Any]]:
        """List all datasets stored in persistent memory."""
        ...

    async def get_dataset_data(self, dataset_id: str) -> list[dict[str, Any]]:
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

    async def cognify(self, dataset_name: Optional[str] = None) -> Any:
        """Run graph and knowledge extraction pipeline on a dataset."""
        ...

    async def get_stats(self) -> dict[str, Any]:
        """Retrieve aggregated memory statistics (dataset count, items, storage)."""
        ...

    async def get_graph(self) -> dict[str, Any]:
        """Retrieve knowledge graph nodes and edges for visualization."""
        ...

    async def get_vectors(self) -> dict[str, Any]:
        """Retrieve vector index metadata and embeddings distribution."""
        ...

    async def add(
        self,
        data: Any,
        dataset_name: str = "default",
        **kwargs: Any,
    ) -> Any:
        """Add data into memory without graph extraction."""
        ...

    async def remember(
        self,
        data: Any,
        dataset_name: str = "default",
        **kwargs: Any,
    ) -> Any:
        """Ingest data into persistent memory."""
        ...

    async def recall(
        self,
        query_text: str,
        datasets: list[str],
        top_k: int = 15,
        **kwargs: Any,
    ) -> Any:
        """Retrieve semantically relevant context from specified datasets."""
        ...
