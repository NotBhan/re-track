"""Domain entities and authority tiers for retrieval arbitration in RE:Track."""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Optional

from app.application.domain.memory import MemoryProvenance


class AuthorityTier(IntEnum):
    """Authority priority tiers for multi-modal evidence arbitration.

    Higher numeric value indicates higher authority in lexicographic sorting.
    """

    TIER_4_COGNEE = 1               # Validated Cognee semantic memory
    TIER_3_LANCEDB_KUZU = 2         # Validated LanceDB / Kùzu projections
    TIER_2_MANIFEST_AST = 3         # Manifest 2.0 AST call nodes & symbols
    TIER_1_SOURCE = 4               # Filesystem verified source snippets & code

    @property
    def label(self) -> str:
        """Human-readable identifier for the authority tier."""
        if self == AuthorityTier.TIER_1_SOURCE:
            return "filesystem_verified_source"
        elif self == AuthorityTier.TIER_2_MANIFEST_AST:
            return "manifest_ast"
        elif self == AuthorityTier.TIER_3_LANCEDB_KUZU:
            return "validated_lancedb_kuzu"
        elif self == AuthorityTier.TIER_4_COGNEE:
            return "validated_cognee"
        return "unknown"


@dataclass
class ArbitratedCandidate:
    """An individual candidate piece of evidence evaluated by the arbitrator."""

    id: str
    tier: AuthorityTier
    content: str
    source_file: str
    source_symbol: Optional[str] = None
    relationship_kind: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    relevance: float = 0.0
    confidence: float = 0.0
    specificity: float = 0.0
    provenance: Optional[MemoryProvenance] = None
    is_valid: bool = True
    token_estimate: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def sort_key(self) -> tuple[int, float, float, float]:
        """Lexicographic comparison tuple.

        Order: (Tier Priority, Relevance, Confidence, Specificity)
        """
        return (
            int(self.tier.value),
            round(self.relevance, 4),
            round(self.confidence, 4),
            round(self.specificity, 4),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize candidate to dictionary."""
        return {
            "id": self.id,
            "tier": self.tier.name,
            "tier_label": self.tier.label,
            "tier_value": int(self.tier.value),
            "content": self.content,
            "source_file": self.source_file,
            "source_symbol": self.source_symbol,
            "relationship_kind": self.relationship_kind,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "relevance": self.relevance,
            "confidence": self.confidence,
            "specificity": self.specificity,
            "provenance": self.provenance.to_dict() if self.provenance else None,
            "is_valid": self.is_valid,
            "token_estimate": self.token_estimate,
            "metadata": self.metadata,
        }


@dataclass
class ArbitratedEvidenceResult:
    """Consolidated result of end-to-end retrieval arbitration."""

    candidates: list[ArbitratedCandidate] = field(default_factory=list)
    tier_counts: dict[str, int] = field(default_factory=dict)
    stale_rejected_count: int = 0
    cross_repo_rejected_count: int = 0
    total_token_estimate: int = 0
    authoritative_files: list[str] = field(default_factory=list)
    authoritative_symbols: list[str] = field(default_factory=list)
    authoritative_snippets: list[str] = field(default_factory=list)
    authoritative_relationships: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize arbitration result to dictionary."""
        return {
            "candidates": [c.to_dict() for c in self.candidates],
            "tier_counts": self.tier_counts,
            "stale_rejected_count": self.stale_rejected_count,
            "cross_repo_rejected_count": self.cross_repo_rejected_count,
            "total_token_estimate": self.total_token_estimate,
            "authoritative_files": self.authoritative_files,
            "authoritative_symbols": self.authoritative_symbols,
            "authoritative_snippets": self.authoritative_snippets,
            "authoritative_relationships": self.authoritative_relationships,
        }
