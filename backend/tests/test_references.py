"""Tests for reference resolution pipeline stage."""

from app.models.responses import RecallResult
from app.services.pipeline.references import ReferenceResolver


def _make(text: str, kind: str = "text", score: float = 0.5) -> RecallResult:
    return RecallResult(kind=kind, search_type="semantic", text=text, score=score, dataset_name="test")


class TestReferenceResolver:
    """Tests for lightweight reference resolution."""

    def test_file_reference(self):
        refs = ReferenceResolver().resolve([_make("backend/app/services/cognee.py", "file", 0.9)])
        assert refs[0].ref_type == "file"
        assert "cognee.py" in refs[0].path

    def test_memory_reference(self):
        refs = ReferenceResolver().resolve([_make("The architecture uses layered patterns")])
        assert refs[0].ref_type == "memory"

    def test_preserves_score(self):
        refs = ReferenceResolver().resolve([_make("test.py", "file", 0.85)])
        assert refs[0].score == 0.85

    def test_empty_input(self):
        assert ReferenceResolver().resolve([]) == []

    def test_provenance_chain(self):
        refs = ReferenceResolver().resolve([_make("service.py", "file")])
        assert len(refs[0].provenance) > 0

    def test_path_detected_in_text(self):
        refs = ReferenceResolver().resolve([_make("see backend/app/config/settings.py for details")])
        assert refs[0].ref_type == "file"
        assert "settings.py" in refs[0].path

    def test_symbol_in_path(self):
        refs = ReferenceResolver().resolve([_make("service.py")])
        assert refs[0].ref_type == "file"

    def test_none_score_handled(self):
        refs = ReferenceResolver().resolve([_make("text", "text", None)])
        assert refs[0].score == 0.0

    def test_multiple_references(self):
        results = [_make("a.py", "file", 0.9), _make("b.py", "file", 0.8)]
        refs = ReferenceResolver().resolve(results)
        assert len(refs) == 2

    def test_provenance_includes_dataset(self):
        refs = ReferenceResolver().resolve([_make("test.py", "file")])
        assert any("test" in p for p in refs[0].provenance)

    def test_provenance_includes_kind(self):
        refs = ReferenceResolver().resolve([_make("test.py", "file")])
        assert any("file" in p for p in refs[0].provenance)

    def test_empty_text_skipped(self):
        refs = ReferenceResolver().resolve([_make("", "file")])
        assert len(refs) == 0

    def test_whitespace_only_text_skipped(self):
        refs = ReferenceResolver().resolve([_make("   ", "file")])
        assert len(refs) == 0

    def test_various_ref_types(self):
        results = [
            _make("file.py", "file"),
            _make("The architecture note"),
            _make("path/to/config.json"),
        ]
        refs = ReferenceResolver().resolve(results)
        assert len(refs) == 3
        types = [r.ref_type for r in refs]
        assert "file" in types
        assert "memory" in types
