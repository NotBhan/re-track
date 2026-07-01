"""Tests for Repository Summary Generator."""

from pathlib import Path

from app.models.responses import RepositorySummary
from app.services.repository_summary import RepositorySummaryGenerator


class TestRepositorySummaryGenerator:
    """Tests for RepositorySummaryGenerator."""

    def test_creates_summary(self, tmp_path):
        (tmp_path / "backend").mkdir()
        (tmp_path / "backend" / "app.py").write_text("import os\nprint('hello')")
        (tmp_path / "README.md").write_text("# Test Project\nA test repository.")

        files = list(tmp_path.rglob("*"))
        files = [f for f in files if f.is_file()]

        gen = RepositorySummaryGenerator()
        summary = gen.generate(tmp_path, files)

        assert isinstance(summary, RepositorySummary)
        assert summary.version == "1.0"
        assert summary.repository_fingerprint != ""
        assert summary.generated_at != ""

    def test_extracts_languages(self, tmp_path):
        (tmp_path / "main.py").write_text("def main(): pass")
        (tmp_path / "app.ts").write_text("const x = 1;")

        files = [tmp_path / "main.py", tmp_path / "app.ts"]
        gen = RepositorySummaryGenerator()
        summary = gen.generate(tmp_path, files)

        langs = [l.lower() for l in summary.technology_stack.languages]
        assert "python" in langs or "typescript" in langs

    def test_maps_directories(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("x = 1")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_main.py").write_text("def test_x(): pass")

        files = [tmp_path / "src" / "main.py", tmp_path / "tests" / "test_main.py"]
        gen = RepositorySummaryGenerator()
        summary = gen.generate(tmp_path, files)

        paths = [e.path for e in summary.repository_map]
        assert any("src" in p for p in paths)

    def test_fingerprint_deterministic(self, tmp_path):
        (tmp_path / "a.py").write_text("x = 1")
        files = [tmp_path / "a.py"]

        gen = RepositorySummaryGenerator()
        s1 = gen.generate(tmp_path, files)
        s2 = gen.generate(tmp_path, files)

        assert s1.repository_fingerprint == s2.repository_fingerprint

    def test_empty_repo(self, tmp_path):
        gen = RepositorySummaryGenerator()
        summary = gen.generate(tmp_path, [])

        assert isinstance(summary, RepositorySummary)
        assert summary.project_purpose != ""

    def test_infers_purpose_from_readme(self, tmp_path):
        (tmp_path / "README.md").write_text("# My Project\nThis is a memory system for AI.")
        (tmp_path / "main.py").write_text("x = 1")

        files = [tmp_path / "main.py"]
        gen = RepositorySummaryGenerator()
        summary = gen.generate(tmp_path, files)

        assert "memory" in summary.project_purpose.lower() or "ai" in summary.project_purpose.lower()

    def test_infers_architecture(self, tmp_path):
        (tmp_path / "backend").mkdir()
        (tmp_path / "backend" / "app.py").write_text("x = 1")
        (tmp_path / "frontend").mkdir()
        (tmp_path / "frontend" / "app.ts").write_text("x = 1")

        files = [tmp_path / "backend" / "app.py", tmp_path / "frontend" / "app.ts"]
        gen = RepositorySummaryGenerator()
        summary = gen.generate(tmp_path, files)

        assert summary.architecture.pattern == "layered"
        assert "Backend" in summary.architecture.layers
        assert "Frontend" in summary.architecture.layers

    def test_extracts_components(self, tmp_path):
        (tmp_path / "cognee_service.py").write_text("class CogneeService: pass")
        (tmp_path / "indexing_service.py").write_text("class IndexingService: pass")

        files = [tmp_path / "cognee_service.py", tmp_path / "indexing_service.py"]
        gen = RepositorySummaryGenerator()
        summary = gen.generate(tmp_path, files)

        assert len(summary.key_components) >= 2
        names = [c.name for c in summary.key_components]
        assert any("Cognee" in n for n in names)

    def test_describes_directories(self, tmp_path):
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test.py").write_text("x = 1")
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "readme.md").write_text("# Docs")

        files = [tmp_path / "tests" / "test.py", tmp_path / "docs" / "readme.md"]
        gen = RepositorySummaryGenerator()
        summary = gen.generate(tmp_path, files)

        descs = {e.path: e.description for e in summary.repository_map}
        assert "tests" in descs
        assert "Test suite" in descs["tests"]
