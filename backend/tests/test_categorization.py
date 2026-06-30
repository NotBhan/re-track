"""Tests for categorization pipeline stage."""

from app.models.responses import RecallResult
from app.services.pipeline.categorization import Categorizer


def _make(text: str, kind: str = "text") -> RecallResult:
    return RecallResult(kind=kind, search_type="semantic", text=text, score=0.5, dataset_name="test")


class TestCategorizer:
    """Tests for rule-based categorization."""

    def test_file_categorized(self):
        assert "files" in Categorizer().categorize([_make("svc.py", "file")])

    def test_architecture_keyword(self):
        assert "architecture" in Categorizer().categorize([_make("The layered architecture uses service boundaries")])

    def test_api_keyword(self):
        assert "apis" in Categorizer().categorize([_make("The REST endpoint handles POST requests")])

    def test_convention_keyword(self):
        assert "conventions" in Categorizer().categorize([_make("Follow snake_case naming convention")])

    def test_decision_keyword(self):
        assert "decisions" in Categorizer().categorize([_make("We chose Cognee because of hybrid retrieval")])

    def test_default_to_knowledge(self):
        assert "knowledge" in Categorizer().categorize([_make("Some random text")])

    def test_empty_input(self):
        assert Categorizer().categorize([]) == {}

    def test_multiple_categories(self):
        results = [_make("svc.py", "file"), _make("architecture is layered"), _make("follow convention")]
        cats = Categorizer().categorize(results)
        assert len(cats) >= 2

    def test_file_extension_detected(self):
        results = [_make("backend/app/services/cognee.py")]
        cats = Categorizer().categorize(results)
        assert "files" in cats

    def test_architecture_priority_over_knowledge(self):
        results = [_make("The architecture uses a service pattern for components")]
        cats = Categorizer().categorize(results)
        assert "architecture" in cats

    def test_api_priority_over_knowledge(self):
        results = [_make("The API endpoint returns a JSON response")]
        cats = Categorizer().categorize(results)
        assert "apis" in cats

    def test_convention_priority_over_knowledge(self):
        results = [_make("Follow the naming convention for variables")]
        cats = Categorizer().categorize(results)
        assert "conventions" in cats

    def test_decision_priority_over_knowledge(self):
        results = [_make("The decision was to use Cognee over custom solution")]
        cats = Categorizer().categorize(results)
        assert "decisions" in cats

    def test_file_kind_always_files(self):
        results = [_make("Some text about architecture", "file")]
        cats = Categorizer().categorize(results)
        assert "files" in cats

    def test_mixed_results(self):
        results = [
            _make("service.py", "file"),
            _make("The layered architecture with service boundaries"),
            _make("Follow the coding convention"),
            _make("random text about weather"),
        ]
        cats = Categorizer().categorize(results)
        assert "files" in cats
        assert "architecture" in cats
        assert "conventions" in cats
        assert "knowledge" in cats
