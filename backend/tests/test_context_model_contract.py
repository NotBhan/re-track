"""Tests for Context DTO and AgentContext schema contracts and telemetry consistency."""

import pytest
from pydantic import ValidationError

from app.models.agent_context import AgentContextRequest, AgentContextResponse
from app.application.dto.context import ContextResponse, GenerateContextRequest
from app.application.domain.intent import ParsedIntentRecord, parse_intent_heuristics


def test_agent_context_response_telemetry_defaults():
    """Verify default values for AgentContextResponse telemetry."""
    resp = AgentContextResponse(
        context_markdown="# Context",
        task_summary="Fix auth issue",
        intent_category="bug_fix",
    )
    assert resp.success is True
    assert resp.model_invoked is False
    assert resp.provider_identity is None
    assert resp.model_name is None
    assert resp.inference_status == "not_configured"
    assert resp.fallback_used is False
    assert resp.fallback_reason is None
    assert resp.inference_time_ms == 0


def test_context_response_telemetry_defaults():
    """Verify default values for ContextResponse telemetry."""
    resp = ContextResponse(
        success=True,
        task="Find database models",
        objective="Find database models",
        markdown="# Models",
        section_count=1,
        source_count=1,
        token_estimate=100,
        dataset="test_repo",
    )
    assert resp.model_invoked is False
    assert resp.provider_identity is None
    assert resp.model_name is None
    assert resp.inference_status == "not_configured"
    assert resp.fallback_used is False
    assert resp.fallback_reason is None
    assert resp.inference_time_ms == 0


def test_parsed_intent_record_telemetry_serialization():
    """Verify ParsedIntentRecord serialization and deserialization with telemetry fields."""
    record = ParsedIntentRecord(
        task_summary="Refactor indexing engine",
        category="refactoring",
        extracted_symbols=["IndexingService", "ManifestService"],
        relevant_file_hints=["indexing_service.py"],
        is_vague=False,
        model_invoked=True,
        provider_identity="lmstudio",
        model_name="qwen2.5-coder:7b",
        inference_status="completed",
        fallback_used=False,
        fallback_reason=None,
        inference_time_ms=124,
    )
    data = record.to_dict()
    assert data["model_invoked"] is True
    assert data["provider_identity"] == "lmstudio"
    assert data["model_name"] == "qwen2.5-coder:7b"
    assert data["inference_status"] == "completed"
    assert data["inference_time_ms"] == 124

    reconstructed = ParsedIntentRecord.from_dict(data)
    assert reconstructed.model_invoked is True
    assert reconstructed.provider_identity == "lmstudio"
    assert reconstructed.model_name == "qwen2.5-coder:7b"
    assert reconstructed.inference_status == "completed"
    assert reconstructed.inference_time_ms == 124


def test_rule_based_fallback_telemetry_consistency():
    """Verify parse_intent_heuristics returns deterministic fallback record."""
    intent = parse_intent_heuristics("Fix the JWT parsing bug in auth.py")
    assert intent.category == "bug_fix"
    assert intent.model_invoked is False
    assert intent.provider_identity is None
    assert intent.inference_status == "not_configured"
    assert intent.fallback_used is False  # Pure heuristic default is unflagged until evaluated in service
