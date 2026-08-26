"""Adversarial and authoritative test suite for End-to-End Retrieval Arbitration (Phase 10D.5).

Verifies strict authority ordering, lexicographic ranking, provenance validation,
budget reservation, and EvidenceService gating integration.
"""

from pathlib import Path
import pytest

from app.application.domain.arbitration import (
    ArbitratedCandidate,
    ArbitratedEvidenceResult,
    AuthorityTier,
)
from app.application.domain.evidence import EvidenceRecord, EvidenceState
from app.application.domain.intent import ParsedIntentRecord
from app.services.manifest_service import FileFingerprint, RepositoryManifest
from app.application.domain.memory import MemoryProvenance
from app.models.responses import (
    ComponentInfo,
    RecallResult,
    RepositorySummary,
    TechnologyStack,
)
from app.services.evidence_service import EvidenceService
from app.services.retrieval_arbitrator import RetrievalArbitrator


def _create_test_manifest() -> RepositoryManifest:
    """Create a mock repository manifest with known files and fingerprints."""
    manifest = RepositoryManifest(
        repo_path="/test/repo",
        dataset_name="test_repo",
        schema_version="2.0",
        parser_version="2.0.0",
        repo_fingerprint="repo_fp_alpha_001",
    )
    manifest.files["src/auth.py"] = FileFingerprint(
        path="src/auth.py",
        mtime=1700000000.0,
        size=1024,
        sha256="sha_auth_12345",
        language="python",
        symbols=["authenticate_user", "verify_token"],
    )
    manifest.files["src/service.py"] = FileFingerprint(
        path="src/service.py",
        mtime=1700000000.0,
        size=2048,
        sha256="sha_service_67890",
        language="python",
        symbols=["process_order", "calculate_tax"],
    )
    return manifest


# =============================================================================
# Scope 1: AuthorityTier & Priority Contract
# =============================================================================


def test_authority_tier_contract_and_ordering():
    """Verify AuthorityTier integer ranking and exact human-readable labels."""
    assert AuthorityTier.TIER_1_SOURCE.value == 4
    assert AuthorityTier.TIER_2_MANIFEST_AST.value == 3
    assert AuthorityTier.TIER_3_LANCEDB_KUZU.value == 2
    assert AuthorityTier.TIER_4_COGNEE.value == 1

    # Numeric ordering: Tier 1 > Tier 2 > Tier 3 > Tier 4
    assert AuthorityTier.TIER_1_SOURCE > AuthorityTier.TIER_2_MANIFEST_AST
    assert AuthorityTier.TIER_2_MANIFEST_AST > AuthorityTier.TIER_3_LANCEDB_KUZU
    assert AuthorityTier.TIER_3_LANCEDB_KUZU > AuthorityTier.TIER_4_COGNEE

    # Label checks
    assert AuthorityTier.TIER_1_SOURCE.label == "filesystem_verified_source"
    assert AuthorityTier.TIER_2_MANIFEST_AST.label == "manifest_ast"
    assert AuthorityTier.TIER_3_LANCEDB_KUZU.label == "validated_lancedb_kuzu"
    assert AuthorityTier.TIER_4_COGNEE.label == "validated_cognee"


# =============================================================================
# Scope 2: ArbitratedCandidate & Result Dataclasses
# =============================================================================


def test_arbitrated_candidate_and_result_dataclass_serialization():
    """Verify ArbitratedCandidate and ArbitratedEvidenceResult serialization and sort_key."""
    prov = MemoryProvenance(
        repository_id="repo_1",
        repository_fingerprint="repo_fp_alpha_001",
        source_file="src/auth.py",
        source_sha256="sha_auth_12345",
        source_symbol="authenticate_user",
    )
    cand = ArbitratedCandidate(
        id="c1",
        tier=AuthorityTier.TIER_1_SOURCE,
        content="def authenticate_user(): pass",
        source_file="src/auth.py",
        source_symbol="authenticate_user",
        relevance=0.85,
        confidence=1.0,
        specificity=0.9,
        provenance=prov,
        is_valid=True,
        token_estimate=10,
    )

    assert cand.sort_key() == (4, 0.85, 1.0, 0.9)
    d = cand.to_dict()
    assert d["tier"] == "TIER_1_SOURCE"
    assert d["tier_label"] == "filesystem_verified_source"
    assert d["tier_value"] == 4
    assert d["relevance"] == 0.85

    res = ArbitratedEvidenceResult(
        candidates=[cand],
        tier_counts={AuthorityTier.TIER_1_SOURCE.label: 1},
        authoritative_files=["src/auth.py"],
        authoritative_symbols=["authenticate_user"],
    )
    res_dict = res.to_dict()
    assert len(res_dict["candidates"]) == 1
    assert res_dict["authoritative_files"] == ["src/auth.py"]


# =============================================================================
# Scope 3: Lexicographic Sort Key & Deterministic Ordering
# =============================================================================


def test_lexicographic_sort_key_determinism():
    """Verify lexicographic sort key guarantees strict tier priority over similarity."""
    c_tier4_high = ArbitratedCandidate(
        id="c4",
        tier=AuthorityTier.TIER_4_COGNEE,
        content="High semantic similarity text",
        source_file="src/auth.py",
        relevance=0.9999,
        confidence=1.0,
        specificity=1.0,
    )
    c_tier3_med = ArbitratedCandidate(
        id="c3",
        tier=AuthorityTier.TIER_3_LANCEDB_KUZU,
        content="Vector match",
        source_file="src/auth.py",
        relevance=0.7000,
        confidence=0.8,
        specificity=0.8,
    )
    c_tier2_low = ArbitratedCandidate(
        id="c2",
        tier=AuthorityTier.TIER_2_MANIFEST_AST,
        content="AST Node",
        source_file="src/auth.py",
        relevance=0.4000,
        confidence=0.5,
        specificity=0.5,
    )
    c_tier1_lowest = ArbitratedCandidate(
        id="c1",
        tier=AuthorityTier.TIER_1_SOURCE,
        content="Source Snippet",
        source_file="src/auth.py",
        relevance=0.1000,
        confidence=0.1,
        specificity=0.1,
    )

    unordered = [c_tier4_high, c_tier3_med, c_tier2_low, c_tier1_lowest]
    ordered = sorted(unordered, key=lambda c: c.sort_key(), reverse=True)

    # Order must be Tier 1 -> Tier 2 -> Tier 3 -> Tier 4
    assert [c.id for c in ordered] == ["c1", "c2", "c3", "c4"]


def test_arbitration_deterministic_reproducibility():
    """Verify that multiple consecutive arbitration runs produce byte-for-byte identical outcomes."""
    manifest = _create_test_manifest()
    intent = ParsedIntentRecord(
        task_summary="Authenticate user login",
        category="authentication",
        extracted_symbols=["authenticate_user"],
        relevant_file_hints=["src/auth.py"],
    )

    prov = MemoryProvenance(
        repository_id="repo_1",
        repository_fingerprint="repo_fp_alpha_001",
        source_file="src/auth.py",
        source_sha256="sha_auth_12345",
        source_symbol="authenticate_user",
    )
    cognee_mem = {
        "text": "Valid auth documentation.",
        "similarity": 0.85,
        "provenance": prov,
    }

    snippets = ["### File: `src/auth.py`\ndef authenticate_user(token):\n    return True"]

    res1 = RetrievalArbitrator.arbitrate(
        task_prompt="Authenticate user login",
        intent=intent,
        manifest=manifest,
        source_snippets=snippets,
        source_matched_files=["src/auth.py"],
        ast_symbols=["authenticate_user"],
        cognee_memories=[cognee_mem],
    )

    res2 = RetrievalArbitrator.arbitrate(
        task_prompt="Authenticate user login",
        intent=intent,
        manifest=manifest,
        source_snippets=snippets,
        source_matched_files=["src/auth.py"],
        ast_symbols=["authenticate_user"],
        cognee_memories=[cognee_mem],
    )

    assert res1.to_dict() == res2.to_dict()
    assert [c.sort_key() for c in res1.candidates] == [c.sort_key() for c in res2.candidates]


# =============================================================================
# Scope 4: Provenance Rejection Rules
# =============================================================================


def test_provenance_rejection_rules_exhaustive():
    """Exhaustively verify each provenance failure reason in validate_candidate_provenance."""
    manifest = _create_test_manifest()

    # 1. Missing manifest
    assert RetrievalArbitrator.validate_candidate_provenance(None, None) == (False, "no_active_manifest")

    # 2. Missing provenance
    assert RetrievalArbitrator.validate_candidate_provenance(None, manifest) == (False, "missing_provenance")

    # 3. Invalid provenance object
    assert RetrievalArbitrator.validate_candidate_provenance("not_a_prov", manifest) == (False, "invalid_provenance_structure")

    # 4. Cross-repository mismatch
    prov_cross = MemoryProvenance(
        repository_fingerprint="repo_fp_alien_999",
        source_file="src/auth.py",
        source_sha256="sha_auth_12345",
    )
    assert RetrievalArbitrator.validate_candidate_provenance(prov_cross, manifest) == (False, "cross_repository_mismatch")

    # 5. Source file missing in manifest
    prov_missing_file = MemoryProvenance(
        repository_fingerprint="repo_fp_alpha_001",
        source_file="src/deleted_file.py",
        source_sha256="sha_any_123",
    )
    assert RetrievalArbitrator.validate_candidate_provenance(prov_missing_file, manifest) == (False, "source_file_missing_in_manifest")

    # 6. SHA-256 stale
    prov_stale_sha = MemoryProvenance(
        repository_fingerprint="repo_fp_alpha_001",
        source_file="src/auth.py",
        source_sha256="sha_stale_99999",
    )
    assert RetrievalArbitrator.validate_candidate_provenance(prov_stale_sha, manifest) == (False, "source_sha256_stale")

    # 7. Source symbol missing
    prov_missing_sym = MemoryProvenance(
        repository_fingerprint="repo_fp_alpha_001",
        source_file="src/auth.py",
        source_sha256="sha_auth_12345",
        source_symbol="nonexistent_function",
    )
    assert RetrievalArbitrator.validate_candidate_provenance(prov_missing_sym, manifest) == (False, "source_symbol_missing")

    # 8. Valid provenance
    prov_valid = MemoryProvenance(
        repository_fingerprint="repo_fp_alpha_001",
        source_file="src/auth.py",
        source_sha256="sha_auth_12345",
        source_symbol="authenticate_user",
    )
    assert RetrievalArbitrator.validate_candidate_provenance(prov_valid, manifest) == (True, "valid")


# =============================================================================
# Scope 5: Adversarial & Pipeline Integration Tests
# =============================================================================


def test_high_similarity_stale_memory_loses_to_valid_source():
    """Adversarial test 1: Stale memory with 0.99 similarity loses to valid source (0.4 relevance)."""
    manifest = _create_test_manifest()
    intent = ParsedIntentRecord(
        task_summary="Authenticate user login",
        category="authentication",
        extracted_symbols=["authenticate_user"],
        relevant_file_hints=["src/auth.py"],
    )

    # Stale Cognee memory (SHA-256 mismatch)
    stale_prov = MemoryProvenance(
        repository_id="repo_1",
        repository_fingerprint="repo_fp_alpha_001",
        source_file="src/auth.py",
        source_sha256="stale_sha_99999",  # Does NOT match manifest
        source_symbol="authenticate_user",
    )
    stale_memory = {
        "text": "Stale authentication logic with outdated password hashing.",
        "similarity": 0.99,
        "provenance": stale_prov,
    }

    # Valid source snippet with lower score
    source_snippets = [
        "### File: `src/auth.py`\ndef authenticate_user(token):\n    return verify_token(token)"
    ]

    result = RetrievalArbitrator.arbitrate(
        task_prompt="Authenticate user login with JWT",
        intent=intent,
        manifest=manifest,
        source_snippets=source_snippets,
        source_matched_files=["src/auth.py"],
        ast_symbols=["authenticate_user"],
        cognee_memories=[stale_memory],
        target_tokens=3000,
    )

    assert result.stale_rejected_count == 1
    cand_tiers = [c.tier for c in result.candidates]
    assert AuthorityTier.TIER_1_SOURCE in cand_tiers
    assert AuthorityTier.TIER_4_COGNEE not in cand_tiers
    assert any("authenticate_user" in c.content for c in result.candidates)


def test_low_relevance_source_remains_above_high_relevance_cognee():
    """Adversarial test 2: Low-relevance source remains lexicographically above high-relevance valid memory."""
    manifest = _create_test_manifest()
    intent = ParsedIntentRecord(
        task_summary="Process order and calculate tax",
        category="feature_request",
        extracted_symbols=["process_order"],
        relevant_file_hints=["src/service.py"],
    )

    # Valid Cognee memory with very high relevance (0.95)
    valid_prov = MemoryProvenance(
        repository_id="repo_1",
        repository_fingerprint="repo_fp_alpha_001",
        source_file="src/service.py",
        source_sha256="sha_service_67890",
        source_symbol="calculate_tax",
    )
    high_rel_memory = {
        "text": "Detailed tax calculation and VAT breakdown algorithms.",
        "similarity": 0.95,
        "provenance": valid_prov,
    }

    # Low relevance source snippet (0.2 relevance score)
    low_rel_source = [
        "### File: `src/service.py`\n# general helper\npass"
    ]

    result = RetrievalArbitrator.arbitrate(
        task_prompt="Process order",
        intent=intent,
        manifest=manifest,
        source_snippets=low_rel_source,
        source_matched_files=["src/service.py"],
        ast_symbols=["process_order"],
        cognee_memories=[high_rel_memory],
        target_tokens=3000,
    )

    assert len(result.candidates) >= 2
    first_cand = result.candidates[0]
    assert first_cand.tier in (AuthorityTier.TIER_1_SOURCE, AuthorityTier.TIER_2_MANIFEST_AST)
    assert first_cand.tier.value > AuthorityTier.TIER_4_COGNEE.value

    tier_1_indices = [i for i, c in enumerate(result.candidates) if c.tier == AuthorityTier.TIER_1_SOURCE]
    tier_4_indices = [i for i, c in enumerate(result.candidates) if c.tier == AuthorityTier.TIER_4_COGNEE]
    if tier_1_indices and tier_4_indices:
        assert max(tier_1_indices) < min(tier_4_indices)


def test_filesystem_path_without_content_is_not_sufficient_evidence():
    """Adversarial test 3: Filesystem path existence alone without content or symbols fails evidence gate."""
    intent = ParsedIntentRecord(
        task_summary="Implement stripe checkout webhook",
        category="payment_billing",
        extracted_symbols=["handle_stripe_webhook"],
        relevant_file_hints=["src/payments.py"],
    )

    indexed_files = ["src/payments.py", "src/models.py"]

    evidence = EvidenceService.assess_evidence(
        task_prompt="Implement stripe checkout webhook and invoice generation",
        intent=intent,
        repo_summary=None,
        indexed_files=indexed_files,
        relevant_snippets=[],
        matched_file_rels=["src/payments.py"],
        structural_symbols=[],
        structural_relationships=[],
    )

    assert evidence.abstained is True
    assert evidence.model_claims_allowed is False
    assert evidence.evidence_state in (EvidenceState.INSUFFICIENT.value, EvidenceState.NONE.value)
    assert "Filesystem path references without matched code content" in (evidence.abstention_reason or "")


def test_llm_output_never_enters_arbitration_candidates():
    """Adversarial test 4: LLM outputs and synthesized markdown do not participate in candidate arbitration."""
    manifest = _create_test_manifest()
    intent = ParsedIntentRecord(
        task_summary="Authenticate user login",
        category="authentication",
        extracted_symbols=["authenticate_user"],
        relevant_file_hints=["src/auth.py"],
    )

    result = RetrievalArbitrator.arbitrate(
        task_prompt="Authenticate user login",
        intent=intent,
        manifest=manifest,
        source_snippets=["### File: `src/auth.py`\ndef authenticate_user(): pass"],
        source_matched_files=["src/auth.py"],
        ast_symbols=["authenticate_user"],
        lancedb_kuzu_memories=[],
        cognee_memories=[],
    )

    for cand in result.candidates:
        assert "<think>" not in cand.content
        assert cand.tier in (
            AuthorityTier.TIER_1_SOURCE,
            AuthorityTier.TIER_2_MANIFEST_AST,
            AuthorityTier.TIER_3_LANCEDB_KUZU,
            AuthorityTier.TIER_4_COGNEE,
        )


def test_lower_tier_cannot_consume_reserved_authoritative_budget():
    """Adversarial test 5: Lower-tier candidates cannot consume budget reserved for Tier 1 and Tier 2."""
    manifest = _create_test_manifest()
    intent = ParsedIntentRecord(
        task_summary="Authenticate user login",
        category="authentication",
        extracted_symbols=["authenticate_user"],
        relevant_file_hints=["src/auth.py"],
    )

    valid_prov = MemoryProvenance(
        repository_id="repo_1",
        repository_fingerprint="repo_fp_alpha_001",
        source_file="src/auth.py",
        source_sha256="sha_auth_12345",
        source_symbol="authenticate_user",
    )
    large_cognee_mem = {
        "text": "Very long semantic explanation " * 50,  # ~350 tokens
        "similarity": 0.99,
        "provenance": valid_prov,
    }

    authoritative_snippet = "### File: `src/auth.py`\ndef authenticate_user(token):\n    return verify_token(token)"

    # Tight budget: 40 tokens (enough for snippet + AST, but not large cognee memory)
    result = RetrievalArbitrator.arbitrate(
        task_prompt="Authenticate user login",
        intent=intent,
        manifest=manifest,
        source_snippets=[authoritative_snippet],
        source_matched_files=["src/auth.py"],
        ast_symbols=["authenticate_user"],
        cognee_memories=[large_cognee_mem],
        target_tokens=40,
        reserve_authoritative_budget=True,
    )

    included_tiers = [c.tier for c in result.candidates]
    assert AuthorityTier.TIER_1_SOURCE in included_tiers
    assert AuthorityTier.TIER_2_MANIFEST_AST in included_tiers
    assert AuthorityTier.TIER_4_COGNEE not in included_tiers


def test_cross_repository_memory_is_rejected_before_ranking():
    """Adversarial test 6: Memory from a different repository is rejected immediately before ranking."""
    manifest = _create_test_manifest()
    intent = ParsedIntentRecord(
        task_summary="Authenticate user login",
        category="authentication",
        extracted_symbols=["authenticate_user"],
        relevant_file_hints=["src/auth.py"],
    )

    # Cross-repository memory item (different repository_fingerprint)
    alien_prov = MemoryProvenance(
        repository_id="alien_repo_999",
        repository_fingerprint="repo_fp_alien_999",  # Mismatch with repo_fp_alpha_001
        source_file="src/auth.py",
        source_sha256="sha_auth_12345",
        source_symbol="authenticate_user",
    )
    alien_memory = {
        "text": "Alien repository authentication instructions.",
        "similarity": 0.99,
        "provenance": alien_prov,
    }

    result = RetrievalArbitrator.arbitrate(
        task_prompt="Authenticate user login",
        intent=intent,
        manifest=manifest,
        source_snippets=["### File: `src/auth.py`\ndef authenticate_user(): pass"],
        source_matched_files=["src/auth.py"],
        cognee_memories=[alien_memory],
    )

    assert result.cross_repo_rejected_count == 1
    assert all("alien" not in c.content.lower() for c in result.candidates)


def test_existing_10d3_abstention_contract_remains_authoritative():
    """Adversarial test 7: Classical Django no-auth negative case abstains without fabricating evidence."""
    intent = ParsedIntentRecord(
        task_summary="Configure Django JWT token authentication",
        category="authentication",
        extracted_symbols=["JWTAuthentication", "obtain_jwt_token"],
        relevant_file_hints=["settings.py", "urls.py"],
    )

    from app.models.responses import ArchitectureInfo, ConventionInfo, DirectoryEntry
    django_summary = RepositorySummary(
        version="1.0",
        repository_fingerprint="fp_django_123",
        generated_at="2026-08-26T00:00:00Z",
        indexed_commit=None,
        project_purpose="Django Clean App",
        technology_stack=TechnologyStack(
            languages=["Python"],
            frameworks=["Django"],
            databases=["PostgreSQL"],
            dependencies=["django>=4.2"],
        ),
        repository_map=[DirectoryEntry(path="myapp", description="App code")],
        architecture=ArchitectureInfo(pattern="mvc", layers=["views", "models"], boundaries=[], major_flows=[]),
        key_components=[
            ComponentInfo(name="CoreViews", responsibilities="Core views", relationships=[]),
            ComponentInfo(name="UserModels", responsibilities="Basic user models", relationships=[]),
        ],
        entry_points=[],
        public_apis=[],
        coding_conventions=ConventionInfo(naming="snake_case", formatting="black", patterns=[]),
        domain_vocabulary={},
    )

    indexed_files = ["manage.py", "myapp/views.py", "myapp/models.py", "myapp/urls.py"]

    # Arbitrate with empty snippets (no auth logic exists)
    arbitrated = RetrievalArbitrator.arbitrate(
        task_prompt="Configure Django JWT token authentication",
        intent=intent,
        manifest=None,
        source_snippets=[],
        source_matched_files=[],
        ast_symbols=["CoreViews", "UserModels"],
        ast_call_edges=[],
    )

    evidence = EvidenceService.assess_evidence(
        task_prompt="Configure Django JWT token authentication",
        intent=intent,
        repo_summary=django_summary,
        indexed_files=indexed_files,
        relevant_snippets=arbitrated.authoritative_snippets,
        matched_file_rels=arbitrated.authoritative_files,
        structural_symbols=arbitrated.authoritative_symbols,
        structural_relationships=arbitrated.authoritative_relationships,
        arbitrated_result=arbitrated,
    )

    assert evidence.abstained is True
    assert evidence.model_claims_allowed is False
    assert any("authentication" in miss.lower() for miss in evidence.missing_evidence)

    package_md = EvidenceService.build_abstention_package(
        task_prompt="Configure Django JWT token authentication",
        intent=intent,
        evidence=evidence,
    )
    assert "# Insufficient Repository Evidence Notice" in package_md
    assert "ABSTAINED" in package_md


# =============================================================================
# Scope 6: Task 2 — Explicit Provenance Boundary Tests
# =============================================================================


def test_provenance_boundary_deleted_file():
    """Case 1: Memory for a deleted file is rejected, never ranked, and consumes 0 budget."""
    manifest = _create_test_manifest()
    intent = ParsedIntentRecord(
        task_summary="Inspect removed legacy subsystem",
        category="general",
        extracted_symbols=["legacy_helper"],
        relevant_file_hints=["src/legacy.py"],
    )

    deleted_file_prov = MemoryProvenance(
        repository_id="repo_1",
        repository_fingerprint="repo_fp_alpha_001",
        source_file="src/legacy.py",  # Not in manifest
        source_sha256="sha_legacy_999",
        source_symbol="legacy_helper",
    )
    deleted_mem = {
        "text": "Legacy helper code " * 30,  # ~120 tokens
        "similarity": 0.98,
        "provenance": deleted_file_prov,
    }

    result = RetrievalArbitrator.arbitrate(
        task_prompt="Inspect removed legacy subsystem",
        intent=intent,
        manifest=manifest,
        source_snippets=[],
        cognee_memories=[deleted_mem],
        target_tokens=500,
    )

    assert result.stale_rejected_count == 1
    assert len(result.candidates) == 0
    assert result.total_token_estimate == 0


def test_provenance_boundary_modified_file_sha_mismatch():
    """Case 2: Memory for a modified file (SHA mismatch) is rejected, never ranked, and consumes 0 budget."""
    manifest = _create_test_manifest()
    intent = ParsedIntentRecord(
        task_summary="Authenticate user login",
        category="authentication",
        extracted_symbols=["authenticate_user"],
        relevant_file_hints=["src/auth.py"],
    )

    modified_file_prov = MemoryProvenance(
        repository_id="repo_1",
        repository_fingerprint="repo_fp_alpha_001",
        source_file="src/auth.py",
        source_sha256="outdated_sha_prior_to_edit",  # Does NOT match sha_auth_12345
        source_symbol="authenticate_user",
    )
    stale_mem = {
        "text": "Outdated authentication algorithm with plain text passwords.",
        "similarity": 0.99,
        "provenance": modified_file_prov,
    }

    result = RetrievalArbitrator.arbitrate(
        task_prompt="Authenticate user login",
        intent=intent,
        manifest=manifest,
        source_snippets=[],
        cognee_memories=[stale_mem],
        target_tokens=500,
    )

    assert result.stale_rejected_count == 1
    assert len(result.candidates) == 0
    assert result.total_token_estimate == 0


def test_provenance_boundary_wrong_repository_fingerprint():
    """Case 3: Memory from a different repository fingerprint is rejected as cross-repo and never ranked."""
    manifest = _create_test_manifest()
    intent = ParsedIntentRecord(
        task_summary="Authenticate user login",
        category="authentication",
        extracted_symbols=["authenticate_user"],
        relevant_file_hints=["src/auth.py"],
    )

    cross_repo_prov = MemoryProvenance(
        repository_id="foreign_repo_x",
        repository_fingerprint="repo_fp_foreign_999",  # Does NOT match repo_fp_alpha_001
        source_file="src/auth.py",
        source_sha256="sha_auth_12345",
        source_symbol="authenticate_user",
    )
    cross_mem = {
        "text": "Foreign repository auth notes.",
        "similarity": 0.95,
        "provenance": cross_repo_prov,
    }

    result = RetrievalArbitrator.arbitrate(
        task_prompt="Authenticate user login",
        intent=intent,
        manifest=manifest,
        source_snippets=[],
        cognee_memories=[cross_mem],
        target_tokens=500,
    )

    assert result.cross_repo_rejected_count == 1
    assert len(result.candidates) == 0
    assert result.total_token_estimate == 0


def test_provenance_boundary_missing_symbol():
    """Case 4: Memory referencing a removed symbol from an active file is rejected, never ranked, and consumes 0 budget."""
    manifest = _create_test_manifest()
    intent = ParsedIntentRecord(
        task_summary="Old login flow",
        category="authentication",
        extracted_symbols=["deprecated_login_flow"],
        relevant_file_hints=["src/auth.py"],
    )

    missing_sym_prov = MemoryProvenance(
        repository_id="repo_1",
        repository_fingerprint="repo_fp_alpha_001",
        source_file="src/auth.py",
        source_sha256="sha_auth_12345",
        source_symbol="deprecated_login_flow",  # auth.py only has authenticate_user, verify_token
    )
    missing_sym_mem = {
        "text": "Deprecated login flow implementation details.",
        "similarity": 0.92,
        "provenance": missing_sym_prov,
    }

    result = RetrievalArbitrator.arbitrate(
        task_prompt="Old login flow",
        intent=intent,
        manifest=manifest,
        source_snippets=[],
        cognee_memories=[missing_sym_mem],
        target_tokens=500,
    )

    assert result.stale_rejected_count == 1
    assert len(result.candidates) == 0
    assert result.total_token_estimate == 0


def test_provenance_boundary_valid_current_record():
    """Case 5: Memory with valid current provenance passes arbitration, is ranked, and fills residual budget."""
    manifest = _create_test_manifest()
    intent = ParsedIntentRecord(
        task_summary="Authenticate user login",
        category="authentication",
        extracted_symbols=["authenticate_user"],
        relevant_file_hints=["src/auth.py"],
    )

    valid_prov = MemoryProvenance(
        repository_id="repo_1",
        repository_fingerprint="repo_fp_alpha_001",
        source_file="src/auth.py",
        source_sha256="sha_auth_12345",
        source_symbol="authenticate_user",
    )
    valid_mem = {
        "text": "Valid and current authentication documentation.",
        "similarity": 0.88,
        "provenance": valid_prov,
    }

    result = RetrievalArbitrator.arbitrate(
        task_prompt="Authenticate user login",
        intent=intent,
        manifest=manifest,
        source_snippets=[],
        cognee_memories=[valid_mem],
        target_tokens=500,
    )

    assert result.stale_rejected_count == 0
    assert result.cross_repo_rejected_count == 0
    assert len(result.candidates) == 1
    assert result.candidates[0].tier == AuthorityTier.TIER_4_COGNEE
    assert result.candidates[0].is_valid is True
    assert result.total_token_estimate > 0


# =============================================================================
# Scope 7: Task 3 — Tier 1 Filesystem Source Integration Tests
# =============================================================================


def test_tier_1_candidate_creation_with_file_snippet_and_line_range():
    """Verify that source search results with line ranges convert to full Tier 1 candidates."""
    manifest = _create_test_manifest()
    intent = ParsedIntentRecord(
        task_summary="Authenticate user login",
        category="authentication",
        extracted_symbols=["authenticate_user"],
        relevant_file_hints=["src/auth.py"],
    )

    snippets = [
        "### `src/auth.py` (Lines 10-35)\n```\ndef authenticate_user(token: str) -> bool:\n    return verify_token(token)\n```"
    ]

    result = RetrievalArbitrator.arbitrate(
        task_prompt="Authenticate user login",
        intent=intent,
        manifest=manifest,
        source_snippets=snippets,
        source_matched_files=["src/auth.py"],
        target_tokens=1000,
    )

    assert len(result.candidates) == 1
    cand = result.candidates[0]

    assert cand.tier == AuthorityTier.TIER_1_SOURCE
    assert cand.source_file == "src/auth.py"
    assert cand.line_start == 10
    assert cand.line_end == 35
    assert cand.confidence == 1.0
    assert cand.relevance >= 0.5
    assert cand.specificity > 0.0
    assert "authenticate_user" in cand.content


def test_path_existence_alone_cannot_become_tier_1_evidence():
    """Verify that path existence in source_matched_files without snippets yields 0 Tier 1 candidates."""
    manifest = _create_test_manifest()
    intent = ParsedIntentRecord(
        task_summary="Inspect order processing",
        category="general",
        extracted_symbols=["process_order"],
        relevant_file_hints=["src/service.py"],
    )

    result = RetrievalArbitrator.arbitrate(
        task_prompt="Inspect order processing",
        intent=intent,
        manifest=manifest,
        source_snippets=[],  # No actual code content matched
        source_matched_files=["src/service.py", "src/auth.py"],  # Only path hints
        target_tokens=1000,
    )

    tier_1_candidates = [c for c in result.candidates if c.tier == AuthorityTier.TIER_1_SOURCE]
    assert len(tier_1_candidates) == 0
    assert result.tier_counts[AuthorityTier.TIER_1_SOURCE.label] == 0


# =============================================================================
# Scope 8: Task 4 — Tier 2 Deterministic AST Evidence Integration Tests
# =============================================================================


def test_tier_2_symbols_definitions_imports_calls_inheritance_and_jsx():
    """Verify conversion of symbols, definitions, imports, calls, inheritance, JSX to Tier 2 candidates."""
    manifest = _create_test_manifest()
    intent = ParsedIntentRecord(
        task_summary="Render UserProfile with custom theme",
        category="frontend_ui",
        extracted_symbols=["UserProfile", "useTheme"],
        relevant_file_hints=["src/components/UserProfile.tsx"],
    )

    ast_symbols = ["UserProfile", "useTheme"]
    ast_definitions = [
        {"symbol": "UserProfile", "file": "src/components/UserProfile.tsx", "signature": "const UserProfile: FC<Props>", "kind": "component"},
    ]
    ast_imports = ["import { useTheme } from '../hooks/useTheme'"]
    ast_calls = ["UserProfile -> useTheme"]
    ast_inheritance = ["AdminUserProfile extends UserProfile"]
    ast_jsx = ["UserProfile -> <Avatar user={user} />", "UserProfile -> <ThemeBadge />"]

    # Lower tier semantic memory with high similarity
    valid_prov = MemoryProvenance(
        repository_id="repo_1",
        repository_fingerprint="repo_fp_alpha_001",
        source_file="src/auth.py",
        source_sha256="sha_auth_12345",
        source_symbol="authenticate_user",
    )
    cognee_mem = {
        "text": "General React styling advice.",
        "similarity": 0.99,
        "provenance": valid_prov,
    }

    result = RetrievalArbitrator.arbitrate(
        task_prompt="Render UserProfile with custom theme",
        intent=intent,
        manifest=manifest,
        source_snippets=[],
        ast_symbols=ast_symbols,
        ast_definitions=ast_definitions,
        ast_imports=ast_imports,
        ast_call_edges=ast_calls,
        ast_inheritance=ast_inheritance,
        ast_jsx_renders=ast_jsx,
        cognee_memories=[cognee_mem],
        target_tokens=2000,
    )

    tier_2_cands = [c for c in result.candidates if c.tier == AuthorityTier.TIER_2_MANIFEST_AST]
    assert len(tier_2_cands) >= 6

    kinds = {c.relationship_kind for c in tier_2_cands}
    assert "symbol" in kinds
    assert "definition" in kinds
    assert "import" in kinds
    assert "call_graph" in kinds
    assert "inheritance" in kinds
    assert "jsx_render" in kinds

    # All Tier 2 candidates must outrank Tier 4
    tier_4_cands = [c for c in result.candidates if c.tier == AuthorityTier.TIER_4_COGNEE]
    assert len(tier_4_cands) == 1
    min_tier_2_rank = min(c.sort_key() for c in tier_2_cands)
    assert min_tier_2_rank > tier_4_cands[0].sort_key()

    # Authoritative relationships must capture AST relations
    assert any("UserProfile -> useTheme" in r for r in result.authoritative_relationships)
    assert any("AdminUserProfile extends UserProfile" in r for r in result.authoritative_relationships)
    assert any("<Avatar user={user} />" in r for r in result.authoritative_relationships)


# =============================================================================
# Scope 9: Task 5 — Tier 3 Validated LanceDB / Kùzu Evidence Integration Tests
# =============================================================================


def test_tier_3_lancedb_kuzu_valid_provenance_enters_tier_3():
    """Verify that a valid LanceDB/Kuzu vector projection passes provenance and enters Tier 3."""
    manifest = _create_test_manifest()
    intent = ParsedIntentRecord(
        task_summary="Authenticate user login",
        category="authentication",
        extracted_symbols=["authenticate_user"],
        relevant_file_hints=["src/auth.py"],
    )

    valid_prov = MemoryProvenance(
        repository_id="repo_1",
        repository_fingerprint="repo_fp_alpha_001",
        source_file="src/auth.py",
        source_sha256="sha_auth_12345",
        source_symbol="authenticate_user",
        relationship_kind="defines",
    )
    kuzu_vec = {
        "text": "Embedded vector node for authenticate_user function.",
        "similarity": 0.89,
        "provenance": valid_prov,
    }

    result = RetrievalArbitrator.arbitrate(
        task_prompt="Authenticate user login",
        intent=intent,
        manifest=manifest,
        source_snippets=[],
        lancedb_kuzu_memories=[kuzu_vec],
        target_tokens=1000,
    )

    assert result.stale_rejected_count == 0
    assert result.cross_repo_rejected_count == 0
    assert len(result.candidates) == 1

    cand = result.candidates[0]
    assert cand.tier == AuthorityTier.TIER_3_LANCEDB_KUZU
    assert cand.source_file == "src/auth.py"
    assert cand.source_symbol == "authenticate_user"
    assert cand.relationship_kind == "defines"
    assert cand.confidence == 0.75
    assert cand.relevance == 0.89
    assert result.tier_counts[AuthorityTier.TIER_3_LANCEDB_KUZU.label] == 1


def test_tier_3_lancedb_kuzu_stale_record_silently_discarded():
    """Verify that a semantically excellent (0.999 sim) but stale LanceDB/Kuzu record is silently discarded."""
    manifest = _create_test_manifest()
    intent = ParsedIntentRecord(
        task_summary="Authenticate user login",
        category="authentication",
        extracted_symbols=["authenticate_user"],
        relevant_file_hints=["src/auth.py"],
    )

    # Stale provenance (file was modified, old sha does not match)
    stale_prov = MemoryProvenance(
        repository_id="repo_1",
        repository_fingerprint="repo_fp_alpha_001",
        source_file="src/auth.py",
        source_sha256="stale_pre_mutation_sha",  # Mismatch
        source_symbol="authenticate_user",
    )
    stale_kuzu = {
        "text": "Semantically perfect but stale vector embedding with outdated API signatures.",
        "similarity": 0.9999,
        "provenance": stale_prov,
    }

    result = RetrievalArbitrator.arbitrate(
        task_prompt="Authenticate user login",
        intent=intent,
        manifest=manifest,
        source_snippets=[],
        lancedb_kuzu_memories=[stale_kuzu],
        target_tokens=1000,
    )

    # The candidate must simply disappear: 0 in pool, 0 tokens consumed
    assert result.stale_rejected_count == 1
    assert len(result.candidates) == 0
    assert result.total_token_estimate == 0
    assert result.tier_counts[AuthorityTier.TIER_3_LANCEDB_KUZU.label] == 0


def test_tier_3_lancedb_kuzu_outranked_by_tier_1_and_2():
    """Verify that a valid Tier 3 LanceDB/Kuzu candidate is strictly outranked by Tier 1 and Tier 2."""
    manifest = _create_test_manifest()
    intent = ParsedIntentRecord(
        task_summary="Process order and calculate tax",
        category="feature_request",
        extracted_symbols=["process_order"],
        relevant_file_hints=["src/service.py"],
    )

    valid_prov = MemoryProvenance(
        repository_id="repo_1",
        repository_fingerprint="repo_fp_alpha_001",
        source_file="src/service.py",
        source_sha256="sha_service_67890",
        source_symbol="process_order",
    )
    kuzu_vec = {
        "text": "Vector search result for order processing pipeline.",
        "similarity": 0.99,
        "provenance": valid_prov,
    }

    # Low relevance Tier 1 source snippet (0.2 relevance)
    low_rel_snip = ["### `src/service.py`\n# placeholder\npass"]
    # Tier 2 AST symbol
    ast_syms = ["process_order"]

    result = RetrievalArbitrator.arbitrate(
        task_prompt="Process order",
        intent=intent,
        manifest=manifest,
        source_snippets=low_rel_snip,
        source_matched_files=["src/service.py"],
        ast_symbols=ast_syms,
        lancedb_kuzu_memories=[kuzu_vec],
        target_tokens=2000,
    )

    assert len(result.candidates) == 3
    tiers = [c.tier for c in result.candidates]
    # Ordering must be Tier 1 -> Tier 2 -> Tier 3
    assert tiers[0] == AuthorityTier.TIER_1_SOURCE
    assert tiers[1] == AuthorityTier.TIER_2_MANIFEST_AST
    assert tiers[2] == AuthorityTier.TIER_3_LANCEDB_KUZU


# =============================================================================
# Scope 10: Task 6 — Tier 4 Validated Cognee Semantic Memory Integration Tests
# =============================================================================


def test_tier_4_cognee_valid_provenance_enters_tier_4():
    """Verify that a valid Cognee memory passes provenance and enters Tier 4 as the most derived tier."""
    manifest = _create_test_manifest()
    intent = ParsedIntentRecord(
        task_summary="Authenticate user login",
        category="authentication",
        extracted_symbols=["authenticate_user"],
        relevant_file_hints=["src/auth.py"],
    )

    valid_prov = MemoryProvenance(
        repository_id="repo_1",
        repository_fingerprint="repo_fp_alpha_001",
        source_file="src/auth.py",
        source_sha256="sha_auth_12345",
        source_symbol="authenticate_user",
        relationship_kind="defines",
    )
    cognee_item = {
        "text": "Semantic documentation on authenticate_user JWT workflow.",
        "score": 0.85,
        "provenance": valid_prov,
    }

    result = RetrievalArbitrator.arbitrate(
        task_prompt="Authenticate user login",
        intent=intent,
        manifest=manifest,
        source_snippets=[],
        cognee_memories=[cognee_item],
        target_tokens=1000,
    )

    assert result.stale_rejected_count == 0
    assert result.cross_repo_rejected_count == 0
    assert len(result.candidates) == 1

    cand = result.candidates[0]
    assert cand.tier == AuthorityTier.TIER_4_COGNEE
    assert cand.source_file == "src/auth.py"
    assert cand.source_symbol == "authenticate_user"
    assert cand.confidence == 0.60  # Most derived representation
    assert cand.relevance == 0.85
    assert result.tier_counts[AuthorityTier.TIER_4_COGNEE.label] == 1


def test_tier_4_cognee_stale_record_silently_discarded():
    """Verify that a high-similarity but stale Cognee semantic memory is discarded before ranking."""
    manifest = _create_test_manifest()
    intent = ParsedIntentRecord(
        task_summary="Authenticate user login",
        category="authentication",
        extracted_symbols=["authenticate_user"],
        relevant_file_hints=["src/auth.py"],
    )

    stale_prov = MemoryProvenance(
        repository_id="repo_1",
        repository_fingerprint="repo_fp_alpha_001",
        source_file="src/auth.py",
        source_sha256="outdated_sha_pre_edit",  # Mismatch
        source_symbol="authenticate_user",
    )
    stale_cognee = {
        "text": "Outdated Cognee memory about obsolete login flow.",
        "score": 0.999,
        "provenance": stale_prov,
    }

    result = RetrievalArbitrator.arbitrate(
        task_prompt="Authenticate user login",
        intent=intent,
        manifest=manifest,
        source_snippets=[],
        cognee_memories=[stale_cognee],
        target_tokens=1000,
    )

    assert result.stale_rejected_count == 1
    assert len(result.candidates) == 0
    assert result.total_token_estimate == 0
    assert result.tier_counts[AuthorityTier.TIER_4_COGNEE.label] == 0


def test_tier_4_cognee_subordinate_to_all_higher_tiers():
    """Verify that Tier 4 Cognee is strictly outranked by Tier 1, Tier 2, and Tier 3 candidates."""
    manifest = _create_test_manifest()
    intent = ParsedIntentRecord(
        task_summary="Process order and calculate tax",
        category="feature_request",
        extracted_symbols=["process_order"],
        relevant_file_hints=["src/service.py"],
    )

    prov = MemoryProvenance(
        repository_id="repo_1",
        repository_fingerprint="repo_fp_alpha_001",
        source_file="src/service.py",
        source_sha256="sha_service_67890",
        source_symbol="process_order",
    )

    cognee_mem = {
        "text": "Cognee high score semantic explanation.",
        "score": 0.9999,  # Highest score in list
        "provenance": prov,
    }
    kuzu_vec = {
        "text": "Kuzu vector node.",
        "similarity": 0.60,
        "provenance": prov,
    }
    src_snip = ["### `src/service.py`\n# code\npass"]
    ast_syms = ["process_order"]

    result = RetrievalArbitrator.arbitrate(
        task_prompt="Process order",
        intent=intent,
        manifest=manifest,
        source_snippets=src_snip,
        source_matched_files=["src/service.py"],
        ast_symbols=ast_syms,
        lancedb_kuzu_memories=[kuzu_vec],
        cognee_memories=[cognee_mem],
        target_tokens=2000,
    )

    assert len(result.candidates) == 4
    tiers = [c.tier for c in result.candidates]
    # Tier 1 > Tier 2 > Tier 3 > Tier 4
    assert tiers[0] == AuthorityTier.TIER_1_SOURCE
    assert tiers[1] == AuthorityTier.TIER_2_MANIFEST_AST
    assert tiers[2] == AuthorityTier.TIER_3_LANCEDB_KUZU
    assert tiers[3] == AuthorityTier.TIER_4_COGNEE


def test_tier_4_cognee_eviction_when_budget_constrained():
    """Verify that Tier 4 is excluded first when token budget is exhausted by higher tiers."""
    manifest = _create_test_manifest()
    intent = ParsedIntentRecord(
        task_summary="Process order and calculate tax",
        category="feature_request",
        extracted_symbols=["process_order"],
        relevant_file_hints=["src/service.py"],
    )

    prov = MemoryProvenance(
        repository_id="repo_1",
        repository_fingerprint="repo_fp_alpha_001",
        source_file="src/service.py",
        source_sha256="sha_service_67890",
        source_symbol="process_order",
    )

    cognee_mem = {
        "text": "Very long Cognee semantic text " * 40,  # ~240 tokens
        "score": 0.99,
        "provenance": prov,
    }
    src_snip = ["### `src/service.py`\n# code\npass"]  # ~8 tokens
    ast_syms = ["process_order"]  # ~5 tokens

    # Tight budget: 20 tokens (sufficient for Tier 1 and Tier 2, but excludes large Tier 4)
    result = RetrievalArbitrator.arbitrate(
        task_prompt="Process order",
        intent=intent,
        manifest=manifest,
        source_snippets=src_snip,
        source_matched_files=["src/service.py"],
        ast_symbols=ast_syms,
        cognee_memories=[cognee_mem],
        target_tokens=20,
    )

    tiers = [c.tier for c in result.candidates]
    assert AuthorityTier.TIER_1_SOURCE in tiers
    assert AuthorityTier.TIER_2_MANIFEST_AST in tiers
    assert AuthorityTier.TIER_4_COGNEE not in tiers


# =============================================================================
# Scope 11: Task 7 — Token Budget Reservation Adversarial Tests
# =============================================================================


def test_budget_reservation_adversarial_tier4_cannot_evict_tier1():
    """Adversarial Test: Tier 4 Cognee memories with 0.999 similarity CANNOT evict Tier 1 source snippets."""
    manifest = _create_test_manifest()
    intent = ParsedIntentRecord(
        task_summary="Authenticate user login",
        category="authentication",
        extracted_symbols=["authenticate_user"],
        relevant_file_hints=["src/auth.py"],
    )

    prov = MemoryProvenance(
        repository_id="repo_1",
        repository_fingerprint="repo_fp_alpha_001",
        source_file="src/auth.py",
        source_sha256="sha_auth_12345",
        source_symbol="authenticate_user",
    )

    # 10 large Cognee candidates with 0.999 score
    cognee_mems = [
        {
            "text": f"Ultra high score semantic memory chunk {i} " * 20,  # ~80 tokens each
            "score": 0.999,
            "provenance": prov,
        }
        for i in range(10)
    ]

    # 1 Tier 1 source snippet (~35 tokens) with lower relevance (0.5)
    source_snip = ["### `src/auth.py` (Lines 1-20)\n```\ndef authenticate_user(token):\n    return True\n```"]

    # Budget strictly 45 tokens: only enough for Tier 1 source snippet
    result = RetrievalArbitrator.arbitrate(
        task_prompt="Authenticate user login",
        intent=intent,
        manifest=manifest,
        source_snippets=source_snip,
        source_matched_files=["src/auth.py"],
        cognee_memories=cognee_mems,
        target_tokens=45,
    )

    # Tier 1 MUST be selected; Tier 4 MUST be excluded (cannot evict Tier 1)
    assert len(result.candidates) == 1
    assert result.candidates[0].tier == AuthorityTier.TIER_1_SOURCE
    assert result.tier_counts[AuthorityTier.TIER_1_SOURCE.label] == 1
    assert result.tier_counts[AuthorityTier.TIER_4_COGNEE.label] == 0


def test_budget_reservation_adversarial_tier3_cannot_evict_tier2():
    """Adversarial Test: Tier 3 LanceDB/Kuzu vector results with 0.999 similarity CANNOT evict Tier 2 AST constructs."""
    manifest = _create_test_manifest()
    intent = ParsedIntentRecord(
        task_summary="Authenticate user login",
        category="authentication",
        extracted_symbols=["authenticate_user"],
        relevant_file_hints=["src/auth.py"],
    )

    prov = MemoryProvenance(
        repository_id="repo_1",
        repository_fingerprint="repo_fp_alpha_001",
        source_file="src/auth.py",
        source_sha256="sha_auth_12345",
        source_symbol="authenticate_user",
    )

    # Large Tier 3 vector projection (~60 tokens) with 0.999 similarity
    kuzu_vec = {
        "text": "Extremely detailed LanceDB/Kuzu vector embedding graph projection " * 10,
        "similarity": 0.999,
        "provenance": prov,
    }

    # Tier 2 AST symbols and definitions (~15 tokens total)
    ast_syms = ["authenticate_user"]
    ast_defs = [{"symbol": "authenticate_user", "signature": "def authenticate_user()", "file": "src/auth.py"}]

    # Budget strictly 25 tokens: enough for Tier 2 AST, but NOT enough to also fit Tier 3
    result = RetrievalArbitrator.arbitrate(
        task_prompt="Authenticate user login",
        intent=intent,
        manifest=manifest,
        source_snippets=[],
        ast_symbols=ast_syms,
        ast_definitions=ast_defs,
        lancedb_kuzu_memories=[kuzu_vec],
        target_tokens=25,
    )

    # Tier 2 MUST be retained; Tier 3 CANNOT evict Tier 2
    selected_tiers = [c.tier for c in result.candidates]
    assert AuthorityTier.TIER_2_MANIFEST_AST in selected_tiers
    assert AuthorityTier.TIER_3_LANCEDB_KUZU not in selected_tiers
    assert result.tier_counts[AuthorityTier.TIER_2_MANIFEST_AST.label] >= 1
    assert result.tier_counts[AuthorityTier.TIER_3_LANCEDB_KUZU.label] == 0


def test_budget_reservation_full_four_tier_budget_filling():
    """Verify that an 8,000 token budget fills sequentially: Tier 1 -> Tier 2 -> Tier 3 -> Tier 4."""
    manifest = _create_test_manifest()
    intent = ParsedIntentRecord(
        task_summary="Process orders with authentication and telemetry",
        category="feature_request",
        extracted_symbols=["process_order", "authenticate_user"],
        relevant_file_hints=["src/service.py", "src/auth.py"],
    )

    prov_auth = MemoryProvenance(
        repository_id="repo_1",
        repository_fingerprint="repo_fp_alpha_001",
        source_file="src/auth.py",
        source_sha256="sha_auth_12345",
        source_symbol="authenticate_user",
    )
    prov_svc = MemoryProvenance(
        repository_id="repo_1",
        repository_fingerprint="repo_fp_alpha_001",
        source_file="src/service.py",
        source_sha256="sha_service_67890",
        source_symbol="process_order",
    )

    # Tier 1 Snippets
    source_snippets = [
        "### `src/auth.py` (Lines 1-10)\n```\ndef authenticate_user(): pass\n```",
        "### `src/service.py` (Lines 1-10)\n```\ndef process_order(): pass\n```",
    ]
    # Tier 2 AST
    ast_symbols = ["process_order", "authenticate_user"]
    ast_calls = ["process_order -> authenticate_user"]
    # Tier 3 LanceDB / Kuzu
    kuzu_mems = [
        {"text": "Kuzu node: process_order calls auth verification.", "similarity": 0.85, "provenance": prov_svc}
    ]
    # Tier 4 Cognee
    cognee_mems = [
        {"text": "Cognee semantic summary of order processing workflow.", "score": 0.78, "provenance": prov_auth}
    ]

    result = RetrievalArbitrator.arbitrate(
        task_prompt="Process orders with authentication and telemetry",
        intent=intent,
        manifest=manifest,
        source_snippets=source_snippets,
        source_matched_files=["src/auth.py", "src/service.py"],
        ast_symbols=ast_symbols,
        ast_call_edges=ast_calls,
        lancedb_kuzu_memories=kuzu_mems,
        cognee_memories=cognee_mems,
        target_tokens=8000,
    )

    # All 4 tiers must be present within 8000 token budget
    assert result.tier_counts[AuthorityTier.TIER_1_SOURCE.label] >= 2
    assert result.tier_counts[AuthorityTier.TIER_2_MANIFEST_AST.label] >= 2
    assert result.tier_counts[AuthorityTier.TIER_3_LANCEDB_KUZU.label] == 1
    assert result.tier_counts[AuthorityTier.TIER_4_COGNEE.label] == 1
    assert result.total_token_estimate <= 8000


# =============================================================================
# Scope 12: Task 9 — Interaction with Phase 10D.3 Abstention Boundary Tests
# =============================================================================


def test_arbitrator_does_not_decide_model_invocation():
    """Verify that RetrievalArbitrator produces ranked evidence but has NO gating or model authorization fields."""
    manifest = _create_test_manifest()
    intent = ParsedIntentRecord(
        task_summary="Non-existent billing integration",
        category="billing",
        extracted_symbols=["process_stripe_payment"],
        relevant_file_hints=["billing.py"],
    )

    arbitrated = RetrievalArbitrator.arbitrate(
        task_prompt="Non-existent billing integration",
        intent=intent,
        manifest=manifest,
        source_snippets=[],
        source_matched_files=[],
    )

    # 1. ArbitratedEvidenceResult is strictly a data container
    assert not hasattr(arbitrated, "abstained")
    assert not hasattr(arbitrated, "model_claims_allowed")
    assert not hasattr(arbitrated, "evidence_state")
    assert not hasattr(arbitrated, "can_call_model")

    # 2. Arbitrator does not make the decision to call model or abstain
    d = arbitrated.to_dict()
    assert "abstained" not in d
    assert "model_claims_allowed" not in d


def test_arbitrator_feeds_evidence_service_without_bypassing_gate():
    """Verify flow: Arbitrator ranks candidates -> EvidenceService decides whether to abstain."""
    manifest = _create_test_manifest()
    intent = ParsedIntentRecord(
        task_summary="Configure OAuth2 Token Provider",
        category="authentication",
        extracted_symbols=["OAuth2TokenProvider", "refresh_access_token"],
        relevant_file_hints=["oauth.py"],
    )

    # Arbitrator ranks available candidates (even if generic/irrelevant)
    generic_snippet = ["### `src/service.py`\ndef process_order(): pass"]
    arbitrated = RetrievalArbitrator.arbitrate(
        task_prompt="Configure OAuth2 Token Provider",
        intent=intent,
        manifest=manifest,
        source_snippets=generic_snippet,
        source_matched_files=["src/service.py"],
        ast_symbols=["process_order"],
    )

    # Arbitrator successfully returned ranked candidate
    assert len(arbitrated.candidates) >= 1
    assert arbitrated.candidates[0].tier == AuthorityTier.TIER_1_SOURCE

    # EvidenceService MUST evaluate if this evidence satisfies the task intent
    evidence = EvidenceService.assess_evidence(
        task_prompt="Configure OAuth2 Token Provider with JWT signing",
        intent=intent,
        repo_summary=None,
        indexed_files=["src/service.py", "src/auth.py"],
        relevant_snippets=arbitrated.authoritative_snippets,
        matched_file_rels=arbitrated.authoritative_files,
        structural_symbols=arbitrated.authoritative_symbols,
        structural_relationships=arbitrated.authoritative_relationships,
        manifest=manifest,
        arbitrated_result=arbitrated,
    )

    # EvidenceService ALONE decides: insufficient evidence -> abstain
    assert evidence.abstained is True
    assert evidence.model_claims_allowed is False
    assert evidence.evidence_state in (EvidenceState.INSUFFICIENT.value, EvidenceState.NONE.value)
    assert any("auth" in m.lower() for m in evidence.missing_evidence) or any("symbol" in m.lower() for m in evidence.missing_evidence)


def test_evidence_service_is_sole_authority_for_synthesis_authorization():
    """Verify that only EvidenceService can authorize model claims and synthesis."""
    intent = ParsedIntentRecord(
        task_summary="Authenticate user login",
        category="authentication",
        extracted_symbols=["authenticate_user"],
        relevant_file_hints=["src/auth.py"],
    )

    valid_snippet = ["### `src/auth.py` (Lines 1-15)\n```\ndef authenticate_user(token: str):\n    return True\n```"]
    manifest = _create_test_manifest()

    arbitrated = RetrievalArbitrator.arbitrate(
        task_prompt="Authenticate user login",
        intent=intent,
        manifest=manifest,
        source_snippets=valid_snippet,
        source_matched_files=["src/auth.py"],
        ast_symbols=["authenticate_user"],
    )

    evidence = EvidenceService.assess_evidence(
        task_prompt="Authenticate user login",
        intent=intent,
        repo_summary=None,
        indexed_files=["src/auth.py"],
        relevant_snippets=arbitrated.authoritative_snippets,
        matched_file_rels=arbitrated.authoritative_files,
        structural_symbols=arbitrated.authoritative_symbols,
        structural_relationships=arbitrated.authoritative_relationships,
        manifest=manifest,
        arbitrated_result=arbitrated,
    )

    # EvidenceService verifies sufficient code and symbol ground truth
    assert evidence.abstained is False
    assert evidence.model_claims_allowed is True
    assert evidence.evidence_state in (EvidenceState.SUFFICIENT.value, EvidenceState.PARTIAL.value)







