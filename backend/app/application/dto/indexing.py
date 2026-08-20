"""Repository indexing and summary DTOs."""

from typing import Optional
from pydantic import BaseModel, Field


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
