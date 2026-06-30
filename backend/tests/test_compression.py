"""Tests for semantic compression pipeline stage."""

from app.models.responses import RecallResult
from app.services.pipeline.compression import Compressor


def _make(text: str, kind: str = "text", score: float = 0.5) -> RecallResult:
    return RecallResult(kind=kind, search_type="semantic", text=text, score=score, dataset_name="test")


class TestCompressor:
    """Tests for semantic compression."""

    def test_merges_redundant(self):
        results = [
            _make("CogneeService wraps cognee APIs"),
            _make("CogneeService is a thin wrapper around cognee APIs"),
        ]
        assert len(Compressor().compress(results)) == 1

    def test_preserves_distinct(self):
        results = [_make("architecture is layered"), _make("use pytest for tests")]
        assert len(Compressor().compress(results)) == 2

    def test_empty_input(self):
        assert Compressor().compress([]) == []

    def test_single_item(self):
        result = [_make("only")]
        assert Compressor().compress(result) == result

    def test_keeps_shorter_version(self):
        results = [
            _make("The CogneeService class wraps the cognee APIs for internal use"),
            _make("CogneeService wraps cognee APIs"),
        ]
        out = Compressor().compress(results)
        assert len(out) == 1
        assert len(out[0].text) < 60

    def test_preserves_executable_facts(self):
        """File paths should survive compression."""
        results = [
            _make("The file backend/app/services/cognee.py contains the service"),
            _make("backend/app/services/cognee.py is the main service file"),
        ]
        out = Compressor().compress(results)
        assert any("cognee.py" in r.text for r in out)

    def test_preserves_symbol_names(self):
        """Function names should survive compression."""
        results = [
            _make("The function recall() calls cognee internally"),
            _make("recall() is the main retrieval function"),
        ]
        out = Compressor().compress(results)
        assert any("recall()" in r.text for r in out)

    def test_no_compression_for_unrelated(self):
        results = [
            _make("Python is a programming language"),
            _make("React is a frontend framework"),
            _make("LanceDB stores vectors"),
        ]
        out = Compressor().compress(results)
        assert len(out) == 3

    def test_preserves_kind(self):
        results = [_make("test", "file")]
        out = Compressor().compress(results)
        assert out[0].kind == "file"

    def test_preserves_score(self):
        results = [_make("unique text", "text", 0.85)]
        out = Compressor().compress(results)
        assert out[0].score == 0.85

    def test_high_overlap_merges(self):
        results = [
            _make("CogneeService is a wrapper around Cognee APIs for memory operations"),
            _make("CogneeService wraps Cognee APIs and provides memory operations"),
        ]
        out = Compressor().compress(results)
        assert len(out) == 1

    def test_low_overlap_preserves(self):
        results = [
            _make("CogneeService handles memory operations"),
            _make("IndexingService processes repository files"),
        ]
        out = Compressor().compress(results)
        assert len(out) == 2
