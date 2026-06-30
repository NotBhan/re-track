"""Tests for deduplication pipeline stage."""

from app.models.responses import RecallResult
from app.services.pipeline.dedup import Deduplicator


def _make(text: str, score: float = 0.5, kind: str = "text") -> RecallResult:
    return RecallResult(kind=kind, search_type="semantic", text=text, score=score, dataset_name="test")


class TestDeduplicator:
    """Tests for structural deduplication."""

    def test_no_duplicates(self):
        results = [_make("alpha", 0.9), _make("beta", 0.8)]
        assert len(Deduplicator().deduplicate(results)) == 2

    def test_exact_duplicates_removed(self):
        results = [_make("same text", 0.9), _make("same text", 0.7)]
        out = Deduplicator().deduplicate(results)
        assert len(out) == 1
        assert out[0].score == 0.9

    def test_case_insensitive(self):
        results = [_make("Hello World", 0.8), _make("hello world", 0.6)]
        assert len(Deduplicator().deduplicate(results)) == 1

    def test_whitespace_normalization(self):
        results = [_make("hello  world", 0.8), _make("hello world", 0.6)]
        assert len(Deduplicator().deduplicate(results)) == 1

    def test_preserves_order(self):
        results = [_make("c", 0.3), _make("a", 0.9), _make("b", 0.6)]
        out = Deduplicator().deduplicate(results)
        assert [r.text for r in out] == ["c", "a", "b"]

    def test_keeps_highest_score(self):
        results = [_make("dup", 0.3), _make("dup", 0.9), _make("dup", 0.5)]
        out = Deduplicator().deduplicate(results)
        assert len(out) == 1
        assert out[0].score == 0.9

    def test_empty_input(self):
        assert Deduplicator().deduplicate([]) == []

    def test_single_item(self):
        result = [_make("only")]
        assert Deduplicator().deduplicate(result) == result

    def test_distinct_items_preserved(self):
        results = [_make("first", 0.5), _make("second", 0.6), _make("third", 0.7)]
        out = Deduplicator().deduplicate(results)
        assert len(out) == 3

    def test_mixed_duplicates(self):
        results = [
            _make("unique one", 0.5),
            _make("duplicate", 0.8),
            _make("unique two", 0.6),
            _make("duplicate", 0.9),
        ]
        out = Deduplicator().deduplicate(results)
        assert len(out) == 3
        assert out[1].text == "duplicate"
        assert out[1].score == 0.9

    def test_preserves_metadata(self):
        results = [_make("test", 0.5, "file")]
        out = Deduplicator().deduplicate(results)
        assert out[0].kind == "file"
        assert out[0].dataset_name == "test"
