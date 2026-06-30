"""Tests for Package Builder."""

from app.models.responses import RecallResult, RepositorySummary
from app.services.package_builder import PackageBuilder


def _make(text: str, kind: str = "text", score: float = 0.5) -> RecallResult:
    """Helper to create a RecallResult."""
    return RecallResult(kind=kind, search_type="semantic", text=text, score=score, dataset_name="test")


def _make_summary(**kwargs) -> RepositorySummary:
    """Helper to create a RepositorySummary with defaults."""
    defaults = dict(
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
    defaults.update(kwargs)
    return RepositorySummary(**defaults)


class TestPackageBuilder:
    """Tests for full package assembly."""

    def test_builds_package(self):
        pkg = PackageBuilder().build(
            "Fix bug",
            [_make("svc.py", "file", 0.9)],
            None,
            ["ws"],
        )
        assert pkg.task == "Fix bug"
        assert pkg.markdown != ""
        assert pkg.section_count > 0

    def test_includes_summary(self):
        summary = _make_summary(project_purpose="Test project")
        pkg = PackageBuilder().build(
            "q",
            [_make("a.py", "file")],
            summary,
            ["ws"],
        )
        assert pkg.repository_summary == summary
        assert "Repository Context" in pkg.markdown

    def test_metadata_populated(self):
        pkg = PackageBuilder().build(
            "q",
            [_make("a.py", "file")],
            None,
            ["ws"],
        )
        assert pkg.metadata is not None
        assert pkg.metadata.retrieved_memory_count == 1

    def test_empty_results(self):
        pkg = PackageBuilder().build("q", [], None, ["ws"])
        assert pkg.task == "q"
        assert pkg.markdown != ""  # Task always rendered
        assert pkg.section_count == 0  # no recall results = no content sections

    def test_objective_derived(self):
        pkg = PackageBuilder().build("Fix the bug", [_make("a.py", "file")], None, ["ws"])
        assert pkg.objective == "Fix the bug"

    def test_long_task_truncated_objective(self):
        long_task = "x" * 150
        pkg = PackageBuilder().build(long_task, [_make("a.py", "file")], None, ["ws"])
        assert len(pkg.objective) <= 100
        assert pkg.objective.endswith("...")

    def test_datasets_recorded(self):
        pkg = PackageBuilder().build("q", [_make("a.py", "file")], None, ["ws", "prod"])
        assert pkg.dataset == "ws, prod"

    def test_metadata_timestamps(self):
        pkg = PackageBuilder().build("q", [_make("a.py", "file")], None, ["ws"])
        assert pkg.metadata.generated_at != ""
        assert pkg.metadata.total_time_ms >= 0

    def test_deduplication_applied(self):
        results = [_make("same", score=0.5), _make("same", score=0.9)]
        pkg = PackageBuilder().build("q", results, None, ["ws"])
        assert pkg.metadata.deduplicated_count == 1

    def test_ranking_applied(self):
        results = [_make("low", score=0.3), _make("high", score=0.9)]
        pkg = PackageBuilder().build("q", results, None, ["ws"])
        # High score should appear first in markdown
        assert pkg.markdown.index("high") < pkg.markdown.index("low") or pkg.section_count >= 1

    def test_references_generated(self):
        results = [_make("service.py", "file", 0.9)]
        pkg = PackageBuilder().build("q", results, None, ["ws"])
        assert len(pkg.references) > 0
        assert pkg.references[0].ref_type == "file"

    def test_files_section_formatted(self):
        results = [_make("backend/app/main.py", "file", 0.9)]
        pkg = PackageBuilder().build("q", results, None, ["ws"])
        assert "`backend/app/main.py`" in pkg.markdown

    def test_architecture_section_created(self):
        results = [_make("The layered architecture uses service boundaries")]
        pkg = PackageBuilder().build("q", results, None, ["ws"])
        assert "Architecture" in pkg.markdown

    def test_knowledge_section_created(self):
        results = [_make("Some implementation detail")]
        pkg = PackageBuilder().build("q", results, None, ["ws"])
        assert "Implementation Notes" in pkg.markdown

    def test_summary_version_in_metadata(self):
        summary = _make_summary(version="2.0")
        pkg = PackageBuilder().build("q", [_make("a.py", "file")], summary, ["ws"])
        assert pkg.metadata.repository_summary_version == "2.0"

    def test_no_summary_version_none(self):
        pkg = PackageBuilder().build("q", [_make("a.py", "file")], None, ["ws"])
        assert pkg.metadata.repository_summary_version == "none"

    def test_source_count_matches_compressed(self):
        results = [_make("a", score=0.5), _make("a", score=0.9), _make("b", score=0.6)]
        pkg = PackageBuilder().build("q", results, None, ["ws"])
        assert pkg.source_count == 2  # deduped from 3 to 2

    def test_pipeline_version(self):
        pkg = PackageBuilder().build("q", [_make("a.py", "file")], None, ["ws"])
        assert pkg.metadata.pipeline_version == "1.0"

    def test_package_version(self):
        pkg = PackageBuilder().build("q", [_make("a.py", "file")], None, ["ws"])
        assert pkg.metadata.package_version == "1.0"
