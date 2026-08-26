"""Tests for repository evidence assessment and gating."""

from dataclasses import dataclass, field
from pathlib import Path
import pytest

from app.application.domain.evidence import EvidenceRecord, EvidenceState
from app.application.domain.intent import ParsedIntentRecord
from app.services.evidence_service import EvidenceService


@dataclass
class MockComponent:
    name: str
    responsibilities: str = ""
    relationships: list[str] = field(default_factory=list)


@dataclass
class MockRepoSummary:
    frameworks: list[str] = field(default_factory=list)
    key_components: list[MockComponent] = field(default_factory=list)


def test_django_without_auth_abstains():
    """Django repo with no auth implementation must abstain."""
    prompt = "Implement an API endpoint requiring JWT authentication and user permissions."
    intent = ParsedIntentRecord(
        task_summary="Implement JWT authenticated API endpoint",
        category="feature",
        extracted_symbols=["jwt_auth", "UserPermission"],
        relevant_file_hints=["auth.py", "views.py"],
    )

    # Repository has Django framework detected, but only general files with no auth symbols
    repo_summary = MockRepoSummary(
        frameworks=["Django"],
        key_components=[
            MockComponent(name="ItemModel", responsibilities="Item data model"),
            MockComponent(name="get_items", responsibilities="List items view"),
        ],
    )
    indexed_files = [Path("manage.py"), Path("app/models.py"), Path("app/views.py"), Path("app/urls.py")]
    relevant_snippets = []
    matched_file_rels = ["app/views.py"]
    structural_symbols = ["ItemModel", "get_items"]

    evidence = EvidenceService.assess_evidence(
        task_prompt=prompt,
        intent=intent,
        repo_summary=repo_summary,
        indexed_files=indexed_files,
        relevant_snippets=relevant_snippets,
        matched_file_rels=matched_file_rels,
        structural_symbols=structural_symbols,
        structural_relationships=[],
    )

    # Must abstain because authentication subsystem is completely absent
    assert evidence.abstained is True
    assert evidence.model_claims_allowed is False
    assert evidence.evidence_state in [EvidenceState.INSUFFICIENT.value, EvidenceState.NONE.value]
    assert any("authentication" in m for m in evidence.missing_evidence)
    assert evidence.abstention_reason is not None


def test_framework_presence_alone_does_not_satisfy_feature():
    """Django detected in summary must only be background evidence, not auth feature evidence."""
    prompt = "Configure authentication middleware and user session handler."
    intent = ParsedIntentRecord(
        task_summary="Configure auth middleware",
        category="configuration",
        extracted_symbols=["AuthMiddleware", "SessionHandler"],
        relevant_file_hints=["middleware.py"],
    )
    repo_summary = MockRepoSummary(
        frameworks=["Django"],
        key_components=[],
    )
    indexed_files = [Path("manage.py"), Path("settings.py")]

    evidence = EvidenceService.assess_evidence(
        task_prompt=prompt,
        intent=intent,
        repo_summary=repo_summary,
        indexed_files=indexed_files,
        relevant_snippets=[],
        matched_file_rels=[],
        structural_symbols=[],
        structural_relationships=[],
    )

    assert evidence.abstained is True
    assert evidence.model_claims_allowed is False
    assert any("Django" in obs for obs in evidence.observed_evidence)
    assert any("authentication" in miss for miss in evidence.missing_evidence)


def test_prompt_vocabulary_is_not_repository_evidence():
    """Words in developer prompt must not fabricate evidence when codebase lacks them."""
    prompt = "Connect to stripe checkout payment gateway and process billing invoice webhook."
    intent = ParsedIntentRecord(
        task_summary="Integrate stripe payment",
        category="feature",
        extracted_symbols=["StripeCheckout", "process_invoice"],
        relevant_file_hints=["billing.py"],
    )
    repo_summary = MockRepoSummary(
        frameworks=["FastAPI"],
        key_components=[
            MockComponent(name="Post", responsibilities="Post model"),
            MockComponent(name="get_posts", responsibilities="Get posts endpoint"),
        ],
    )
    indexed_files = [Path("main.py"), Path("models.py"), Path("routes.py")]

    evidence = EvidenceService.assess_evidence(
        task_prompt=prompt,
        intent=intent,
        repo_summary=repo_summary,
        indexed_files=indexed_files,
        relevant_snippets=[],
        matched_file_rels=[],
        structural_symbols=["Post", "get_posts"],
        structural_relationships=[],
    )

    assert evidence.abstained is True
    assert evidence.model_claims_allowed is False
    assert any("payment" in m or "billing" in m for m in evidence.missing_evidence)


def test_genuine_code_and_symbol_evidence_passes_gate():
    """When genuine route and symbol evidence exists in codebase, evidence gate passes."""
    prompt = "Modify the get_user_profile endpoint to include user bio."
    intent = ParsedIntentRecord(
        task_summary="Modify user profile endpoint",
        category="refactoring",
        extracted_symbols=["get_user_profile", "UserProfile"],
        relevant_file_hints=["routes/users.py"],
    )
    repo_summary = MockRepoSummary(
        frameworks=["FastAPI"],
        key_components=[
            MockComponent(name="get_user_profile", responsibilities="Profile handler", relationships=["UserProfile"]),
            MockComponent(name="UserProfile", responsibilities="User model"),
        ],
    )
    indexed_files = [Path("routes/users.py"), Path("models/user.py"), Path("main.py")]
    relevant_snippets = [
        "def get_user_profile(user_id: str) -> UserProfile:\n    return user_repo.find(user_id)"
    ]
    matched_file_rels = ["routes/users.py", "models/user.py"]
    structural_symbols = ["get_user_profile", "UserProfile"]
    structural_relationships = ["get_user_profile -> UserProfile"]

    evidence = EvidenceService.assess_evidence(
        task_prompt=prompt,
        intent=intent,
        repo_summary=repo_summary,
        indexed_files=indexed_files,
        relevant_snippets=relevant_snippets,
        matched_file_rels=matched_file_rels,
        structural_symbols=structural_symbols,
        structural_relationships=structural_relationships,
    )

    assert evidence.abstained is False
    assert evidence.model_claims_allowed is True
    assert evidence.evidence_state in [EvidenceState.SUFFICIENT.value, EvidenceState.PARTIAL.value]
    assert evidence.evidence_score >= 0.40
    assert "get_user_profile" in evidence.evidence_symbols
    assert "routes/users.py" in evidence.evidence_files


def test_partial_evidence_identifies_missing_items():
    """When partial code exists, partial evidence state is set and missing components are tracked."""
    prompt = "Connect existing get_items route to a new persistent sqlite database repository."
    intent = ParsedIntentRecord(
        task_summary="Connect get_items to database repository",
        category="feature",
        extracted_symbols=["get_items", "SqliteItemRepository"],
        relevant_file_hints=["routes.py"],
    )
    repo_summary = MockRepoSummary(
        frameworks=["Flask"],
        key_components=[
            MockComponent(name="get_items", responsibilities="Get items handler"),
        ],
    )
    indexed_files = [Path("routes.py"), Path("app.py")]
    relevant_snippets = ["def get_items():\n    return []"]
    matched_file_rels = ["routes.py"]
    structural_symbols = ["get_items"]

    evidence = EvidenceService.assess_evidence(
        task_prompt=prompt,
        intent=intent,
        repo_summary=repo_summary,
        indexed_files=indexed_files,
        relevant_snippets=relevant_snippets,
        matched_file_rels=matched_file_rels,
        structural_symbols=structural_symbols,
        structural_relationships=[],
    )

    assert evidence.abstained is False
    assert evidence.model_claims_allowed is True
    assert evidence.evidence_state == EvidenceState.PARTIAL.value
    assert "get_items" in evidence.evidence_symbols


def test_empty_indexed_files_returns_index_unavailable():
    """When repo is unindexed or empty, index_unavailable state is produced."""
    prompt = "Explain the system architecture."
    intent = ParsedIntentRecord(task_summary="Explain architecture", category="general")

    evidence = EvidenceService.assess_evidence(
        task_prompt=prompt,
        intent=intent,
        repo_summary=None,
        indexed_files=[],
    )

    assert evidence.abstained is True
    assert evidence.model_claims_allowed is False
    assert evidence.evidence_state == EvidenceState.INDEX_UNAVAILABLE.value
