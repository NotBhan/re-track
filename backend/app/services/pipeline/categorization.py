"""Rule-based categorization stage for the retrieval pipeline.

Classifies recall results into section types using a priority-ordered
rule system:

1. Explicit metadata from Cognee (e.g., kind="file")
2. File extension detection
3. Keyword matching (architecture, API, convention, decision keywords)
4. Fallback to general knowledge

Results are classified into section types matching Context Package sections:
- files: File paths and code references
- architecture: Architectural patterns, design decisions
- apis: API endpoints, interfaces, contracts
- conventions: Coding conventions, naming, formatting
- decisions: Design decisions, rationale, tradeoffs
- knowledge: General knowledge (fallback)
"""

import logging
from pathlib import Path

from app.models.responses import RecallResult

logger = logging.getLogger(__name__)

# Keyword sets for categorization (ordered by priority)
_ARCHITECTURE_KEYWORDS = frozenset({
    "architecture", "design", "pattern", "structure", "layer",
    "module", "component", "service", "pipeline", "workflow",
    "system", "infrastructure", "deployment",
})

_API_KEYWORDS = frozenset({
    "api", "endpoint", "route", "interface", "contract",
    "schema", "request", "response", "http", "rest",
    "graphql", "grpc", "webhook",
})

_CONVENTION_KEYWORDS = frozenset({
    "convention", "style", "format", "linting", "naming",
    "indentation", "standard", "guideline", "practice",
})

_DECISION_KEYWORDS = frozenset({
    "decision", "rationale", "tradeoff", "trade-off",
    "chosen", "chose", "selected", "alternative", "rejected",
    "adr", "why we", "reason for",
})

# Code file extensions for detection
_CODE_EXTENSIONS = frozenset({
    ".py", ".ts", ".tsx", ".js", ".jsx", ".json",
    ".yaml", ".yml", ".toml", ".rs", ".go",
})


class Categorizer:
    """Classifies recall results into section types by rule priority.

    Uses a priority-ordered rule system to assign each result to a
    section type. Explicit metadata (kind="file") takes highest priority,
    followed by file extension detection, then keyword matching, with
    fallback to "knowledge".
    """

    def categorize(self, results: list[RecallResult]) -> dict[str, list[RecallResult]]:
        """Categorize results into sections.

        Args:
            results: Recall results to categorize.

        Returns:
            Dict mapping section_type to list of results.
        """
        categories: dict[str, list[RecallResult]] = {}

        for r in results:
            section = self._classify(r)
            categories.setdefault(section, []).append(r)

        return categories

    def _classify(self, result: RecallResult) -> str:
        """Classify a single result into a section type.

        Priority order:
        1. Explicit metadata (kind="file")
        2. File extension detection
        3. Keyword matching
        4. Fallback to knowledge

        Args:
            result: Recall result to classify.

        Returns:
            Section type string.
        """
        kind = result.kind.lower() if result.kind else ""
        text_lower = result.text.lower()

        # Priority 1: Explicit metadata
        if kind == "file":
            return "files"

        # Priority 2: File extension detection
        if self._has_code_extension(text_lower):
            return "files"

        # Priority 3: Keywords (order matters — first match wins)
        if self._has_keyword(text_lower, _ARCHITECTURE_KEYWORDS):
            return "architecture"
        if self._has_keyword(text_lower, _API_KEYWORDS):
            return "apis"
        if self._has_keyword(text_lower, _CONVENTION_KEYWORDS):
            return "conventions"
        if self._has_keyword(text_lower, _DECISION_KEYWORDS):
            return "decisions"

        # Priority 4: Fallback
        return "knowledge"

    def _has_code_extension(self, text: str) -> bool:
        """Check if text contains a code file path."""
        return any(text.endswith(ext) for ext in _CODE_EXTENSIONS)

    def _has_keyword(self, text: str, keywords: frozenset[str]) -> bool:
        """Check if text contains any of the given keywords."""
        return any(kw in text for kw in keywords)
