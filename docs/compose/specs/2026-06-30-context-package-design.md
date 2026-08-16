# RE:Track Context Package Specification

## Status

Target Architecture Specification

---

## 1. Executive Summary

RE:Track generates two complementary artifacts from indexed repository memory:

**Artifact A — Repository Summary**: A structured, cached knowledge model of global repository facts. Generated after indexing. Regenerated only on re-index. Contains stable information: project purpose, architecture, technologies, conventions, repository structure, key components.

**Artifact B — Context Package**: A task-specific briefing assembled per user query. Combines the Repository Summary with relevant retrieved memories, implementation guidance, and traceable references. This is what gets sent to the coding LLM.

### Design Principles

- **Task-driven progressive refinement** — Context flows from user objective down to exact implementation details. Each level appears only if it contributes to the current task.
- **Deterministic core** — Given identical repository state, retrieval config, and query, the pipeline produces identical output. Future optional LLM-assisted stages are enhancements, not core behavior.
- **Structured over prose** — The pipeline operates on typed fact objects. Markdown is always the final rendering step, never an intermediate representation.
- **Executable facts are sacred** — File paths, symbol names, API signatures, config keys, and command names are never modified by compression or summarization.
- **Success definition** — A Context Package is successful if a competent coding LLM can complete the requested task without requiring additional repository exploration in most cases.

---

## [S2] Repository Summary

### Purpose

Captures stable, global repository knowledge that applies across all tasks. Avoids re-retrieving the same architectural and structural information for every query.

### Lifecycle

```
Repository
    ↓
Index (IndexingService)
    ↓
Extract Stable Facts (post-index analysis)
    ↓
RepositorySummary (Structured Model)
    ↓
Cache (invalidated on re-index)
    ↓
Render on Demand (Markdown / JSON / UI)
```

### Structured Model

```python
@dataclass
class RepositorySummary:
    version: str                          # Summary schema version
    repository_fingerprint: str           # Hash of indexed content
    generated_at: str                     # ISO timestamp
    indexed_commit: str | None            # Git commit if available

    project_purpose: str                  # What and why (50-100 tokens)
    technology_stack: TechnologyStack     # Languages, frameworks, DBs, deps
    repository_map: list[DirectoryEntry]  # Top-level dirs with responsibilities
    architecture: ArchitectureInfo       # Layers, patterns, service boundaries
    key_components: list[ComponentInfo]   # Major components and relationships
    entry_points: list[EntryPoint]        # CLI, API, startup files
    public_apis: list[APIInfo]            # Public interfaces, endpoints, contracts
    coding_conventions: ConventionInfo    # Naming, formatting, patterns
    domain_vocabulary: dict[str, str]     # Repository-specific terminology
```

### Sections

| Field | Content | Target Tokens |
|-------|---------|---------------|
| Project Purpose | One-paragraph description | 50-100 |
| Technology Stack | Languages, frameworks, databases, dependencies | 50-100 |
| Repository Map | Top-level directories with one-line responsibilities | 100-200 |
| Architecture | Layers, patterns, service boundaries, major flows | 100-200 |
| Key Components | Important services/classes, responsibilities, relationships | 100-200 |
| Entry Points | Main application, CLI, API entry points | 50-100 |
| Public APIs | Interfaces, commands, endpoints, contracts | 50-100 |
| Coding Conventions | Naming, formatting, project-specific patterns | 50-100 |
| Domain Vocabulary | Repository-specific terminology and concepts | 50-100 |

**Total target: 500-1000 tokens** (soft target, enforced by Budget Manager)

### Generation

Generated immediately after `IndexingService.index_repository()` completes. Does not depend on `improve()`. Uses indexed file metadata, directory structure, and content analysis to extract stable facts.

### Cache Invalidation

- Re-index triggers regeneration
- Repository fingerprint (hash of indexed file paths + sizes) used for staleness detection
- Manual regeneration available via API command

---

## [S3] Context Package

### Purpose

A task-specific briefing that gives a coding LLM everything needed to understand and complete a development task without additional repository exploration.

### Information Hierarchy (Internal)

Task → Repository Context → Architectural Context → Component Context → Implementation Context → Action Guidance → References

This hierarchy describes how information is discovered and refined internally. The Markdown output is optimized for readability and may merge or reorder sections.

### Output Layout (External)

```
# Task
# Objective
# Repository Context
# Relevant Files
# Relevant Symbols
# Architecture
# Existing APIs
# Dependencies
# Previous Decisions
# Coding Conventions
# Implementation Notes
# Constraints
# Suggested Starting Point
# References
```

**Sections are optional.** Only include sections that contain useful information. Four strong sections beat fourteen empty ones.

### Section Definitions

Each section specifies its source, processing pipeline, and output format.

#### Task
- **Source**: User input
- **Processing**: None (verbatim)
- **Output**: Markdown paragraph
- **Priority**: Critical (never removed)

#### Objective
- **Source**: Derived from task via pattern matching
- **Processing**: Extract desired outcome and implicit acceptance criteria
- **Output**: Markdown paragraph
- **Priority**: Critical

#### Repository Context
- **Source**: Repository Summary (rendered)
- **Processing**: Render structured model to Markdown
- **Output**: Markdown sections
- **Priority**: High

#### Relevant Files
- **Source**: Cognee Recall
- **Processing**: Ranking → Deduplication → File extraction
- **Output**: Markdown bullets with `why` annotation
- **Priority**: Critical

#### Relevant Symbols
- **Source**: Cognee Recall
- **Processing**: Ranking → Deduplication → Symbol extraction
- **Output**: Markdown table (name, type, location, purpose)
- **Priority**: Medium

#### Architecture
- **Source**: Cognee Recall + Repository Summary
- **Processing**: Merge architectural memories with stable architecture info
- **Output**: Markdown prose
- **Priority**: High

#### Existing APIs
- **Source**: Cognee Recall
- **Processing**: Filter for API-related memories → rank
- **Output**: Markdown list with signatures
- **Priority**: Medium

#### Dependencies
- **Source**: Cognee Recall
- **Processing**: Extract component relationships
- **Output**: Markdown list
- **Priority**: Low

#### Previous Decisions
- **Source**: Cognee Recall
- **Processing**: Filter for decision/rationale keywords → rank
- **Output**: Markdown list with rationale
- **Priority**: Medium

#### Coding Conventions
- **Source**: Repository Summary + Cognee Recall
- **Processing**: Filter conventions relevant to current task
- **Output**: Markdown bullets
- **Priority**: Low

#### Implementation Notes
- **Source**: Cognee Recall
- **Processing**: Extract factual implementation details → compress
- **Output**: Markdown bullets (no speculation, facts only)
- **Priority**: High

#### Constraints
- **Source**: Cognee Recall
- **Processing**: Extract assumptions, invariants, limitations
- **Output**: Markdown list
- **Priority**: High

#### Suggested Starting Point
- **Source**: Derived from ranked files + component relationships
- **Processing**: Navigation guidance only — never invents implementation
- **Output**: Markdown paragraph answering: which component first, which files, which APIs exist, what constraints apply
- **Priority**: Critical

#### References
- **Source**: All retrieval sources
- **Processing**: Format provenance chain: fact → memory node → chunk → document → repository path
- **Output**: Markdown numbered list
- **Priority**: Low (traceability, compressible)

### Package Metadata

Every Context Package includes metadata for debugging and evaluation:

```python
@dataclass
class PackageMetadata:
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
```

---

## [S4] Retrieval Pipeline

The pipeline has two phases: **Retrieval** (collecting and refining knowledge) and **Package Assembly** (building the final output).

### Phase 1: Retrieval Pipeline

```
User Query
    ↓
[1] Semantic Recall
    ↓
[2] Graph Expansion
    ↓
[3] Deduplication
    ↓
[4] Ranking
    ↓
[5] Semantic Compression
    ↓
[6] Categorization
    ↓
[7] Reference Resolution
    ↓
Structured Knowledge (list of categorized fact objects)
```

#### Stage 1 — Semantic Recall

Calls `CogneeService.recall()` with the user query.

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `top_k` | 20 | Over-retrieve to allow ranking selection |
| `include_references` | True | Enable traceability |
| `datasets` | User-specified | Scope to relevant workspace |

Returns: raw `RecallResult` objects from Cognee.

#### Stage 2 — Graph Expansion

For each of the top-scoring results, follow one hop in the Kuzu knowledge graph to discover related entities.

**Budget constraints** (scales with repository size):

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_nodes` | 50 | Maximum entities to add |
| `max_edges` | 100 | Maximum relationships to follow |
| `max_depth` | 1 | Hop depth from seed nodes |
| `max_latency_ms` | 5000 | Time limit for expansion |

Discovery targets: parent components, dependent services, imported modules, related configurations.

#### Stage 3 — Deduplication

Structural deduplication operating on normalized text:
- Lowercase all text
- Collapse whitespace
- Merge entries referencing the same file, symbol, or concept
- Keep the entry with the highest relevance score

Deduplication count recorded for metrics.

#### Stage 4 — Ranking

Multi-factor composite scoring:

```
FinalScore = SemanticRelevance × GraphConnectivity × InformationTypeWeight × Confidence × Recency(optional)
```

| Factor | Source | Range |
|--------|--------|-------|
| SemanticRelevance | Cognee score | 0.0 - 1.0 |
| GraphConnectivity | Number of graph connections discovered | 0.0 - 1.0 |
| InformationTypeWeight | Type priority (files=1.0, arch=0.8, conventions=0.5) | 0.0 - 1.0 |
| Confidence | Score presence (None → 0.5, present → 1.0) | 0.5 - 1.0 |
| Recency | Time-based decay if available | 0.0 - 1.0 |

Selection: top N results per category, where N is determined by the Budget Manager's allocation.

#### Stage 5 — Semantic Compression

Operates on **structured fact objects**, never on Markdown.

**Tier 1 — Structural (lossless)**: Remove exact duplicates, normalize formatting, merge identical references.

**Tier 2 — Semantic (low-loss)**: Merge entries describing the same concept. Summarize redundant narrative. Collapse multiple bullets about one file into a single entry with combined context.

**Tier 3 — Budget (conditional)**: Applied only when the assembled package exceeds the target budget. Removes sections by priority class.

**Preserved exactly** (never compressed or modified):
- File paths
- Symbol names (functions, classes, interfaces, methods)
- Function signatures
- API endpoints and contracts
- Configuration keys
- Environment variables
- Command names

**Compressible**: Narrative descriptions, redundant explanations, verbose bullet points.

#### Stage 6 — Categorization

Rule-based classification in priority order:

1. Explicit metadata from Cognee (e.g., `kind="file"`)
2. Semantic type from Cognee recall
3. File extension detection
4. Keyword matching (architecture, API, convention, decision keywords)
5. Fallback to general knowledge

Results classified into section types matching the Context Package sections.

#### Stage 7 — Reference Resolution (Lightweight MVP)

Formats existing Cognee reference metadata into structured citations.

Each reference includes:
- **Type**: file | symbol | memory_node | documentation | directory
- **Path**: Repository-relative path or memory identifier
- **Section**: Where in the source this fact appears
- **Score**: Relevance score from retrieval
- **Provenance chain**: fact → memory node → chunk → document → repository path

Interface designed for future upgrade to symbol-level and AST-aware resolution without pipeline redesign.

### Phase 2: Package Assembly

```
Structured Knowledge (from Retrieval Pipeline)
    ↓
[1] Package Builder
    ↓
[2] Budget Manager
    ↓
[3] Validation
    ↓
[4] Renderer
    ↓
Context Package (Markdown + metadata)
```

#### Package Builder

Decides what information belongs in the final package:
- Merges Repository Summary with retrieved knowledge
- Assigns each fact to a section
- Preserves section optionality (empty sections are dropped)

#### Budget Manager

Soft-target budget enforcement using priority classes:

| Class | Sections | Behavior when over budget |
|-------|----------|--------------------------|
| Critical | Task, Objective, Relevant Files, Suggested Starting Point | Never removed |
| High | Architecture, Implementation Notes, Constraints | Compress content, never remove |
| Medium | Symbols, APIs, Previous Decisions | Compress, then remove if still over |
| Low | Dependencies, Coding Conventions, References | Remove first |

Overall target: 2000-4000 tokens. Budget Manager allocates dynamically based on available content and priority classes.

#### Validation

Before rendering, verify:
- Required sections present (Task, Objective)
- No duplicate references
- Budget satisfied (or Critical sections preserved)
- All references point to valid sources
- Executable facts unmodified

#### Renderer

Generates Markdown from structured package data. The renderer is format-agnostic — the same structured package can be rendered as Markdown, JSON, or displayed in UI.

---

## [S5] Compression Strategy

See [S4] Stage 5 for full details. Summary:

| Tier | Type | Loss Level | Trigger |
|------|------|------------|---------|
| Structural | Dedup, normalize, merge identical | Lossless | Always |
| Semantic | Merge facts, summarize narrative | Low-loss | Always |
| Budget | Remove low-priority sections | Lossy | Only when over target |

**Invariant**: Executable facts (paths, names, signatures, configs) are never modified by any compression tier.

---

## [S6] Quality Metrics

### Structural Metrics (Automated)

| Metric | Description | Target |
|--------|-------------|--------|
| Coverage | Percentage of query-relevant facts present in package | > 80% |
| Token Efficiency | Useful information per token (coverage / total tokens) | > 0.7 |
| Duplicate Rate | Percentage of content that is duplicated | < 5% |
| Compression Ratio | Input tokens / output tokens | 1.5 - 3.0 |
| Reference Validity | Percentage of references pointing to real sources | 100% |
| Section Utilization | Percentage of included sections that contain content | > 70% |

### Quality Dimensions (LLM-Assessed)

| Dimension | Description | Scale |
|-----------|-------------|-------|
| Relevance | How well does the package address the specific task? | 1-5 |
| Organization | Is information logically structured and easy to navigate? | 1-5 |
| Compactness | Is the package concise without losing critical information? | 1-5 |
| Task Readiness | Can an LLM start implementation immediately? | 1-5 |
| Explainability | Can a human understand why each piece of information is included? | 1-5 |

### Context Delta (Comparative)

Measures practical value by comparing LLM performance with and without the Context Package:

```
ContextDelta = Score(with_package) - Score(without_package)
```

Evaluated on repository-specific questions where the answer requires project knowledge. A positive ContextDelta means the package improves LLM understanding.

---

## [S7] Evaluation Methodology

### Three-Layer Evaluation

**Layer 1 — Automated Structural Metrics**
Run after every package generation. Measures coverage, efficiency, duplicates, compression, reference validity. No LLM required.

**Layer 2 — Context Package Quality Scoring**
LLM-as-judge evaluates packages against predefined criteria. Uses a rubric for each quality dimension. Run periodically or on demand.

**Layer 3 — Context Delta Benchmark**
Compare LLM answers with and without the package on a set of repository-specific questions. Directly measures practical value.

### Benchmark Design

**Evaluation Questions**: 20-30 questions per repository covering:
- Architecture understanding (5-7 questions)
- File location (5-7 questions)
- API understanding (3-5 questions)
- Convention identification (3-5 questions)
- Extension point discovery (2-3 questions)

**Expected Answers**: Ground-truth answers derived from manual codebase analysis.

**Scoring**:
- Binary correct/incorrect for factual questions
- Partial credit for multi-part questions
- LLM-as-judge for open-ended questions using rubric

**Success Criteria**:
- Structural metrics pass all targets
- Quality dimensions average > 3.5/5
- Context Delta > 0.3 (measurable improvement over no-context baseline)
- 16/20+ factual questions answered correctly (matches existing test_4 benchmark)

---

## [S8] Data Models

### Core Types

```python
@dataclass
class TechnologyStack:
    languages: list[str]
    frameworks: list[str]
    databases: list[str]
    dependencies: list[str]

@dataclass
class DirectoryEntry:
    path: str
    description: str

@dataclass
class ArchitectureInfo:
    pattern: str                    # e.g., "layered", "microservice"
    layers: list[str]
    boundaries: list[str]
    major_flows: list[str]

@dataclass
class ComponentInfo:
    name: str
    responsibilities: str
    relationships: list[str]

@dataclass
class EntryPoint:
    name: str
    path: str
    type: str                       # "cli" | "api" | "startup"

@dataclass
class APIInfo:
    name: str
    signature: str
    description: str

@dataclass
class ConventionInfo:
    naming: str
    formatting: str
    patterns: list[str]

@dataclass
class RepositorySummary:
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

@dataclass
class PackageReference:
    ref_type: str                   # "file" | "symbol" | "memory" | "doc" | "dir"
    path: str
    section: str | None
    score: float
    provenance: list[str]           # fact → node → chunk → doc → repo path

@dataclass
class PackageSection:
    section_type: str
    heading: str
    content: str                    # Markdown content
    priority: int                   # 1-5 (5 = critical)
    source_sections: list[str]      # Which info hierarchy levels contributed
    reference_count: int

@dataclass
class PackageMetadata:
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

@dataclass
class ContextPackage:
    task: str
    objective: str
    sections: list[PackageSection]
    references: list[PackageReference]
    metadata: PackageMetadata
    repository_summary: RepositorySummary
    markdown: str                   # Rendered output

    @property
    def section_count(self) -> int:
        return len(self.sections)

    @property
    def token_estimate(self) -> int:
        return self.metadata.estimated_tokens
```

---

## [S9] Interface Contracts

### Pipeline Stages (Replaceable)

Each stage exposes a stable interface for future replacement:

```python
class RecallProvider(Protocol):
    async def recall(self, query: str, datasets: list[str], top_k: int) -> list[RecallResult]: ...

class ExpansionStrategy(Protocol):
    async def expand(self, seeds: list[RecallResult], budget: ExpansionBudget) -> list[RecallResult]: ...

class RankingStrategy(Protocol):
    def rank(self, results: list[RecallResult]) -> list[RecallResult]: ...

class CompressionStrategy(Protocol):
    def compress(self, facts: list[FactObject], budget: int) -> list[FactObject]: ...

class CategorizationStrategy(Protocol):
    def categorize(self, facts: list[FactObject]) -> dict[str, list[FactObject]]: ...

class ReferenceResolver(Protocol):
    def resolve(self, facts: list[FactObject]) -> list[PackageReference]: ...

class Renderer(Protocol):
    def render(self, package: StructuredPackage) -> str: ...
```

### Deferred Types

The following types are referenced in protocols but not yet defined. They will be specified when their corresponding stages are implemented:

- `FactObject` — intermediate representation for compression and categorization stages. Will be defined when Stage 5 (Compression) is implemented.
- `ExpansionBudget` — budget constraints for graph expansion. Will be defined when Stage 2 (Graph Expansion) is implemented.
- `StructuredPackage` — intermediate representation before rendering. Will be defined when the Package Builder is implemented.

### Future Extension Points

Reserved slots for optional enhancement stages (not MVP):

- AST-aware symbol expansion
- Call graph expansion
- Semantic summarization (LLM-assisted)
- Cross-repository retrieval
- Git history integration

These remain optional plugins, not core pipeline requirements.

---

## [S10] Implementation Scope

### MVP (Stages 1-6 fully functional)

- Semantic Recall via CogneeService
- Deduplication (structural)
- Ranking (multi-factor)
- Semantic Compression (structural + semantic tiers)
- Categorization (rule-based)
- Reference Resolution (lightweight, formats existing Cognee references)
- Package Builder (section assembly)
- Budget Manager (priority classes)
- Validation
- Markdown Renderer
- Repository Summary generation
- Package metadata

### Not MVP

- Graph Expansion (Stage 2) — implement after MVP pipeline is validated
- Budget Compression tier (Tier 3) — implement when package sizes are measured
- LLM-as-judge evaluation — implement for demo/hackathon
- Context Delta benchmark — implement for demo/hackathon
- JSON/UI/MCP renderers — implement after Markdown renderer is validated

### Dependencies

- CogneeService.recall() with `include_references=True`
- Repository Summary generation (new capability)
- `FactObject` intermediate representation (new data model)
- Budget Manager (new component)
- Package Validator (new component)
