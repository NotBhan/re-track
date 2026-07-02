"""SavedContextPackage dataclass with provenance fields."""

from dataclasses import dataclass, field


@dataclass
class SavedContextPackage:
    """A persisted context package with provenance tracking.

    This is the persistence-layer representation, distinct from the in-memory
    ContextPackage used during generation. It stores the rendered markdown
    output plus metadata about where it came from and how it was produced.
    """

    # Identity
    id: str = ""
    name: str = ""
    task: str = ""
    objective: str = ""

    # Provenance
    repository_id: str = ""
    repository_name: str = ""
    repository_branch: str = ""
    repository_commit: str = ""
    indexing_version: str = ""

    # Content
    markdown: str = ""
    section_count: int = 0
    token_estimate: int = 0
    retrieved_memories: int = 0
    deduplicated_memories: int = 0
    compression_ratio: float = 0.0
    total_time_ms: int = 0

    # Metadata
    created_at: str = ""
    updated_at: str = ""
    tags: list[str] = field(default_factory=list)
