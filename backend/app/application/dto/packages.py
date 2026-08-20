"""Context Package persistence DTOs."""

from pydantic import BaseModel, Field


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
