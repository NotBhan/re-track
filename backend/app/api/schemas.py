"""Request and response schemas for RE:Track (RefinedEngine Track) API commands.

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
    batch_size: Optional[int] = Field(
        default=10, ge=1, le=100, description="Files per ingestion batch"
    )
    force_reindex: Optional[bool] = Field(
        default=False, description="Force complete re-indexing bypassing manifest diff"
    )


class GenerateContextRequest(BaseModel):
    """Request to generate a Context Package for a developer task."""

    task: str = Field(
        ..., min_length=1, description="Developer request or question"
    )
    datasets: list[str] = Field(
        default_factory=list, description="Datasets to search"
    )
    top_k: Optional[int] = Field(default=20, ge=1, le=100, description="Maximum memories to retrieve")


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


class DatasetInfo(BaseModel):
    """Metadata for a single stored dataset."""

    id: str = Field(description="UUID of the dataset")
    name: str = Field(description="Dataset name")
    type: str = Field(default="repository", description="Dataset type")
    size_bytes: Optional[int] = Field(default=None, description="Total size in bytes (unknown if unavailable)")
    created_at: Optional[str] = Field(default=None, description="ISO 8601 creation timestamp")
    file_count: int = Field(default=0, description="Number of files in dataset")
    source_path: Optional[str] = Field(default=None, description="Source repository path (unknown if unavailable)")


class DatasetListResponse(BaseModel):
    """Response listing all stored datasets."""

    success: bool = Field(description="Whether the query succeeded")
    datasets: list[DatasetInfo] = Field(default_factory=list, description="List of datasets")
    total_count: int = Field(default=0, description="Total number of datasets")


# --- Repository Summary Schemas ---


class RepoArchInfo(BaseModel):
    """Architecture pattern for a repository."""

    icon: str = Field(description="Icon identifier for the pattern")
    label: str = Field(description="Human-readable architecture label")


class RepoComponentInfo(BaseModel):
    """A key component in the repository."""

    path: str = Field(description="Relative path to the component")
    centrality: str = Field(description="Centrality level (e.g., core, peripheral)")


class RepositorySummaryInfo(BaseModel):
    """Metadata for a single indexed repository."""

    id: str = Field(description="Unique repository identifier")
    name: str = Field(description="Repository name")
    path: str = Field(description="Repository file path")
    languages: list[str] = Field(default_factory=list, description="Programming languages detected")
    file_count: int = Field(default=0, description="Number of indexed files")
    memory_size: str = Field(default="0 B", description="Human-readable memory size")
    last_indexed: str = Field(description="ISO 8601 timestamp of last indexing")
    purpose: Optional[str] = Field(default=None, description="Inferred project purpose")
    architecture: Optional[list[RepoArchInfo]] = Field(
        default=None, description="Architecture patterns detected"
    )
    components: Optional[list[RepoComponentInfo]] = Field(
        default=None, description="Key components detected"
    )


class IndexedRepositoryListResponse(BaseModel):
    """Response listing all indexed repositories (summary store)."""

    success: bool = Field(description="Whether the query succeeded")
    repositories: list[RepositorySummaryInfo] = Field(
        default_factory=list, description="List of indexed repositories"
    )
    total_count: int = Field(default=0, description="Total number of repositories")


# --- Dashboard Stats Schemas ---


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


# --- Error Schema ---


class ErrorResponse(BaseModel):
    """Structured error response for API failures."""

    error: str = Field(description="Error type name")
    message: str = Field(description="Human-readable error message")
    success: bool = Field(default=False, description="Always False for errors")
    details: Optional[str] = Field(default=None, description="Additional error context")


# --- Context Package Schemas ---


class ContextPackageSaveRequest(BaseModel):
    """Request to save a context package."""

    name: str = Field(..., min_length=1)
    task: str = ""
    objective: str = ""
    repository_id: str = ""
    repository_name: str = ""
    repository_branch: str = ""
    repository_commit: str = ""
    indexing_version: str = ""
    markdown: str = ""
    section_count: int = 0
    token_estimate: int = 0
    retrieved_memories: int = 0
    deduplicated_memories: int = 0
    compression_ratio: float = 0.0
    total_time_ms: float = 0.0
    tags: list[str] = []


class ContextPackageResponse(BaseModel):
    """Response for a single saved context package."""

    id: str
    name: str
    task: str
    objective: str
    repository_id: str
    repository_name: str
    repository_branch: str
    repository_commit: str
    indexing_version: str
    markdown: str
    section_count: int
    token_estimate: int
    retrieved_memories: int
    deduplicated_memories: int
    compression_ratio: float
    total_time_ms: float
    created_at: str
    updated_at: str
    tags: list[str]


class ContextPackageListResponse(BaseModel):
    """Response listing all saved context packages."""

    success: bool
    packages: list[ContextPackageResponse]
    total_count: int


class ContextPackageAppendRequest(BaseModel):
    """Request to append content to an existing context package."""

    additional_task: str = Field(..., min_length=1)
    additional_markdown: str = ""
    additional_objective: str = ""


class HealthResponse(BaseModel):
    """System health check response."""

    status: str = Field(description="Health status: 'ok' or 'degraded'")
    ollama_reachable: bool = Field(description="Whether Ollama is reachable")
    cognee_initialized: bool = Field(description="Whether CogneeService is initialized")
    version: str = Field(default="0.1.0", description="Backend version")
    ram_total_gb: float = Field(default=0.0, description="Total host RAM in GB")
    ram_used_gb: float = Field(default=0.0, description="Used host RAM in GB")
    ram_percent: float = Field(default=0.0, description="Host RAM usage percentage")
    high_memory_pressure: bool = Field(default=False, description="Whether RAM pressure is above 90%")
    cpu_percent: float = Field(default=0.0, description="Host CPU utilization percent")
    gpu_presence: str = Field(default="None", description="Detected GPU model or family ('AMD', 'NVIDIA', 'None')")
    gpu_name: Optional[str] = Field(default=None, description="GPU device model name")
    vram_total_gb: float = Field(default=0.0, description="Total GPU VRAM in GB")
    vram_used_gb: float = Field(default=0.0, description="Used GPU VRAM in GB")
    execution_device: str = Field(default="CPU", description="Actual runtime execution device ('CPU', 'GPU', 'UNKNOWN')")
    active_model: Optional[str] = Field(default=None, description="Currently active model loaded in memory")


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
    gpu_presence: str = Field(default="None", description="GPU presence")
    execution_device: str = Field(default="CPU", description="Runtime execution device")


class MemoryStatsResponse(BaseModel):
    """Memory topology statistics for the memory page sidebar."""

    success: bool = Field(description="Whether the query succeeded")
    total_size_display: str = Field(description="Human-readable total memory size (e.g. '127 files')")
    dataset_count: int = Field(description="Number of indexed datasets")
    knowledge_graph_status: str = Field(default="not_extracted", description="'not_extracted' | 'extracting' | 'extracted' | 'failed'")
    graph_nodes: Optional[int] = Field(default=None, description="Number of graph nodes if extracted")
    graph_edges: Optional[int] = Field(default=None, description="Number of graph edges if extracted")


# --- Benchmark Schemas ---


class BenchmarkResultItem(BaseModel):
    """A single benchmark query measurement."""

    question: str = Field(description="Benchmark question")
    baseline_tokens: int = Field(default=0, description="Tokens in full eligible repo baseline")
    context_tokens: int = Field(default=0, description="Tokens in generated RE:Track context package")
    compression_ratio: float = Field(default=1.0, description="baseline_tokens / context_tokens")
    token_savings_percent: float = Field(default=0.0, description="Percentage of prompt tokens saved")
    retrieval_time_ms: float = Field(default=0.0, description="Retrieval latency in milliseconds")
    total_time_ms: float = Field(default=0.0, description="Total latency in milliseconds")
    section_count: int = Field(default=0, description="Number of sections generated")
    retrieved_memories: int = Field(default=0, description="Memories retrieved from index")
    accuracy_status: str = Field(default="Not evaluated (requires ground truth set)", description="Context accuracy evaluation status")
    passed: bool = Field(default=False, description="Whether query context met quality criteria")


class BenchmarkSuiteResponse(BaseModel):
    """Response from a benchmark suite run."""

    success: bool = Field(description="Whether the suite completed")
    results: list[BenchmarkResultItem] = Field(default_factory=list)
    avg_retrieval_latency_ms: float = Field(default=0.0, description="Average retrieval latency")
    avg_total_latency_ms: float = Field(default=0.0, description="Average total latency")
    avg_token_savings_percent: float = Field(default=0.0, description="Average token savings percentage")
    avg_compression_ratio: float = Field(default=1.0, description="Average compression ratio")
    accuracy_summary: str = Field(default="Not evaluated (no ground truth set)", description="Accuracy evaluation summary")
    total_questions: int = Field(default=0, description="Total questions tested")
    run_metadata: dict = Field(default_factory=dict, description="Immutable run environment metadata")


# --- Repository Manager Schemas ---


class RepositoryCreateRequest(BaseModel):
    """Request to create (import) a new repository."""

    source_type: str = Field(..., description="github | local")
    source_url: Optional[str] = Field(None, description="GitHub URL")
    local_path: Optional[str] = Field(None, description="Local path")
    name: Optional[str] = Field(None, description="Display name")


class RepositoryResponse(BaseModel):
    """Response for a single managed repository."""

    id: str = Field(description="Unique repository identifier")
    name: str = Field(description="Repository name")
    source_type: str = Field(description="github | local")
    source_url: Optional[str] = Field(default=None, description="GitHub URL")
    local_path: str = Field(description="Local filesystem path")
    branch: str = Field(description="Git branch")
    commit_hash: Optional[str] = Field(default=None, description="Latest commit hash")
    status: str = Field(description="registered | scanning | indexing | indexed | error")
    languages: list[str] = Field(default_factory=list, description="Detected languages")
    frameworks: list[str] = Field(default_factory=list, description="Detected frameworks")
    file_count: int = Field(default=0, description="Number of source files")
    size_bytes: int = Field(default=0, description="Total size in bytes")
    indexed_at: Optional[str] = Field(default=None, description="ISO 8601 indexing timestamp")
    error_message: Optional[str] = Field(default=None, description="Error if status is error")
    summary: str = Field(default="", description="Repository summary")
    entry_points: list[str] = Field(default_factory=list, description="Main entry point files")
    architecture: str = Field(default="", description="Inferred architecture pattern")
    components: list[str] = Field(default_factory=list, description="Top-level code directories")
    dependencies: list[str] = Field(default_factory=list, description="External dependencies")
    metadata: dict = Field(default_factory=dict, description="Extensible metadata")
    call_graph_status: str = Field(default="not_analyzed", description="'not_analyzed' | 'analyzing' | 'analyzed' | 'zero_edges' | 'failed'")
    call_graph_error: Optional[str] = Field(default=None, description="Error if call graph analysis failed")
    call_graph_nodes: Optional[list[dict]] = Field(default=None, description="Extracted call graph nodes")
    call_graph_edges: Optional[list[dict]] = Field(default=None, description="Extracted call graph edges")


class RepositoryListResponse(BaseModel):
    """Response listing all managed repositories."""

    success: bool = Field(description="Whether the query succeeded")
    repositories: list[RepositoryResponse] = Field(
        default_factory=list, description="List of managed repositories"
    )
    total_count: int = Field(default=0, description="Total number of repositories")


class ScanResultResponse(BaseModel):
    """Response from a repository scan operation."""

    success: bool = Field(description="Whether the scan succeeded")
    languages: list[str] = Field(default_factory=list, description="Detected languages")
    frameworks: list[str] = Field(default_factory=list, description="Detected frameworks")
    file_count: int = Field(default=0, description="Number of source files")
    size_bytes: int = Field(default=0, description="Total size in bytes")
    ignored_dirs: list[str] = Field(default_factory=list, description="Directories skipped")
    estimated_index_time_ms: float = Field(default=0.0, description="Estimated indexing time")
