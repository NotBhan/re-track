"""Tests for Markdown Renderer."""

from app.models.responses import (
    ArchitectureInfo,
    ComponentInfo,
    DirectoryEntry,
    PackageReference,
    PackageSection,
    RepositorySummary,
    TechnologyStack,
)
from app.services.renderer import MarkdownRenderer


def _sec(section_type: str, heading: str, content: str) -> PackageSection:
    """Helper to create a PackageSection."""
    return PackageSection(section_type=section_type, heading=heading, content=content)


def _make_summary(**kwargs) -> RepositorySummary:
    """Helper to create a RepositorySummary with defaults."""
    defaults = dict(
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
    defaults.update(kwargs)
    return RepositorySummary(**defaults)


class TestMarkdownRenderer:
    """Tests for Markdown rendering."""

    def test_renders_task(self):
        md = MarkdownRenderer().render("Fix bug", "Resolve error", [], [], None)
        assert "# Task" in md
        assert "Fix bug" in md

    def test_renders_objective(self):
        md = MarkdownRenderer().render("t", "Fix auth", [], [], None)
        assert "# Objective" in md
        assert "Fix auth" in md

    def test_renders_sections(self):
        sections = [_sec("files", "Files", "- `app.py`")]
        md = MarkdownRenderer().render("t", "o", sections, [], None)
        assert "# Files" in md
        assert "app.py" in md

    def test_renders_references(self):
        refs = [PackageReference("file", "app.py", None, 0.9, [])]
        md = MarkdownRenderer().render("t", "o", [], refs, None)
        assert "# References" in md
        assert "app.py" in md
        assert "0.90" in md

    def test_skips_empty_sections(self):
        sections = [_sec("empty", "Empty Section", "")]
        md = MarkdownRenderer().render("t", "o", sections, [], None)
        assert "Empty Section" not in md

    def test_renders_repository_summary(self):
        summary = _make_summary(project_purpose="Test project purpose")
        md = MarkdownRenderer().render("t", "o", [], [], summary)
        assert "# Repository Context" in md
        assert "Test project purpose" in md

    def test_empty_input(self):
        md = MarkdownRenderer().render("", "", [], [], None)
        assert "# Task" in md

    def test_sections_separated_by_divider(self):
        sections = [_sec("files", "Files", "content")]
        md = MarkdownRenderer().render("t", "o", sections, [], None)
        assert "---" in md

    def test_summary_with_technology(self):
        summary = _make_summary(
            technology_stack=TechnologyStack(
                languages=["Python", "TypeScript"],
                frameworks=["FastAPI"],
                databases=["LanceDB"],
                dependencies=[],
            )
        )
        md = MarkdownRenderer().render("t", "o", [], [], summary)
        assert "Python" in md
        assert "TypeScript" in md

    def test_summary_with_repository_map(self):
        summary = _make_summary(
            repository_map=[DirectoryEntry(path="backend", description="Backend services")]
        )
        md = MarkdownRenderer().render("t", "o", [], [], summary)
        assert "backend" in md
        assert "Backend services" in md

    def test_summary_with_architecture(self):
        summary = _make_summary(
            architecture=ArchitectureInfo(
                pattern="layered",
                layers=["CLI", "API", "Services"],
                boundaries=[],
                major_flows=[],
            )
        )
        md = MarkdownRenderer().render("t", "o", [], [], summary)
        assert "layered" in md
        assert "CLI" in md

    def test_summary_with_components(self):
        summary = _make_summary(
            key_components=[ComponentInfo("CogneeService", "Wrapper", [])]
        )
        md = MarkdownRenderer().render("t", "o", [], [], summary)
        assert "CogneeService" in md

    def test_multiple_references_numbered(self):
        refs = [
            PackageReference("file", "a.py", None, 0.9, []),
            PackageReference("file", "b.py", None, 0.8, []),
        ]
        md = MarkdownRenderer().render("t", "o", [], refs, None)
        assert "1." in md
        assert "2." in md

    def test_no_objective_if_empty(self):
        md = MarkdownRenderer().render("t", "", [], [], None)
        assert "# Objective" not in md

    def test_task_always_first(self):
        sections = [_sec("files", "Files", "content")]
        refs = [PackageReference("file", "a.py", None, 0.9, [])]
        md = MarkdownRenderer().render("task", "obj", sections, refs, None)
        lines = md.split("\n")
        task_line = next(i for i, l in enumerate(lines) if "# Task" in l)
        assert task_line == 0
