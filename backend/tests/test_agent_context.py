"""Unit tests for get_agent_context command and AgentContext schemas."""

from pathlib import Path
import pytest

from app.models.agent_context import AgentContextRequest, AgentContextResponse
from app.services.intent_parser import IntentParserService


def test_agent_context_request_validation():
    req = AgentContextRequest(
        task_prompt="Fix the authentication token expiry bug in auth.py",
        repository_path="/test/repo",
        max_tokens=2000,
    )
    assert req.task_prompt.startswith("Fix")
    assert req.include_structural_graph is True


def test_intent_parser_fallback():
    prompt = "Add new feature for ManifestService in indexing_service.py"
    intent = IntentParserService.rule_based_fallback(prompt)

    assert intent.category == "feature_addition"
    assert "indexing_service.py" in intent.relevant_file_hints
    assert "ManifestService" in intent.extracted_symbols or "indexing_service.py" in intent.relevant_file_hints
    assert intent.is_vague is False


def test_intent_parser_vague_prompt():
    prompt = "explain everything"
    intent = IntentParserService.rule_based_fallback(prompt)

    assert intent.is_vague is True
    assert intent.category == "explanation"
