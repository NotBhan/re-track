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


class ContextPackageReplaceRequest(BaseModel):
    """Replacement generated content for an existing saved package (re-synthesis).

    This updates a package in place: the record's identity (id, name, task,
    repository identity, creation time, tags) is preserved by the backend, and
    only the fields the generation actually produced are replaced. Absent fields
    keep their stored value, so a client never has to invent a zero. Appending
    additional context is a different operation (`/append`) and is never used as
    a substitute for regeneration.
    """

    markdown: str = Field(..., min_length=1, description="Newly generated markdown (a replacement must replace content)")
    objective: str | None = Field(default=None, description="Derived objective of the regeneration")
    section_count: int | None = Field(default=None, description="Section count of the new markdown")
    token_estimate: int | None = Field(default=None, description="Token estimate of the new markdown")
    retrieved_memories: int | None = Field(default=None, description="Memories retrieved for this generation")
    deduplicated_memories: int | None = Field(default=None, description="Memories after deduplication")
    compression_ratio: float | None = Field(default=None, description="Input/output token ratio")
    total_time_ms: float | None = Field(default=None, description="Generation time in milliseconds")
    repository_commit: str | None = Field(default=None, description="Repository commit the regeneration ran against")
    indexing_version: str | None = Field(default=None, description="Indexing version the regeneration ran against")
