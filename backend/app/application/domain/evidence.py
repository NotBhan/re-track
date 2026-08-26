"""Evidence evaluation domain entities."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class EvidenceState(str, Enum):
    """Evidence sufficiency states."""

    SUFFICIENT = "sufficient"
    PARTIAL = "partial"
    INSUFFICIENT = "insufficient"
    NONE = "none"
    INDEX_UNAVAILABLE = "index_unavailable"


@dataclass
class EvidenceRecord:
    """Evaluated evidence record for a task context."""

    evidence_state: str = EvidenceState.NONE.value
    evidence_score: float = 0.0
    evidence_confidence: float = 0.0
    evidence_files: list[str] = field(default_factory=list)
    evidence_symbols: list[str] = field(default_factory=list)
    evidence_relationships: list[str] = field(default_factory=list)
    observed_evidence: list[str] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)
    abstained: bool = False
    abstention_reason: Optional[str] = None
    suggested_next_action: Optional[str] = None
    model_claims_allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize evidence record to dictionary."""
        return {
            "evidence_state": self.evidence_state,
            "evidence_score": self.evidence_score,
            "evidence_confidence": self.evidence_confidence,
            "evidence_files": self.evidence_files,
            "evidence_symbols": self.evidence_symbols,
            "evidence_relationships": self.evidence_relationships,
            "observed_evidence": self.observed_evidence,
            "missing_evidence": self.missing_evidence,
            "abstained": self.abstained,
            "abstention_reason": self.abstention_reason,
            "suggested_next_action": self.suggested_next_action,
            "model_claims_allowed": self.model_claims_allowed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceRecord":
        """Construct evidence record from dictionary."""
        return cls(
            evidence_state=str(data.get("evidence_state", EvidenceState.NONE.value)),
            evidence_score=float(data.get("evidence_score", 0.0)),
            evidence_confidence=float(data.get("evidence_confidence", 0.0)),
            evidence_files=list(data.get("evidence_files", [])),
            evidence_symbols=list(data.get("evidence_symbols", [])),
            evidence_relationships=list(data.get("evidence_relationships", [])),
            observed_evidence=list(data.get("observed_evidence", [])),
            missing_evidence=list(data.get("missing_evidence", [])),
            abstained=bool(data.get("abstained", False)),
            abstention_reason=data.get("abstention_reason"),
            suggested_next_action=data.get("suggested_next_action"),
            model_claims_allowed=bool(data.get("model_claims_allowed", False)),
        )
