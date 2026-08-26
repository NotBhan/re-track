"""Multi-factor ranking stage for the retrieval pipeline.

Ranks recall results by composite relevance score and authority tiers:
  FinalScore = AuthorityTierWeight × SemanticRelevance × Confidence × TypeWeight

Factors:
- AuthorityTierWeight: Tier 1 (Source=1.0), Tier 2 (AST=0.9), Tier 3 (LanceDB/Kùzu=0.7), Tier 4 (Cognee=0.6)
- SemanticRelevance: Cognee's similarity score (0.0-1.0)
- Confidence: 1.0 if score present, 0.5 if score is None
- TypeWeight: file=1.0, code=0.9, text=0.7 (others=0.7)
"""

import logging
from typing import Any, Optional

from app.models.responses import RecallResult

logger = logging.getLogger(__name__)

# Information type weights — files and code rank higher than plain text
_TYPE_WEIGHTS: dict[str, float] = {
    "file": 1.0,
    "code": 0.9,
    "text": 0.7,
}


class Ranker:
    """Ranks recall results by composite score and authority tiers."""

    def rank(
        self,
        results: list[RecallResult],
        manifest: Optional[Any] = None,
    ) -> list[RecallResult]:
        """Rank results by composite score and authority (descending).

        Args:
            results: Recall results to rank.
            manifest: Optional active repository manifest for provenance validation.

        Returns:
            Results sorted by composite score (highest first), with stale records pruned.
        """
        if not results:
            return []

        scored = []
        for r in results:
            # Validate provenance if manifest is supplied and provenance exists
            if manifest:
                prov = getattr(r, "provenance", None) or (r.raw.get("provenance") if isinstance(r.raw, dict) else getattr(r.raw, "provenance", None))
                if prov:
                    from app.services.retrieval_arbitrator import RetrievalArbitrator
                    is_valid, _ = RetrievalArbitrator.validate_candidate_provenance(prov, manifest)
                    if not is_valid:
                        continue

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

        # Base multi-factor score
        return semantic * confidence * type_weight
