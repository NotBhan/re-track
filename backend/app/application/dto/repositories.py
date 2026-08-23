"""Repository management DTOs."""

from typing import Optional
from pydantic import BaseModel, Field


class RepositoryCreateRequest(BaseModel):
    """Request to create (import) a new repository."""

    source_type: str = Field(..., description="github | local")
    source_url: Optional[str] = Field(None, description="GitHub URL")
    local_path: Optional[str] = Field(None, description="Local path")
    path: Optional[str] = Field(None, description="Alternative local path alias")
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


class RepositorySummaryResponse(BaseModel):
    """Structured architectural summary response for a repository."""

    success: bool = Field(default=True, description="Whether summary extraction succeeded")
    repository_path: str = Field(description="Resolved local path to repository")
    project_purpose: str = Field(default="", description="Inferred project purpose")
    languages: list[str] = Field(default_factory=list, description="Detected languages")
    frameworks: list[str] = Field(default_factory=list, description="Detected frameworks")
    databases: list[str] = Field(default_factory=list, description="Detected databases")
    dependencies: list[str] = Field(default_factory=list, description="Detected dependencies")
    architecture_pattern: str = Field(default="", description="Inferred architecture pattern")
    architecture_layers: list[str] = Field(default_factory=list, description="Architectural layers")
    key_components: list[dict] = Field(default_factory=list, description="Key components")
    entry_points: list[dict] = Field(default_factory=list, description="Application entry points")
    public_apis: list[dict] = Field(default_factory=list, description="Public APIs and routes")
    coding_conventions: dict = Field(default_factory=dict, description="Inferred coding conventions")
    file_count: int = Field(default=0, description="Number of analyzed files")
    call_graph_status: str = Field(default="not_analyzed", description="Status of call graph analysis")


class ASTCallGraphResponse(BaseModel):
    """Deterministic AST call graph response."""

    success: bool = Field(default=True, description="Whether AST extraction succeeded")
    repository_path: str = Field(description="Resolved local path to repository")
    nodes: list[dict] = Field(default_factory=list, description="Call graph nodes")
    edges: list[dict] = Field(default_factory=list, description="Call graph edges")
    total_nodes: int = Field(default=0, description="Total nodes extracted")
    total_edges: int = Field(default=0, description="Total edges extracted")
    call_graph_status: str = Field(default="analyzed", description="Status of call graph extraction")
    call_graph_error: Optional[str] = Field(default=None, description="Error if call graph failed")


class SourceSearchResultItem(BaseModel):
    """A single matched file result in a source search."""

    file_path: str = Field(description="Repository-relative file path")
    score: float = Field(default=0.0, description="Relevance score")
    matched_symbols: list[str] = Field(default_factory=list, description="Matched symbol names")
    snippet: str = Field(default="", description="Code snippet")


class SourceSearchResponse(BaseModel):
    """Response containing source search results."""

    success: bool = Field(default=True, description="Whether search succeeded")
    repository_path: str = Field(description="Resolved local path to repository")
    query: str = Field(description="Original search query")
    results: list[SourceSearchResultItem] = Field(default_factory=list, description="Matching file candidates")
    total_results: int = Field(default=0, description="Number of matching results")
