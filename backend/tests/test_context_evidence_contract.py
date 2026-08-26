"""Tests for evidence contract, DTO serialization stability, and schema invariants."""

import pytest

from app.application.domain.evidence import EvidenceRecord, EvidenceState
from app.application.dto import ContextResponse
from app.models.agent_context import AgentContextResponse


def test_evidence_record_roundtrip_serialization():
    """EvidenceRecord should serialize to dict and deserialize faithfully."""
    rec = EvidenceRecord(
        evidence_state=EvidenceState.PARTIAL.value,
        evidence_score=0.45,
        evidence_confidence=0.5,
        evidence_files=["src/app.py", "src/models.py"],
        evidence_symbols=["App", "User"],
        evidence_relationships=["App -> User"],
        observed_evidence=["Framework detected: React"],
        missing_evidence=["Database backend"],
        abstained=False,
        abstention_reason=None,
        suggested_next_action="Synthesize bounded context",
        model_claims_allowed=True,
    )

    d = rec.to_dict()
    assert d["evidence_state"] == "partial"
    assert d["evidence_score"] == 0.45
    assert d["abstained"] is False
    assert d["model_claims_allowed"] is True
    assert d["evidence_files"] == ["src/app.py", "src/models.py"]

    reconstituted = EvidenceRecord.from_dict(d)
    assert reconstituted.evidence_state == rec.evidence_state
    assert reconstituted.evidence_score == rec.evidence_score
    assert reconstituted.evidence_files == rec.evidence_files
    assert reconstituted.abstained == rec.abstained
    assert reconstituted.model_claims_allowed == rec.model_claims_allowed


def test_agent_context_response_evidence_fields_default():
    """AgentContextResponse should default to truthful evidence fields."""
    resp = AgentContextResponse(
        context_markdown="# Header\n\nContent",
        task_summary="Test summary",
        intent_category="feature",
    )

    assert resp.evidence_state == "sufficient"
    assert resp.evidence_score == 1.0
    assert resp.abstained is False
    assert resp.model_claims_allowed is True
    assert resp.missing_evidence == []


def test_agent_context_response_abstention_invariants():
    """When abstained is True, model_invoked must be False and claims not allowed."""
    resp = AgentContextResponse(
        context_markdown="# Abstention Package",
        task_summary="Build nonexistent feature",
        intent_category="feature",
        abstained=True,
        abstention_reason="No repository evidence found",
        model_claims_allowed=False,
        model_invoked=False,
        evidence_state=EvidenceState.INSUFFICIENT.value,
    )

    assert resp.abstained is True
    assert resp.model_invoked is False
    assert resp.model_claims_allowed is False
    assert resp.evidence_state == "insufficient"


def test_context_response_dto_evidence_fields():
    """ContextResponse DTO should carry evidence fields without breaking existing callers."""
    dto = ContextResponse(
        success=True,
        markdown="# Markdown",
        objective="Test objective",
        task="Test task",
        section_count=2,
        source_count=2,
        token_estimate=120,
        dataset="test_repo",
        evidence_state=EvidenceState.SUFFICIENT.value,
        evidence_score=0.9,
        abstained=False,
    )

    assert dto.evidence_state == "sufficient"
    assert dto.evidence_score == 0.9
    assert dto.abstained is False
