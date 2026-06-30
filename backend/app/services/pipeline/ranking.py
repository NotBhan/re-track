"""Multi-factor ranking stage for the retrieval pipeline.

Ranks recall results by composite relevance score:
  FinalScore = SemanticRelevance × Confidence × TypeWeight

Factors:
- SemanticRelevance: Cognee's similarity score (0.0-1.0)
- Confidence: 1.0 if score present, 0.5 if score is None
- TypeWeight: file=1.0, code=0.9, text=0.7 (others=0.7)
"""

import logging

from app.models.responses import RecallResult

logger = logging.getLogger(__name__)

# Information type weights — files and code rank higher than plain text
_TYPE_WEIGHTS: dict[str, float] = {
    "file": 1.0,
    "code": 0.9,
    "text": 0.7,
}


class Ranker:
    """Ranks recall results by composite relevance score.

    Uses multi-factor scoring to prioritize results by semantic similarity,
    confidence in the score, and information type.
    """

    def rank(self, results: list[RecallResult]) -> list[RecallResult]:
        """Rank results by composite score (descending).

        Args:
            results: Recall results to rank.

        Returns:
            Results sorted by composite score (highest first).
        """
        if not results:
            return []

        scored = []
        for r in results:
            composite = self._compute_score(r)
            scored.append((composite, r))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored]

    def _compute_score(self, result: RecallResult) -> float:
        """Compute composite score for a single result.

        Args:
            result: Recall result to score.

        Returns:
            Composite score (higher = more relevant).
        """
        semantic = result.score if result.score is not None else 0.5
        confidence = 1.0 if result.score is not None else 0.5
        type_weight = _TYPE_WEIGHTS.get(result.kind, 0.7)

        return semantic * confidence * type_weight
