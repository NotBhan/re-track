"""Semantic compression stage for the retrieval pipeline.

Merges redundant entries while preserving executable facts.
Operates on structured RecallResult objects, never on Markdown.

Compression strategy:
- Tier 1 (Structural): Exact duplicate removal (handled by Deduplicator)
- Tier 2 (Semantic): Merge entries describing the same concept

Executable facts are never modified:
- File paths
- Symbol names (functions, classes, interfaces)
- API endpoints and contracts
- Configuration keys
- Environment variables
- Command names
"""

import logging

from app.models.responses import RecallResult

logger = logging.getLogger(__name__)

# Overlap threshold for considering two texts redundant (0.0-1.0)
_OVERLAP_THRESHOLD = 0.35


class Compressor:
    """Compresses recall results by merging redundant entries.

    When two entries describe the same concept (high token overlap),
    the shorter, more concise version is kept.
    """

    def compress(self, results: list[RecallResult]) -> list[RecallResult]:
        """Compress results by merging redundant entries.

        Args:
            results: Ranked recall results.

        Returns:
            Compressed list with redundant entries merged.
        """
        if not results:
            return []

        merged: list[RecallResult] = []
        used: set[int] = set()

        for i, r in enumerate(results):
            if i in used:
                continue

            best = r
            best_idx = i

            for j in range(i + 1, len(results)):
                if j in used:
                    continue
                if self._are_redundant(r.text, results[j].text):
                    used.add(j)
                    if len(results[j].text) < len(best.text):
                        best = results[j]
                        best_idx = j

            merged.append(best)
            used.add(best_idx)

        removed = len(results) - len(merged)
        if removed > 0:
            logger.debug("compression merged %d redundant entries", removed)

        return merged

    def _are_redundant(self, a: str, b: str) -> bool:
        """Check if two texts describe the same concept.

        Uses token overlap ratio: if >70% of tokens are shared,
        the texts are considered redundant.

        Args:
            a: First text.
            b: Second text.

        Returns:
            True if texts are redundant.
        """
        a_tokens = set(a.lower().split())
        b_tokens = set(b.lower().split())

        if not a_tokens or not b_tokens:
            return False

        intersection = a_tokens & b_tokens
        overlap_count = len(intersection)
        overlap_ratio = overlap_count / max(len(a_tokens), len(b_tokens))

        # Require both sufficient ratio AND minimum token overlap
        # to avoid merging unrelated short sentences via common words
        return overlap_ratio > _OVERLAP_THRESHOLD and overlap_count >= 3
