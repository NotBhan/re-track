"""Tests for post-generation grounding validation and think block sanitization."""

from pathlib import Path
import pytest

from app.application.domain.evidence import EvidenceRecord, EvidenceState
from app.application.domain.intent import ParsedIntentRecord
from app.services.evidence_service import EvidenceService


def test_strip_think_tags_from_reasoning_models():
    """Reasoning model <think>...</think> tags must be cleanly stripped before presentation."""
    raw_markdown = (
        "<think>\n"
        "The user is asking for an endpoint modification.\n"
        "Let's look at the Django codebase structure...\n"
        "Wait, we have get_user_profile in routes/users.py.\n"
        "</think>\n"
        "# Context Package\n\n"
        "## Target Functions\n"
        "- `get_user_profile` in `routes/users.py`\n"
    )

    evidence = EvidenceRecord(
        evidence_state=EvidenceState.SUFFICIENT.value,
        evidence_score=0.85,
        model_claims_allowed=True,
    )
    indexed_files = [Path("routes/users.py")]

    sanitized = EvidenceService.sanitize_and_validate_grounded_response(
        raw_markdown=raw_markdown,
        evidence=evidence,
        indexed_files=indexed_files,
    )

    assert "<think>" not in sanitized
    assert "</think>" not in sanitized
    assert "The user is asking for an endpoint modification" not in sanitized
    assert "# Context Package" in sanitized
    assert "`get_user_profile` in `routes/users.py`" in sanitized


def test_strip_thinking_bracket_tags():
    """[THINKING]...[/THINKING] blocks must also be stripped."""
    raw_markdown = (
        "[THINKING]\n"
        "Internal chain of thought step 1\n"
        "Internal chain of thought step 2\n"
        "[/THINKING]\n"
        "# Grounded Overview\n\n"
        "Modifications should target `app/main.py`."
    )

    evidence = EvidenceRecord(
        evidence_state=EvidenceState.SUFFICIENT.value,
        evidence_score=0.9,
        model_claims_allowed=True,
    )

    sanitized = EvidenceService.sanitize_and_validate_grounded_response(
        raw_markdown=raw_markdown,
        evidence=evidence,
        indexed_files=[Path("app/main.py")],
    )

    assert "[THINKING]" not in sanitized
    assert "[/THINKING]" not in sanitized
    assert "Internal chain of thought" not in sanitized
    assert "# Grounded Overview" in sanitized


def test_build_abstention_package_structure():
    """Abstention package must contain all required sections deterministically."""
    prompt = "Create an OAuth2 authentication provider."
    intent = ParsedIntentRecord(
        task_summary="Create OAuth2 provider",
        category="feature",
    )
    evidence = EvidenceRecord(
        evidence_state=EvidenceState.INSUFFICIENT.value,
        evidence_score=0.05,
        observed_evidence=["Framework detected: Django (architectural structure).", "Indexed repository files: 12 files analyzed."],
        missing_evidence=["authentication (no existing symbols, middleware, models, or endpoints found)"],
        abstained=True,
        abstention_reason="No repository evidence was found for: authentication.",
        suggested_next_action="Treat authentication as a new subsystem to build from scratch rather than modifying an existing implementation.",
        model_claims_allowed=False,
    )

    pkg = EvidenceService.build_abstention_package(
        task_prompt=prompt,
        intent=intent,
        evidence=evidence,
    )

    assert "# Task Intent" in pkg
    assert "# Observed Repository Evidence" in pkg
    assert "# Missing Evidence" in pkg
    assert "# Insufficient Repository Evidence Notice" in pkg
    assert "Framework detected: Django" in pkg
    assert "authentication (no existing symbols, middleware, models, or endpoints found)" in pkg
    assert "Treat authentication as a new subsystem to build from scratch" in pkg
    assert "`ABSTAINED` (insufficient)" in pkg
