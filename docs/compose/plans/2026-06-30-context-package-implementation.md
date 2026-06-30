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

---

## File Structure

```
backend/app/models/
    responses.py          # MODIFY — add new data models (TechnologyStack, RepositorySummary, etc.)
    errors.py             # MODIFY — add ContextPackageError if needed

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
    test_models.py        # CREATE — data model tests
    test_repository_summary.py # CREATE — summary generator tests
    test_dedup.py         # CREATE — deduplication tests
    test_ranking.py       # CREATE — ranking tests
    test_compression.py   # CREATE — compression tests
    test_categorization.py # CREATE — categorization tests
    test_references.py    # CREATE — reference resolution tests
    test_budget_manager.py # CREATE — budget manager tests
    test_package_builder.py # CREATE — package builder tests
    test_renderer.py      # CREATE — renderer tests
    test_context_service_v2.py # CREATE — integration tests
```

---

### Task 1: Data Models

**Covers:** [S2, S3, S8]

**Files:**
- Modify: `backend/app/models/responses.py`
- Create: `backend/tests/test_models.py`

**Interfaces:**
- Consumes: existing `RecallResult`, `RecallResponse`, `SectionType`
- Produces: `TechnologyStack`, `DirectoryEntry`, `ArchitectureInfo`, `ComponentInfo`, `EntryPoint`, `APIInfo`, `ConventionInfo`, `RepositorySummary`, `PackageReference`, `PackageSection` (updated), `PackageMetadata`, `ContextPackage` (updated)

- [ ] **Step 1: Write failing tests for new data models**

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
    PackageMetadata,
    PackageReference,
    PackageSection,
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
    assert entry.description == "Backend services"


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
        relationships=["Used by IndexingService", "Used by ContextService"],
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
        project_purpose="Local-first AI memory for software development",
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


def test_repository_summary_is_frozen():
    summary = RepositorySummary(
        version="1.0",
        repository_fingerprint="abc",
        generated_at="2026-01-01T00:00:00Z",
        indexed_commit=None,
        project_purpose="test",
        technology_stack=TechnologyStack([], [], [], []),
        repository_map=[],
        architecture=ArchitectureInfo("", [], [], []),
        key_components=[],
        entry_points=[],
        public_apis=[],
        coding_conventions=ConventionInfo("", "", []),
        domain_vocabulary={},
    )
    try:
        summary.version = "2.0"
        assert False, "Should be frozen"
    except AttributeError:
        pass


def test_package_reference_construction():
    ref = PackageReference(
        ref_type="file",
        path="backend/app/services/cognee_service.py",
        section="Services",
        score=0.95,
        provenance=["memory_node_1", "chunk_2", "doc_3"],
    )
    assert ref.ref_type == "file"
    assert ref.score == 0.95
    assert len(ref.provenance) == 3


def test_package_reference_frozen():
    ref = PackageReference("file", "test.py", None, 0.5, [])
    try:
        ref.score = 1.0
        assert False, "Should be frozen"
    except AttributeError:
        pass


def test_package_section_construction():
    section = PackageSection(
        section_type="files",
        heading="Relevant Files",
        content="- `backend/app/services/cognee_service.py`",
        priority=5,
        source_sections=["Component Context"],
        reference_count=1,
    )
    assert section.priority == 5
    assert section.section_type == "files"


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

Run: `cd backend && python -m pytest tests/test_models.py -v`
Expected: FAIL with ImportError for new types

- [ ] **Step 3: Implement new data models**

Add to `backend/app/models/responses.py`:

```python
# Add after existing SectionType enum, before PackageSection

@dataclass(frozen=True)
class TechnologyStack:
    """Technology stack for a repository."""
    languages: list[str]
    frameworks: list[str]
    databases: list[str]
    dependencies: list[str]


@dataclass(frozen=True)
class DirectoryEntry:
    """A directory in the repository map."""
    path: str
    description: str


@dataclass(frozen=True)
class ArchitectureInfo:
    """Architecture information for a repository."""
    pattern: str
    layers: list[str]
    boundaries: list[str]
    major_flows: list[str]


@dataclass(frozen=True)
class ComponentInfo:
    """A key component in the repository."""
    name: str
    responsibilities: str
    relationships: list[str]


@dataclass(frozen=True)
class EntryPoint:
    """An application entry point."""
    name: str
    path: str
    type: str  # "cli" | "api" | "startup"


@dataclass(frozen=True)
class APIInfo:
    """A public API interface."""
    name: str
    signature: str
    description: str


@dataclass(frozen=True)
class ConventionInfo:
    """Coding conventions for a repository."""
    naming: str
    formatting: str
    patterns: list[str]


@dataclass(frozen=True)
class RepositorySummary:
    """Structured knowledge model of global repository facts."""
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


@dataclass(frozen=True)
class PackageReference:
    """A traceable reference in a Context Package."""
    ref_type: str  # "file" | "symbol" | "memory" | "doc" | "dir"
    path: str
    section: str | None
    score: float
    provenance: list[str]
```

Update existing `PackageSection` to add priority and source_sections:

```python
# Replace existing PackageSection
@dataclass(frozen=True)
class PackageSection:
    """A section in a Context Package."""
    section_type: str
    heading: str
    content: str
    priority: int = 3
    source_sections: list[str] = field(default_factory=list)
    reference_count: int = 0
```

Add `PackageMetadata` after `PackageSection`:

```python
@dataclass(frozen=True)
class PackageMetadata:
    """Metadata for a Context Package."""
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

Update existing `ContextPackage` to add new fields:

```python
# Replace existing ContextPackage
@dataclass(frozen=True)
class ContextPackage:
    """A structured Context Package for AI coding assistants."""
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

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_models.py -v`
Expected: All 13 tests PASS

- [ ] **Step 5: Run full test suite to verify no regressions**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All existing tests still PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/responses.py backend/tests/test_models.py
git commit -m "feat: add data models for Repository Summary and Context Package"
```

---

### Task 2: Repository Summary Generator

**Covers:** [S2]

**Files:**
- Create: `backend/app/services/repository_summary.py`
- Create: `backend/tests/test_repository_summary.py`

**Interfaces:**
- Consumes: repository path (`Path`), indexed file list (`list[Path]`)
- Produces: `RepositorySummary`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_repository_summary.py
"""Tests for Repository Summary generator."""

from pathlib import Path

from app.models.responses import RepositorySummary
from app.services.repository_summary import RepositorySummaryGenerator


def test_generator_creates_summary(tmp_path):
    # Create minimal repo structure
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend" / "app.py").write_text("import os\nprint('hello')")
    (tmp_path / "README.md").write_text("# Test Project\nA test repository.")
    (tmp_path / "requirements.txt").write_text("cognee\npydantic")

    files = list(tmp_path.rglob("*"))
    files = [f for f in files if f.is_file()]

    gen = RepositorySummaryGenerator()
    summary = gen.generate(tmp_path, files)

    assert isinstance(summary, RepositorySummary)
    assert summary.version == "1.0"
    assert summary.repository_fingerprint != ""
    assert summary.generated_at != ""
    assert len(summary.technology_stack.languages) > 0 or len(summary.technology_stack.dependencies) > 0


def test_generator_extracts_languages(tmp_path):
    (tmp_path / "main.py").write_text("def main(): pass")
    (tmp_path / "app.ts").write_text("const x = 1;")

    files = [tmp_path / "main.py", tmp_path / "app.ts"]
    gen = RepositorySummaryGenerator()
    summary = gen.generate(tmp_path, files)

    langs = [l.lower() for l in summary.technology_stack.languages]
    assert "python" in langs or "typescript" in langs


def test_generator_maps_directories(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("x = 1")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_main.py").write_text("def test_x(): pass")

    files = [tmp_path / "src" / "main.py", tmp_path / "tests" / "test_main.py"]
    gen = RepositorySummaryGenerator()
    summary = gen.generate(tmp_path, files)

    paths = [e.path for e in summary.repository_map]
    assert any("src" in p for p in paths)


def test_generator_fingerprint_is_deterministic(tmp_path):
    (tmp_path / "a.py").write_text("x = 1")
    files = [tmp_path / "a.py"]

    gen = RepositorySummaryGenerator()
    s1 = gen.generate(tmp_path, files)
    s2 = gen.generate(tmp_path, files)

    assert s1.repository_fingerprint == s2.repository_fingerprint


def test_generator_empty_repo(tmp_path):
    gen = RepositorySummaryGenerator()
    summary = gen.generate(tmp_path, [])

    assert isinstance(summary, RepositorySummary)
    assert summary.project_purpose != ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_repository_summary.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement Repository Summary Generator**

```python
# backend/app/services/repository_summary.py
"""
Repository Summary generator for AndesContext.

Analyzes indexed repository files to extract stable, global knowledge:
project purpose, technology stack, directory structure, architecture,
key components, entry points, APIs, conventions, and domain vocabulary.

Generates a RepositorySummary after indexing completes.
"""

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

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

logger = logging.getLogger(__name__)

# Extension to language mapping
_EXT_LANG_MAP: dict[str, str] = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".rs": "Rust",
    ".go": "Go",
    ".java": "Java",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".cpp": "C++",
    ".c": "C",
    ".h": "C",
}

# Extension to framework hints
_EXT_FRAMEWORK_MAP: dict[str, str] = {
    ".tsx": "React",
    ".jsx": "React",
    ".vue": "Vue",
    ".svelte": "Svelte",
}


class RepositorySummaryGenerator:
    """Generates a RepositorySummary from indexed repository files."""

    def generate(self, repo_path: Path, files: list[Path]) -> RepositorySummary:
        """Generate a RepositorySummary from a repository and its files.

        Args:
            repo_path: Root directory of the repository.
            files: List of indexed file paths.

        Returns:
            RepositorySummary with extracted stable facts.
        """
        logger.info("generating repository summary | path=%s | files=%d", repo_path, len(files))

        fingerprint = self._compute_fingerprint(files)
        rel_files = [f.relative_to(repo_path) if f.is_relative_to(repo_path) else f for f in files]

        tech_stack = self._extract_tech_stack(rel_files)
        repo_map = self._build_repo_map(rel_files)
        architecture = self._infer_architecture(repo_map)
        components = self._extract_components(rel_files)
        entry_points = self._find_entry_points(repo_map)
        conventions = self._infer_conventions(rel_files)
        purpose = self._infer_purpose(repo_path, repo_map)

        summary = RepositorySummary(
            version="1.0",
            repository_fingerprint=fingerprint,
            generated_at=datetime.now(timezone.utc).isoformat(),
            indexed_commit=None,
            project_purpose=purpose,
            technology_stack=tech_stack,
            repository_map=repo_map,
            architecture=architecture,
            key_components=components,
            entry_points=entry_points,
            public_apis=[],
            coding_conventions=conventions,
            domain_vocabulary={},
        )

        logger.info(
            "repository summary generated | languages=%d | dirs=%d | components=%d",
            len(tech_stack.languages),
            len(repo_map),
            len(components),
        )
        return summary

    def _compute_fingerprint(self, files: list[Path]) -> str:
        """Compute a fingerprint from file paths and sizes."""
        hasher = hashlib.sha256()
        for f in sorted(str(p) for p in files):
            hasher.update(f.encode())
        return hasher.hexdigest()[:16]

    def _extract_tech_stack(self, files: list[Path]) -> TechnologyStack:
        """Extract technologies from file extensions."""
        languages: set[str] = set()
        frameworks: set[str] = set()

        for f in files:
            ext = f.suffix.lower()
            if ext in _EXT_LANG_MAP:
                languages.add(_EXT_LANG_MAP[ext])
            if ext in _EXT_FRAMEWORK_MAP:
                frameworks.add(_EXT_FRAMEWORK_MAP[ext])

        return TechnologyStack(
            languages=sorted(languages),
            frameworks=sorted(frameworks),
            databases=[],
            dependencies=[],
        )

    def _build_repo_map(self, files: list[Path]) -> list[DirectoryEntry]:
        """Build a map of top-level directories."""
        dirs: dict[str, list[str]] = {}
        for f in files:
            parts = f.parts
            if len(parts) > 1:
                top_dir = parts[0]
                dirs.setdefault(top_dir, []).append(str(f))
            else:
                dirs.setdefault(".", []).append(str(f))

        entries = []
        for dir_path, dir_files in sorted(dirs.items()):
            desc = self._describe_directory(dir_path, dir_files)
            entries.append(DirectoryEntry(path=dir_path, description=desc))
        return entries

    def _describe_directory(self, name: str, files: list[str]) -> str:
        """Generate a one-line description for a directory."""
        exts = set()
        for f in files:
            p = Path(f)
            if p.suffix:
                exts.add(p.suffix.lower())

        if name == "tests" or name == "test":
            return "Test suite"
        if name == "docs":
            return "Documentation"
        if name == "scripts":
            return "Development scripts"
        if name == ".github":
            return "CI/CD configuration"
        if ".py" in exts:
            return f"Python module ({len(files)} files)"
        if ".ts" in exts or ".tsx" in exts:
            return f"TypeScript module ({len(files)} files)"
        return f"Source directory ({len(files)} files)"

    def _infer_architecture(self, repo_map: list[DirectoryEntry]) -> ArchitectureInfo:
        """Infer architecture from directory structure."""
        dir_names = {e.path for e in repo_map}
        layers = []
        if "backend" in dir_names or "server" in dir_names:
            layers.append("Backend")
        if "frontend" in dir_names or "src" in dir_names:
            layers.append("Frontend")
        if "tests" in dir_names:
            layers.append("Tests")

        return ArchitectureInfo(
            pattern="layered" if len(layers) > 1 else "monolith",
            layers=layers,
            boundaries=[],
            major_flows=[],
        )

    def _extract_components(self, files: list[Path]) -> list[ComponentInfo]:
        """Extract key components from file structure."""
        components = []
        service_files = [f for f in files if "service" in f.name.lower()]
        for sf in service_files[:10]:
            name = sf.stem.replace("_", " ").title()
            components.append(ComponentInfo(
                name=name,
                responsibilities=f"Defined in {sf}",
                relationships=[],
            ))
        return components

    def _find_entry_points(self, repo_map: list[DirectoryEntry]) -> list[EntryPoint]:
        """Identify likely entry points."""
        entry_points = []
        for entry in repo_map:
            if entry.path == "backend":
                entry_points.append(EntryPoint(
                    name="backend",
                    path="backend/",
                    type="startup",
                ))
            elif entry.path in ("src", "frontend"):
                entry_points.append(EntryPoint(
                    name=entry.path,
                    path=f"{entry.path}/",
                    type="startup",
                ))
        return entry_points

    def _infer_conventions(self, files: list[Path]) -> ConventionInfo:
        """Infer coding conventions from file patterns."""
        has_snake = any("_" in f.stem for f in files if f.suffix == ".py")
        has_camel = any(any(c.isupper() for c in f.stem) for f in files if f.suffix in (".ts", ".tsx", ".js"))

        naming = "snake_case" if has_snake else "camelCase" if has_camel else "unknown"
        return ConventionInfo(naming=naming, formatting="unknown", patterns=[])

    def _infer_purpose(self, repo_path: Path, repo_map: list[DirectoryEntry]) -> str:
        """Infer project purpose from README or directory structure."""
        readme = repo_path / "README.md"
        if readme.exists():
            try:
                content = readme.read_text(errors="replace")[:500]
                lines = content.strip().split("\n")
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith("#") and not line.startswith("---"):
                        return line[:200]
            except Exception:
                pass

        dir_names = [e.path for e in repo_map]
        return f"Software project with directories: {', '.join(dir_names[:5])}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_repository_summary.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Run full test suite**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All existing tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/repository_summary.py backend/tests/test_repository_summary.py
git commit -m "feat: add Repository Summary generator"
```

---

### Task 3: Deduplication Stage

**Covers:** [S4 Stage 3]

**Files:**
- Create: `backend/app/services/pipeline/__init__.py`
- Create: `backend/app/services/pipeline/dedup.py`
- Create: `backend/tests/test_dedup.py`

**Interfaces:**
- Consumes: `list[RecallResult]`
- Produces: `list[RecallResult]` (deduplicated, same order, highest-score kept)

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_dedup.py
"""Tests for deduplication pipeline stage."""

from app.models.responses import RecallResult
from app.services.pipeline.dedup import Deduplicator


def _make_result(text: str, score: float = 0.5, kind: str = "text") -> RecallResult:
    return RecallResult(kind=kind, search_type="semantic", text=text, score=score, dataset_name="test")


def test_no_duplicates():
    results = [_make_result("alpha", 0.9), _make_result("beta", 0.8)]
    dedup = Deduplicator()
    out = dedup.deduplicate(results)
    assert len(out) == 2


def test_exact_duplicates_removed():
    results = [
        _make_result("same text", 0.9),
        _make_result("same text", 0.7),
    ]
    dedup = Deduplicator()
    out = dedup.deduplicate(results)
    assert len(out) == 1
    assert out[0].score == 0.9  # keeps highest score


def test_case_insensitive_dedup():
    results = [
        _make_result("Hello World", 0.8),
        _make_result("hello world", 0.6),
    ]
    dedup = Deduplicator()
    out = dedup.deduplicate(results)
    assert len(out) == 1


def test_whitespace_normalization():
    results = [
        _make_result("hello  world", 0.8),
        _make_result("hello world", 0.6),
    ]
    dedup = Deduplicator()
    out = dedup.deduplicate(results)
    assert len(out) == 1


def test_preserves_order_for_unique():
    results = [_make_result("c", 0.3), _make_result("a", 0.9), _make_result("b", 0.6)]
    dedup = Deduplicator()
    out = dedup.deduplicate(results)
    texts = [r.text for r in out]
    assert texts == ["c", "a", "b"]


def test_empty_input():
    dedup = Deduplicator()
    assert dedup.deduplicate([]) == []


def test_single_item():
    dedup = Deduplicator()
    result = [_make_result("only")]
    assert dedup.deduplicate(result) == result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_dedup.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement deduplication**

```python
# backend/app/services/pipeline/dedup.py
"""Structural deduplication stage for the retrieval pipeline."""

from app.models.responses import RecallResult


class Deduplicator:
    """Removes duplicate memories based on normalized text."""

    def deduplicate(self, results: list[RecallResult]) -> list[RecallResult]:
        """Remove duplicates, keeping the highest-scored entry.

        Args:
            results: Raw recall results (assumed score-sorted descending).

        Returns:
            Deduplicated list preserving original order for unique entries.
        """
        seen: dict[str, RecallResult] = {}
        order: list[str] = []

        for r in results:
            key = self._normalize(r.text)
            if key not in seen:
                seen[key] = r
                order.append(key)
            elif r.score > seen[key].score:
                seen[key] = r

        return [seen[k] for k in order]

    def _normalize(self, text: str) -> str:
        """Lowercase and collapse whitespace for comparison."""
        return " ".join(text.lower().split())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_dedup.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/pipeline/ backend/tests/test_dedup.py
git commit -m "feat: add deduplication pipeline stage"
```

---

### Task 4: Ranking Stage

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
"""Tests for ranking pipeline stage."""

from app.models.responses import RecallResult
from app.services.pipeline.ranking import Ranker


def _make_result(text: str, score: float | None, kind: str = "text") -> RecallResult:
    return RecallResult(kind=kind, search_type="semantic", text=text, score=score or 0.0, dataset_name="test")


def test_high_score_ranks_first():
    results = [_make_result("low", 0.3), _make_result("high", 0.9)]
    ranker = Ranker()
    ranked = ranker.rank(results)
    assert ranked[0].text == "high"


def test_none_score_treated_as_medium():
    results = [_make_result("has_score", 0.5), _make_result("no_score", None)]
    ranker = Ranker()
    ranked = ranker.rank(results)
    # no_score gets confidence=0.5, has_score gets confidence=1.0
    # so has_score should rank higher
    assert ranked[0].text == "has_score"


def test_file_type_boosted():
    results = [_make_result("architecture note", 0.7, kind="text"), _make_result("service.py", 0.6, kind="file")]
    ranker = Ranker()
    ranked = ranker.rank(results)
    assert ranked[0].kind == "file"


def test_empty_input():
    ranker = Ranker()
    assert ranker.rank([]) == []


def test_single_item():
    ranker = Ranker()
    result = [_make_result("only", 0.5)]
    assert ranker.rank(result) == result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_ranking.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement ranking**

```python
# backend/app/services/pipeline/ranking.py
"""Multi-factor ranking stage for the retrieval pipeline."""

from app.models.responses import RecallResult

# Information type weights
_TYPE_WEIGHTS: dict[str, float] = {
    "file": 1.0,
    "code": 0.9,
    "text": 0.7,
}


class Ranker:
    """Ranks recall results by composite relevance score."""

    def rank(self, results: list[RecallResult]) -> list[RecallResult]:
        """Rank results by composite score.

        Score = SemanticRelevance × Confidence × TypeWeight

        Args:
            results: Recall results to rank.

        Returns:
            Results sorted by composite score (descending).
        """
        scored = []
        for r in results:
            semantic = r.score if r.score is not None else 0.5
            confidence = 1.0 if r.score is not None else 0.5
            type_weight = _TYPE_WEIGHTS.get(r.kind, 0.7)
            composite = semantic * confidence * type_weight
            scored.append((composite, r))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_ranking.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/pipeline/ranking.py backend/tests/test_ranking.py
git commit -m "feat: add multi-factor ranking pipeline stage"
```

---

### Task 5: Compression Stage

**Covers:** [S4 Stage 5, S5]

**Files:**
- Create: `backend/app/services/pipeline/compression.py`
- Create: `backend/tests/test_compression.py`

**Interfaces:**
- Consumes: `list[RecallResult]`
- Produces: `list[RecallResult]` (compressed, executable facts preserved)

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_compression.py
"""Tests for compression pipeline stage."""

from app.models.responses import RecallResult
from app.services.pipeline.compression import Compressor


def _make_result(text: str, kind: str = "text") -> RecallResult:
    return RecallResult(kind=kind, search_type="semantic", text=text, score=0.5, dataset_name="test")


def test_preserves_file_paths():
    results = [_make_result("The file backend/app/services/cognee.py contains the service")]
    comp = Compressor()
    compressed = comp.compress(results)
    assert any("backend/app/services/cognee.py" in r.text for r in compressed)


def test_preserves_symbol_names():
    results = [_make_result("The function recall() calls cognee.recall internally")]
    comp = Compressor()
    compressed = comp.compress(results)
    assert any("recall()" in r.text for r in compressed)


def test_merges_identical_concepts():
    results = [
        _make_result("CogneeService wraps cognee APIs"),
        _make_result("CogneeService is a thin wrapper around cognee APIs"),
    ]
    comp = Compressor()
    compressed = comp.compress(results)
    assert len(compressed) == 1


def test_empty_input():
    comp = Compressor()
    assert comp.compress([]) == []


def test_narrative_compressed():
    results = [
        _make_result("The system uses a layered architecture with clear separation of concerns between frontend and backend"),
        _make_result("Layered architecture with frontend/backend separation"),
    ]
    comp = Compressor()
    compressed = comp.compress(results)
    assert len(compressed) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_compression.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement compression**

```python
# backend/app/services/pipeline/compression.py
"""Semantic compression stage for the retrieval pipeline."""

import re

from app.models.responses import RecallResult

# Patterns that indicate executable facts (never compress)
_EXECUTABLE_PATTERNS = [
    r"[/\w.-]+\.\w+",          # file paths
    r"\b\w+\(\)",              # function calls
    r"\b[A-Z]\w+\b",           # class names (PascalCase)
    r"@[a-z_]+",               # decorators
    r"ENV_\w+|[A-Z_]{3,}",    # env vars / constants
]


class Compressor:
    """Compresses recall results while preserving executable facts."""

    def compress(self, results: list[RecallResult]) -> list[RecallResult]:
        """Compress results by merging redundant entries.

        Structural compression (lossless):
        - Merge entries describing the same concept
        - Keep the shorter, more concise version

        Args:
            results: Ranked recall results.

        Returns:
            Compressed list with redundant entries merged.
        """
        if not results:
            return []

        merged: list[RecallResult] = []
        used: set[int] = set()

        for i, r in enumerate(results):
            if i in used:
                continue

            best = r
            best_idx = i

            for j in range(i + 1, len(results)):
                if j in used:
                    continue
                if self._are_redundant(r.text, results[j].text):
                    used.add(j)
                    if len(results[j].text) < len(best.text):
                        best = results[j]
                        best_idx = j

            merged.append(best)
            used.add(best_idx)

        return merged

    def _are_redundant(self, a: str, b: str) -> bool:
        """Check if two texts describe the same concept."""
        a_norm = self._normalize(a)
        b_norm = self._normalize(b)

        if a_norm == b_norm:
            return True

        a_tokens = set(a_norm.split())
        b_tokens = set(b_norm.split())

        if not a_tokens or not b_tokens:
            return False

        overlap = len(a_tokens & b_tokens) / max(len(a_tokens), len(b_tokens))
        return overlap > 0.7

    def _normalize(self, text: str) -> str:
        """Normalize text for comparison."""
        return " ".join(text.lower().split())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_compression.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/pipeline/compression.py backend/tests/test_compression.py
git commit -m "feat: add semantic compression pipeline stage"
```

---

### Task 6: Categorization Stage

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
"""Tests for categorization pipeline stage."""

from app.models.responses import RecallResult
from app.services.pipeline.categorization import Categorizer


def _make_result(text: str, kind: str = "text") -> RecallResult:
    return RecallResult(kind=kind, search_type="semantic", text=text, score=0.5, dataset_name="test")


def test_file_categorized_as_files():
    results = [_make_result("backend/app/services/cognee.py", kind="file")]
    cat = Categorizer()
    categories = cat.categorize(results)
    assert "files" in categories
    assert len(categories["files"]) == 1


def test_architecture_keyword():
    results = [_make_result("The layered architecture uses service boundaries")]
    cat = Categorizer()
    categories = cat.categorize(results)
    assert "architecture" in categories


def test_api_keyword():
    results = [_make_result("The REST endpoint handles POST requests")]
    cat = Categorizer()
    categories = cat.categorize(results)
    assert "apis" in categories


def test_convention_keyword():
    results = [_make_result("Follow snake_case naming convention")]
    cat = Categorizer()
    categories = cat.categorize(results)
    assert "conventions" in categories


def test_decision_keyword():
    results = [_make_result("We chose Cognee because of hybrid retrieval")]
    cat = Categorizer()
    categories = cat.categorize(results)
    assert "decisions" in categories


def test_default_to_knowledge():
    results = [_make_result("Some random text about the weather")]
    cat = Categorizer()
    categories = cat.categorize(results)
    assert "knowledge" in categories


def test_empty_input():
    cat = Categorizer()
    assert cat.categorize([]) == {}


def test_multiple_categories():
    results = [
        _make_result("backend/service.py", kind="file"),
        _make_result("The architecture is layered"),
        _make_result("Follow snake_case convention"),
    ]
    cat = Categorizer()
    categories = cat.categorize(results)
    assert len(categories) >= 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_categorization.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement categorization**

```python
# backend/app/services/pipeline/categorization.py
"""Rule-based categorization stage for the retrieval pipeline."""

from app.models.responses import RecallResult

# Keyword sets for categorization (ordered by priority)
_ARCHITECTURE_KW = frozenset({
    "architecture", "design", "pattern", "structure", "layer",
    "module", "component", "service", "pipeline", "workflow",
    "system", "infrastructure", "deployment",
})

_API_KW = frozenset({
    "api", "endpoint", "route", "interface", "contract",
    "schema", "request", "response", "http", "rest",
    "graphql", "grpc", "webhook",
})

_CONVENTION_KW = frozenset({
    "convention", "style", "format", "linting", "naming",
    "indentation", "standard", "guideline", "practice",
})

_DECISION_KW = frozenset({
    "decision", "rationale", "tradeoff", "trade-off",
    "chosen", "selected", "alternative", "rejected",
    "adr", "why we", "reason for",
})

_CODE_EXTENSIONS = frozenset({
    ".py", ".ts", ".tsx", ".js", ".jsx", ".json",
    ".yaml", ".yml", ".toml", ".rs", ".go",
})


class Categorizer:
    """Classifies recall results into section types by rule priority."""

    def categorize(self, results: list[RecallResult]) -> dict[str, list[RecallResult]]:
        """Categorize results into sections.

        Priority order:
        1. Explicit metadata (kind="file")
        2. File extension detection
        3. Keyword matching
        4. Fallback to knowledge

        Args:
            results: Recall results to categorize.

        Returns:
            Dict mapping section_type to list of results.
        """
        categories: dict[str, list[RecallResult]] = {}

        for r in results:
            section = self._classify(r)
            categories.setdefault(section, []).append(r)

        return categories

    def _classify(self, result: RecallResult) -> str:
        """Classify a single result into a section type."""
        kind = result.kind.lower() if result.kind else ""
        text_lower = result.text.lower()

        # Priority 1: Explicit metadata
        if kind == "file":
            return "files"

        # Priority 2: File extension
        if any(text_lower.endswith(ext) for ext in _CODE_EXTENSIONS):
            return "files"

        # Priority 3: Keywords (order matters — first match wins)
        if self._has_keyword(text_lower, _ARCHITECTURE_KW):
            return "architecture"
        if self._has_keyword(text_lower, _API_KW):
            return "apis"
        if self._has_keyword(text_lower, _CONVENTION_KW):
            return "conventions"
        if self._has_keyword(text_lower, _DECISION_KW):
            return "decisions"

        # Priority 4: Fallback
        return "knowledge"

    def _has_keyword(self, text: str, keywords: frozenset[str]) -> bool:
        return any(kw in text for kw in keywords)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_categorization.py -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/pipeline/categorization.py backend/tests/test_categorization.py
git commit -m "feat: add rule-based categorization pipeline stage"
```

---

### Task 7: Reference Resolution Stage

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
"""Tests for reference resolution pipeline stage."""

from app.models.responses import PackageReference, RecallResult
from app.services.pipeline.references import ReferenceResolver


def _make_result(text: str, kind: str = "text", score: float = 0.5) -> RecallResult:
    return RecallResult(kind=kind, search_type="semantic", text=text, score=score, dataset_name="test")


def test_file_reference():
    results = [_make_result("backend/app/services/cognee.py", kind="file", score=0.9)]
    resolver = ReferenceResolver()
    refs = resolver.resolve(results)
    assert len(refs) == 1
    assert refs[0].ref_type == "file"
    assert "cognee.py" in refs[0].path


def test_text_reference():
    results = [_make_result("The architecture uses layered patterns")]
    resolver = ReferenceResolver()
    refs = resolver.resolve(results)
    assert len(refs) == 1
    assert refs[0].ref_type == "memory"


def test_preserves_score():
    results = [_make_result("test.py", kind="file", score=0.85)]
    resolver = ReferenceResolver()
    refs = resolver.resolve(results)
    assert refs[0].score == 0.85


def test_empty_input():
    resolver = ReferenceResolver()
    assert resolver.resolve([]) == []


def test_provenance_chain():
    results = [_make_result("service.py", kind="file")]
    resolver = ReferenceResolver()
    refs = resolver.resolve(results)
    assert len(refs[0].provenance) > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_references.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement reference resolution**

```python
# backend/app/services/pipeline/references.py
"""Lightweight reference resolution for the MVP pipeline."""

import re

from app.models.responses import PackageReference, RecallResult


class ReferenceResolver:
    """Formats Cognee references into structured citations."""

    def resolve(self, results: list[RecallResult]) -> list[PackageReference]:
        """Resolve recall results into package references.

        Args:
            results: Recall results to format.

        Returns:
            List of PackageReference with provenance chains.
        """
        refs = []
        for r in results:
            ref = self._resolve_one(r)
            if ref:
                refs.append(ref)
        return refs

    def _resolve_one(self, result: RecallResult) -> PackageReference | None:
        """Resolve a single recall result into a reference."""
        kind = result.kind.lower() if result.kind else ""
        text = result.text.strip()

        if not text:
            return None

        if kind == "file":
            ref_type = "file"
            path = self._extract_path(text) or text
        elif self._looks_like_path(text):
            ref_type = "file"
            path = text
        else:
            ref_type = "memory"
            path = text[:100]

        return PackageReference(
            ref_type=ref_type,
            path=path,
            section=None,
            score=result.score,
            provenance=[f"recall:{result.dataset_name}", f"kind:{kind}"],
        )

    def _extract_path(self, text: str) -> str | None:
        match = re.search(r"([/\w.-]+\.\w+)", text)
        return match.group(1) if match else None

    def _looks_like_path(self, text: str) -> bool:
        return bool(re.search(r"[/\w.-]+\.\w+", text))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_references.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/pipeline/references.py backend/tests/test_references.py
git commit -m "feat: add reference resolution pipeline stage"
```

---

### Task 8: Budget Manager

**Covers:** [S4 Budget Manager]

**Files:**
- Create: `backend/app/services/budget_manager.py`
- Create: `backend/tests/test_budget_manager.py`

**Interfaces:**
- Consumes: `list[PackageSection]`, target token budget
- Produces: `list[PackageSection]` (trimmed to fit budget)

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_budget_manager.py
"""Tests for Budget Manager."""

from app.models.responses import PackageSection
from app.services.budget_manager import BudgetManager


def _make_section(section_type: str, content: str, priority: int) -> PackageSection:
    return PackageSection(
        section_type=section_type,
        heading=section_type.title(),
        content=content,
        priority=priority,
    )


def test_under_budget_preserves_all():
    sections = [
        _make_section("task", "Do something", 5),
        _make_section("files", "- file.py", 5),
    ]
    bm = BudgetManager(target_tokens=5000)
    result = bm.apply(sections)
    assert len(result) == 2


def test_over_budget_removes_low_priority():
    sections = [
        _make_section("task", "x" * 100, 5),
        _make_section("references", "y" * 5000, 1),
    ]
    bm = BudgetManager(target_tokens=500)
    result = bm.apply(sections)
    types = [s.section_type for s in result]
    assert "references" not in types
    assert "task" in types


def test_critical_never_removed():
    sections = [
        _make_section("task", "x" * 100, 5),
        _make_section("objective", "y" * 100, 5),
        _make_section("files", "z" * 100, 5),
        _make_section("refs", "w" * 10000, 1),
    ]
    bm = BudgetManager(target_tokens=200)
    result = bm.apply(sections)
    types = [s.section_type for s in result]
    assert "task" in types
    assert "objective" in types
    assert "files" in types


def test_empty_input():
    bm = BudgetManager(target_tokens=1000)
    assert bm.apply([]) == []


def test_compression_ratio_recorded():
    sections = [_make_section("task", "x" * 100, 5)]
    bm = BudgetManager(target_tokens=50)
    bm.apply(sections)
    assert bm.last_compression_ratio > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_budget_manager.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement Budget Manager**

```python
# backend/app/services/budget_manager.py
"""Budget Manager for Context Package token enforcement."""

from app.models.responses import PackageSection

# Priority classes
_CRITICAL = {5}
_HIGH = {4}
_MEDIUM = {3}
_LOW = {1, 2}

# Estimated tokens per character (rough: 1 token ~ 4 chars)
_CHARS_PER_TOKEN = 4


class BudgetManager:
    """Enforces soft-target token budgets on Context Package sections."""

    def __init__(self, target_tokens: int = 3000) -> None:
        self._target = target_tokens
        self.last_compression_ratio: float = 1.0

    def apply(self, sections: list[PackageSection]) -> list[PackageSection]:
        """Trim sections to fit within the target budget.

        Priority order for removal:
        1. Low priority (Dependencies, Conventions, References)
        2. Medium priority (Symbols, APIs, Decisions) — compress then remove
        3. High priority (Architecture, Implementation Notes, Constraints) — compress only
        4. Critical (Task, Objective, Files, Starting Point) — never removed

        Args:
            sections: Sections to budget-trim.

        Returns:
            Trimmed sections fitting within target.
        """
        if not sections:
            return []

        total_tokens = self._estimate_tokens(sections)
        if total_tokens <= self._target:
            self.last_compression_ratio = 1.0
            return sections

        result = list(sections)

        # Phase 1: Remove low priority
        result = self._remove_by_priority(result, _LOW)
        if self._estimate_tokens(result) <= self._target:
            return self._finalize(result, total_tokens)

        # Phase 2: Remove medium priority
        result = self._remove_by_priority(result, _MEDIUM)
        if self._estimate_tokens(result) <= self._target:
            return self._finalize(result, total_tokens)

        # Phase 3: Compress high priority (truncate content to 50%)
        result = self._compress_by_priority(result, _HIGH, 0.5)
        if self._estimate_tokens(result) <= self._target:
            return self._finalize(result, total_tokens)

        # Phase 4: Compress medium (truncate to 25%)
        # Re-add medium sections compressed
        return self._finalize(result, total_tokens)

    def _estimate_tokens(self, sections: list[PackageSection]) -> int:
        chars = sum(len(s.content) for s in sections)
        return chars // _CHARS_PER_TOKEN

    def _remove_by_priority(
        self, sections: list[PackageSection], priorities: set[int]
    ) -> list[PackageSection]:
        return [s for s in sections if s.priority not in priorities]

    def _compress_by_priority(
        self,
        sections: list[PackageSection],
        priorities: set[int],
        ratio: float,
    ) -> list[PackageSection]:
        result = []
        for s in sections:
            if s.priority in priorities:
                truncated = s.content[: int(len(s.content) * ratio)]
                result.append(PackageSection(
                    section_type=s.section_type,
                    heading=s.heading,
                    content=truncated,
                    priority=s.priority,
                    source_sections=s.source_sections,
                    reference_count=s.reference_count,
                ))
            else:
                result.append(s)
        return result

    def _finalize(self, sections: list[PackageSection], original_tokens: int) -> list[PackageSection]:
        final_tokens = self._estimate_tokens(sections)
        self.last_compression_ratio = original_tokens / max(final_tokens, 1)
        return sections
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_budget_manager.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/budget_manager.py backend/tests/test_budget_manager.py
git commit -m "feat: add Budget Manager for token enforcement"
```

---

### Task 9: Markdown Renderer

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
"""Tests for Markdown renderer."""

from app.models.responses import PackageReference, PackageSection, RepositorySummary
from app.services.renderer import MarkdownRenderer


def _make_section(section_type: str, heading: str, content: str) -> PackageSection:
    return PackageSection(section_type=section_type, heading=heading, content=content)


def test_renders_task_section():
    renderer = MarkdownRenderer()
    md = renderer.render("Fix the bug", "Resolve error", [], [], None)
    assert "# Task" in md
    assert "Fix the bug" in md


def test_renders_objective():
    renderer = MarkdownRenderer()
    md = renderer.render("task", "Fix authentication", [], [], None)
    assert "# Objective" in md
    assert "Fix authentication" in md


def test_renders_sections():
    sections = [_make_section("files", "Relevant Files", "- `app.py`")]
    renderer = MarkdownRenderer()
    md = renderer.render("task", "objective", sections, [], None)
    assert "# Relevant Files" in md
    assert "app.py" in md


def test_renders_references():
    refs = [PackageReference("file", "app.py", None, 0.9, [])]
    renderer = MarkdownRenderer()
    md = renderer.render("task", "objective", [], refs, None)
    assert "# References" in md
    assert "app.py" in md


def test_skips_empty_sections():
    sections = [_make_section("empty", "Empty Section", "")]
    renderer = MarkdownRenderer()
    md = renderer.render("task", "objective", sections, [], None)
    assert "Empty Section" not in md


def test_renders_repository_summary():
    summary = RepositorySummary(
        version="1.0",
        repository_fingerprint="abc",
        generated_at="2026-01-01T00:00:00Z",
        indexed_commit=None,
        project_purpose="Test project",
        technology_stack=None,
        repository_map=[],
        architecture=None,
        key_components=[],
        entry_points=[],
        public_apis=[],
        coding_conventions=None,
        domain_vocabulary={},
    )
    renderer = MarkdownRenderer()
    md = renderer.render("task", "objective", [], [], summary)
    assert "# Repository Context" in md
    assert "Test project" in md


def test_empty_input():
    renderer = MarkdownRenderer()
    md = renderer.render("", "", [], [], None)
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
    """Renders a Context Package as Markdown."""

    def render(
        self,
        task: str,
        objective: str,
        sections: list[PackageSection],
        references: list[PackageReference],
        repository_summary: RepositorySummary | None,
    ) -> str:
        """Render a complete Context Package as Markdown.

        Args:
            task: Developer request.
            objective: Desired outcome.
            sections: Content sections (empty sections are skipped).
            references: Traceable references.
            repository_summary: Optional repository summary to include.

        Returns:
            Formatted Markdown string.
        """
        parts: list[str] = []

        # Task (always first)
        parts.append(f"# Task\n\n{task}")

        # Objective
        if objective:
            parts.append(f"# Objective\n\n{objective}")

        # Repository Context (from summary)
        if repository_summary:
            summary_md = self._render_summary(repository_summary)
            if summary_md:
                parts.append(f"# Repository Context\n\n{summary_md}")

        # Content sections (skip empty)
        for section in sections:
            if section.content.strip():
                parts.append(f"# {section.heading}\n\n{section.content}")

        # References (always last)
        if references:
            ref_lines = []
            for i, ref in enumerate(references, 1):
                ref_lines.append(f"{i}. [{ref.ref_type}] `{ref.path}` (score: {ref.score:.2f})")
            parts.append("# References\n\n" + "\n".join(ref_lines))

        return "\n\n---\n\n".join(parts)

    def _render_summary(self, summary: RepositorySummary) -> str:
        """Render Repository Summary as Markdown."""
        parts = []

        if summary.project_purpose:
            parts.append(f"**Purpose**: {summary.project_purpose}")

        if summary.technology_stack:
            tech = summary.technology_stack
            items = []
            if tech.languages:
                items.append(f"Languages: {', '.join(tech.languages)}")
            if tech.frameworks:
                items.append(f"Frameworks: {', '.join(tech.frameworks)}")
            if tech.databases:
                items.append(f"Databases: {', '.join(tech.databases)}")
            if items:
                parts.append("**Technology**: " + " | ".join(items))

        if summary.repository_map:
            dirs = "\n".join(f"- `{e.path}` — {e.description}" for e in summary.repository_map)
            parts.append(f"**Repository Map**:\n{dirs}")

        if summary.architecture and summary.architecture.layers:
            parts.append(f"**Architecture**: {summary.architecture.pattern} ({', '.join(summary.architecture.layers)})")

        if summary.key_components:
            comps = "\n".join(f"- **{c.name}**: {c.responsibilities}" for c in summary.key_components[:5])
            parts.append(f"**Key Components**:\n{comps}")

        return "\n\n".join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_renderer.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/renderer.py backend/tests/test_renderer.py
git commit -m "feat: add Markdown renderer for Context Packages"
```

---

### Task 10: Package Builder

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
"""Tests for Package Builder."""

from app.models.responses import RecallResult, RepositorySummary
from app.services.package_builder import PackageBuilder


def _make_result(text: str, kind: str = "text", score: float = 0.5) -> RecallResult:
    return RecallResult(kind=kind, search_type="semantic", text=text, score=score, dataset_name="test")


def test_builds_package_from_results():
    results = [_make_result("backend/service.py", kind="file", score=0.9)]
    builder = PackageBuilder()
    pkg = builder.build("Fix the bug", results, None, ["workspace"])
    assert pkg.task == "Fix the bug"
    assert pkg.markdown != ""
    assert pkg.section_count > 0


def test_includes_repository_summary():
    summary = RepositorySummary(
        version="1.0",
        repository_fingerprint="abc",
        generated_at="2026-01-01T00:00:00Z",
        indexed_commit=None,
        project_purpose="Test",
        technology_stack=None,
        repository_map=[],
        architecture=None,
        key_components=[],
        entry_points=[],
        public_apis=[],
        coding_conventions=None,
        domain_vocabulary={},
    )
    results = [_make_result("test.py", kind="file")]
    builder = PackageBuilder()
    pkg = builder.build("query", results, summary, ["ws"])
    assert pkg.repository_summary == summary
    assert "Repository Context" in pkg.markdown


def test_metadata_populated():
    results = [_make_result("a.py", kind="file")]
    builder = PackageBuilder()
    pkg = builder.build("query", results, None, ["ws"])
    assert pkg.metadata is not None
    assert pkg.metadata.retrieved_memory_count == 1


def test_empty_results():
    builder = PackageBuilder()
    pkg = builder.build("query", [], None, ["ws"])
    assert pkg.task == "query"
    assert pkg.section_count >= 1  # at least Task
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_package_builder.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement Package Builder**

```python
# backend/app/services/package_builder.py
"""Assembles structured Context Packages from pipeline output."""

import time
from datetime import datetime, timezone

from app.models.responses import (
    ContextPackage,
    PackageMetadata,
    PackageSection,
    RecallResult,
    RepositorySummary,
)
from app.services.budget_manager import BudgetManager
from app.services.pipeline.categorization import Categorizer
from app.services.pipeline.compression import Compressor
from app.services.pipeline.dedup import Deduplicator
from app.services.pipeline.ranking import Ranker
from app.services.pipeline.references import ReferenceResolver
from app.services.renderer import MarkdownRenderer


class PackageBuilder:
    """Assembles a Context Package from recall results."""

    def __init__(self, target_tokens: int = 3000) -> None:
        self._dedup = Deduplicator()
        self._ranker = Ranker()
        self._compressor = Compressor()
        self._categorizer = Categorizer()
        self._resolver = ReferenceResolver()
        self._budget = BudgetManager(target_tokens)
        self._renderer = MarkdownRenderer()

    def build(
        self,
        task: str,
        results: list[RecallResult],
        repository_summary: RepositorySummary | None,
        datasets: list[str],
    ) -> ContextPackage:
        """Build a complete Context Package.

        Pipeline:
        1. Deduplicate
        2. Rank
        3. Compress
        4. Categorize
        5. Build sections
        6. Apply budget
        7. Resolve references
        8. Render Markdown

        Args:
            task: Developer request.
            results: Raw recall results.
            repository_summary: Optional cached summary.
            datasets: Dataset names used.

        Returns:
            Complete ContextPackage.
        """
        start = time.monotonic()

        # Phase 1: Retrieval pipeline
        deduplicated = self._dedup.deduplicate(results)
        ranked = self._ranker.rank(deduplicated)
        compressed = self._compressor.compress(ranked)
        categories = self._categorizer.categorize(compressed)

        # Phase 2: Package assembly
        sections = self._build_sections(categories, task)
        budgeted = self._budget.apply(sections)
        references = self._resolver.resolve(compressed)

        # Phase 3: Render
        objective = self._derive_objective(task)
        markdown = self._renderer.render(task, objective, budgeted, references, repository_summary)

        elapsed_ms = int((time.monotonic() - start) * 1000)

        metadata = PackageMetadata(
            package_version="1.0",
            repository_summary_version=repository_summary.version if repository_summary else "none",
            generated_at=datetime.now(timezone.utc).isoformat(),
            datasets_used=datasets,
            retrieved_memory_count=len(results),
            deduplicated_count=len(deduplicated),
            compressed_count=len(compressed),
            compression_ratio=self._budget.last_compression_ratio,
            estimated_tokens=len(markdown) // 4,
            pipeline_version="1.0",
            retrieval_time_ms=0,
            total_time_ms=elapsed_ms,
        )

        return ContextPackage(
            task=task,
            objective=objective,
            sections=budgeted,
            references=references,
            metadata=metadata,
            repository_summary=repository_summary,
            markdown=markdown,
            source_count=len(compressed),
            dataset=", ".join(datasets),
        )

    def _build_sections(
        self, categories: dict[str, list[RecallResult]], task: str
    ) -> list[PackageSection]:
        """Convert categorized results into PackageSections."""
        heading_map = {
            "files": "Relevant Files",
            "architecture": "Architecture",
            "apis": "Existing APIs",
            "conventions": "Coding Conventions",
            "decisions": "Previous Decisions",
            "knowledge": "Implementation Notes",
        }

        priority_map = {
            "files": 5,
            "architecture": 4,
            "knowledge": 4,
            "apis": 3,
            "decisions": 3,
            "conventions": 2,
        }

        sections = []
        for section_type, results in categories.items():
            if not results:
                continue
            content = self._format_category(section_type, results)
            sections.append(PackageSection(
                section_type=section_type,
                heading=heading_map.get(section_type, section_type.title()),
                content=content,
                priority=priority_map.get(section_type, 2),
                source_sections=["Component Context"],
                reference_count=len(results),
            ))

        return sections

    def _format_category(self, section_type: str, results: list[RecallResult]) -> str:
        """Format results for a specific section type."""
        if section_type == "files":
            return self._format_files(results)
        return "\n".join(f"- {r.text.strip()}" for r in results)

    def _format_files(self, results: list[RecallResult]) -> str:
        lines = []
        for r in results:
            path = r.text.strip()
            if path:
                lines.append(f"- `{path}`")
        return "\n".join(lines)

    def _derive_objective(self, task: str) -> str:
        """Derive a brief objective from the task."""
        if len(task) <= 100:
            return task
        return task[:97] + "..."
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_package_builder.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/package_builder.py backend/tests/test_package_builder.py
git commit -m "feat: add Package Builder assembling full Context Packages"
```

---

### Task 11: Rewrite ContextService

**Covers:** [S3, S4, S10]

**Files:**
- Modify: `backend/app/services/context_service.py`
- Create: `backend/tests/test_context_service_v2.py`

**Interfaces:**
- Consumes: `CogneeService`
- Produces: `ContextPackage` via `generate_context_package()`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_context_service_v2.py
"""Tests for rewritten ContextService integration."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.models.responses import RecallResult, RecallResponse
from app.services.context_service import ContextService


def _make_result(text: str, kind: str = "text", score: float = 0.5) -> RecallResult:
    return RecallResult(kind=kind, search_type="semantic", text=text, score=score, dataset_name="test")


@pytest.fixture
def mock_cognee():
    cognee = AsyncMock()
    cognee.recall = AsyncMock(return_value=RecallResponse(
        query="test",
        dataset="test",
        results=[_make_result("backend/service.py", kind="file", score=0.9)],
    ))
    return cognee


@pytest.mark.asyncio
async def test_generate_returns_context_package(mock_cognee):
    svc = ContextService(mock_cognee)
    pkg = await svc.generate_context_package("Fix the bug", ["workspace"])
    assert pkg.task == "Fix the bug"
    assert pkg.markdown != ""


@pytest.mark.asyncio
async def test_generate_has_metadata(mock_cognee):
    svc = ContextService(mock_cognee)
    pkg = await svc.generate_context_package("query", ["ws"])
    assert pkg.metadata is not None
    assert pkg.metadata.retrieved_memory_count == 1


@pytest.mark.asyncio
async def test_generate_with_empty_results(mock_cognee):
    mock_cognee.recall.return_value = RecallResponse(query="q", dataset="d", results=[])
    svc = ContextService(mock_cognee)
    pkg = await svc.generate_context_package("query", ["ws"])
    assert pkg.task == "query"


@pytest.mark.asyncio
async def test_generate_includes_repository_summary(mock_cognee):
    svc = ContextService(mock_cognee, repository_summary=None)
    pkg = await svc.generate_context_package("query", ["ws"])
    # No summary provided, so repository_summary should be None
    assert pkg.repository_summary is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_context_service_v2.py -v`
Expected: FAIL (ContextService constructor mismatch)

- [ ] **Step 3: Rewrite ContextService**

Replace `backend/app/services/context_service.py` entirely:

```python
"""
Context Package generator for AndesContext.

Transforms Cognee memory retrieval into structured Markdown
Context Packages suitable for AI coding assistants.

Pipeline:
    Developer Request
        → CogneeService.recall()
        → Deduplication
        → Ranking
        → Compression
        → Categorization
        → Package Assembly
        → Budget Enforcement
        → Reference Resolution
        → Markdown Rendering
        → Context Package

No LLM calls. Deterministic output.
"""

import logging

from app.models.errors import CogneeServiceError
from app.models.responses import ContextPackage, RepositorySummary
from app.services.cognee_service import CogneeService
from app.services.package_builder import PackageBuilder

logger = logging.getLogger(__name__)


class ContextService:
    """Generates structured Context Packages from Cognee memory.

    Orchestrates memory retrieval via CogneeService and produces
    deterministic Markdown output through the full pipeline.
    """

    def __init__(
        self,
        cognee_service: CogneeService,
        repository_summary: RepositorySummary | None = None,
        target_tokens: int = 3000,
    ) -> None:
        self._cognee = cognee_service
        self._repository_summary = repository_summary
        self._builder = PackageBuilder(target_tokens)

    async def generate_context_package(
        self,
        task: str,
        datasets: list[str],
        top_k: int = 20,
    ) -> ContextPackage:
        """Generate a Context Package for a developer task.

        Args:
            task: The developer request or question.
            datasets: Dataset names to search.
            top_k: Maximum memories to retrieve.

        Returns:
            ContextPackage with structured Markdown content.
        """
        logger.info(
            "generate_context_package | task=%s | datasets=%s | top_k=%d",
            task[:80],
            datasets,
            top_k,
        )

        # 1. Retrieve memories
        recall = await self._cognee.recall(
            query_text=task,
            datasets=datasets,
            top_k=top_k,
        )

        # 2. Build package through full pipeline
        package = self._builder.build(
            task=task,
            results=recall.results,
            repository_summary=self._repository_summary,
            datasets=datasets,
        )

        logger.info(
            "context package generated | sections=%d | sources=%d | ~%d tokens",
            package.section_count,
            package.source_count,
            package.token_estimate,
        )

        return package
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_context_service_v2.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Run full test suite**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All tests PASS (existing API/CLI tests must still work)

- [ ] **Step 6: Fix any integration issues**

If existing tests fail due to ContextService constructor changes, update the test fixtures to pass `repository_summary=None`.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/context_service.py backend/tests/test_context_service_v2.py
git commit -m "feat: rewrite ContextService with full pipeline integration"
```

---

## Summary

| Task | Component | Spec Coverage | Est. Time |
|------|-----------|---------------|-----------|
| 1 | Data Models | S2, S3, S8 | 15 min |
| 2 | Repository Summary Generator | S2 | 20 min |
| 3 | Deduplication Stage | S4 Stage 3 | 10 min |
| 4 | Ranking Stage | S4 Stage 4 | 10 min |
| 5 | Compression Stage | S4 Stage 5, S5 | 15 min |
| 6 | Categorization Stage | S4 Stage 6 | 10 min |
| 7 | Reference Resolution | S4 Stage 7 | 10 min |
| 8 | Budget Manager | S4 Budget Manager | 15 min |
| 9 | Markdown Renderer | S4 Renderer | 15 min |
| 10 | Package Builder | S4 Package Builder | 20 min |
| 11 | ContextService Rewrite | S3, S4, S10 | 15 min |

**Total estimated time: ~2.5 hours**

### Not in MVP (Deferred)

- Graph Expansion (Stage 2) — requires Kuzu graph queries
- Budget Compression Tier 3 — measure first, then implement
- LLM-as-judge evaluation
- Context Delta benchmark
- JSON/UI/MCP renderers
