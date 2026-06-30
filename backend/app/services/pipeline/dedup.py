"""Structural deduplication stage for the retrieval pipeline.

Removes duplicate memories based on normalized text comparison.
Keeps the entry with the highest relevance score when duplicates are found.
Preserves original order for unique entries.
"""

import logging

from app.models.responses import RecallResult

logger = logging.getLogger(__name__)


class Deduplicator:
    """Removes duplicate memories based on normalized text.

    Deduplication is case-insensitive and whitespace-normalized.
    When duplicates exist, the entry with the highest score is kept.
    """

    def deduplicate(self, results: list[RecallResult]) -> list[RecallResult]:
        """Remove duplicate memories from recall results.

        Args:
            results: Raw recall results (assumed score-sorted descending).

        Returns:
            Deduplicated list preserving original order for unique entries.
        """
        if not results:
            return []

        seen: dict[str, RecallResult] = {}
        order: list[str] = []

        for r in results:
            key = self._normalize(r.text)
            if key not in seen:
                seen[key] = r
                order.append(key)
            elif r.score > seen[key].score:
                seen[key] = r

        deduped = [seen[k] for k in order]
        removed = len(results) - len(deduped)
        if removed > 0:
            logger.debug("deduplication removed %d duplicates", removed)

        return deduped

    def _normalize(self, text: str) -> str:
        """Lowercase and collapse whitespace for comparison."""
        return " ".join(text.lower().split())
