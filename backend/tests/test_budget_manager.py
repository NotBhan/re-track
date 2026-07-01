"""Tests for Budget Manager."""

from app.models.responses import PackageSection
from app.services.budget_manager import BudgetManager


def _sec(section_type: str, content: str, priority: int) -> PackageSection:
    """Helper to create a PackageSection."""
    return PackageSection(
        section_type=section_type,
        heading=section_type.title(),
        content=content,
        priority=priority,
    )


class TestBudgetManager:
    """Tests for budget enforcement with priority classes."""

    def test_under_budget_preserves_all(self):
        sections = [_sec("task", "Do something", 5), _sec("files", "- file.py", 5)]
        result = BudgetManager(target_tokens=5000).apply(sections)
        assert len(result) == 2

    def test_over_budget_removes_low_priority(self):
        sections = [
            _sec("task", "x" * 100, 5),
            _sec("references", "y" * 5000, 1),
        ]
        result = BudgetManager(target_tokens=500).apply(sections)
        types = [s.section_type for s in result]
        assert "references" not in types
        assert "task" in types

    def test_critical_never_removed(self):
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

    def test_empty_input(self):
        assert BudgetManager(target_tokens=1000).apply([]) == []

    def test_compression_ratio_recorded(self):
        bm = BudgetManager(target_tokens=50)
        bm.apply([_sec("task", "x" * 100, 5)])
        assert bm.last_compression_ratio > 0

    def test_medium_removed_before_high_compressed(self):
        sections = [
            _sec("task", "x" * 100, 5),
            _sec("architecture", "y" * 1000, 4),
            _sec("apis", "z" * 500, 3),
            _sec("refs", "w" * 5000, 1),
        ]
        result = BudgetManager(target_tokens=300).apply(sections)
        types = [s.section_type for s in result]
        assert "apis" not in types  # medium removed
        assert "task" in types
        assert "architecture" in types  # high compressed, not removed

    def test_high_section_compressed_not_removed(self):
        sections = [
            _sec("task", "x" * 50, 5),
            _sec("architecture", "y" * 2000, 4),
        ]
        result = BudgetManager(target_tokens=200).apply(sections)
        types = [s.section_type for s in result]
        assert "architecture" in types
        # Content should be truncated
        arch = [s for s in result if s.section_type == "architecture"][0]
        assert len(arch.content) < 2000

    def test_preserves_section_order(self):
        sections = [
            _sec("task", "x" * 50, 5),
            _sec("files", "y" * 50, 5),
            _sec("refs", "z" * 5000, 1),
        ]
        result = BudgetManager(target_tokens=200).apply(sections)
        types = [s.section_type for s in result]
        assert types.index("task") < types.index("files")

    def test_single_critical_section(self):
        sections = [_sec("task", "Do something", 5)]
        result = BudgetManager(target_tokens=10).apply(sections)
        assert len(result) == 1

    def test_ratio_calculation(self):
        bm = BudgetManager(target_tokens=10)
        sections = [_sec("task", "x" * 100, 5), _sec("refs", "y" * 1000, 1)]
        bm.apply(sections)
        assert bm.last_compression_ratio >= 1.0

    def test_truncation_at_line_boundary(self):
        bm = BudgetManager(target_tokens=10)
        content = "- line one\n- line two\n- line three\n- line four"
        result = bm._truncate_at_line_boundary(content, 0.5)
        # Should cut at a newline boundary, not mid-line
        # Result should be a prefix that ends at a complete line
        assert len(result) <= len(content)
        # Every line in result should be complete (no partial lines)
        lines = result.split("\n")
        for line in lines[:-1]:  # all but last
            assert len(line) > 0

    def test_truncation_preserves_bullets(self):
        bm = BudgetManager(target_tokens=10)
        content = "- item one\n- item two\n- item three\n- item four"
        result = bm._truncate_at_line_boundary(content, 0.5)
        lines = result.strip().split("\n")
        # Every line should be a complete bullet
        for line in lines:
            assert line.startswith("- ") or line == ""

    def test_truncation_single_line(self):
        bm = BudgetManager(target_tokens=10)
        content = "single line content here"
        result = bm._truncate_at_line_boundary(content, 0.5)
        assert len(result) <= len(content) // 2

    def test_truncation_empty_content(self):
        bm = BudgetManager(target_tokens=10)
        assert bm._truncate_at_line_boundary("", 0.5) == ""

    def test_truncation_ratio_one_returns_full(self):
        bm = BudgetManager(target_tokens=10)
        content = "line one\nline two"
        result = bm._truncate_at_line_boundary(content, 1.0)
        assert result == content

    def test_budget_manager_uses_line_truncation(self):
        bm = BudgetManager(target_tokens=10)
        content = "- first item\n- second item\n- third item\n- fourth item"
        sections = [_sec("task", "x" * 50, 5), _sec("arch", content, 4)]
        result = bm.apply(sections)
        arch = [s for s in result if s.section_type == "arch"]
        if arch:
            # Content should end at a line boundary
            assert "\n" not in arch[0].content.rstrip() or arch[0].content.endswith("\n")
