"""Tests for Phase 10D.6 Milestone P0.3: Restore Genuine Tier-3 LanceDB/Kùzu Retrieval.

Validates:
1. test_direct_lancedb_projection_becomes_tier3_candidate
2. test_stale_lancedb_record_rejected_before_arbitration
3. test_cross_repository_lancedb_record_rejected
4. test_direct_kuzu_projection_becomes_tier3_candidate
5. test_stale_kuzu_projection_rejected
6. test_cross_repository_kuzu_record_rejected
7. test_strict_tier3_tier4_separation
8. test_authority_ordering_tier1_tier2_tier3_tier4
9. test_resilience_lancedb_outage_does_not_break_kuzu
10. test_resilience_kuzu_outage_does_not_break_lancedb
11. test_resilience_both_tier3_stores_failing_preserves_tier1_tier2
12. test_tier3_retrieval_is_strictly_read_only
13. test_production_get_agent_context_passes_genuine_tier3
"""

import asyncio
from pathlib import Path
import time
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.domain.arbitration import AuthorityTier
from app.application.domain.memory import (
    MemoryProvenance,
    SemanticMemoryRecord,
    Tier3ProjectionCandidate,
    Tier3RetrievalResult,
)
from app.models.agent_context import AgentContextRequest, AgentContextResponse
from app.models.provider import ProviderType
from app.services.cognee_service import CogneeService
from app.services.evidence_service import EvidenceService
from app.services.manifest_service import ManifestService
from app.services.repository_summary import RepositorySummaryGenerator
from app.services.retrieval_arbitrator import RetrievalArbitrator
from app.application.use_cases.context import ContextUseCases


class MockIntent:
    """Mock Intent parser output for test queries."""

    def __init__(
        self,
        task_type: str = "feature_implementation",
        extracted_symbols: Optional[list[str]] = None,
        relevant_file_hints: Optional[list[str]] = None,
    ) -> None:
        self.task_type = task_type
        self.extracted_symbols = extracted_symbols or ["UserAuthService", "login"]
        self.relevant_file_hints = relevant_file_hints or ["src/auth.py"]
        self.scope_boundary = "frontend_and_backend"
        self.confidence_score = 0.95
        self.needs_arbitration = True


class MockManifest:
    """Mock Manifest 2.0 object."""

    def __init__(
        self,
        repo_id: str = "repo_test_123",
        fingerprint: str = "fp_abc_789",
        files: Optional[dict[str, Any]] = None,
    ) -> None:
        self.repository_id = repo_id
        self.fingerprint = fingerprint
        self.files = files or {
            "src/auth.py": {
                "sha256": "sha_auth_valid_123",
                "symbols": ["UserAuthService", "login"],
            },
            "src/utils.py": {
                "sha256": "sha_utils_valid_456",
                "symbols": ["hash_password"],
            },
        }
        self.file_hashes = {f: meta["sha256"] for f, meta in self.files.items()}


@pytest.fixture
def manifest() -> MockManifest:
    return MockManifest()


@pytest.fixture
def intent() -> MockIntent:
    return MockIntent()


@pytest.fixture
def cognee_service() -> CogneeService:
    service = CogneeService()
    service._initialized = True
    return service


# =====================================================================
# 1. Direct LanceDB Projection Retrieval & Provenance
# =====================================================================

@pytest.mark.asyncio
async def test_direct_lancedb_projection_becomes_tier3_candidate(
    cognee_service: CogneeService,
    manifest: MockManifest,
    intent: MockIntent,
) -> None:
    """A real LanceDB projection with valid provenance becomes a TIER_3_LANCEDB_KUZU candidate."""
    raw_lancedb_records = [
        {
            "id": "lance_chunk_1",
            "text": "class UserAuthService handles user login and authentication tokens.",
            "score": 0.15,  # cosine distance -> high relevance
            "source_file": "src/auth.py",
            "source_sha256": "sha_auth_valid_123",
            "repository_id": "repo_test_123",
            "repository_fingerprint": "fp_abc_789",
            "source_symbol": "UserAuthService",
            "relationship_kind": "vector_projection",
        }
    ]

    tier3_result = await cognee_service.retrieve_tier3_lancedb_kuzu(
        repository_id="repo_test_123",
        query_text="user authentication login",
        manifest=manifest,
        lancedb_records=raw_lancedb_records,
        kuzu_records=[],
    )

    assert isinstance(tier3_result, Tier3RetrievalResult)
    assert len(tier3_result.candidates) == 1
    cand = tier3_result.candidates[0]
    assert cand.origin == "lancedb"
    assert cand.source_file == "src/auth.py"
    assert cand.source_symbol == "UserAuthService"
    assert cand.relevance > 0.8
    assert tier3_result.accepted_count == 1
    assert tier3_result.rejected_count == 0
    # Verify arbitration enters as Tier 3
    arbitrated = RetrievalArbitrator.arbitrate(
        task_prompt="user authentication login",
        intent=intent,
        manifest=manifest,
        source_snippets=[],
        source_matched_files=[],
        ast_symbols=[],
        ast_call_edges=[],
        lancedb_kuzu_memories=tier3_result.candidates,
        cognee_memories=[],
        target_tokens=2000,
    )

    tier3_in_arbitration = [c for c in arbitrated.candidates if c.tier == AuthorityTier.TIER_3_LANCEDB_KUZU]
    assert len(tier3_in_arbitration) == 1
    assert tier3_in_arbitration[0].content == cand.text
    assert tier3_in_arbitration[0].provenance is not None
    assert tier3_in_arbitration[0].provenance.repository_fingerprint == "fp_abc_789"


@pytest.mark.asyncio
async def test_stale_lancedb_record_rejected_before_arbitration(
    cognee_service: CogneeService,
    manifest: MockManifest,
    intent: MockIntent,
) -> None:
    """A stale LanceDB record (SHA-256 mismatch against active manifest) is rejected before arbitration."""
    stale_lancedb_records = [
        {
            "id": "lance_chunk_stale",
            "text": "old stale auth implementation",
            "score": 0.10,
            "source_file": "src/auth.py",
            "source_sha256": "sha_auth_STALE_OUTDATED_999",
            "repository_id": "repo_test_123",
            "repository_fingerprint": "fp_abc_789",
        }
    ]

    tier3_result = await cognee_service.retrieve_tier3_lancedb_kuzu(
        repository_id="repo_test_123",
        query_text="user login",
        manifest=manifest,
        lancedb_records=stale_lancedb_records,
        kuzu_records=[],
    )

    assert len(tier3_result.candidates) == 0
    assert tier3_result.accepted_count == 0
    assert tier3_result.rejected_count == 1
    assert "stale_sha256_mismatch" in tier3_result.rejection_reasons

    # Ensure stale records never reach arbitration
    arbitrated = RetrievalArbitrator.arbitrate(
        task_prompt="user login",
        intent=intent,
        manifest=manifest,
        source_snippets=[],
        source_matched_files=[],
        ast_symbols=[],
        ast_call_edges=[],
        lancedb_kuzu_memories=tier3_result.candidates,
        cognee_memories=[],
        target_tokens=2000,
    )
    tier3_in_arbitration = [c for c in arbitrated.candidates if c.tier == AuthorityTier.TIER_3_LANCEDB_KUZU]
    assert len(tier3_in_arbitration) == 0


@pytest.mark.asyncio
async def test_cross_repository_lancedb_record_rejected(
    cognee_service: CogneeService,
    manifest: MockManifest,
) -> None:
    """A cross-repository LanceDB record (fingerprint mismatch) is rejected."""
    foreign_records = [
        {
            "id": "lance_foreign",
            "text": "foreign repository code",
            "score": 0.05,
            "source_file": "src/auth.py",
            "source_sha256": "sha_auth_valid_123",
            "repository_id": "different_repo",
            "repository_fingerprint": "foreign_fingerprint_xyz",
        }
    ]

    tier3_result = await cognee_service.retrieve_tier3_lancedb_kuzu(
        repository_id="repo_test_123",
        query_text="user login",
        manifest=manifest,
        lancedb_records=foreign_records,
        kuzu_records=[],
    )

    assert len(tier3_result.candidates) == 0
    assert tier3_result.rejected_count == 1
    assert "cross_repository_mismatch" in tier3_result.rejection_reasons


# =====================================================================
# 2. Direct Kùzu Projection Retrieval & Provenance
# =====================================================================

@pytest.mark.asyncio
async def test_direct_kuzu_projection_becomes_tier3_candidate(
    cognee_service: CogneeService,
    manifest: MockManifest,
    intent: MockIntent,
) -> None:
    """A real Kùzu graph projection with valid provenance becomes a TIER_3_LANCEDB_KUZU candidate."""
    raw_kuzu_records = [
        (
            "UserAuthService",
            "login",
            "defines_method",
            {
                "source_file": "src/auth.py",
                "source_sha256": "sha_auth_valid_123",
                "source_symbol": "UserAuthService",
                "repository_id": "repo_test_123",
                "repository_fingerprint": "fp_abc_789",
                "description": "UserAuthService defines login method for session creation",
            },
        )
    ]

    tier3_result = await cognee_service.retrieve_tier3_lancedb_kuzu(
        repository_id="repo_test_123",
        query_text="login session",
        manifest=manifest,
        lancedb_records=[],
        kuzu_records=raw_kuzu_records,
    )

    assert len(tier3_result.candidates) == 1
    cand = tier3_result.candidates[0]
    assert cand.origin == "kuzu"
    assert cand.graph_source_node == "UserAuthService"
    assert cand.graph_target_node == "login"
    assert cand.relationship_kind == "defines_method"
    assert cand.source_file == "src/auth.py"

    arbitrated = RetrievalArbitrator.arbitrate(
        task_prompt="login session",
        intent=intent,
        manifest=manifest,
        source_snippets=[],
        source_matched_files=[],
        ast_symbols=[],
        ast_call_edges=[],
        lancedb_kuzu_memories=tier3_result.candidates,
        cognee_memories=[],
        target_tokens=2000,
    )

    tier3_in_arbitration = [c for c in arbitrated.candidates if c.tier == AuthorityTier.TIER_3_LANCEDB_KUZU]
    assert len(tier3_in_arbitration) == 1
    assert "defines_method" in str(tier3_in_arbitration[0].relationship_kind)


@pytest.mark.asyncio
async def test_stale_kuzu_projection_rejected(
    cognee_service: CogneeService,
    manifest: MockManifest,
) -> None:
    """A stale Kùzu relationship is rejected before arbitration."""
    stale_kuzu_records = [
        (
            "OldService",
            "old_method",
            "calls",
            {
                "source_file": "src/deleted_file.py",
                "source_sha256": "sha_deleted_file_999",
                "repository_id": "repo_test_123",
                "repository_fingerprint": "fp_abc_789",
            },
        )
    ]

    tier3_result = await cognee_service.retrieve_tier3_lancedb_kuzu(
        repository_id="repo_test_123",
        query_text="old method",
        manifest=manifest,
        lancedb_records=[],
        kuzu_records=stale_kuzu_records,
    )

    assert len(tier3_result.candidates) == 0
    assert tier3_result.rejected_count == 1
    assert "file_not_in_manifest" in tier3_result.rejection_reasons


@pytest.mark.asyncio
async def test_cross_repository_kuzu_record_rejected(
    cognee_service: CogneeService,
    manifest: MockManifest,
) -> None:
    """A cross-repository Kùzu record is rejected before arbitration."""
    cross_repo_kuzu = [
        (
            "ForeignNodeA",
            "ForeignNodeB",
            "depends_on",
            {
                "source_file": "src/auth.py",
                "source_sha256": "sha_auth_valid_123",
                "repository_id": "other_repo",
                "repository_fingerprint": "foreign_fp_abc",
            },
        )
    ]

    tier3_result = await cognee_service.retrieve_tier3_lancedb_kuzu(
        repository_id="repo_test_123",
        query_text="dependencies",
        manifest=manifest,
        lancedb_records=[],
        kuzu_records=cross_repo_kuzu,
    )

    assert len(tier3_result.candidates) == 0
    assert tier3_result.rejected_count == 1
    assert "cross_repository_mismatch" in tier3_result.rejection_reasons


# =====================================================================
# 3. Strict Separation of Tier 3 & Tier 4
# =====================================================================

@pytest.mark.asyncio
async def test_strict_tier3_tier4_separation(
    cognee_service: CogneeService,
    manifest: MockManifest,
    intent: MockIntent,
) -> None:
    """SemanticMemoryRecord remains TIER_4_COGNEE; cognee.recall cannot be relabeled as Tier 3."""
    lancedb_records = [
        {
            "id": "lance_vector_1",
            "text": "Vector projection text from LanceDB",
            "score": 0.20,
            "source_file": "src/auth.py",
            "source_sha256": "sha_auth_valid_123",
            "repository_id": "repo_test_123",
            "repository_fingerprint": "fp_abc_789",
        }
    ]

    t3_result = await cognee_service.retrieve_tier3_lancedb_kuzu(
        repository_id="repo_test_123",
        query_text="vector projection",
        manifest=manifest,
        lancedb_records=lancedb_records,
        kuzu_records=[],
    )

    # Tier 4 record constructed as Cognee semantic memory
    t4_record = SemanticMemoryRecord(
        memory_id="cognee_sem_1",
        repository_id="repo_test_123",
        repository_fingerprint="fp_abc_789",
        semantic_text="Cognee semantic summary of auth architecture",
        source_files=["src/auth.py"],
        source_symbols=["UserAuthService"],
        source_sha256=["sha_auth_valid_123"],
        relationship_kind="semantic_summary",
        generated_by="cognee_pipeline",
        generated_at=time.time(),
        evidence_status="derived_projection",
        is_derived=True,
        is_authoritative=False,
        confidence_score=0.9,
    )

    arbitrated = RetrievalArbitrator.arbitrate(
        task_prompt="authentication architecture",
        intent=intent,
        manifest=manifest,
        source_snippets=[],
        source_matched_files=[],
        ast_symbols=[],
        ast_call_edges=[],
        lancedb_kuzu_memories=t3_result.candidates,
        cognee_memories=[t4_record],
        target_tokens=2000,
    )

    tier3_candidates = [c for c in arbitrated.candidates if c.tier == AuthorityTier.TIER_3_LANCEDB_KUZU]
    tier4_candidates = [c for c in arbitrated.candidates if c.tier == AuthorityTier.TIER_4_COGNEE]

    assert len(tier3_candidates) == 1
    assert tier3_candidates[0].content == "Vector projection text from LanceDB"

    assert len(tier4_candidates) == 1
    assert tier4_candidates[0].content == "Cognee semantic summary of auth architecture"

    # Telemetry separation check
    assert cognee_service.last_tier3_telemetry["tier3_items_accepted"] == 1
    assert "tier3_lancedb_count" in cognee_service.last_tier3_telemetry
    assert "cognee_recall_attempted" not in cognee_service.last_tier3_telemetry


# =====================================================================
# 4. Authority Hierarchy: Tier 1 > Tier 2 > Tier 3 > Tier 4
# =====================================================================

def test_authority_ordering_tier1_tier2_tier3_tier4(
    manifest: MockManifest,
    intent: MockIntent,
) -> None:
    """Tier 1 > Tier 2 > Tier 3 > Tier 4 ordering invariant is strictly enforced."""
    tier1_snippets = ["def login(): return True"]
    tier2_symbols = ["UserAuthService"]
    tier2_calls = ["UserAuthService -> login"]

    tier3_candidate = Tier3ProjectionCandidate(
        id="t3_cand_1",
        origin="lancedb",
        text="Derived vector projection from LanceDB",
        relevance=1.0,  # maximum relevance
        source_file="src/auth.py",
        source_sha256="sha_auth_valid_123",
        repository_id="repo_test_123",
        repository_fingerprint="fp_abc_789",
    )

    tier4_record = SemanticMemoryRecord(
        memory_id="t4_rec_1",
        repository_id="repo_test_123",
        repository_fingerprint="fp_abc_789",
        semantic_text="Cognee semantic memory overview",
        source_files=["src/auth.py"],
        source_symbols=["UserAuthService"],
        source_sha256=["sha_auth_valid_123"],
        relationship_kind="summary",
        generated_by="cognee_pipeline",
        generated_at=time.time(),
        evidence_status="derived_projection",
        is_derived=True,
        is_authoritative=False,
        confidence_score=1.0,
    )

    arbitrated = RetrievalArbitrator.arbitrate(
        task_prompt="login function",
        intent=intent,
        manifest=manifest,
        source_snippets=tier1_snippets,
        source_matched_files=["src/auth.py"],
        ast_symbols=tier2_symbols,
        ast_call_edges=tier2_calls,
        lancedb_kuzu_memories=[tier3_candidate],
        cognee_memories=[tier4_record],
        target_tokens=2000,
    )

    tiers_in_order = [c.tier for c in arbitrated.candidates]
    seen_tiers = []
    for t in tiers_in_order:
        if not seen_tiers or seen_tiers[-1] != t:
            seen_tiers.append(t)

    # Authority tier numeric values must be monotonically non-increasing
    for i in range(len(seen_tiers) - 1):
        assert seen_tiers[i].value >= seen_tiers[i + 1].value


# =====================================================================
# 5. Resilience: Subsystem Outages & Evidence Preservations
# =====================================================================

@pytest.mark.asyncio
async def test_resilience_lancedb_outage_does_not_break_kuzu(
    cognee_service: CogneeService,
    manifest: MockManifest,
) -> None:
    """LanceDB outage does not prevent Kùzu retrieval from returning candidates."""
    valid_kuzu_records = [
        (
            "UserAuthService",
            "login",
            "calls",
            {
                "source_file": "src/auth.py",
                "source_sha256": "sha_auth_valid_123",
                "repository_id": "repo_test_123",
                "repository_fingerprint": "fp_abc_789",
            },
        )
    ]

    # Mock _retrieve_lancedb_projections_internal to simulate storage outage
    with patch.object(
        cognee_service,
        "_retrieve_lancedb_projections_internal",
        new=AsyncMock(side_effect=Exception("LanceDB disk full / lock error")),
    ):
        result = await cognee_service.retrieve_tier3_lancedb_kuzu(
            repository_id="repo_test_123",
            query_text="login",
            manifest=manifest,
            kuzu_records=valid_kuzu_records,
        )

    assert result.lancedb_state == "unavailable"
    assert result.kuzu_state == "healthy"
    assert len(result.candidates) == 1
    assert result.candidates[0].origin == "kuzu"
    assert result.to_telemetry()["tier3_retrieval_succeeded"] is True


@pytest.mark.asyncio
async def test_resilience_kuzu_outage_does_not_break_lancedb(
    cognee_service: CogneeService,
    manifest: MockManifest,
) -> None:
    """Kùzu outage does not prevent LanceDB retrieval from returning candidates."""
    valid_lancedb_records = [
        {
            "id": "l_1",
            "text": "Valid auth snippet",
            "score": 0.15,
            "source_file": "src/auth.py",
            "source_sha256": "sha_auth_valid_123",
            "repository_id": "repo_test_123",
            "repository_fingerprint": "fp_abc_789",
        }
    ]

    with patch.object(
        cognee_service,
        "_retrieve_kuzu_projections_internal",
        new=AsyncMock(side_effect=Exception("Kùzu connection timeout")),
    ):
        result = await cognee_service.retrieve_tier3_lancedb_kuzu(
            repository_id="repo_test_123",
            query_text="auth",
            manifest=manifest,
            lancedb_records=valid_lancedb_records,
        )

    assert result.lancedb_state == "healthy"
    assert result.kuzu_state == "unavailable"
    assert len(result.candidates) == 1
    assert result.candidates[0].origin == "lancedb"
    assert result.to_telemetry()["tier3_retrieval_succeeded"] is True


@pytest.mark.asyncio
async def test_resilience_both_tier3_stores_failing_preserves_tier1_tier2(
    manifest: MockManifest,
    intent: MockIntent,
) -> None:
    """Both Tier-3 stores failing still leaves Tier 1/2 fully operational and does not trigger abstention."""
    tier1_snippets = ["def authenticate(): pass"]
    tier2_symbols = ["authenticate"]

    # Arbitration receives empty Tier 3 due to outage
    arbitrated = RetrievalArbitrator.arbitrate(
        task_prompt="authenticate user",
        intent=intent,
        manifest=manifest,
        source_snippets=tier1_snippets,
        source_matched_files=["src/auth.py"],
        ast_symbols=tier2_symbols,
        ast_call_edges=[],
        lancedb_kuzu_memories=[],
        cognee_memories=[],
        target_tokens=2000,
    )

    assert len(arbitrated.candidates) >= 2
    assert arbitrated.tier_counts[AuthorityTier.TIER_1_SOURCE.label] >= 1
    assert arbitrated.tier_counts[AuthorityTier.TIER_2_MANIFEST_AST.label] >= 1

    # Evidence service assessment is based on authoritative evidence, not datastore availability
    evidence = EvidenceService.assess_evidence(
        task_prompt="authenticate user",
        intent=intent,
        repo_summary=None,
        indexed_files=["src/auth.py"],
        relevant_snippets=arbitrated.authoritative_snippets,
        matched_file_rels=arbitrated.authoritative_files,
        structural_symbols=arbitrated.authoritative_symbols,
        structural_relationships=[],
        manifest=manifest,
        arbitrated_result=arbitrated,
    )

    assert evidence.abstained is False


# =====================================================================
# 6. Read-Only Guarantees (0 LLM, 0 Cognify, 0 Writes)
# =====================================================================

@pytest.mark.asyncio
async def test_tier3_retrieval_is_strictly_read_only(
    cognee_service: CogneeService,
    manifest: MockManifest,
) -> None:
    """Tier-3 retrieval does not invoke LLM, does not call cognify, and does not mutate persistence."""
    with patch("cognee.add", new=MagicMock(side_effect=AssertionError("cognee.add must not be called"))), \
         patch("cognee.cognify", new=MagicMock(side_effect=AssertionError("cognify must not be called"))), \
         patch.object(cognee_service, "remember", new=MagicMock(side_effect=AssertionError("remember must not be called"))), \
         patch.object(cognee_service, "recall", new=MagicMock(side_effect=AssertionError("recall must not be called for Tier 3"))):

        result = await cognee_service.retrieve_tier3_lancedb_kuzu(
            repository_id="repo_test_123",
            query_text="search query",
            manifest=manifest,
            lancedb_records=[],
            kuzu_records=[],
        )

        assert isinstance(result, Tier3RetrievalResult)


# =====================================================================
# 7. Production ContextUseCases Integration
# =====================================================================

@pytest.mark.asyncio
async def test_production_get_agent_context_passes_genuine_tier3(
    manifest: MockManifest,
) -> None:
    """ContextUseCases.get_agent_context passes real Tier-3 candidates into RetrievalArbitrator."""
    mock_cognee = MagicMock()
    mock_cognee.retrieve_semantic_memory = AsyncMock(return_value=[])

    tier3_cand = Tier3ProjectionCandidate(
        id="t3_prod_1",
        origin="lancedb",
        text="Production Tier-3 LanceDB candidate",
        relevance=0.88,
        source_file="src/auth.py",
        source_sha256="sha_auth_valid_123",
        repository_id="repo_test_123",
        repository_fingerprint="fp_abc_789",
        source_symbol="UserAuthService",
    )
    mock_tier3_result = Tier3RetrievalResult(
        candidates=[tier3_cand],
        lancedb_count=1,
        kuzu_count=0,
        accepted_count=1,
        rejected_count=0,
        lancedb_state="healthy",
        kuzu_state="healthy",
    )

    async def mock_retrieve_tier3(**kwargs: Any):
        if "telemetry" in kwargs and isinstance(kwargs["telemetry"], dict):
            kwargs["telemetry"].update(mock_tier3_result.to_telemetry())
        return mock_tier3_result

    mock_cognee.retrieve_tier3_lancedb_kuzu = AsyncMock(side_effect=mock_retrieve_tier3)

    mock_intent_parser = MagicMock()
    mock_intent_parser.parse_intent = AsyncMock(return_value=MockIntent())

    mock_summary_gen = MagicMock()
    mock_summary_gen.generate = MagicMock(return_value=None)
    mock_summary_gen.get_summary = MagicMock(return_value=None)

    mock_source_search = MagicMock()
    mock_source_search.build_search_terms = MagicMock(return_value=["auth"])
    mock_source_search.extract_relevant_snippets = MagicMock(return_value=(["def login(): pass"], ["src/auth.py"]))

    mock_cache = MagicMock()
    mock_cache.make_key = MagicMock(return_value="test_cache_key")
    mock_cache.get = MagicMock(return_value=None)
    mock_cache.set = MagicMock()

    mock_fs = MagicMock()
    mock_fs.read_file = MagicMock(return_value="")

    mock_indexing = MagicMock()
    mock_indexing.discover_files = MagicMock(return_value=["src/auth.py"])
    mock_indexing.filter_files = MagicMock(return_value=["src/auth.py"])
    manifest.repo_fingerprint = manifest.fingerprint
    mock_indexing.load_manifest = MagicMock(return_value=manifest)
    mock_indexing._manifest_service = MagicMock()
    mock_indexing._manifest_service.load_manifest = MagicMock(return_value=manifest)

    mock_auth = MagicMock()
    mock_auth.is_path_authorized = MagicMock(return_value=(True, None))

    mock_context_service = MagicMock()
    mock_context_service.generate_context_package = AsyncMock(return_value=MagicMock())

    use_cases = ContextUseCases(
        context_service=mock_context_service,
        cognee_service=mock_cognee,
        indexing_service=mock_indexing,
        intent_parser=mock_intent_parser,
        llm_provider=None,
        cgc_service=None,
        summary_generator=mock_summary_gen,
        context_cache=mock_cache,
        source_search=mock_source_search,
        filesystem=mock_fs,
        workspace_auth=mock_auth,
    )

    req = AgentContextRequest(
        task_prompt="login to user service",
        repository_path="/fake/repo",
    )

    with patch.object(RetrievalArbitrator, "arbitrate", wraps=RetrievalArbitrator.arbitrate) as mock_arbitrate:
        resp = await use_cases.get_agent_context(req)

        assert mock_arbitrate.called
        call_kwargs = mock_arbitrate.call_args.kwargs
        lancedb_kuzu_memories = call_kwargs.get("lancedb_kuzu_memories")
        assert lancedb_kuzu_memories is not None
        assert len(lancedb_kuzu_memories) == 1
        assert lancedb_kuzu_memories[0].origin == "lancedb"
        assert lancedb_kuzu_memories[0].text == "Production Tier-3 LanceDB candidate"

    assert use_cases.last_tier3_telemetry["tier3_retrieval_attempted"] is True
    assert use_cases.last_tier3_telemetry["tier3_items_accepted"] == 1
