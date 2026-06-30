# Context Package Specification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent (recommended) or compose:execute to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Context Package specification, transforming the existing basic ContextService into a full pipeline with Repository Summary, structured fact processing, budget management, and Markdown rendering.

**Architecture:** Two-phase pipeline (Retrieval + Package Assembly) operating on structured fact objects. Repository Summary generated after indexing as a cached knowledge model. Context Package assembled per query by merging summary with retrieved memories.

**Tech Stack:** Python 3.13, dataclasses, pytest, existing CogneeService/IndexingService

## Global Constraints

- Python 3.13+ (uses `X | None` union syntax)
- All Cognee interactions through CogneeService only
- No LLM calls in the pipeline (deterministic core)
- TDD: write failing test first, then implement
- Each task commits independently
- Existing tests must continue passing (run `pytest backend/tests/ -v` after each task)

## Post-Task Verification Gate

After completing EVERY task, the agent must answer these four questions before marking it done:

1. **Does this still conform to the specification?** — Check the relevant `[Sn]` section in `docs/compose/specs/2026-06-30-context-package-design.md`. If the implementation diverges, fix it or update the spec.
2. **Does it introduce unnecessary complexity?** — If the code exceeds 3x the apparent complexity of the task, stop and simplify.
3. **Are existing tests still passing?** — Run `pytest backend/tests/ -v`. If any test fails, fix before proceeding.
4. **Can this be demonstrated immediately?** — Show the component working. A test passing IS the demonstration for isolated components. For integrated components, run the actual pipeline.

If any answer is "no", fix the issue before moving to the next task.

---

## File Structure

```
backend/app/models/
    responses.py          # MODIFY — add new data models

backend/app/services/
    context_service.py    # REWRITE — full pipeline implementation
    repository_summary.py # CREATE — Repository Summary generator
    pipeline/
        __init__.py       # CREATE — pipeline package
        dedup.py          # CREATE — deduplication stage
        ranking.py        # CREATE — ranking stage
        compression.py    # CREATE — compression stage
        categorization.py # CREATE — categorization stage
        references.py     # CREATE — reference resolution stage
    budget_manager.py     # CREATE — budget enforcement
    package_builder.py    # CREATE — assembles final package
    renderer.py           # CREATE — Markdown renderer

backend/tests/
    test_models.py        # CREATE
    test_repository_summary.py # CREATE
    test_dedup.py         # CREATE
    test_ranking.py       # CREATE
    test_compression.py   # CREATE
    test_categorization.py # CREATE
    test_references.py    # CREATE
    test_budget_manager.py # CREATE
    test_package_builder.py # CREATE
    test_renderer.py      # CREATE
    test_context_service_v2.py # CREATE
```

---

# Milestone 1 — Core Data Model

**Result:** You can construct and validate package objects.

---

### Task 1.1: Repository Summary Models

**Covers:** [S2, S8]

**Files:**
- Modify: `backend/app/models/responses.py`
- Create: `backend/tests/test_models.py`

**Interfaces:**
- Consumes: nothing (new types)
- Produces: `TechnologyStack`, `DirectoryEntry`, `ArchitectureInfo`, `ComponentInfo`, `EntryPoint`, `APIInfo`, `ConventionInfo`, `RepositorySummary`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_models.py
"""Tests for Context Package data models."""

from app.models.responses import (
    ArchitectureInfo,
    APIInfo,
    ComponentInfo,
    ConventionInfo,
    DirectoryEntry,
    EntryPoint,
    RepositorySummary,
    TechnologyStack,
)


def test_technology_stack_construction():
    stack = TechnologyStack(
        languages=["Python", "TypeScript"],
        frameworks=["FastAPI", "React"],
        databases=["LanceDB", "Kuzu"],
        dependencies=["cognee", "pydantic"],
    )
    assert stack.languages == ["Python", "TypeScript"]
    assert len(stack.frameworks) == 2


def test_directory_entry_construction():
    entry = DirectoryEntry(path="backend/app/services", description="Backend services")
    assert entry.path == "backend/app/services"


def test_architecture_info_construction():
    arch = ArchitectureInfo(
        pattern="layered",
        layers=["CLI", "API", "Services"],
        boundaries=["Backend/Frontend via Tauri IPC"],
        major_flows=["Index → Recall → Package"],
    )
    assert arch.pattern == "layered"
    assert len(arch.layers) == 3


def test_component_info_construction():
    comp = ComponentInfo(
        name="CogneeService",
        responsibilities="Thin wrapper around Cognee APIs",
        relationships=["Used by IndexingService"],
    )
    assert comp.name == "CogneeService"


def test_entry_point_construction():
    ep = EntryPoint(name="cli", path="backend/andescontext.py", type="cli")
    assert ep.type == "cli"


def test_api_info_construction():
    api = APIInfo(name="recall", signature="recall(query, datasets, top_k)", description="Retrieve memories")
    assert api.name == "recall"


def test_convention_info_construction():
    conv = ConventionInfo(naming="snake_case", formatting="black", patterns=["service-per-domain"])
    assert conv.naming == "snake_case"


def test_repository_summary_construction():
    summary = RepositorySummary(
        version="1.0",
        repository_fingerprint="abc123",
        generated_at="2026-06-30T00:00:00Z",
        indexed_commit=None,
        project_purpose="Local-first AI memory",
        technology_stack=TechnologyStack(["Python"], [], [], []),
        repository_map=[],
        architecture=ArchitectureInfo("layered", [], [], []),
        key_components=[],
        entry_points=[],
        public_apis=[],
        coding_conventions=ConventionInfo("", "", []),
        domain_vocabulary={},
    )
    assert summary.version == "1.0"
    assert summary.indexed_commit is None


def test_repository_summary_frozen():
    summary = RepositorySummary(
        version="1.0", repository_fingerprint="abc", generated_at="2026-01-01T00:00:00Z",
        indexed_commit=None, project_purpose="test",
        technology_stack=TechnologyStack([], [], [], []),
        repository_map=[], architecture=ArchitectureInfo("", [], [], []),
        key_components=[], entry_points=[], public_apis=[],
        coding_conventions=ConventionInfo("", "", []), domain_vocabulary={},
    )
    try:
        summary.version = "2.0"
        assert False, "Should be frozen"
    except AttributeError:
        pass
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_models.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement data models**

Add to `backend/app/models/responses.py` after existing `SectionType` enum:

```python
@dataclass(frozen=True)
class TechnologyStack:
    languages: list[str]
    frameworks: list[str]
    databases: list[str]
    dependencies: list[str]


@dataclass(frozen=True)
class DirectoryEntry:
    path: str
    description: str


@dataclass(frozen=True)
class ArchitectureInfo:
    pattern: str
    layers: list[str]
    boundaries: list[str]
    major_flows: list[str]


@dataclass(frozen=True)
class ComponentInfo:
    name: str
    responsibilities: str
    relationships: list[str]


@dataclass(frozen=True)
class EntryPoint:
    name: str
    path: str
    type: str


@dataclass(frozen=True)
class APIInfo:
    name: str
    signature: str
    description: str


@dataclass(frozen=True)
class ConventionInfo:
    naming: str
    formatting: str
    patterns: list[str]


@dataclass(frozen=True)
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_models.py -v`
Expected: All 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/responses.py backend/tests/test_models.py
git commit -m "feat(models): add Repository Summary data models"
```

- [ ] **Step 6: Post-task verification**

Answer the four verification questions. Run `pytest backend/tests/ -v` to confirm no regressions.

---

### Task 1.2: Context Package Models

**Covers:** [S3, S8]

**Files:**
- Modify: `backend/app/models/responses.py`
- Modify: `backend/tests/test_models.py`

**Interfaces:**
- Consumes: existing `SectionType`
- Produces: `PackageReference`, `PackageSection` (updated), `PackageMetadata`, `ContextPackage` (updated)

- [ ] **Step 1: Write failing tests**

Add to `backend/tests/test_models.py`:

```python
from app.models.responses import PackageMetadata, PackageReference, PackageSection


def test_package_reference_construction():
    ref = PackageReference(
        ref_type="file",
        path="backend/app/services/cognee_service.py",
        section="Services",
        score=0.95,
        provenance=["memory_node_1", "chunk_2"],
    )
    assert ref.ref_type == "file"
    assert ref.score == 0.95
    assert len(ref.provenance) == 2


def test_package_reference_frozen():
    ref = PackageReference("file", "test.py", None, 0.5, [])
    try:
        ref.score = 1.0
        assert False, "Should be frozen"
    except AttributeError:
        pass


def test_package_section_with_priority():
    section = PackageSection(
        section_type="files",
        heading="Relevant Files",
        content="- `backend/app/services/cognee_service.py`",
        priority=5,
        source_sections=["Component Context"],
        reference_count=1,
    )
    assert section.priority == 5
    assert section.reference_count == 1


def test_package_section_defaults():
    section = PackageSection(section_type="knowledge", heading="Notes", content="text")
    assert section.priority == 3
    assert section.source_sections == []


def test_package_metadata_construction():
    meta = PackageMetadata(
        package_version="1.0",
        repository_summary_version="1.0",
        generated_at="2026-06-30T00:00:00Z",
        datasets_used=["workspace"],
        retrieved_memory_count=20,
        deduplicated_count=15,
        compressed_count=12,
        compression_ratio=1.67,
        estimated_tokens=2500,
        pipeline_version="1.0",
        retrieval_time_ms=5000,
        total_time_ms=8000,
    )
    assert meta.compression_ratio == 1.67
    assert meta.estimated_tokens == 2500
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_models.py::test_package_reference_construction -v`
Expected: FAIL with TypeError (wrong number of arguments)

- [ ] **Step 3: Implement updated models**

Replace existing `PackageSection` in `responses.py`:

```python
@dataclass(frozen=True)
class PackageSection:
    section_type: str
    heading: str
    content: str
    priority: int = 3
    source_sections: list[str] = field(default_factory=list)
    reference_count: int = 0
```

Add after `PackageSection`:

```python
@dataclass(frozen=True)
class PackageReference:
    ref_type: str
    path: str
    section: str | None
    score: float
    provenance: list[str]


@dataclass(frozen=True)
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

Replace existing `ContextPackage`:

```python
@dataclass(frozen=True)
class ContextPackage:
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
        return len(self.sections)

    @property
    def token_estimate(self) -> int:
        if self.metadata:
            return self.metadata.estimated_tokens
        return len(self.markdown) // 4
```

- [ ] **Step 4: Run all model tests**

Run: `cd backend && python -m pytest tests/test_models.py -v`
Expected: All 14 tests PASS

- [ ] **Step 5: Run full test suite**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All existing tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/responses.py backend/tests/test_models.py
git commit -m "feat(models): add Context Package models with priority and metadata"
```

- [ ] **Step 7: Post-task verification**

Answer the four verification questions.

---

### Task 1.3: Serialization

**Covers:** [S8]

**Files:**
- Modify: `backend/tests/test_models.py`

**Interfaces:**
- Consumes: all data models from Tasks 1.1 and 1.2
- Produces: verified construction, property access, and default values

- [ ] **Step 1: Write serialization tests**

Add to `backend/tests/test_models.py`:

```python
def test_context_package_construction():
    from app.models.responses import ContextPackage
    pkg = ContextPackage(
        task="Fix bug",
        objective="Resolve error",
        sections=[],
        references=[],
        metadata=None,
        repository_summary=None,
        markdown="# Task\n\nFix bug",
        source_count=0,
        dataset="test",
    )
    assert pkg.task == "Fix bug"
    assert pkg.section_count == 0
    assert pkg.token_estimate == 4  # len("# Task\n\nFix bug") // 4


def test_context_package_with_metadata_token_estimate():
    from app.models.responses import ContextPackage, PackageMetadata
    meta = PackageMetadata(
        package_version="1.0", repository_summary_version="1.0",
        generated_at="2026-01-01T00:00:00Z", datasets_used=[],
        retrieved_memory_count=0, deduplicated_count=0, compressed_count=0,
        compression_ratio=1.0, estimated_tokens=1500, pipeline_version="1.0",
        retrieval_time_ms=0, total_time_ms=0,
    )
    pkg = ContextPackage(task="q", objective="o", metadata=meta)
    assert pkg.token_estimate == 1500


def test_context_package_defaults():
    from app.models.responses import ContextPackage
    pkg = ContextPackage(task="q", objective="o")
    assert pkg.sections == []
    assert pkg.references == []
    assert pkg.markdown == ""
    assert pkg.source_count == 0
```

- [ ] **Step 2: Run tests**

Run: `cd backend && python -m pytest tests/test_models.py -v`
Expected: All 17 tests PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_models.py
git commit -m "test(models): add serialization and construction tests"
```

- [ ] **Step 4: Post-task verification**

**Milestone 1 Complete.** Demonstrate: run `pytest tests/test_models.py -v` — 17/17 pass.

---

# Milestone 2 — Retrieval Processing

**Result:** Cognee recall results become structured sections.

---

### Task 2.1: Deduplication

**Covers:** [S4 Stage 3]

**Files:**
- Create: `backend/app/services/pipeline/__init__.py`
- Create: `backend/app/services/pipeline/dedup.py`
- Create: `backend/tests/test_dedup.py`

**Interfaces:**
- Consumes: `list[RecallResult]`
- Produces: `list[RecallResult]` (deduplicated, highest-score kept)

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_dedup.py
"""Tests for deduplication pipeline stage."""

from app.models.responses import RecallResult
from app.services.pipeline.dedup import Deduplicator


def _make(text: str, score: float = 0.5, kind: str = "text") -> RecallResult:
    return RecallResult(kind=kind, search_type="semantic", text=text, score=score, dataset_name="test")


def test_no_duplicates():
    results = [_make("alpha", 0.9), _make("beta", 0.8)]
    assert len(Deduplicator().deduplicate(results)) == 2


def test_exact_duplicates_removed():
    results = [_make("same text", 0.9), _make("same text", 0.7)]
    out = Deduplicator().deduplicate(results)
    assert len(out) == 1
    assert out[0].score == 0.9


def test_case_insensitive():
    results = [_make("Hello World", 0.8), _make("hello world", 0.6)]
    assert len(Deduplicator().deduplicate(results)) == 1


def test_whitespace_normalization():
    results = [_make("hello  world", 0.8), _make("hello world", 0.6)]
    assert len(Deduplicator().deduplicate(results)) == 1


def test_preserves_order():
    results = [_make("c", 0.3), _make("a", 0.9), _make("b", 0.6)]
    out = Deduplicator().deduplicate(results)
    assert [r.text for r in out] == ["c", "a", "b"]


def test_empty_input():
    assert Deduplicator().deduplicate([]) == []


def test_single_item():
    result = [_make("only")]
    assert Deduplicator().deduplicate(result) == result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_dedup.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement deduplication**

```python
# backend/app/services/pipeline/__init__.py
"""Pipeline stages for Context Package generation."""

# backend/app/services/pipeline/dedup.py
"""Structural deduplication stage."""

from app.models.responses import RecallResult


class Deduplicator:
    def deduplicate(self, results: list[RecallResult]) -> list[RecallResult]:
        seen: dict[str, RecallResult] = {}
        order: list[str] = []
        for r in results:
            key = " ".join(r.text.lower().split())
            if key not in seen:
                seen[key] = r
                order.append(key)
            elif r.score > seen[key].score:
                seen[key] = r
        return [seen[k] for k in order]
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_dedup.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/pipeline/ backend/tests/test_dedup.py
git commit -m "feat(pipeline): add deduplication stage"
```

- [ ] **Step 6: Post-task verification**

---

### Task 2.2: Ranking

**Covers:** [S4 Stage 4]

**Files:**
- Create: `backend/app/services/pipeline/ranking.py`
- Create: `backend/tests/test_ranking.py`

**Interfaces:**
- Consumes: `list[RecallResult]`
- Produces: `list[RecallResult]` (re-ranked by composite score)

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_ranking.py
from app.models.responses import RecallResult
from app.services.pipeline.ranking import Ranker


def _make(text: str, score: float | None, kind: str = "text") -> RecallResult:
    return RecallResult(kind=kind, search_type="semantic", text=text, score=score or 0.0, dataset_name="test")


def test_high_score_first():
    results = [_make("low", 0.3), _make("high", 0.9)]
    assert Ranker().rank(results)[0].text == "high"


def test_none_score_ranked_lower():
    results = [_make("scored", 0.5), _make("unscored", None)]
    assert Ranker().rank(results)[0].text == "scored"


def test_file_type_boosted():
    results = [_make("note", 0.7, "text"), _make("svc.py", 0.6, "file")]
    assert Ranker().rank(results)[0].kind == "file"


def test_empty_input():
    assert Ranker().rank([]) == []


def test_single_item():
    result = [_make("only", 0.5)]
    assert Ranker().rank(result) == result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_ranking.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement ranking**

```python
# backend/app/services/pipeline/ranking.py
"""Multi-factor ranking stage."""

from app.models.responses import RecallResult

_TYPE_WEIGHTS = {"file": 1.0, "code": 0.9, "text": 0.7}


class Ranker:
    def rank(self, results: list[RecallResult]) -> list[RecallResult]:
        scored = []
        for r in results:
            semantic = r.score if r.score is not None else 0.5
            confidence = 1.0 if r.score is not None else 0.5
            type_w = _TYPE_WEIGHTS.get(r.kind, 0.7)
            scored.append((semantic * confidence * type_w, r))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored]
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_ranking.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/pipeline/ranking.py backend/tests/test_ranking.py
git commit -m "feat(pipeline): add multi-factor ranking stage"
```

- [ ] **Step 6: Post-task verification**

---

### Task 2.3: Compression

**Covers:** [S4 Stage 5, S5]

**Files:**
- Create: `backend/app/services/pipeline/compression.py`
- Create: `backend/tests/test_compression.py`

**Interfaces:**
- Consumes: `list[RecallResult]`
- Produces: `list[RecallResult]` (compressed, redundant merged)

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_compression.py
from app.models.responses import RecallResult
from app.services.pipeline.compression import Compressor


def _make(text: str) -> RecallResult:
    return RecallResult(kind="text", search_type="semantic", text=text, score=0.5, dataset_name="test")


def test_merges_redundant():
    results = [
        _make("CogneeService wraps cognee APIs"),
        _make("CogneeService is a thin wrapper around cognee APIs"),
    ]
    assert len(Compressor().compress(results)) == 1


def test_preserves_distinct():
    results = [_make("architecture is layered"), _make("use pytest for tests")]
    assert len(Compressor().compress(results)) == 2


def test_empty_input():
    assert Compressor().compress([]) == []


def test_single_item():
    result = [_make("only")]
    assert Compressor().compress(result) == result


def test_keeps_shorter_version():
    results = [
        _make("The CogneeService class wraps the cognee APIs for internal use"),
        _make("CogneeService wraps cognee APIs"),
    ]
    out = Compressor().compress(results)
    assert len(out) == 1
    assert len(out[0].text) < 60
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_compression.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement compression**

```python
# backend/app/services/pipeline/compression.py
"""Semantic compression stage."""

from app.models.responses import RecallResult


class Compressor:
    def compress(self, results: list[RecallResult]) -> list[RecallResult]:
        if not results:
            return []
        merged: list[RecallResult] = []
        used: set[int] = set()
        for i, r in enumerate(results):
            if i in used:
                continue
            best = r
            for j in range(i + 1, len(results)):
                if j in used:
                    continue
                if self._are_redundant(r.text, results[j].text):
                    used.add(j)
                    if len(results[j].text) < len(best.text):
                        best = results[j]
            merged.append(best)
            used.add(i)
        return merged

    def _are_redundant(self, a: str, b: str) -> bool:
        a_tokens = set(a.lower().split())
        b_tokens = set(b.lower().split())
        if not a_tokens or not b_tokens:
            return False
        overlap = len(a_tokens & b_tokens) / max(len(a_tokens), len(b_tokens))
        return overlap > 0.7
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_compression.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/pipeline/compression.py backend/tests/test_compression.py
git commit -m "feat(pipeline): add semantic compression stage"
```

- [ ] **Step 6: Post-task verification**

---

### Task 2.4: Categorization

**Covers:** [S4 Stage 6]

**Files:**
- Create: `backend/app/services/pipeline/categorization.py`
- Create: `backend/tests/test_categorization.py`

**Interfaces:**
- Consumes: `list[RecallResult]`
- Produces: `dict[str, list[RecallResult]]` (section_type → results)

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_categorization.py
from app.models.responses import RecallResult
from app.services.pipeline.categorization import Categorizer


def _make(text: str, kind: str = "text") -> RecallResult:
    return RecallResult(kind=kind, search_type="semantic", text=text, score=0.5, dataset_name="test")


def test_file_categorized():
    assert "files" in Categorizer().categorize([_make("svc.py", "file")])


def test_architecture_keyword():
    assert "architecture" in Categorizer().categorize([_make("The layered architecture uses service boundaries")])


def test_api_keyword():
    assert "apis" in Categorizer().categorize([_make("The REST endpoint handles POST requests")])


def test_convention_keyword():
    assert "conventions" in Categorizer().categorize([_make("Follow snake_case naming convention")])


def test_decision_keyword():
    assert "decisions" in Categorizer().categorize([_make("We chose Cognee because of hybrid retrieval")])


def test_default_to_knowledge():
    assert "knowledge" in Categorizer().categorize([_make("Some random text")])


def test_empty_input():
    assert Categorizer().categorize([]) == {}


def test_multiple_categories():
    results = [_make("svc.py", "file"), _make("architecture is layered"), _use("follow convention")]
    cats = Categorizer().categorize(results)
    assert len(cats) >= 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_categorization.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement categorization**

```python
# backend/app/services/pipeline/categorization.py
"""Rule-based categorization stage."""

from app.models.responses import RecallResult

_ARCH_KW = frozenset({"architecture", "design", "pattern", "structure", "layer", "module", "component", "service", "pipeline", "workflow"})
_API_KW = frozenset({"api", "endpoint", "route", "interface", "contract", "schema", "request", "response", "http", "rest"})
_CONV_KW = frozenset({"convention", "style", "format", "linting", "naming", "standard", "guideline"})
_DEC_KW = frozenset({"decision", "rationale", "tradeoff", "chosen", "selected", "alternative", "rejected"})


class Categorizer:
    def categorize(self, results: list[RecallResult]) -> dict[str, list[RecallResult]]:
        cats: dict[str, list[RecallResult]] = {}
        for r in results:
            section = self._classify(r)
            cats.setdefault(section, []).append(r)
        return cats

    def _classify(self, r: RecallResult) -> str:
        kind = r.kind.lower() if r.kind else ""
        text = r.text.lower()
        if kind == "file":
            return "files"
        if any(kw in text for kw in _ARCH_KW):
            return "architecture"
        if any(kw in text for kw in _API_KW):
            return "apis"
        if any(kw in text for kw in _CONV_KW):
            return "conventions"
        if any(kw in text for kw in _DEC_KW):
            return "decisions"
        return "knowledge"
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_categorization.py -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/pipeline/categorization.py backend/tests/test_categorization.py
git commit -m "feat(pipeline): add rule-based categorization stage"
```

- [ ] **Step 6: Post-task verification**

---

### Task 2.5: Reference Resolution

**Covers:** [S4 Stage 7]

**Files:**
- Create: `backend/app/services/pipeline/references.py`
- Create: `backend/tests/test_references.py`

**Interfaces:**
- Consumes: `list[RecallResult]`
- Produces: `list[PackageReference]`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_references.py
from app.models.responses import RecallResult
from app.services.pipeline.references import ReferenceResolver


def _make(text: str, kind: str = "text", score: float = 0.5) -> RecallResult:
    return RecallResult(kind=kind, search_type="semantic", text=text, score=score, dataset_name="test")


def test_file_reference():
    refs = ReferenceResolver().resolve([_make("backend/app/services/cognee.py", "file", 0.9)])
    assert refs[0].ref_type == "file"
    assert "cognee.py" in refs[0].path


def test_memory_reference():
    refs = ReferenceResolver().resolve([_make("The architecture uses layered patterns")])
    assert refs[0].ref_type == "memory"


def test_preserves_score():
    refs = ReferenceResolver().resolve([_make("test.py", "file", 0.85)])
    assert refs[0].score == 0.85


def test_empty_input():
    assert ReferenceResolver().resolve([]) == []


def test_provenance_chain():
    refs = ReferenceResolver().resolve([_make("service.py", "file")])
    assert len(refs[0].provenance) > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_references.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement reference resolution**

```python
# backend/app/services/pipeline/references.py
"""Lightweight reference resolution."""

import re
from app.models.responses import PackageReference, RecallResult


class ReferenceResolver:
    def resolve(self, results: list[RecallResult]) -> list[PackageReference]:
        return [ref for r in results if (ref := self._resolve_one(r)) is not None]

    def _resolve_one(self, r: RecallResult) -> PackageReference | None:
        text = r.text.strip()
        if not text:
            return None
        kind = r.kind.lower() if r.kind else ""
        if kind == "file" or re.search(r"[/\w.-]+\.\w+", text):
            ref_type, path = "file", text
        else:
            ref_type, path = "memory", text[:100]
        return PackageReference(ref_type=ref_type, path=path, section=None, score=r.score, provenance=[f"recall:{r.dataset_name}", f"kind:{kind}"])
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_references.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/pipeline/references.py backend/tests/test_references.py
git commit -m "feat(pipeline): add reference resolution stage"
```

- [ ] **Step 6: Post-task verification**

**Milestone 2 Complete.** Demonstrate: run all pipeline tests — `pytest tests/test_dedup.py tests/test_ranking.py tests/test_compression.py tests/test_categorization.py tests/test_references.py -v` — 30/30 pass.

---

# Milestone 3 — Package Generation

**Result:** One query produces a complete Context Package.

---

### Task 3.1: Budget Manager

**Covers:** [S4 Budget Manager]

**Files:**
- Create: `backend/app/services/budget_manager.py`
- Create: `backend/tests/test_budget_manager.py`

**Interfaces:**
- Consumes: `list[PackageSection]`, target token budget
- Produces: `list[PackageSection]` (trimmed to fit)

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_budget_manager.py
from app.models.responses import PackageSection
from app.services.budget_manager import BudgetManager


def _sec(type_: str, content: str, priority: int) -> PackageSection:
    return PackageSection(section_type=type_, heading=type_.title(), content=content, priority=priority)


def test_under_budget_preserves_all():
    sections = [_sec("task", "Do something", 5), _sec("files", "- file.py", 5)]
    assert len(BudgetManager(target_tokens=5000).apply(sections)) == 2


def test_over_budget_removes_low_priority():
    sections = [_sec("task", "x" * 100, 5), _sec("references", "y" * 5000, 1)]
    result = BudgetManager(target_tokens=500).apply(sections)
    types = [s.section_type for s in result]
    assert "references" not in types
    assert "task" in types


def test_critical_never_removed():
    sections = [
        _sec("task", "x" * 100, 5),
        _sec("objective", "y" * 100, 5),
        _sec("files", "z" * 100, 5),
        _sec("refs", "w" * 10000, 1),
    ]
    result = BudgetManager(target_tokens=200).apply(sections)
    types = [s.section_type for s in result]
    assert "task" in types
    assert "objective" in types
    assert "files" in types


def test_empty_input():
    assert BudgetManager(target_tokens=1000).apply([]) == []


def test_compression_ratio_recorded():
    bm = BudgetManager(target_tokens=50)
    bm.apply([_sec("task", "x" * 100, 5)])
    assert bm.last_compression_ratio > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_budget_manager.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement Budget Manager**

```python
# backend/app/services/budget_manager.py
"""Budget enforcement for Context Package sections."""

from app.models.responses import PackageSection

_CRITICAL = {5}
_HIGH = {4}
_MEDIUM = {3}
_LOW = {1, 2}
_CHARS_PER_TOKEN = 4


class BudgetManager:
    def __init__(self, target_tokens: int = 3000) -> None:
        self._target = target_tokens
        self.last_compression_ratio: float = 1.0

    def apply(self, sections: list[PackageSection]) -> list[PackageSection]:
        if not sections:
            return []
        total = self._tokens(sections)
        if total <= self._target:
            self.last_compression_ratio = 1.0
            return sections
        result = list(sections)
        for priorities in [_LOW, _MEDIUM]:
            result = [s for s in result if s.priority not in priorities]
            if self._tokens(result) <= self._target:
                return self._finalize(result, total)
        result = self._compress(result, _HIGH, 0.5)
        return self._finalize(result, total)

    def _tokens(self, sections: list[PackageSection]) -> int:
        return sum(len(s.content) for s in sections) // _CHARS_PER_TOKEN

    def _compress(self, sections: list[PackageSection], priorities: set[int], ratio: float) -> list[PackageSection]:
        return [
            PackageSection(s.section_type, s.heading, s.content[: int(len(s.content) * ratio)], s.priority, s.source_sections, s.reference_count)
            if s.priority in priorities else s
            for s in sections
        ]

    def _finalize(self, sections: list[PackageSection], original: int) -> list[PackageSection]:
        self.last_compression_ratio = original / max(self._tokens(sections), 1)
        return sections
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_budget_manager.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/budget_manager.py backend/tests/test_budget_manager.py
git commit -m "feat: add Budget Manager for token enforcement"
```

- [ ] **Step 6: Post-task verification**

---

### Task 3.2: Markdown Renderer

**Covers:** [S4 Renderer]

**Files:**
- Create: `backend/app/services/renderer.py`
- Create: `backend/tests/test_renderer.py`

**Interfaces:**
- Consumes: task, objective, `list[PackageSection]`, `list[PackageReference]`, `RepositorySummary | None`
- Produces: Markdown string

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_renderer.py
from app.models.responses import PackageReference, PackageSection, RepositorySummary
from app.services.renderer import MarkdownRenderer


def _sec(type_: str, heading: str, content: str) -> PackageSection:
    return PackageSection(section_type=type_, heading=heading, content=content)


def test_renders_task():
    md = MarkdownRenderer().render("Fix bug", "Resolve error", [], [], None)
    assert "# Task" in md and "Fix bug" in md


def test_renders_objective():
    md = MarkdownRenderer().render("t", "Fix auth", [], [], None)
    assert "# Objective" in md and "Fix auth" in md


def test_renders_sections():
    md = MarkdownRenderer().render("t", "o", [_sec("files", "Files", "- `app.py`")], [], None)
    assert "# Files" in md and "app.py" in md


def test_renders_references():
    refs = [PackageReference("file", "app.py", None, 0.9, [])]
    md = MarkdownRenderer().render("t", "o", [], refs, None)
    assert "# References" in md and "app.py" in md


def test_skips_empty_sections():
    md = MarkdownRenderer().render("t", "o", [_sec("empty", "Empty", "")], [], None)
    assert "Empty" not in md


def test_renders_repository_summary():
    summary = RepositorySummary(
        version="1.0", repository_fingerprint="abc", generated_at="2026-01-01T00:00:00Z",
        indexed_commit=None, project_purpose="Test project", technology_stack=None,
        repository_map=[], architecture=None, key_components=[], entry_points=[],
        public_apis=[], coding_conventions=None, domain_vocabulary={},
    )
    md = MarkdownRenderer().render("t", "o", [], [], summary)
    assert "# Repository Context" in md and "Test project" in md


def test_empty_input():
    md = MarkdownRenderer().render("", "", [], [], None)
    assert "# Task" in md
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_renderer.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement Markdown Renderer**

```python
# backend/app/services/renderer.py
"""Markdown renderer for Context Packages."""

from app.models.responses import PackageReference, PackageSection, RepositorySummary


class MarkdownRenderer:
    def render(self, task: str, objective: str, sections: list[PackageSection], references: list[PackageReference], summary: RepositorySummary | None) -> str:
        parts = [f"# Task\n\n{task}"]
        if objective:
            parts.append(f"# Objective\n\n{objective}")
        if summary:
            md = self._render_summary(summary)
            if md:
                parts.append(f"# Repository Context\n\n{md}")
        for s in sections:
            if s.content.strip():
                parts.append(f"# {s.heading}\n\n{s.content}")
        if references:
            refs = "\n".join(f"{i}. [{r.ref_type}] `{r.path}` (score: {r.score:.2f})" for i, r in enumerate(references, 1))
            parts.append(f"# References\n\n{refs}")
        return "\n\n---\n\n".join(parts)

    def _render_summary(self, s: RepositorySummary) -> str:
        parts = []
        if s.project_purpose:
            parts.append(f"**Purpose**: {s.project_purpose}")
        if s.technology_stack:
            tech = s.technology_stack
            items = []
            if tech.languages: items.append(f"Languages: {', '.join(tech.languages)}")
            if tech.frameworks: items.append(f"Frameworks: {', '.join(tech.frameworks)}")
            if items: parts.append("**Technology**: " + " | ".join(items))
        if s.repository_map:
            dirs = "\n".join(f"- `{e.path}` — {e.description}" for e in s.repository_map)
            parts.append(f"**Repository Map**:\n{dirs}")
        if s.architecture and s.architecture.layers:
            parts.append(f"**Architecture**: {s.architecture.pattern} ({', '.join(s.architecture.layers)})")
        return "\n\n".join(parts)
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_renderer.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/renderer.py backend/tests/test_renderer.py
git commit -m "feat: add Markdown renderer for Context Packages"
```

- [ ] **Step 6: Post-task verification**

---

### Task 3.3: Package Builder

**Covers:** [S4 Package Builder]

**Files:**
- Create: `backend/app/services/package_builder.py`
- Create: `backend/tests/test_package_builder.py`

**Interfaces:**
- Consumes: task, `list[RecallResult]`, `RepositorySummary | None`, datasets
- Produces: `ContextPackage`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_package_builder.py
from app.models.responses import RecallResult, RepositorySummary
from app.services.package_builder import PackageBuilder


def _make(text: str, kind: str = "text", score: float = 0.5) -> RecallResult:
    return RecallResult(kind=kind, search_type="semantic", text=text, score=score, dataset_name="test")


def test_builds_package():
    pkg = PackageBuilder().build("Fix bug", [_make("svc.py", "file", 0.9)], None, ["ws"])
    assert pkg.task == "Fix bug"
    assert pkg.markdown != ""
    assert pkg.section_count > 0


def test_includes_summary():
    summary = RepositorySummary(
        version="1.0", repository_fingerprint="abc", generated_at="2026-01-01T00:00:00Z",
        indexed_commit=None, project_purpose="Test", technology_stack=None,
        repository_map=[], architecture=None, key_components=[], entry_points=[],
        public_apis=[], coding_conventions=None, domain_vocabulary={},
    )
    pkg = PackageBuilder().build("q", [_make("a.py", "file")], summary, ["ws"])
    assert pkg.repository_summary == summary
    assert "Repository Context" in pkg.markdown


def test_metadata_populated():
    pkg = PackageBuilder().build("q", [_make("a.py", "file")], None, ["ws"])
    assert pkg.metadata is not None
    assert pkg.metadata.retrieved_memory_count == 1


def test_empty_results():
    pkg = PackageBuilder().build("q", [], None, ["ws"])
    assert pkg.task == "q"
    assert pkg.section_count >= 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_package_builder.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement Package Builder**

```python
# backend/app/services/package_builder.py
"""Assembles Context Packages from pipeline output."""

import time
from datetime import datetime, timezone
from app.models.responses import ContextPackage, PackageMetadata, PackageSection, RecallResult, RepositorySummary
from app.services.budget_manager import BudgetManager
from app.services.pipeline.categorization import Categorizer
from app.services.pipeline.compression import Compressor
from app.services.pipeline.dedup import Deduplicator
from app.services.pipeline.ranking import Ranker
from app.services.pipeline.references import ReferenceResolver
from app.services.renderer import MarkdownRenderer


class PackageBuilder:
    def __init__(self, target_tokens: int = 3000) -> None:
        self._dedup = Deduplicator()
        self._ranker = Ranker()
        self._compressor = Compressor()
        self._categorizer = Categorizer()
        self._resolver = ReferenceResolver()
        self._budget = BudgetManager(target_tokens)
        self._renderer = MarkdownRenderer()

    def build(self, task: str, results: list[RecallResult], summary: RepositorySummary | None, datasets: list[str]) -> ContextPackage:
        start = time.monotonic()
        deduped = self._dedup.deduplicate(results)
        ranked = self._ranker.rank(deduped)
        compressed = self._compressor.compress(ranked)
        categories = self._categorizer.categorize(compressed)
        sections = self._build_sections(categories)
        budgeted = self._budget.apply(sections)
        refs = self._resolver.resolve(compressed)
        objective = task if len(task) <= 100 else task[:97] + "..."
        md = self._renderer.render(task, objective, budgeted, refs, summary)
        elapsed = int((time.monotonic() - start) * 1000)
        metadata = PackageMetadata(
            package_version="1.0", repository_summary_version=summary.version if summary else "none",
            generated_at=datetime.now(timezone.utc).isoformat(), datasets_used=datasets,
            retrieved_memory_count=len(results), deduplicated_count=len(deduped),
            compressed_count=len(compressed), compression_ratio=self._budget.last_compression_ratio,
            estimated_tokens=len(md) // 4, pipeline_version="1.0", retrieval_time_ms=0, total_time_ms=elapsed,
        )
        return ContextPackage(task=task, objective=objective, sections=budgeted, references=refs, metadata=metadata, repository_summary=summary, markdown=md, source_count=len(compressed), dataset=", ".join(datasets))

    def _build_sections(self, categories: dict[str, list[RecallResult]]) -> list[PackageSection]:
        headings = {"files": "Relevant Files", "architecture": "Architecture", "apis": "Existing APIs", "conventions": "Coding Conventions", "decisions": "Previous Decisions", "knowledge": "Implementation Notes"}
        priorities = {"files": 5, "architecture": 4, "knowledge": 4, "apis": 3, "decisions": 3, "conventions": 2}
        sections = []
        for st, results in categories.items():
            if not results: continue
            content = "\n".join(f"- `{r.text.strip()}`" if st == "files" else f"- {r.text.strip()}" for r in results)
            sections.append(PackageSection(section_type=st, heading=headings.get(st, st.title()), content=content, priority=priorities.get(st, 2), source_sections=["Component Context"], reference_count=len(results)))
        return sections
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_package_builder.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/package_builder.py backend/tests/test_package_builder.py
git commit -m "feat: add Package Builder assembling full Context Packages"
```

- [ ] **Step 6: Post-task verification**

**Milestone 3 Complete.** Demonstrate: run `pytest tests/test_budget_manager.py tests/test_renderer.py tests/test_package_builder.py -v` — 16/16 pass.

---

# Milestone 4 — Integration

**Result:** End-to-end generation through your existing backend.

---

### Task 4.1: Rewrite ContextService

**Covers:** [S3, S4, S10]

**Files:**
- Modify: `backend/app/services/context_service.py`
- Create: `backend/tests/test_context_service_v2.py`

**Interfaces:**
- Consumes: `CogneeService`, optional `RepositorySummary`
- Produces: `ContextPackage` via `generate_context_package()`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_context_service_v2.py
import pytest
from unittest.mock import AsyncMock
from app.models.responses import RecallResult, RecallResponse
from app.services.context_service import ContextService


def _make(text: str, kind: str = "text", score: float = 0.5) -> RecallResult:
    return RecallResult(kind=kind, search_type="semantic", text=text, score=score, dataset_name="test")


@pytest.fixture
def mock_cognee():
    cognee = AsyncMock()
    cognee.recall.return_value = RecallResponse(query="test", dataset="test", results=[_make("svc.py", "file", 0.9)])
    return cognee


@pytest.mark.asyncio
async def test_generate_returns_package(mock_cognee):
    pkg = await ContextService(mock_cognee).generate_context_package("Fix bug", ["ws"])
    assert pkg.task == "Fix bug"
    assert pkg.markdown != ""


@pytest.mark.asyncio
async def test_generate_has_metadata(mock_cognee):
    pkg = await ContextService(mock_cognee).generate_context_package("q", ["ws"])
    assert pkg.metadata is not None
    assert pkg.metadata.retrieved_memory_count == 1


@pytest.mark.asyncio
async def test_generate_empty_results(mock_cognee):
    mock_cognee.recall.return_value = RecallResponse(query="q", dataset="d", results=[])
    pkg = await ContextService(mock_cognee).generate_context_package("q", ["ws"])
    assert pkg.task == "q"


@pytest.mark.asyncio
async def test_generate_no_summary(mock_cognee):
    pkg = await ContextService(mock_cognee).generate_context_package("q", ["ws"])
    assert pkg.repository_summary is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_context_service_v2.py -v`
Expected: FAIL (constructor mismatch)

- [ ] **Step 3: Rewrite ContextService**

Replace `backend/app/services/context_service.py`:

```python
"""
Context Package generator for AndesContext.

Pipeline: recall → dedup → rank → compress → categorize → build → budget → render → ContextPackage
"""

import logging
from app.models.responses import ContextPackage, RepositorySummary
from app.services.cognee_service import CogneeService
from app.services.package_builder import PackageBuilder

logger = logging.getLogger(__name__)


class ContextService:
    def __init__(self, cognee_service: CogneeService, repository_summary: RepositorySummary | None = None, target_tokens: int = 3000) -> None:
        self._cognee = cognee_service
        self._repository_summary = repository_summary
        self._builder = PackageBuilder(target_tokens)

    async def generate_context_package(self, task: str, datasets: list[str], top_k: int = 20) -> ContextPackage:
        logger.info("generate_context_package | task=%s | datasets=%s | top_k=%d", task[:80], datasets, top_k)
        recall = await self._cognee.recall(query_text=task, datasets=datasets, top_k=top_k)
        package = self._builder.build(task=task, results=recall.results, summary=self._repository_summary, datasets=datasets)
        logger.info("context package generated | sections=%d | sources=%d | ~%d tokens", package.section_count, package.source_count, package.token_estimate)
        return package
```

- [ ] **Step 4: Run new tests**

Run: `cd backend && python -m pytest tests/test_context_service_v2.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Run full test suite**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All tests PASS. If API/CLI tests fail due to constructor change, update fixtures to pass `repository_summary=None`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/context_service.py backend/tests/test_context_service_v2.py
git commit -m "feat: rewrite ContextService with full pipeline integration"
```

- [ ] **Step 7: Post-task verification**

---

### Task 4.2: API & CLI Verification

**Covers:** [S10]

**Files:**
- Verify: `backend/app/api/commands.py` — no changes needed (already calls ContextService)
- Verify: `backend/app/cli/main.py` — no changes needed

**Interfaces:**
- Consumes: existing API commands and CLI
- Produces: verified end-to-end flow

- [ ] **Step 1: Run all automated tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: ALL tests PASS

- [ ] **Step 2: Verify CLI context command works**

Run: `cd backend && python andescontext.py context --query "What is AndesContext?" --dataset test_ws`
Expected: Markdown output with Task, sections, and metadata

- [ ] **Step 3: Verify API command works**

Run: `cd backend && python -c "import asyncio; from app.api.commands import generate_context; print(asyncio.run(generate_context('What is AndesContext?', ['test_ws'])))"`
Expected: ContextPackage object with markdown content

- [ ] **Step 4: Commit (if any fixes were needed)**

```bash
git add -A
git commit -m "fix: update API/CLI for new ContextService interface"
```

- [ ] **Step 5: Post-task verification**

**Milestone 4 Complete.** Demonstrate: run full test suite, then run CLI context command against a real dataset.

---

# Milestone 5 — Validation

**Result:** Pipeline works against real repositories. Measured quality.

---

### Task 5.1: AndesContext Self-Test

**Covers:** [S6, S7]

**Files:**
- Create: `backend/tests/test_validation_andescontext.py`

**Interfaces:**
- Consumes: full pipeline against this repository
- Produces: validation report

- [ ] **Step 1: Write validation test**

```python
# backend/tests/test_validation_andescontext.py
"""Validate Context Package generation against AndesContext itself."""

import asyncio
import time
import pytest
from app.services.cognee_service import CogneeService
from app.services.context_service import ContextService


@pytest.mark.asyncio
@pytest.mark.live
async def test_andescontext_self_test():
    """Generate a Context Package for 'Add Rust file support' against this repo."""
    cognee = CogneeService()
    await cognee.initialize()

    svc = ContextService(cognee)
    start = time.monotonic()
    pkg = await svc.generate_context_package(
        "Add .rs file extension support to the indexing pipeline",
        ["andescontext"],
    )
    elapsed = time.monotonic() - start

    # Assertions
    assert pkg.task != ""
    assert pkg.markdown != ""
    assert pkg.metadata is not None
    assert pkg.metadata.retrieved_memory_count > 0
    assert pkg.section_count >= 2
    assert elapsed < 120  # under 2 minutes

    # Quality checks
    md_lower = pkg.markdown.lower()
    assert "indexing" in md_lower or "service" in md_lower or "file" in md_lower

    print(f"\n--- AndesContext Self-Test ---")
    print(f"Sections: {pkg.section_count}")
    print(f"Sources: {pkg.metadata.retrieved_memory_count}")
    print(f"Tokens: {pkg.metadata.estimated_tokens}")
    print(f"Time: {elapsed:.1f}s")
    print(f"Markdown preview:\n{pkg.markdown[:500]}")
```

- [ ] **Step 2: Run validation**

Run: `cd backend && python -m pytest tests/test_validation_andescontext.py -v -m live`
Expected: PASS with printed quality report

- [ ] **Step 3: Record results in `backend/tests/RESULTS/`**

Create `backend/tests/RESULTS/test_5_CONTEXT_PACKAGE_RESULTS.md` with:
- Generation time
- Package size (tokens)
- Sections generated
- Retrieval quality (memory count)
- Whether the package answers the test question

- [ ] **Step 4: Post-task verification**

---

### Task 5.2: Cognee Reference Test

**Covers:** [S6, S7]

**Files:**
- Create: `backend/tests/test_validation_cognee.py`

- [ ] **Step 1: Write validation test**

```python
# backend/tests/test_validation_cognee.py
"""Validate against Cognee's own codebase (if indexed)."""

import asyncio
import time
import pytest
from app.services.cognee_service import CogneeService
from app.services.context_service import ContextService


@pytest.mark.asyncio
@pytest.mark.live
async def test_cognee_reference():
    """Generate a Context Package for a Cognee-related query."""
    cognee = CogneeService()
    await cognee.initialize()

    svc = ContextService(cognee)
    start = time.monotonic()
    pkg = await svc.generate_context_package(
        "How does CogneeService initialize the local AI providers?",
        ["andescontext"],
    )
    elapsed = time.monotonic() - start

    assert pkg.metadata is not None
    assert elapsed < 120

    print(f"\n--- Cognee Reference Test ---")
    print(f"Sections: {pkg.section_count}")
    print(f"Tokens: {pkg.metadata.estimated_tokens}")
    print(f"Time: {elapsed:.1f}s")
    print(f"Markdown:\n{pkg.markdown[:800]}")
```

- [ ] **Step 2: Run validation**

Run: `cd backend && python -m pytest tests/test_validation_cognee.py -v -m live`
Expected: PASS

- [ ] **Step 3: Record results**

- [ ] **Step 4: Post-task verification**

---

### Task 5.3: Quality Metrics

**Covers:** [S6]

**Files:**
- Create: `backend/tests/test_quality_metrics.py`

- [ ] **Step 1: Write quality metric tests**

```python
# backend/tests/test_quality_metrics.py
"""Automated structural quality metrics for Context Packages."""

import pytest
from app.models.responses import ContextPackage
from app.services.package_builder import PackageBuilder


def _make_package(task: str, results) -> ContextPackage:
    from app.models.responses import RecallResult
    return PackageBuilder().build(task, results, None, ["test"])


def _make_result(text, kind="text", score=0.5):
    from app.models.responses import RecallResult
    return RecallResult(kind=kind, search_type="semantic", text=text, score=score, dataset_name="test")


def test_no_duplicate_references():
    results = [_make_result("same text")] * 5
    pkg = _make_package("query", results)
    ref_paths = [r.path for r in pkg.references]
    assert len(ref_paths) == len(set(ref_paths))


def test_section_utilization():
    results = [_make_result("architecture is layered"), _make_result("backend/service.py", "file")]
    pkg = _make_package("query", results)
    if pkg.sections:
        non_empty = sum(1 for s in pkg.sections if s.content.strip())
        assert non_empty / len(pkg.sections) > 0.5


def test_token_estimate_reasonable():
    results = [_make_result(f"fact {i}") for i in range(10)]
    pkg = _make_package("query", results)
    assert 100 < pkg.token_estimate < 10000


def test_metadata_populated():
    results = [_make_result("test")]
    pkg = _make_package("query", results)
    assert pkg.metadata is not None
    assert pkg.metadata.package_version == "1.0"
    assert pkg.metadata.pipeline_version == "1.0"
```

- [ ] **Step 2: Run tests**

Run: `cd backend && python -m pytest tests/test_quality_metrics.py -v`
Expected: All 4 tests PASS

- [ ] **Step 3: Record final results**

Update `backend/tests/RESULTS/test_5_CONTEXT_PACKAGE_RESULTS.md` with complete metrics.

- [ ] **Step 4: Post-task verification**

**Milestone 5 Complete.** Demonstrate: run full validation suite, show quality metrics report.

---

## Summary

| Milestone | Tasks | Result |
|-----------|-------|--------|
| 1 — Core Data Model | 1.1, 1.2, 1.3 | Construct and validate package objects |
| 2 — Retrieval Processing | 2.1, 2.2, 2.3, 2.4, 2.5 | Cognee results → structured sections |
| 3 — Package Generation | 3.1, 3.2, 3.3 | One query → complete Context Package |
| 4 — Integration | 4.1, 4.2 | End-to-end through existing backend |
| 5 — Validation | 5.1, 5.2, 5.3 | Real repos, measured quality |

**Total: 15 tasks across 5 milestones**

### Not in MVP (Deferred)

- Graph Expansion (Stage 2) — requires Kuzu graph queries
- Budget Compression Tier 3 — measure first
- LLM-as-judge evaluation
- Context Delta benchmark
- JSON/UI/MCP renderers
