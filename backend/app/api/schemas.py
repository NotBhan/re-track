"""Request and response schemas for AndesContext API commands.

Serializable Pydantic models for Tauri IPC transport.
"""

from typing import Optional

from pydantic import BaseModel, Field


# --- Request Schemas ---


class IndexRepositoryRequest(BaseModel):
    """Request to index a repository into Cognee memory."""

    repository_path: str = Field(
        ..., min_length=1, description="Absolute path to the repository root"
    )
    dataset_name: str = Field(
        ..., min_length=1, description="Logical memory namespace for Cognee"
    )
    batch_size: int = Field(
        default=10, ge=1, le=100, description="Files per ingestion batch"
    )


class GenerateContextRequest(BaseModel):
    """Request to generate a Context Package for a developer task."""

    task: str = Field(
        ..., min_length=1, description="Developer request or question"
    )
    datasets: list[str] = Field(
        ..., description="Dataset names to search"
    )
    top_k: int = Field(default=20, ge=1, le=100, description="Maximum memories to retrieve")


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


# --- Response Schemas ---


class HealthResponse(BaseModel):
    """System health check response."""

    status: str = Field(description="Health status: 'ok' or 'degraded'")
    ollama_reachable: bool = Field(description="Whether Ollama is reachable")
    cognee_initialized: bool = Field(description="Whether CogneeService is initialized")
    version: str = Field(default="0.1.0", description="Backend version")


class BackendStatusResponse(BaseModel):
    """Detailed backend status."""

    status: str = Field(description="Health status: 'ok' or 'degraded'")
    ollama_reachable: bool = Field(description="Whether Ollama is reachable")
    ollama_host: str = Field(description="Ollama host")
    ollama_port: int = Field(description="Ollama port")
    llm_model: str = Field(description="Current LLM model name")
    embedding_model: str = Field(description="Current embedding model name")
    vector_db: str = Field(description="Vector database provider")
    graph_db: str = Field(description="Graph database provider")
    relational_db: str = Field(description="Relational database provider")
    data_root: str = Field(description="Data storage root path")
    system_root: str = Field(description="System storage root path")
    cognee_initialized: bool = Field(description="Whether CogneeService is initialized")


class IndexRepositoryResponse(BaseModel):
    """Response from repository indexing."""

    success: bool = Field(description="Whether indexing completed without fatal errors")
    repository_path: str = Field(description="Indexed repository path")
    dataset_name: str = Field(description="Dataset name used")
    total_files: int = Field(description="Total files discovered")
    processed_files: int = Field(description="Files successfully processed")
    failed_files: int = Field(description="Files that failed processing")
    total_batches: int = Field(description="Total batches processed")
    failed_paths: list[str] = Field(
        default_factory=list, description="Paths of files that failed"
    )
    summary: str = Field(description="Human-readable progress summary")


class ContextResponse(BaseModel):
    """Response containing a generated Context Package."""

    success: bool = Field(description="Whether generation succeeded")
    task: str = Field(description="Original developer request")
    objective: str = Field(description="Derived objective from the task")
    markdown: str = Field(description="Generated Markdown context")
    section_count: int = Field(description="Number of sections")
    source_count: int = Field(description="Number of memory sources used")
    token_estimate: int = Field(description="Estimated token count")
    dataset: str = Field(description="Datasets searched")
    # Metadata fields
    retrieved_memories: int = Field(default=0, description="Total memories retrieved")
    deduplicated_memories: int = Field(default=0, description="Memories after dedup")
    compressed_memories: int = Field(default=0, description="Memories after compression")
    compression_ratio: float = Field(default=1.0, description="Input/output token ratio")
    retrieval_time_ms: int = Field(default=0, description="Time spent in Cognee recall")
    total_time_ms: int = Field(default=0, description="Total generation time")
    # Reference fields
    reference_count: int = Field(default=0, description="Number of traceable references")
    section_headings: list[str] = Field(default_factory=list, description="Headings of generated sections")


class ForgetDatasetResponse(BaseModel):
    """Response from forget operation."""

    success: bool = Field(description="Whether the operation completed")
    message: str = Field(description="Human-readable status message")


# --- Error Schema ---


class ErrorResponse(BaseModel):
    """Structured error response for API failures."""

    error: str = Field(description="Error type name")
    message: str = Field(description="Human-readable error message")
    success: bool = Field(default=False, description="Always False for errors")
    details: Optional[str] = Field(default=None, description="Additional error context")
