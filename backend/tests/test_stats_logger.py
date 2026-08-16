"""Tests for Package Statistics Logger."""

from app.models.responses import (
    ContextPackage,
    PackageMetadata,
    PackageSection,
)
from app.services.stats_logger import StatsLogger


def _make_package(sections: int = 3, tokens: int = 2000) -> ContextPackage:
    """Helper to create a ContextPackage with metadata."""
    secs = [PackageSection(f"s{i}", f"Section {i}", "content") for i in range(sections)]
    meta = PackageMetadata(
        package_version="1.0",
        repository_summary_version="1.0",
        generated_at="2026-06-30T00:00:00Z",
        datasets_used=["test"],
        retrieved_memory_count=43,
        deduplicated_count=18,
        compressed_count=18,
        compression_ratio=2.39,
        estimated_tokens=tokens,
        pipeline_version="1.0",
        retrieval_time_ms=5000,
        total_time_ms=8000,
    )
    return ContextPackage(
        task="Add Rust support",
        objective="Add Rust",
        sections=secs,
        metadata=meta,
        markdown="test",
    )


class TestStatsLogger:
    """Tests for package statistics logger."""

    def test_format_includes_key_fields(self):
        logger = StatsLogger()
        pkg = _make_package()
        report = logger.format_stats(pkg, "RE:Track")
        assert "Repository: RE:Track" in report
        assert "Task: Add Rust support" in report
        assert "Retrieved Memories: 43" in report
        assert "Unique Memories: 18" in report
        assert "Final Tokens: 2000" in report

    def test_format_includes_sections(self):
        logger = StatsLogger()
        pkg = _make_package(sections=3)
        report = logger.format_stats(pkg, "RE:Track")
        assert "Sections Generated:" in report
        assert "Section 0" in report

    def test_format_includes_ratio(self):
        logger = StatsLogger()
        pkg = _make_package()
        report = logger.format_stats(pkg, "RE:Track")
        assert "Compression Ratio:" in report

    def test_format_includes_validation(self):
        logger = StatsLogger()
        pkg = _make_package()
        report = logger.format_stats(pkg, "RE:Track")
        assert "Validation:" in report
        assert "PASS" in report

    def test_dup_rate_calculation(self):
        logger = StatsLogger()
        pkg = _make_package()
        report = logger.format_stats(pkg, "RE:Track")
        # 43 retrieved, 18 unique → 25/43 = 58%
        assert "Duplicate Rate: 58%" in report

    def test_empty_package_warns(self):
        logger = StatsLogger()
        pkg = ContextPackage(task="q", objective="o", markdown="test")
        report = logger.format_stats(pkg, "Test")
        assert "Validation: WARN" in report

    def test_benchmark_report_format(self):
        logger = StatsLogger()
        results = [
            {"question_id": "Q1", "overall_score": 0.8, "verdict": "PASS",
             "file_score": {"found": ["a.py"]}, "symbol_score": {"found": ["Foo"]}},
            {"question_id": "Q2", "overall_score": 0.4, "verdict": "FAIL",
             "file_score": {"found": []}, "symbol_score": {"found": ["Bar"]}},
        ]
        report = logger.format_benchmark_report(results, "TestRepo")
        assert "TestRepo" in report
        assert "Q1" in report
        assert "Q2" in report
        assert "PASS" in report
        assert "FAIL" in report

    def test_log_to_file(self, tmp_path):
        logger = StatsLogger()
        pkg = _make_package()
        path = str(tmp_path / "stats.txt")
        logger.log_to_file(pkg, "RE:Track", path)
        with open(path) as f:
            content = f.read()
        assert "RE:Track" in content
        assert "Add Rust support" in content
