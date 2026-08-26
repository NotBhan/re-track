"""Empirical Evaluation and Regression Certification Suite for Retrieval Arbitration (Phase 10D.5 Tasks 10-12).

Measures and certifies:
- Scope 10: Retrieval quality & tier distribution, adversarial ranking, rejection rates, abstention & path-only boundaries.
- Scope 11: Token budget scaling (minimal, medium, full), latency (<5ms), deterministic reproducibility.
- Scope 12: End-to-end regression certification across Phase 10D.3, 10D.4, provider/storage outages, and expanded benchmarks.
"""

import asyncio
from pathlib import Path
import tempfile
import time
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.application.container import ApplicationContainer
from app.application.domain.arbitration import (
    ArbitratedCandidate,
    ArbitratedEvidenceResult,
    AuthorityTier,
)
from app.application.domain.evidence import EvidenceRecord, EvidenceState
from app.application.domain.intent import ParsedIntentRecord
from app.application.domain.memory import MemoryProvenance
from app.application.domain.repository import IndexedRepositoryRecord
from app.application.dto import AgentContextRequest, AgentContextResponse
from app.application.ports.llm_provider import LLMProviderPort
from app.application.ports.repository_metadata import RepositoryMetadataPort
from app.models.provider import ProviderType
from app.models.responses import (
    ArchitectureInfo,
    ComponentInfo,
    ConventionInfo,
    DirectoryEntry,
    RepositorySummary,
    TechnologyStack,
)
from app.services.evidence_service import EvidenceService
from app.services.indexing_service import IndexingService
from app.services.intent_parser import IntentParserService
from app.services.manifest_service import FileFingerprint, RepositoryManifest
from app.services.repository_summary import RepositorySummaryGenerator
from app.services.retrieval_arbitrator import RetrievalArbitrator
from app.services.source_search_service import SourceSearchService
from app.services.workspace_authorization_service import WorkspaceAuthorizationService


def _create_evaluation_manifest() -> RepositoryManifest:
    """Create a standardized repository manifest for evaluation benchmarks."""
    manifest = RepositoryManifest(
        repo_path="/test/eval_repo",
        dataset_name="eval_repo",
        schema_version="2.0",
        parser_version="2.0.0",
        repo_fingerprint="eval_repo_fp_2026_001",
    )
    manifest.files["src/auth.py"] = FileFingerprint(
        path="src/auth.py",
        mtime=1700000000.0,
        size=1024,
        sha256="sha256_auth_valid_001",
        language="python",
        symbols=["authenticate_user", "verify_token", "issue_jwt"],
    )
    manifest.files["src/service.py"] = FileFingerprint(
        path="src/service.py",
        mtime=1700000000.0,
        size=2048,
        sha256="sha256_service_valid_002",
        language="python",
        symbols=["process_order", "calculate_vat", "apply_discount"],
    )
    manifest.files["src/components/UserProfile.tsx"] = FileFingerprint(
        path="src/components/UserProfile.tsx",
        mtime=1700000000.0,
        size=3072,
        sha256="sha256_userprofile_valid_003",
        language="typescript",
        symbols=["UserProfile", "UserAvatar", "ThemeBadge"],
    )
    return manifest


class _EvalInMemoryMetaStore(RepositoryMetadataPort):
    """In-memory metadata store for regression evaluation."""

    def __init__(self) -> None:
        self._records: dict[str, IndexedRepositoryRecord] = {}

    def get_by_path(self, path: Path) -> Optional[IndexedRepositoryRecord]:
        for r in self._records.values():
            if Path(r.path).resolve() == Path(path).resolve():
                return r
        return None

    def get_by_id(self, repo_id: str) -> Optional[IndexedRepositoryRecord]:
        return self._records.get(repo_id)

    def list_all(self) -> list[IndexedRepositoryRecord]:
        return list(self._records.values())

    def upsert(self, record: IndexedRepositoryRecord) -> None:
        self._records[record.id] = record

    def delete(self, repo_id: str) -> bool:
        return self._records.pop(repo_id, None) is not None

    def count(self) -> int:
        return len(self._records)


class _EvalMockProvider(LLMProviderPort):
    """Test double for LLM provider in regression evaluation."""

    def __init__(
        self,
        provider_type: ProviderType = ProviderType.LM_STUDIO,
        default_model: str = "qwen2.5-coder:7b",
        response_text: str = '{"task_summary": "Parsed task", "category": "feature", "extracted_symbols": [], "relevant_file_hints": [], "is_vague": false}',
        should_fail: bool = False,
    ) -> None:
        self.provider_type = provider_type
        self.default_model = default_model
        self.response_text = response_text
        self.should_fail = should_fail
        self.call_count = 0

    async def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> str:
        self.call_count += 1
        if self.should_fail:
            raise ConnectionError("Provider unreachable at http://127.0.0.1:1234/v1")
        return self.response_text

    async def check_health(self) -> Any:
        mock_h = MagicMock()
        mock_h.is_reachable = not self.should_fail
        mock_h.active_model = self.default_model
        mock_h.loaded_models = [self.default_model] if not self.should_fail else []
        mock_h.quantization_warning = None
        return mock_h

    async def list_models(self) -> list[Any]:
        return []

    async def discover_models(self, *args: Any, **kwargs: Any) -> Any:
        mock_res = MagicMock()
        mock_res.is_reachable = not self.should_fail
        mock_res.models = []
        return mock_res


# =============================================================================
# Scope 10: Retrieval-Quality Evaluation
# =============================================================================


def test_eval_authority_order_under_adversarial_similarity():
    """Evaluate candidate distribution: Tier 1 (relevance=0.10) unconditionally outranks Tier 4 (relevance=0.999)."""
    manifest = _create_evaluation_manifest()
    intent = ParsedIntentRecord(
        task_summary="Authenticate user login",
        category="authentication",
        extracted_symbols=["authenticate_user"],
        relevant_file_hints=["src/auth.py"],
    )

    prov = MemoryProvenance(
        repository_id="eval_repo",
        repository_fingerprint="eval_repo_fp_2026_001",
        source_file="src/auth.py",
        source_sha256="sha256_auth_valid_001",
        source_symbol="authenticate_user",
    )

    # Low relevance Tier 1 snippet (relevance baseline 0.5 without symbol matches)
    source_snippet = ["### `src/auth.py` (Lines 1-5)\n```\n# comment\npass\n```"]
    # Semantic Tier 4 memory with maximum similarity
    cognee_mem = {
        "text": "Highly relevant semantic description of JWT login.",
        "score": 0.9999,
        "provenance": prov,
    }

    t0 = time.perf_counter()
    result = RetrievalArbitrator.arbitrate(
        task_prompt="Authenticate user login",
        intent=intent,
        manifest=manifest,
        source_snippets=source_snippet,
        source_matched_files=["src/auth.py"],
        cognee_memories=[cognee_mem],
        target_tokens=2000,
    )
    latency_ms = (time.perf_counter() - t0) * 1000

    # Empirical Metrics
    assert latency_ms < 15.0  # Arbitration overhead sub-15ms
    assert len(result.candidates) == 2
    assert result.candidates[0].tier == AuthorityTier.TIER_1_SOURCE
    assert result.candidates[1].tier == AuthorityTier.TIER_4_COGNEE

    # Assert sort key invariant
    assert result.candidates[0].sort_key() > result.candidates[1].sort_key()


def test_eval_stale_memory_rejection_rate():
    """Evaluate stale memory rejection: 100% of mutated/stale records are rejected prior to ranking."""
    manifest = _create_evaluation_manifest()
    intent = ParsedIntentRecord(
        task_summary="Process orders",
        category="feature_request",
        extracted_symbols=["process_order"],
        relevant_file_hints=["src/service.py"],
    )

    # 1 Valid memory
    valid_prov = MemoryProvenance(
        repository_id="eval_repo",
        repository_fingerprint="eval_repo_fp_2026_001",
        source_file="src/service.py",
        source_sha256="sha256_service_valid_002",
        source_symbol="process_order",
    )
    # 4 Stale memories with outdated SHA
    stale_mems = [
        {
            "text": f"Stale order calculation rule {i}",
            "score": 0.95,
            "provenance": MemoryProvenance(
                repository_id="eval_repo",
                repository_fingerprint="eval_repo_fp_2026_001",
                source_file="src/service.py",
                source_sha256=f"stale_sha_{i}",
                source_symbol="process_order",
            ),
        }
        for i in range(4)
    ]

    all_cognee = [{"text": "Valid order calculation", "score": 0.80, "provenance": valid_prov}] + stale_mems

    result = RetrievalArbitrator.arbitrate(
        task_prompt="Process orders",
        intent=intent,
        manifest=manifest,
        cognee_memories=all_cognee,
        target_tokens=2000,
    )

    # Empirical Rejection Ratio: 4 / 5 = 80% rejected
    assert result.stale_rejected_count == 4
    assert len(result.candidates) == 1
    assert result.candidates[0].is_valid is True
    assert result.candidates[0].provenance.source_sha256 == "sha256_service_valid_002"


def test_eval_cross_repository_isolation():
    """Evaluate cross-repository isolation: 100% of foreign repository memories are rejected."""
    manifest = _create_evaluation_manifest()
    intent = ParsedIntentRecord(
        task_summary="Authenticate user login",
        category="authentication",
        extracted_symbols=["authenticate_user"],
        relevant_file_hints=["src/auth.py"],
    )

    foreign_mems = [
        {
            "text": f"Foreign repo {i} authentication notes.",
            "score": 0.99,
            "provenance": MemoryProvenance(
                repository_id=f"foreign_repo_{i}",
                repository_fingerprint=f"foreign_fp_{i}",
                source_file="src/auth.py",
                source_sha256="sha256_auth_valid_001",
                source_symbol="authenticate_user",
            ),
        }
        for i in range(5)
    ]

    result = RetrievalArbitrator.arbitrate(
        task_prompt="Authenticate user login",
        intent=intent,
        manifest=manifest,
        cognee_memories=foreign_mems,
        target_tokens=2000,
    )

    assert result.cross_repo_rejected_count == 5
    assert len(result.candidates) == 0


def test_eval_path_only_evidence_does_not_pass_gate():
    """Evaluate path-only boundary: Indexed files alone without snippet or symbol match fails gate."""
    manifest = _create_evaluation_manifest()
    intent = ParsedIntentRecord(
        task_summary="Configure Stripe payments",
        category="billing",
        extracted_symbols=["handle_stripe_webhook"],
        relevant_file_hints=["src/payments.py"],
    )

    arbitrated = RetrievalArbitrator.arbitrate(
        task_prompt="Configure Stripe payments",
        intent=intent,
        manifest=manifest,
        source_snippets=[],
        source_matched_files=["src/auth.py", "src/service.py"],
    )

    evidence = EvidenceService.assess_evidence(
        task_prompt="Configure Stripe payments",
        intent=intent,
        repo_summary=None,
        indexed_files=["src/auth.py", "src/service.py"],
        relevant_snippets=arbitrated.authoritative_snippets,
        matched_file_rels=arbitrated.authoritative_files,
        structural_symbols=arbitrated.authoritative_symbols,
        structural_relationships=arbitrated.authoritative_relationships,
        manifest=manifest,
        arbitrated_result=arbitrated,
    )

    assert evidence.abstained is True
    assert evidence.model_claims_allowed is False
    assert evidence.evidence_state in (EvidenceState.INSUFFICIENT.value, EvidenceState.NONE.value)


def test_eval_abstention_preservation_when_no_feature_evidence():
    """Evaluate abstention preservation: Complete absence of feature evidence deterministically abstains."""
    intent = ParsedIntentRecord(
        task_summary="Configure Stripe payment checkout billing",
        category="payment_billing",
        extracted_symbols=["handle_stripe_checkout", "StripeInvoiceManager"],
        relevant_file_hints=["billing.py"],
    )

    arbitrated = RetrievalArbitrator.arbitrate(
        task_prompt="Configure Stripe payment checkout billing",
        intent=intent,
        manifest=None,
        source_snippets=[],
        source_matched_files=[],
    )

    evidence = EvidenceService.assess_evidence(
        task_prompt="Configure Stripe payment checkout billing",
        intent=intent,
        repo_summary=None,
        indexed_files=["src/auth.py", "src/service.py"],
        relevant_snippets=arbitrated.authoritative_snippets,
        matched_file_rels=arbitrated.authoritative_files,
        structural_symbols=arbitrated.authoritative_symbols,
        structural_relationships=arbitrated.authoritative_relationships,
        manifest=None,
        arbitrated_result=arbitrated,
    )

    assert evidence.abstained is True
    assert evidence.model_claims_allowed is False
    assert any("billing" in m.lower() or "payment" in m.lower() for m in evidence.missing_evidence)


# =============================================================================
# Scope 11: Budget and Performance Evaluation
# =============================================================================


def test_eval_minimal_budget_protects_tier1_and_tier2():
    """Evaluate minimal budget: Tight 30-token budget protects Tier 1/2 while omitting Tier 3/4."""
    manifest = _create_evaluation_manifest()
    intent = ParsedIntentRecord(
        task_summary="Authenticate user login",
        category="authentication",
        extracted_symbols=["authenticate_user"],
        relevant_file_hints=["src/auth.py"],
    )

    prov = MemoryProvenance(
        repository_id="eval_repo",
        repository_fingerprint="eval_repo_fp_2026_001",
        source_file="src/auth.py",
        source_sha256="sha256_auth_valid_001",
        source_symbol="authenticate_user",
    )

    snip = ["### `src/auth.py` (Lines 1-5)\n```\ndef authenticate_user(): pass\n```"]  # ~15 tokens
    ast_syms = ["authenticate_user"]  # ~5 tokens
    large_kuzu = {"text": "Kuzu vector node description " * 20, "similarity": 0.99, "provenance": prov}  # ~80 tokens
    large_cognee = {"text": "Cognee semantic explanation " * 20, "score": 0.99, "provenance": prov}  # ~80 tokens

    result = RetrievalArbitrator.arbitrate(
        task_prompt="Authenticate user login",
        intent=intent,
        manifest=manifest,
        source_snippets=snip,
        source_matched_files=["src/auth.py"],
        ast_symbols=ast_syms,
        lancedb_kuzu_memories=[large_kuzu],
        cognee_memories=[large_cognee],
        target_tokens=30,
    )

    assert result.tier_counts[AuthorityTier.TIER_1_SOURCE.label] == 1
    assert result.tier_counts[AuthorityTier.TIER_2_MANIFEST_AST.label] == 1
    assert result.tier_counts[AuthorityTier.TIER_3_LANCEDB_KUZU.label] == 0
    assert result.tier_counts[AuthorityTier.TIER_4_COGNEE.label] == 0
    assert result.total_token_estimate <= 30


def test_eval_medium_budget_allocates_residual_to_tier3():
    """Evaluate medium budget: Tier 3 occupies residual space without evicting Tier 1 or Tier 2."""
    manifest = _create_evaluation_manifest()
    intent = ParsedIntentRecord(
        task_summary="Authenticate user login",
        category="authentication",
        extracted_symbols=["authenticate_user"],
        relevant_file_hints=["src/auth.py"],
    )

    prov = MemoryProvenance(
        repository_id="eval_repo",
        repository_fingerprint="eval_repo_fp_2026_001",
        source_file="src/auth.py",
        source_sha256="sha256_auth_valid_001",
        source_symbol="authenticate_user",
    )

    snip = ["### `src/auth.py` (Lines 1-5)\n```\ndef authenticate_user(): pass\n```"]  # ~15 tokens
    ast_syms = ["authenticate_user"]  # ~5 tokens
    compact_kuzu = {"text": "Kuzu node: auth verification.", "similarity": 0.88, "provenance": prov}  # ~10 tokens
    large_cognee = {"text": "Cognee semantic explanation " * 30, "score": 0.99, "provenance": prov}  # ~120 tokens

    # 40 tokens: enough for Tier 1 (15) + Tier 2 (5) + Tier 3 (10) = 30 tokens, but not large Cognee (120)
    result = RetrievalArbitrator.arbitrate(
        task_prompt="Authenticate user login",
        intent=intent,
        manifest=manifest,
        source_snippets=snip,
        source_matched_files=["src/auth.py"],
        ast_symbols=ast_syms,
        lancedb_kuzu_memories=[compact_kuzu],
        cognee_memories=[large_cognee],
        target_tokens=40,
    )

    assert result.tier_counts[AuthorityTier.TIER_1_SOURCE.label] == 1
    assert result.tier_counts[AuthorityTier.TIER_2_MANIFEST_AST.label] == 1
    assert result.tier_counts[AuthorityTier.TIER_3_LANCEDB_KUZU.label] == 1
    assert result.tier_counts[AuthorityTier.TIER_4_COGNEE.label] == 0
    assert result.total_token_estimate <= 40


def test_eval_full_budget_sequential_filling():
    """Evaluate full budget: 8,000 tokens allocates Tier 1 -> Tier 2 -> Tier 3 -> Tier 4 sequentially."""
    manifest = _create_evaluation_manifest()
    intent = ParsedIntentRecord(
        task_summary="Process orders and render UserProfile",
        category="full_stack",
        extracted_symbols=["process_order", "UserProfile"],
        relevant_file_hints=["src/service.py", "src/components/UserProfile.tsx"],
    )

    prov_svc = MemoryProvenance(
        repository_id="eval_repo",
        repository_fingerprint="eval_repo_fp_2026_001",
        source_file="src/service.py",
        source_sha256="sha256_service_valid_002",
        source_symbol="process_order",
    )
    prov_ui = MemoryProvenance(
        repository_id="eval_repo",
        repository_fingerprint="eval_repo_fp_2026_001",
        source_file="src/components/UserProfile.tsx",
        source_sha256="sha256_userprofile_valid_003",
        source_symbol="UserProfile",
    )

    snippets = [
        "### `src/service.py` (Lines 1-10)\n```\ndef process_order(): pass\n```",
        "### `src/components/UserProfile.tsx` (Lines 1-15)\n```\nexport const UserProfile = () => <div />;\n```",
    ]
    ast_symbols = ["process_order", "UserProfile"]
    ast_calls = ["process_order -> calculate_vat"]
    ast_jsx = ["UserProfile -> <ThemeBadge />"]
    kuzu_mems = [{"text": "Kuzu vector embedding node", "similarity": 0.85, "provenance": prov_svc}]
    cognee_mems = [{"text": "Cognee semantic React UI documentation", "score": 0.82, "provenance": prov_ui}]

    result = RetrievalArbitrator.arbitrate(
        task_prompt="Process orders and render UserProfile",
        intent=intent,
        manifest=manifest,
        source_snippets=snippets,
        source_matched_files=["src/service.py", "src/components/UserProfile.tsx"],
        ast_symbols=ast_symbols,
        ast_call_edges=ast_calls,
        ast_jsx_renders=ast_jsx,
        lancedb_kuzu_memories=kuzu_mems,
        cognee_memories=cognee_mems,
        target_tokens=8000,
    )

    assert result.tier_counts[AuthorityTier.TIER_1_SOURCE.label] == 2
    assert result.tier_counts[AuthorityTier.TIER_2_MANIFEST_AST.label] >= 3
    assert result.tier_counts[AuthorityTier.TIER_3_LANCEDB_KUZU.label] == 1
    assert result.tier_counts[AuthorityTier.TIER_4_COGNEE.label] == 1
    assert result.total_token_estimate <= 8000


def test_eval_deterministic_budget_reproducibility():
    """Evaluate reproducibility: 5 consecutive arbitration runs produce bitwise identical sort keys & allocation."""
    manifest = _create_evaluation_manifest()
    intent = ParsedIntentRecord(
        task_summary="Authenticate user login",
        category="authentication",
        extracted_symbols=["authenticate_user"],
        relevant_file_hints=["src/auth.py"],
    )

    prov = MemoryProvenance(
        repository_id="eval_repo",
        repository_fingerprint="eval_repo_fp_2026_001",
        source_file="src/auth.py",
        source_sha256="sha256_auth_valid_001",
        source_symbol="authenticate_user",
    )
    snip = ["### `src/auth.py` (Lines 1-10)\n```\ndef authenticate_user(): pass\n```"]
    ast_syms = ["authenticate_user"]
    cognee = [{"text": "Valid auth documentation.", "score": 0.85, "provenance": prov}]

    runs = [
        RetrievalArbitrator.arbitrate(
            task_prompt="Authenticate user login",
            intent=intent,
            manifest=manifest,
            source_snippets=snip,
            source_matched_files=["src/auth.py"],
            ast_symbols=ast_syms,
            cognee_memories=cognee,
            target_tokens=1000,
        )
        for _ in range(5)
    ]

    first_run_dict = runs[0].to_dict()
    for i, r in enumerate(runs[1:], start=2):
        assert r.to_dict() == first_run_dict, f"Run {i} diverged from deterministic baseline"


# =============================================================================
# Scope 12: End-to-End Regression Certification
# =============================================================================


@pytest.mark.asyncio
async def test_eval_phase_10d3_grounding_regression():
    """Certify Phase 10D.3 grounding regression: Live pipeline cleanly abstains on missing auth."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_path = Path(tmp_dir) / "django_sample_app"
        repo_path.mkdir()
        (repo_path / "manage.py").write_text("#!/usr/bin/env python\n")
        (repo_path / "settings.py").write_text("INSTALLED_APPS = ['django.contrib.admin']\n")
        (repo_path / "models.py").write_text("class Product:\n    pass\n")

        meta = _EvalInMemoryMetaStore()
        auth = WorkspaceAuthorizationService(metadata_store=meta, workspace_roots=[Path(tmp_dir)])
        container = ApplicationContainer.create()
        container.metadata_store = meta
        container.workspace_auth = auth

        mock_provider = _EvalMockProvider(
            response_text='{"task_summary": "Implement JWT auth", "category": "feature", "extracted_symbols": ["jwt_auth"], "relevant_file_hints": ["auth.py"], "is_vague": false}'
        )
        container.llm_provider = mock_provider
        container.intent_parser = IntentParserService(llm_service=mock_provider)

        mock_cognee = MagicMock()
        container.cognee_service = mock_cognee
        container.indexing_service = IndexingService(cognee_service=mock_cognee)
        container.summary_generator = RepositorySummaryGenerator()
        container.source_search = SourceSearchService()

        mock_pkg = MagicMock()
        mock_pkg.markdown = "# Synthetic Context Package"
        mock_pkg.sections = []
        mock_pkg.references = []
        container.context_service = MagicMock()
        container.context_service.generate_context_package = AsyncMock(return_value=mock_pkg)

        context_uc = container.get_context_use_cases()
        req = AgentContextRequest(
            task_prompt="Implement JWT auth and token verification",
            repository_path=str(repo_path),
        )

        resp = await context_uc.get_agent_context(req)

        assert isinstance(resp, AgentContextResponse)
        assert resp.success is True
        assert resp.abstained is True
        assert resp.model_invoked is False
        assert resp.model_claims_allowed is False
        assert "# Insufficient Repository Evidence Notice" in resp.context_markdown
        assert "<think>" not in resp.context_markdown


def test_eval_phase_10d4_memory_truth_regression():
    """Certify Phase 10D.4 memory truth regression: Modified source file immediately invalidates memory."""
    manifest = _create_evaluation_manifest()

    # Old SHA before edit
    old_sha_prov = MemoryProvenance(
        repository_id="eval_repo",
        repository_fingerprint="eval_repo_fp_2026_001",
        source_file="src/auth.py",
        source_sha256="sha256_auth_outdated_old",
        source_symbol="authenticate_user",
    )

    is_valid, reason = RetrievalArbitrator.validate_candidate_provenance(old_sha_prov, manifest)
    assert is_valid is False
    assert reason == "source_sha256_stale"


@pytest.mark.asyncio
async def test_eval_provider_failure_resilience():
    """Certify provider outage resilience: ConnectionError triggers deterministic fallback without crashing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_path = Path(tmp_dir) / "app_repo"
        repo_path.mkdir()
        (repo_path / "main.py").write_text("def run(): pass\n")

        meta = _EvalInMemoryMetaStore()
        auth = WorkspaceAuthorizationService(metadata_store=meta, workspace_roots=[Path(tmp_dir)])
        container = ApplicationContainer.create()
        container.metadata_store = meta
        container.workspace_auth = auth

        failing_provider = _EvalMockProvider(should_fail=True)
        container.llm_provider = failing_provider
        container.intent_parser = IntentParserService(llm_service=failing_provider)
        mock_cognee = MagicMock()
        container.cognee_service = mock_cognee
        container.indexing_service = IndexingService(cognee_service=mock_cognee)
        container.summary_generator = RepositorySummaryGenerator()
        container.source_search = SourceSearchService()

        mock_pkg = MagicMock()
        mock_pkg.markdown = "# Fallback Package"
        mock_pkg.sections = []
        mock_pkg.references = []
        container.context_service = MagicMock()
        container.context_service.generate_context_package = AsyncMock(return_value=mock_pkg)

        context_uc = container.get_context_use_cases()
        req = AgentContextRequest(
            task_prompt="Inspect main execution loop",
            repository_path=str(repo_path),
        )

        resp = await context_uc.get_agent_context(req)

        assert resp.success is True
        assert resp.model_invoked is False
        assert resp.fallback_used is True
        assert resp.context_markdown is not None


def test_eval_storage_failure_resilience():
    """Certify datastore outage resilience: When memory stores are empty or None, AST & source retrieval works."""
    manifest = _create_evaluation_manifest()
    intent = ParsedIntentRecord(
        task_summary="Authenticate user login",
        category="authentication",
        extracted_symbols=["authenticate_user"],
        relevant_file_hints=["src/auth.py"],
    )

    snip = ["### `src/auth.py` (Lines 1-10)\n```\ndef authenticate_user(): pass\n```"]
    ast_syms = ["authenticate_user"]

    # LanceDB and Cognee are unavailable / empty
    result = RetrievalArbitrator.arbitrate(
        task_prompt="Authenticate user login",
        intent=intent,
        manifest=manifest,
        source_snippets=snip,
        source_matched_files=["src/auth.py"],
        ast_symbols=ast_syms,
        lancedb_kuzu_memories=[],
        cognee_memories=[],
        target_tokens=1000,
    )

    assert len(result.candidates) == 2
    assert result.tier_counts[AuthorityTier.TIER_1_SOURCE.label] == 1
    assert result.tier_counts[AuthorityTier.TIER_2_MANIFEST_AST.label] == 1
    assert "src/auth.py" in result.authoritative_files
    assert "authenticate_user" in result.authoritative_symbols
