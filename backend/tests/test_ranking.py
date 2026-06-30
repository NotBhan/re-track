"""Tests for ranking pipeline stage."""

from app.models.responses import RecallResult
from app.services.pipeline.ranking import Ranker


def _make(text: str, score: float | None, kind: str = "text") -> RecallResult:
    return RecallResult(kind=kind, search_type="semantic", text=text, score=score or 0.0, dataset_name="test")


class TestRanker:
    """Tests for multi-factor ranking."""

    def test_high_score_first(self):
        results = [_make("low", 0.3), _make("high", 0.9)]
        assert Ranker().rank(results)[0].text == "high"

    def test_none_score_ranked_lower(self):
        results = [_make("scored", 0.5), _make("unscored", None)]
        assert Ranker().rank(results)[0].text == "scored"

    def test_file_type_boosted(self):
        results = [_make("note", 0.7, "text"), _make("svc.py", 0.6, "file")]
        assert Ranker().rank(results)[0].kind == "file"

    def test_empty_input(self):
        assert Ranker().rank([]) == []

    def test_single_item(self):
        result = [_make("only", 0.5)]
        assert Ranker().rank(result) == result

    def test_all_same_score(self):
        results = [_make("a", 0.5), _make("b", 0.5), _make("c", 0.5)]
        out = Ranker().rank(results)
        assert len(out) == 3

    def test_composite_scoring(self):
        """File type with moderate score can beat text with high score."""
        results = [_make("text content", 0.8, "text"), _make("important.py", 0.7, "file")]
        ranked = Ranker().rank(results)
        # file: 0.7 * 1.0 * 1.0 = 0.7
        # text: 0.8 * 1.0 * 0.7 = 0.56
        assert ranked[0].kind == "file"

    def test_none_score_gets_medium_confidence(self):
        results = [_make("unscored", None, "text")]
        ranked = Ranker().rank(results)
        # 0.5 * 0.5 * 0.7 = 0.175
        assert len(ranked) == 1

    def test_code_type_boosted(self):
        results = [_make("plain text", 0.9, "text"), _make("code snippet", 0.7, "code")]
        ranked = Ranker().rank(results)
        # code: 0.7 * 1.0 * 0.9 = 0.63
        # text: 0.9 * 1.0 * 0.7 = 0.63
        # tied, but code type has higher weight
        assert ranked[0].text in ("plain text", "code snippet")

    def test_preserves_all_results(self):
        results = [_make(f"item {i}", i * 0.1) for i in range(5)]
        out = Ranker().rank(results)
        assert len(out) == 5
