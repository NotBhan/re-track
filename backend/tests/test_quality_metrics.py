"""Automated structural quality metrics for Context Packages.

Validates that generated packages meet quality standards:
- No duplicate references
- Section utilization > 50%
- Token estimates in reasonable range
- Metadata fully populated
"""

from app.models.responses import RecallResult
from app.services.package_builder import PackageBuilder


def _make_result(text: str, kind: str = "text", score: float = 0.5) -> RecallResult:
    """Helper to create a RecallResult."""
    return RecallResult(kind=kind, search_type="semantic", text=text, score=score, dataset_name="test")


def _make_package(task: str, results: list[RecallResult]):
    """Helper to build a package from results."""
    return PackageBuilder().build(task, results, None, ["test"])


class TestQualityMetrics:
    """Structural quality metrics for Context Packages."""

    def test_no_duplicate_references(self):
        results = [_make_result("same text")] * 5
        pkg = _make_package("query", results)
        ref_paths = [r.path for r in pkg.references]
        assert len(ref_paths) == len(set(ref_paths))

    def test_section_utilization(self):
        results = [
            _make_result("architecture is layered"),
            _make_result("backend/service.py", "file"),
        ]
        pkg = _make_package("query", results)
        if pkg.sections:
            non_empty = sum(1 for s in pkg.sections if s.content.strip())
            assert non_empty / len(pkg.sections) > 0.5

    def test_token_estimate_reasonable(self):
        results = [_make_result(f"fact {i}") for i in range(10)]
        pkg = _make_package("query", results)
        assert 100 < pkg.token_estimate < 10000

    def test_metadata_populated(self):
        results = [_make_result("test")]
        pkg = _make_package("query", results)
        assert pkg.metadata is not None
        assert pkg.metadata.package_version == "1.0"
        assert pkg.metadata.pipeline_version == "1.0"

    def test_metadata_has_timing(self):
        results = [_make_result("test")]
        pkg = _make_package("query", results)
        assert pkg.metadata.total_time_ms >= 0
        assert pkg.metadata.generated_at != ""

    def test_metadata_has_counts(self):
        results = [_make_result("a"), _make_result("b"), _make_result("a")]
        pkg = _make_package("query", results)
        assert pkg.metadata.retrieved_memory_count == 3
        assert pkg.metadata.deduplicated_count == 2

    def test_compression_ratio_recorded(self):
        results = [_make_result("x" * 500)]
        pkg = _make_package("query", results)
        assert pkg.metadata.compression_ratio >= 1.0

    def test_references_have_provenance(self):
        results = [_make_result("service.py", "file")]
        pkg = _make_package("query", results)
        assert len(pkg.references) > 0
        assert len(pkg.references[0].provenance) > 0

    def test_empty_package_valid(self):
        pkg = _make_package("query", [])
        assert pkg.task == "query"
        assert pkg.metadata is not None
        assert pkg.metadata.retrieved_memory_count == 0

    def test_large_input_handled(self):
        results = [_make_result(f"item {i}", score=i * 0.01) for i in range(50)]
        pkg = _make_package("query", results)
        assert pkg.metadata is not None
        assert pkg.metadata.retrieved_memory_count == 50
        assert pkg.metadata.estimated_tokens < 50000
