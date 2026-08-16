"""Response models for RE:Track (RefinedEngine Track) backend services."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


@dataclass(frozen=True)
class RememberResult:
    """Result of a remember() operation."""

    dataset_name: str
    items_sent: int
    raw_result: Any = None


@dataclass(frozen=True)
class RecallResult:
    """A single result from a recall() operation."""

    kind: str
    search_type: str
    text: str
    score: float
    dataset_name: str
    raw: Any = None


@dataclass(frozen=True)
class RecallResponse:
    """Aggregated result of a recall() operation."""

    query: str
    dataset: str
    results: list[RecallResult] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.results)


@dataclass
class IndexingProgress:
    """Progress information for a repository indexing operation."""

    total_files: int = 0
    processed_files: int = 0
    skipped_files: int = 0
    failed_files: int = 0
    current_batch: int = 0
    total_batches: int = 0
    failed_paths: list[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        return self.current_batch >= self.total_batches and self.total_batches > 0

    def summary(self) -> str:
        return (
            f"Indexed {self.processed_files}/{self.total_files} files "
            f"({self.skipped_files} skipped, {self.failed_files} failed) "
            f"in {self.total_batches} batches"
        )


class SectionType(str, Enum):
    """Types of sections in a Context Package."""

    TASK = "task"
    OVERVIEW = "overview"
    FILES = "files"
    KNOWLEDGE = "knowledge"
    ARCHITECTURE = "architecture"
    APIS = "apis"
    CONVENTIONS = "conventions"
    DECISIONS = "decisions"
    REFERENCES = "references"


# =============================================================================
# Repository Summary Models [S2, S8]
# =============================================================================


@dataclass(frozen=True)
class TechnologyStack:
    """Technology stack for a repository.

    Attributes:
        languages: Programming languages used in the project.
        frameworks: Frameworks and libraries.
        databases: Database and storage systems.
        dependencies: Key external dependencies.
    """

    languages: list[str]
    frameworks: list[str]
    databases: list[str]
    dependencies: list[str]


@dataclass(frozen=True)
class DirectoryEntry:
    """A top-level directory in the repository map.

    Attributes:
        path: Directory path relative to repository root.
        description: One-line description of the directory's purpose.
    """

    path: str
    description: str


@dataclass(frozen=True)
class ArchitectureInfo:
    """Architecture information for a repository.

    Attributes:
        pattern: High-level architecture pattern (e.g., "layered", "microservice").
        layers: Major architectural layers.
        boundaries: Service or component boundaries.
        major_flows: Key data or control flows.
    """

    pattern: str
    layers: list[str]
    boundaries: list[str]
    major_flows: list[str]


@dataclass(frozen=True)
class ComponentInfo:
    """A key component in the repository.

    Attributes:
        name: Component name.
        responsibilities: What this component does.
        relationships: Dependencies or interactions with other components.
    """

    name: str
    responsibilities: str
    relationships: list[str]


@dataclass(frozen=True)
class EntryPoint:
    """An application entry point.

    Attributes:
        name: Human-readable name (e.g., "cli", "api", "main").
        path: File path relative to repository root.
        type: Entry point type ("cli", "api", "startup").
    """

    name: str
    path: str
    type: str


@dataclass(frozen=True)
class APIInfo:
    """A public API interface.

    Attributes:
        name: API or endpoint name.
        signature: Function signature or endpoint pattern.
        description: What this API does.
    """

    name: str
    signature: str
    description: str


@dataclass(frozen=True)
class ConventionInfo:
    """Coding conventions for a repository.

    Attributes:
        naming: Naming convention (e.g., "snake_case", "camelCase").
        formatting: Code formatter (e.g., "black", "prettier").
        patterns: Project-specific design patterns.
    """

    naming: str
    formatting: str
    patterns: list[str]


@dataclass(frozen=True)
class RepositorySummary:
    """Structured knowledge model of global repository facts.

    Generated after indexing. Cached until re-index. Contains stable
    information about the repository that applies across all tasks.

    Attributes:
        version: Summary schema version.
        repository_fingerprint: Hash of indexed content for staleness detection.
        generated_at: ISO timestamp of generation.
        indexed_commit: Git commit hash if available.
        project_purpose: One-paragraph description of what the project does.
        technology_stack: Languages, frameworks, databases, dependencies.
        repository_map: Top-level directories with responsibilities.
        architecture: Layers, patterns, service boundaries.
        key_components: Major components and their relationships.
        entry_points: CLI, API, startup files.
        public_apis: Public interfaces, endpoints, contracts.
        coding_conventions: Naming, formatting, patterns.
        domain_vocabulary: Repository-specific terminology.
    """

    version: str
    repository_fingerprint: str
    generated_at: str
    indexed_commit: str | None
    project_purpose: str
    technology_stack: TechnologyStack
    repository_map: list[DirectoryEntry]
    architecture: ArchitectureInfo
    key_components: list[ComponentInfo]
    entry_points: list[EntryPoint]
    public_apis: list[APIInfo]
    coding_conventions: ConventionInfo
    domain_vocabulary: dict[str, str]


# =============================================================================
# Context Package Models [S3, S8]
# =============================================================================


@dataclass(frozen=True)
class PackageReference:
    """A traceable reference in a Context Package.

    Attributes:
        ref_type: Reference type ("file", "symbol", "memory", "doc", "dir").
        path: Repository-relative path or memory identifier.
        section: Source section within the referenced item.
        score: Relevance score from retrieval.
        provenance: Chain of source nodes leading to this reference.
    """

    ref_type: str
    path: str
    section: str | None
    score: float
    provenance: list[str]


@dataclass(frozen=True)
class PackageSection:
    """A section in a Context Package.

    Attributes:
        section_type: Section identifier (e.g., "files", "architecture").
        heading: Display heading for the section.
        content: Markdown content of the section.
        priority: Budget priority (1=low, 5=critical). Higher = more important.
        source_sections: Which information hierarchy levels contributed.
        reference_count: Number of source references used.
    """

    section_type: str
    heading: str
    content: str
    priority: int = 3
    source_sections: list[str] = field(default_factory=list)
    reference_count: int = 0


@dataclass(frozen=True)
class PackageMetadata:
    """Metadata for a Context Package.

    Attributes:
        package_version: Schema version.
        repository_summary_version: Version of the Repository Summary used.
        generated_at: ISO timestamp of generation.
        datasets_used: Dataset names searched.
        retrieved_memory_count: Total memories retrieved from Cognee.
        deduplicated_count: Memories after deduplication.
        compressed_count: Memories after compression.
        compression_ratio: Input tokens / output tokens.
        estimated_tokens: Estimated token count of the package.
        pipeline_version: Pipeline implementation version.
        retrieval_time_ms: Time spent in Cognee recall.
        total_time_ms: Total generation time.
    """

    package_version: str
    repository_summary_version: str
    generated_at: str
    datasets_used: list[str]
    retrieved_memory_count: int
    deduplicated_count: int
    compressed_count: int
    compression_ratio: float
    estimated_tokens: int
    pipeline_version: str
    retrieval_time_ms: int
    total_time_ms: int


@dataclass(frozen=True)
class ContextPackage:
    """A structured Context Package for AI coding assistants.

    Combines the Repository Summary with relevant retrieved memories,
    implementation guidance, and traceable references.

    Attributes:
        task: Developer request or question.
        objective: Desired outcome derived from the task.
        sections: Content sections (empty sections are dropped).
        references: Traceable citations to source material.
        metadata: Generation metadata for debugging and evaluation.
        repository_summary: Cached Repository Summary (if available).
        markdown: Rendered Markdown output.
        source_count: Number of source memories used.
        dataset: Dataset name(s) searched.
    """

    task: str
    objective: str
    sections: list[PackageSection] = field(default_factory=list)
    references: list[PackageReference] = field(default_factory=list)
    metadata: PackageMetadata | None = None
    repository_summary: RepositorySummary | None = None
    markdown: str = ""
    source_count: int = 0
    dataset: str = ""

    @property
    def section_count(self) -> int:
        """Number of sections in the package."""
        return len(self.sections)

    @property
    def token_estimate(self) -> int:
        """Estimated token count.

        Uses metadata estimate when available, falls back to
        character-based approximation (1 token ~ 4 chars).
        """
        if self.metadata:
            return self.metadata.estimated_tokens
        return len(self.markdown) // 4
