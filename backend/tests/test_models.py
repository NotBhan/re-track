"""Tests for Context Package data models.

Covers Milestone 1 — Core Data Model:
- Task 1.1: Repository Summary models
- Task 1.2: Context Package models (PackageReference, PackageSection, PackageMetadata, ContextPackage)
- Task 1.3: Serialization and construction tests
"""

import pytest

from app.models.responses import (
    ArchitectureInfo,
    APIInfo,
    ComponentInfo,
    ContextPackage,
    ConventionInfo,
    DirectoryEntry,
    EntryPoint,
    PackageMetadata,
    PackageReference,
    PackageSection,
    RepositorySummary,
    TechnologyStack,
)


# =============================================================================
# Task 1.1: Repository Summary Models
# =============================================================================


class TestTechnologyStack:
    """Tests for TechnologyStack data model."""

    def test_construction(self):
        stack = TechnologyStack(
            languages=["Python", "TypeScript"],
            frameworks=["FastAPI", "React"],
            databases=["LanceDB", "Kuzu"],
            dependencies=["cognee", "pydantic"],
        )
        assert stack.languages == ["Python", "TypeScript"]
        assert len(stack.frameworks) == 2

    def test_empty_construction(self):
        stack = TechnologyStack(languages=[], frameworks=[], databases=[], dependencies=[])
        assert stack.languages == []
        assert stack.frameworks == []

    def test_frozen(self):
        stack = TechnologyStack(["Python"], [], [], [])
        with pytest.raises(AttributeError):
            stack.languages = ["Rust"]


class TestDirectoryEntry:
    """Tests for DirectoryEntry data model."""

    def test_construction(self):
        entry = DirectoryEntry(path="backend/app/services", description="Backend services")
        assert entry.path == "backend/app/services"
        assert entry.description == "Backend services"

    def test_frozen(self):
        entry = DirectoryEntry(path="src", description="Source")
        with pytest.raises(AttributeError):
            entry.path = "lib"


class TestArchitectureInfo:
    """Tests for ArchitectureInfo data model."""

    def test_construction(self):
        arch = ArchitectureInfo(
            pattern="layered",
            layers=["CLI", "API", "Services"],
            boundaries=["Backend/Frontend via Tauri IPC"],
            major_flows=["Index → Recall → Package"],
        )
        assert arch.pattern == "layered"
        assert len(arch.layers) == 3

    def test_empty_construction(self):
        arch = ArchitectureInfo(pattern="", layers=[], boundaries=[], major_flows=[])
        assert arch.pattern == ""

    def test_frozen(self):
        arch = ArchitectureInfo("monolith", [], [], [])
        with pytest.raises(AttributeError):
            arch.pattern = "microservice"


class TestComponentInfo:
    """Tests for ComponentInfo data model."""

    def test_construction(self):
        comp = ComponentInfo(
            name="CogneeService",
            responsibilities="Thin wrapper around Cognee APIs",
            relationships=["Used by IndexingService", "Used by ContextService"],
        )
        assert comp.name == "CogneeService"
        assert len(comp.relationships) == 2

    def test_frozen(self):
        comp = ComponentInfo("Service", "Duty", [])
        with pytest.raises(AttributeError):
            comp.name = "Other"


class TestEntryPoint:
    """Tests for EntryPoint data model."""

    def test_construction(self):
        ep = EntryPoint(name="cli", path="backend/retrack.py", type="cli")
        assert ep.type == "cli"
        assert ep.name == "cli"

    def test_frozen(self):
        ep = EntryPoint("api", "app.py", "startup")
        with pytest.raises(AttributeError):
            ep.type = "cli"


class TestAPIInfo:
    """Tests for APIInfo data model."""

    def test_construction(self):
        api = APIInfo(
            name="recall",
            signature="recall(query, datasets, top_k)",
            description="Retrieve memories",
        )
        assert api.name == "recall"
        assert "top_k" in api.signature

    def test_frozen(self):
        api = APIInfo("get", "get()", "Fetch")
        with pytest.raises(AttributeError):
            api.name = "post"


class TestConventionInfo:
    """Tests for ConventionInfo data model."""

    def test_construction(self):
        conv = ConventionInfo(
            naming="snake_case",
            formatting="black",
            patterns=["service-per-domain", "frozen-dataclasses"],
        )
        assert conv.naming == "snake_case"
        assert len(conv.patterns) == 2

    def test_frozen(self):
        conv = ConventionInfo("camelCase", "prettier", [])
        with pytest.raises(AttributeError):
            conv.naming = "snake_case"


class TestRepositorySummary:
    """Tests for RepositorySummary data model."""

    def test_construction(self):
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
        assert summary.project_purpose == "Local-first AI memory for software development"

    def test_with_optional_commit(self):
        summary = RepositorySummary(
            version="1.0",
            repository_fingerprint="abc",
            generated_at="2026-01-01T00:00:00Z",
            indexed_commit="a1b2c3d",
            project_purpose="Test",
            technology_stack=TechnologyStack([], [], [], []),
            repository_map=[],
            architecture=ArchitectureInfo("", [], [], []),
            key_components=[],
            entry_points=[],
            public_apis=[],
            coding_conventions=ConventionInfo("", "", []),
            domain_vocabulary={},
        )
        assert summary.indexed_commit == "a1b2c3d"

    def test_frozen(self):
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
        with pytest.raises(AttributeError):
            summary.version = "2.0"

    def test_with_full_data(self):
        summary = RepositorySummary(
            version="1.0",
            repository_fingerprint="full123",
            generated_at="2026-06-30T12:00:00Z",
            indexed_commit="abc123",
            project_purpose="Full test repository",
            technology_stack=TechnologyStack(
                languages=["Python", "TypeScript"],
                frameworks=["FastAPI", "React"],
                databases=["LanceDB", "Kuzu"],
                dependencies=["cognee", "pydantic"],
            ),
            repository_map=[
                DirectoryEntry(path="backend", description="Backend services"),
                DirectoryEntry(path="src", description="Frontend source"),
            ],
            architecture=ArchitectureInfo(
                pattern="layered",
                layers=["CLI", "API", "Services"],
                boundaries=["IPC"],
                major_flows=["Index → Recall"],
            ),
            key_components=[
                ComponentInfo(name="CogneeService", responsibilities="Wrap Cognee", relationships=[]),
            ],
            entry_points=[EntryPoint(name="cli", path="cli.py", type="cli")],
            public_apis=[APIInfo(name="recall", signature="recall()", description="Retrieve")],
            coding_conventions=ConventionInfo(naming="snake_case", formatting="black", patterns=[]),
            domain_vocabulary={"cognee": "Memory layer", "recall": "Search operation"},
        )
        assert len(summary.repository_map) == 2
        assert len(summary.technology_stack.languages) == 2
        assert summary.domain_vocabulary["cognee"] == "Memory layer"


# =============================================================================
# Task 1.2: Context Package Models
# =============================================================================


class TestPackageReference:
    """Tests for PackageReference data model."""

    def test_construction(self):
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

    def test_with_none_section(self):
        ref = PackageReference("memory", "some text", None, 0.5, [])
        assert ref.section is None

    def test_frozen(self):
        ref = PackageReference("file", "test.py", None, 0.5, [])
        with pytest.raises(AttributeError):
            ref.score = 1.0

    def test_various_ref_types(self):
        for ref_type in ["file", "symbol", "memory", "doc", "dir"]:
            ref = PackageReference(ref_type, "path", None, 0.5, [])
            assert ref.ref_type == ref_type


class TestPackageSection:
    """Tests for PackageSection data model."""

    def test_construction_with_defaults(self):
        section = PackageSection(
            section_type="knowledge",
            heading="Implementation Notes",
            content="- Fact 1\n- Fact 2",
        )
        assert section.section_type == "knowledge"
        assert section.priority == 3
        assert section.source_sections == []
        assert section.reference_count == 0

    def test_construction_with_all_fields(self):
        section = PackageSection(
            section_type="files",
            heading="Relevant Files",
            content="- `backend/app/services/cognee_service.py`",
            priority=5,
            source_sections=["Component Context", "Architectural Context"],
            reference_count=1,
        )
        assert section.priority == 5
        assert section.reference_count == 1
        assert len(section.source_sections) == 2

    def test_priority_range(self):
        for p in range(1, 6):
            section = PackageSection("test", "Test", "content", priority=p)
            assert section.priority == p

    def test_frozen(self):
        section = PackageSection("test", "Test", "content")
        with pytest.raises(AttributeError):
            section.content = "modified"


class TestPackageMetadata:
    """Tests for PackageMetadata data model."""

    def test_construction(self):
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
        assert meta.retrieved_memory_count == 20

    def test_frozen(self):
        meta = PackageMetadata(
            package_version="1.0",
            repository_summary_version="1.0",
            generated_at="2026-01-01T00:00:00Z",
            datasets_used=[],
            retrieved_memory_count=0,
            deduplicated_count=0,
            compressed_count=0,
            compression_ratio=1.0,
            estimated_tokens=0,
            pipeline_version="1.0",
            retrieval_time_ms=0,
            total_time_ms=0,
        )
        with pytest.raises(AttributeError):
            meta.estimated_tokens = 999


class TestContextPackage:
    """Tests for ContextPackage data model."""

    def test_construction_with_all_fields(self):
        pkg = ContextPackage(
            task="Fix the bug",
            objective="Resolve the authentication error",
            sections=[],
            references=[],
            metadata=None,
            repository_summary=None,
            markdown="# Task\n\nFix the bug",
            source_count=0,
            dataset="test",
        )
        assert pkg.task == "Fix the bug"
        assert pkg.section_count == 0
        assert pkg.token_estimate == 4  # len("# Task\n\nFix the bug") // 4

    def test_construction_with_defaults(self):
        pkg = ContextPackage(task="query", objective="outcome")
        assert pkg.sections == []
        assert pkg.references == []
        assert pkg.markdown == ""
        assert pkg.source_count == 0
        assert pkg.dataset == ""
        assert pkg.metadata is None
        assert pkg.repository_summary is None

    def test_token_estimate_with_metadata(self):
        meta = PackageMetadata(
            package_version="1.0",
            repository_summary_version="1.0",
            generated_at="2026-01-01T00:00:00Z",
            datasets_used=[],
            retrieved_memory_count=0,
            deduplicated_count=0,
            compressed_count=0,
            compression_ratio=1.0,
            estimated_tokens=1500,
            pipeline_version="1.0",
            retrieval_time_ms=0,
            total_time_ms=0,
        )
        pkg = ContextPackage(task="q", objective="o", metadata=meta)
        assert pkg.token_estimate == 1500

    def test_token_estimate_fallback_without_metadata(self):
        pkg = ContextPackage(task="q", objective="o", markdown="x" * 400)
        assert pkg.token_estimate == 100  # 400 // 4

    def test_section_count_with_sections(self):
        sections = [
            PackageSection("files", "Files", "content"),
            PackageSection("architecture", "Arch", "content"),
        ]
        pkg = ContextPackage(task="q", objective="o", sections=sections)
        assert pkg.section_count == 2

    def test_with_repository_summary(self):
        summary = RepositorySummary(
            version="1.0",
            repository_fingerprint="abc",
            generated_at="2026-01-01T00:00:00Z",
            indexed_commit=None,
            project_purpose="Test",
            technology_stack=TechnologyStack([], [], [], []),
            repository_map=[],
            architecture=ArchitectureInfo("", [], [], []),
            key_components=[],
            entry_points=[],
            public_apis=[],
            coding_conventions=ConventionInfo("", "", []),
            domain_vocabulary={},
        )
        pkg = ContextPackage(task="q", objective="o", repository_summary=summary)
        assert pkg.repository_summary is not None
        assert pkg.repository_summary.version == "1.0"

    def test_with_references(self):
        refs = [
            PackageReference("file", "a.py", None, 0.9, []),
            PackageReference("symbol", "main()", None, 0.8, []),
        ]
        pkg = ContextPackage(task="q", objective="o", references=refs)
        assert len(pkg.references) == 2

    def test_frozen(self):
        pkg = ContextPackage(task="q", objective="o")
        with pytest.raises(AttributeError):
            pkg.task = "modified"


# =============================================================================
# Task 1.3: Serialization and Construction
# =============================================================================


class TestSerialization:
    """Tests for data model serialization patterns."""

    def test_context_package_construction(self):
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
        assert pkg.token_estimate == 3  # len("# Task\n\nFix bug") // 4 == 14 // 4

    def test_context_package_with_metadata_token_estimate(self):
        meta = PackageMetadata(
            package_version="1.0",
            repository_summary_version="1.0",
            generated_at="2026-01-01T00:00:00Z",
            datasets_used=[],
            retrieved_memory_count=0,
            deduplicated_count=0,
            compressed_count=0,
            compression_ratio=1.0,
            estimated_tokens=1500,
            pipeline_version="1.0",
            retrieval_time_ms=0,
            total_time_ms=0,
        )
        pkg = ContextPackage(task="q", objective="o", metadata=meta)
        assert pkg.token_estimate == 1500

    def test_context_package_defaults(self):
        pkg = ContextPackage(task="q", objective="o")
        assert pkg.sections == []
        assert pkg.references == []
        assert pkg.markdown == ""
        assert pkg.source_count == 0

    def test_repository_summary_defaults(self):
        """RepositorySummary has no defaults — all fields required."""
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
        assert summary.version == "1.0"

    def test_section_type_is_str_enum(self):
        """SectionType remains a str enum for backwards compatibility."""
        from app.models.responses import SectionType
        assert SectionType.TASK.value == "task"
        assert SectionType.FILES.value == "files"
        assert str(SectionType.ARCHITECTURE) == "SectionType.ARCHITECTURE"

    def test_package_section_type_is_str(self):
        """New PackageSection uses str for section_type, not SectionType enum."""
        section = PackageSection(section_type="files", heading="Files", content="content")
        assert section.section_type == "files"
        assert isinstance(section.section_type, str)

    def test_context_package_backwards_compat(self):
        """ContextPackage construction with old-style fields still works."""
        pkg = ContextPackage(task="q", objective="o", markdown="content")
        assert pkg.task == "q"
        assert pkg.markdown == "content"

    def test_full_roundtrip(self):
        """Construct a complete package with all model types."""
        summary = RepositorySummary(
            version="1.0",
            repository_fingerprint="fp123",
            generated_at="2026-06-30T00:00:00Z",
            indexed_commit="abc",
            project_purpose="Test project",
            technology_stack=TechnologyStack(["Python"], ["FastAPI"], ["LanceDB"], ["cognee"]),
            repository_map=[DirectoryEntry(path="backend", description="Backend")],
            architecture=ArchitectureInfo("layered", ["CLI", "API"], [], []),
            key_components=[ComponentInfo("CogneeService", "Wrapper", [])],
            entry_points=[EntryPoint("cli", "cli.py", "cli")],
            public_apis=[APIInfo("recall", "recall()", "Search")],
            coding_conventions=ConventionInfo("snake_case", "black", []),
            domain_vocabulary={"cognee": "Memory layer"},
        )
        sections = [
            PackageSection("files", "Relevant Files", "- `service.py`", priority=5),
            PackageSection("architecture", "Architecture", "Layered", priority=4),
        ]
        refs = [
            PackageReference("file", "service.py", "Services", 0.9, ["memory:1"]),
        ]
        meta = PackageMetadata(
            package_version="1.0",
            repository_summary_version="1.0",
            generated_at="2026-06-30T00:00:00Z",
            datasets_used=["workspace"],
            retrieved_memory_count=20,
            deduplicated_count=15,
            compressed_count=12,
            compression_ratio=1.33,
            estimated_tokens=2500,
            pipeline_version="1.0",
            retrieval_time_ms=5000,
            total_time_ms=8000,
        )
        pkg = ContextPackage(
            task="Add Rust support",
            objective="Add .rs to indexing",
            sections=sections,
            references=refs,
            metadata=meta,
            repository_summary=summary,
            markdown="# Task\n\nAdd Rust support",
            source_count=12,
            dataset="workspace",
        )
        assert pkg.task == "Add Rust support"
        assert pkg.section_count == 2
        assert pkg.token_estimate == 2500
        assert pkg.repository_summary.version == "1.0"
        assert len(pkg.references) == 1
        assert pkg.references[0].ref_type == "file"
        assert pkg.metadata.compression_ratio == 1.33
