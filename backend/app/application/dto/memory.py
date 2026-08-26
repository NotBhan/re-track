"""Memory, dataset, and graph topology DTOs."""

from typing import Any, Optional
from pydantic import BaseModel, Field


class ForgetDatasetRequest(BaseModel):
    """Request to forget (delete) a dataset from Cognee memory."""

    dataset: Optional[str] = Field(
        default=None, description="Dataset name to delete"
    )
    dataset_id: Optional[str] = Field(
        default=None, description="UUID of dataset to delete"
    )
    data_id: Optional[str] = Field(
        default=None, description="UUID of specific data item to delete"
    )


class ForgetDatasetResponse(BaseModel):
    """Response from forget operation."""

    success: bool = Field(description="Whether the operation completed")
    message: str = Field(description="Human-readable status message")


class DatasetInfo(BaseModel):
    """Metadata for a single stored dataset."""

    id: str = Field(description="UUID of the dataset")
    name: str = Field(description="Dataset name")
    type: str = Field(default="repository", description="Dataset type")
    size_bytes: Optional[int] = Field(default=None, description="Total size in bytes (unknown if unavailable)")
    created_at: Optional[str] = Field(default=None, description="ISO 8601 creation timestamp")
    file_count: int = Field(default=0, description="Number of files in dataset")
    source_path: Optional[str] = Field(default=None, description="Source repository path (unknown if unavailable)")
    storage_state: str = Field(default="healthy", description="Subsystem storage status")
    provenance: Optional[dict[str, Any]] = Field(default=None, description="Provenance anchoring metadata")


class DatasetListResponse(BaseModel):
    """Response listing all stored datasets."""

    success: bool = Field(description="Whether the query succeeded")
    datasets: list[DatasetInfo] = Field(default_factory=list, description="List of datasets")
    total_count: int = Field(default=0, description="Total number of datasets")


class MemoryGraphNode(BaseModel):
    """A node in the Cognee semantic knowledge graph."""

    id: str = Field(description="Unique node identifier")
    label: str = Field(description="Display label")
    kind: str = Field(default="entity", description="Node kind (entity, concept, document, file)")
    type: Optional[str] = Field(default=None, description="Entity type classification")
    properties: dict[str, Any] = Field(default_factory=dict, description="Node attributes")
    provenance: Optional[dict[str, Any]] = Field(default=None, description="Provenance metadata")


class MemoryGraphEdge(BaseModel):
    """A directed edge in the Cognee semantic knowledge graph."""

    source: str = Field(description="Source node ID")
    target: str = Field(description="Target node ID")
    kind: str = Field(default="relates_to", description="Relationship classification")
    relationship_type: Optional[str] = Field(default=None, description="Semantic relation")
    properties: dict[str, Any] = Field(default_factory=dict, description="Edge attributes")
    provenance: Optional[dict[str, Any]] = Field(default=None, description="Provenance metadata")


class MemoryGraphResponse(BaseModel):
    """Response containing Cognee Knowledge Graph topology."""

    success: bool = Field(description="Whether the operation succeeded")
    status: str = Field(description="Knowledge graph status: extracted, not_extracted, extracting, failed")
    storage_state: str = Field(default="healthy", description="Kùzu graph engine state (healthy, degraded, unavailable)")
    nodes: list[MemoryGraphNode] = Field(default_factory=list, description="Authoritative graph nodes")
    edges: list[MemoryGraphEdge] = Field(default_factory=list, description="Authoritative graph edges")
    total_nodes: int = Field(default=0, description="Total nodes count")
    total_edges: int = Field(default=0, description="Total edges count")
    dataset_name: Optional[str] = Field(default=None, description="Filtered dataset namespace")
    message: str = Field(default="", description="Truthful explanatory status message")


class VectorDatasetInfo(BaseModel):
    """Authoritative vector index status for a dataset."""

    id: str = Field(description="Dataset UUID")
    name: str = Field(description="Dataset name")
    file_count: int = Field(default=0, description="Number of source files")
    size_bytes: int = Field(default=0, description="Size in bytes")
    created_at: Optional[str] = Field(default=None, description="Creation timestamp")
    vector_status: str = Field(default="ready", description="Vector index status (ready, indexing, empty)")
    chunk_count: int = Field(default=0, description="Estimated vector chunk count")
    provenance: Optional[dict[str, Any]] = Field(default=None, description="Provenance metadata")


class MemoryVectorsResponse(BaseModel):
    """Response containing vector space and embedding index details."""

    success: bool = Field(description="Whether query succeeded")
    storage_state: str = Field(default="healthy", description="LanceDB engine state (healthy, degraded, unavailable)")
    vector_db_provider: str = Field(default="lancedb", description="Vector database provider")
    embedding_model: str = Field(default="", description="Active embedding model")
    embedding_dimensions: int = Field(default=768, description="Embedding vector dimensions")
    total_datasets: int = Field(default=0, description="Total datasets count")
    total_files: int = Field(default=0, description="Total source files indexed")
    total_vectors: int = Field(default=0, description="Total vector embedding rows in database")
    tables: list[dict[str, Any]] = Field(default_factory=list, description="Active LanceDB tables information")
    datasets: list[VectorDatasetInfo] = Field(default_factory=list, description="Vector datasets list")
    message: str = Field(default="", description="Truthful vector index status explanation")


class MemoryDataItem(BaseModel):
    """A single stored/ingested file or document in Cognee."""

    id: str = Field(description="Data item UUID")
    name: str = Field(description="Data item file or document name")
    mime_type: str = Field(default="text/plain", description="MIME content type")
    data_size: int = Field(default=0, description="Size in bytes")
    created_at: Optional[str] = Field(default=None, description="Ingestion timestamp")
    extension: str = Field(default="", description="File extension")
    content_hash: str = Field(default="", description="Content SHA hash")
    pipeline_status: dict[str, Any] = Field(default_factory=dict, description="Pipeline processing status")
    provenance: Optional[dict[str, Any]] = Field(default=None, description="Provenance metadata")


class DatasetDataItemsResponse(BaseModel):
    """Response listing stored files/documents for a dataset."""

    success: bool = Field(description="Whether query succeeded")
    dataset_id: str = Field(description="Dataset UUID")
    dataset_name: str = Field(description="Dataset name")
    items: list[MemoryDataItem] = Field(default_factory=list, description="Stored data items")
    total_count: int = Field(default=0, description="Total items count")


class CognifyRequest(BaseModel):
    """Request to extract memory vectors and knowledge graph for a dataset."""

    dataset_name: Optional[str] = Field(default=None, description="Dataset name to cognify (or all datasets if omitted)")


class CognifyResponse(BaseModel):
    """Response for Cognee cognify extraction operation."""

    success: bool = Field(description="Whether operation succeeded")
    dataset_name: Optional[str] = Field(default=None, description="Cognified dataset name")
    total_vectors: int = Field(default=0, description="Total vector embeddings generated")
    total_nodes: int = Field(default=0, description="Total knowledge graph entities extracted")
    total_edges: int = Field(default=0, description="Total knowledge graph relationships extracted")
    message: str = Field(default="", description="Extraction status message")


class MemoryStatsResponse(BaseModel):
    """Memory topology statistics for the memory page sidebar."""

    success: bool = Field(description="Whether the query succeeded")
    total_size_display: str = Field(description="Human-readable total memory size (e.g. '127 files')")
    dataset_count: int = Field(description="Number of indexed datasets")
    knowledge_graph_status: str = Field(default="not_extracted", description="'not_extracted' | 'extracting' | 'extracted' | 'failed'")
    graph_nodes: Optional[int] = Field(default=None, description="Number of graph nodes if extracted")
    graph_edges: Optional[int] = Field(default=None, description="Number of graph edges if extracted")
    storage_subsystems: dict[str, str] = Field(
        default_factory=lambda: {"lancedb": "healthy", "kuzu": "healthy", "cognee": "healthy"},
        description="Individual storage subsystem states",
    )


class DashboardStats(BaseModel):
    """Aggregate dashboard statistics."""

    success: bool = Field(description="Whether the query succeeded")
    indexed_repos: int = Field(description="Number of indexed repositories")
    total_files: int = Field(description="Total files across all repositories")
    total_embeddings: int = Field(description="Approximate total embeddings")
    packages_generated: int = Field(description="Number of packages generated")
    avg_gen_time_ms: float = Field(description="Average generation time in milliseconds")
    last_indexed_repo: str = Field(description="Name of most recently indexed repository")
    last_indexed_time: str = Field(description="ISO 8601 timestamp of most recent indexing")
