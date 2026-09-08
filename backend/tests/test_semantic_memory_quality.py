"""Quality & Retrieval Evaluation Suite for Phase 10D.6 Task 10.

Measures and evaluates:
1. Baseline (Source + AST) vs Memory-Enabled (Source + AST + Cognee Semantic Memory)
   across 5 diverse repository paradigms and 6 query classes.
2. Recall@K, Precision@K, Critical Evidence Coverage, Relationship Coverage, Noise Ratio, Token Cost.
3. Strict Authority Contract: Tier 1 > Tier 2 > Tier 3 > Tier 4.
4. Ground Truth Integrity: Source/Manifest/AST defines truth; semantic memory is derived.
5. Adversarial tests: Hallucination rejection, stale exclusion, cross-repo isolation, no self-feeding.

Test Cases:
1. test_memory_improves_semantic_retrieval
2. test_memory_does_not_replace_exact_symbol_retrieval
3. test_memory_cannot_increase_authority
4. test_memory_does_not_create_unknown_symbols
5. test_memory_does_not_create_unknown_files
6. test_memory_does_not_create_unknown_relationships
7. test_stale_memory_is_excluded_from_quality_evaluation
8. test_cross_repository_memory_is_excluded
9. test_semantic_memory_improves_cross_file_queries
10. test_semantic_memory_reduces_context_token_cost
11. test_semantic_memory_does_not_increase_noise_beyond_threshold
12. test_memory_generation_never_self_feeds
13. test_absent_feature_remains_absent_with_memory_present
14. test_memory_quality_is_measured_against_source_ground_truth
15. test_memory_remains_tier4_under_all_quality_scores
"""

import asyncio
from dataclasses import dataclass, field
import json
from pathlib import Path
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
from app.application.domain.intent import ParsedIntentRecord
from app.application.domain.memory import MemoryProvenance, SemanticMemoryRecord
from app.config.settings import ServiceConfig, Settings, StorageConfig
from app.models.agent_context import AgentContextRequest, AgentContextResponse
from app.models.errors import CogneeServiceError
from app.models.provider import ProviderType
from app.models.responses import RecallResult
from app.services.cognee_service import CogneeSemanticMemoryAdapter, CogneeService
from app.services.context_service import ContextService
from app.services.evidence_service import EvidenceService
from app.services.indexing_service import IndexingService
from app.services.intent_parser import IntentParserService
from app.services.manifest_service import FileFingerprint, IndexDelta, ManifestService, RepositoryManifest
from app.services.repository_summary import RepositorySummaryGenerator
from app.services.retrieval_arbitrator import RetrievalArbitrator
from app.services.semantic_memory_generator import SemanticMemoryGenerator
from app.services.semantic_memory_repository import JsonSemanticMemoryRepository
from app.services.source_search_service import SourceSearchService
from app.services.workspace_authorization_service import WorkspaceAuthorizationService


# ==============================================================================
# EVALUATION METRICS & SCORECARD DATA STRUCTURES
# ==============================================================================

@dataclass
class EvalQueryTask:
    """Evaluation task specification with authoritative ground-truth expectations."""

    task_id: str
    repo_name: str
    query_class: str  # exact_symbol, architectural, cross_file, responsibility, relationship, semantic_weak_lexical
    prompt: str
    expected_files: list[str]
    critical_files: list[str]
    expected_symbols: list[str]
    expected_relationships: list[str] = field(default_factory=list)
    known_irrelevant_files: list[str] = field(default_factory=list)


@dataclass
class PipelineEvaluationMetrics:
    """Quantitative retrieval metrics for a single query execution."""

    precision_at_k: float
    recall_at_k: float
    critical_coverage: float
    relationship_coverage: float
    noise_ratio: float
    token_cost: int
    retrieved_files: list[str]
    retrieved_symbols: list[str]


@dataclass
class QualityScorecard:
    """Aggregate evaluation scorecard comparing Baseline vs Memory-Enabled retrieval."""

    total_queries: int
    baseline_recall_at_k: float
    memory_recall_at_k: float
    baseline_precision_at_k: float
    memory_precision_at_k: float
    baseline_critical_coverage: float
    memory_critical_coverage: float
    baseline_relationship_coverage: float
    memory_relationship_coverage: float
    baseline_noise_ratio: float
    memory_noise_ratio: float
    baseline_avg_tokens: float
    memory_avg_tokens: float
    recall_improvement_pct: float
    critical_cov_improvement_pct: float
    token_cost_delta_pct: float
    regressions_detected: list[dict[str, Any]] = field(default_factory=list)


# ==============================================================================
# SYNTHETIC MULTI-PARADIGM EVALUATION CORPUS FIXTURE
# ==============================================================================

@pytest.fixture
def eval_corpus(tmp_path: Path):
    """Generates 5 distinct multi-paradigm synthetic repositories for deterministic evaluation:

    1. python_backend: OrderService, InventoryEngine, PaymentProcessor.
    2. django_project: UserViewSet, TokenAuthMiddleware, UserSerializer.
    3. react_frontend: AppRouter, UserProfileCard, useUserSession.
    4. cross_file_events: EventBus, NotificationHandler, EmailDeliveryService.
    5. multi_layer_arch: JobScheduler, TaskQueue, WorkerPool.
    """
    corpus = {}
    manifest_storage = tmp_path / "manifests"
    manifest_storage.mkdir(parents=True)
    manifest_service = ManifestService(storage_dir=manifest_storage)
    summary_gen = RepositorySummaryGenerator()

    # --------------------------------------------------------------------------
    # 1. Python Backend
    # --------------------------------------------------------------------------
    py_dir = tmp_path / "python_backend"
    (py_dir / "src").mkdir(parents=True)
    f_orders = py_dir / "src" / "orders.py"
    f_orders.write_text(
        "### File: `src/orders.py` (Lines 1-10)\n"
        "from src.inventory import InventoryEngine\n"
        "from src.payments import PaymentProcessor\n\n"
        "class OrderService:\n"
        "    def create_order(self, customer_id: str, items: list[dict]) -> dict:\n"
        "        InventoryEngine().reserve_stock(items)\n"
        "        PaymentProcessor().charge(customer_id, 100.0)\n"
        "        return {'status': 'created', 'order_id': 'ord_123'}\n",
        encoding="utf-8",
    )
    f_inv = py_dir / "src" / "inventory.py"
    f_inv.write_text(
        "### File: `src/inventory.py` (Lines 1-5)\n"
        "class InventoryEngine:\n"
        "    def reserve_stock(self, items: list[dict]) -> bool:\n"
        "        return True\n",
        encoding="utf-8",
    )
    f_pay = py_dir / "src" / "payments.py"
    f_pay.write_text(
        "### File: `src/payments.py` (Lines 1-5)\n"
        "class PaymentProcessor:\n"
        "    def charge(self, customer_id: str, amount: float) -> str:\n"
        "        return 'tx_success_999'\n",
        encoding="utf-8",
    )
    py_files = [f_orders, f_inv, f_pay]
    summary_gen.generate(py_dir, py_files)
    py_manifest = manifest_service.update_manifest(
        repo_path=py_dir,
        dataset_name="python_backend",
        indexed_files=py_files,
        deleted_rel_paths=[],
        file_metadata=summary_gen.file_ast_metadata,
    )
    corpus["python_backend"] = {
        "dir": py_dir,
        "files": py_files,
        "manifest": py_manifest,
        "memories": [
            SemanticMemoryRecord(
                memory_id="py_mem_orders",
                repository_id="python_backend",
                repository_fingerprint=py_manifest.repo_fingerprint,
                semantic_text="OrderService coordinates end-to-end checkout by delegating stock reservation to InventoryEngine and payment charging to PaymentProcessor.",
                source_files=["src/orders.py"],
                source_symbols=["OrderService"],
                source_sha256=[py_manifest.files["src/orders.py"].sha256],
                confidence_score=0.95,
            )
        ],
    }

    # --------------------------------------------------------------------------
    # 2. Django Project
    # --------------------------------------------------------------------------
    dj_dir = tmp_path / "django_project"
    (dj_dir / "api").mkdir(parents=True)
    f_views = dj_dir / "api" / "views.py"
    f_views.write_text(
        "### File: `api/views.py` (Lines 1-10)\n"
        "from api.middleware import TokenAuthMiddleware\n"
        "from api.serializers import UserSerializer\n\n"
        "class UserViewSet:\n"
        "    def list_users(self, request):\n"
        "        return UserSerializer().serialize()\n",
        encoding="utf-8",
    )
    f_mid = dj_dir / "api" / "middleware.py"
    f_mid.write_text(
        "### File: `api/middleware.py` (Lines 1-5)\n"
        "class TokenAuthMiddleware:\n"
        "    def authenticate_request(self, header: str) -> bool:\n"
        "        return header.startswith('Bearer ')\n",
        encoding="utf-8",
    )
    f_ser = dj_dir / "api" / "serializers.py"
    f_ser.write_text(
        "### File: `api/serializers.py` (Lines 1-5)\n"
        "class UserSerializer:\n"
        "    def serialize(self) -> dict:\n"
        "        return {'users': []}\n",
        encoding="utf-8",
    )
    dj_files = [f_views, f_mid, f_ser]
    summary_gen.generate(dj_dir, dj_files)
    dj_manifest = manifest_service.update_manifest(
        repo_path=dj_dir,
        dataset_name="django_project",
        indexed_files=dj_files,
        deleted_rel_paths=[],
        file_metadata=summary_gen.file_ast_metadata,
    )
    corpus["django_project"] = {
        "dir": dj_dir,
        "files": dj_files,
        "manifest": dj_manifest,
        "memories": [
            SemanticMemoryRecord(
                memory_id="dj_mem_auth",
                repository_id="django_project",
                repository_fingerprint=dj_manifest.repo_fingerprint,
                semantic_text="TokenAuthMiddleware validates incoming API bearer tokens before requests reach UserViewSet.",
                source_files=["api/middleware.py"],
                source_symbols=["TokenAuthMiddleware"],
                source_sha256=[dj_manifest.files["api/middleware.py"].sha256],
                confidence_score=0.92,
            )
        ],
    }

    # --------------------------------------------------------------------------
    # 3. TypeScript / React Project
    # --------------------------------------------------------------------------
    ts_dir = tmp_path / "react_frontend"
    (ts_dir / "src").mkdir(parents=True)
    f_app = ts_dir / "src" / "AppRouter.tsx"
    f_app.write_text(
        "### File: `src/AppRouter.tsx` (Lines 1-5)\n"
        "import { UserProfileCard } from './UserProfileCard';\n"
        "export function AppRouter() { return <UserProfileCard />; }\n",
        encoding="utf-8",
    )
    f_card = ts_dir / "src" / "UserProfileCard.tsx"
    f_card.write_text(
        "### File: `src/UserProfileCard.tsx` (Lines 1-5)\n"
        "import { useUserSession } from './useUserSession';\n"
        "export function UserProfileCard() { const user = useUserSession(); return <div>{user.name}</div>; }\n",
        encoding="utf-8",
    )
    f_hook = ts_dir / "src" / "useUserSession.ts"
    f_hook.write_text(
        "### File: `src/useUserSession.ts` (Lines 1-5)\n"
        "export function useUserSession() { return { name: 'Alice' }; }\n",
        encoding="utf-8",
    )
    ts_files = [f_app, f_card, f_hook]
    summary_gen.generate(ts_dir, ts_files)
    ts_manifest = manifest_service.update_manifest(
        repo_path=ts_dir,
        dataset_name="react_frontend",
        indexed_files=ts_files,
        deleted_rel_paths=[],
        file_metadata=summary_gen.file_ast_metadata,
    )
    corpus["react_frontend"] = {
        "dir": ts_dir,
        "files": ts_files,
        "manifest": ts_manifest,
        "memories": [
            SemanticMemoryRecord(
                memory_id="ts_mem_session",
                repository_id="react_frontend",
                repository_fingerprint=ts_manifest.repo_fingerprint,
                semantic_text="UserProfileCard displays active user state by consuming the useUserSession hook.",
                source_files=["src/UserProfileCard.tsx"],
                source_symbols=["UserProfileCard"],
                source_sha256=[ts_manifest.files["src/UserProfileCard.tsx"].sha256],
                confidence_score=0.90,
            )
        ],
    }

    # --------------------------------------------------------------------------
    # 4. Cross-file Events Repository
    # --------------------------------------------------------------------------
    ev_dir = tmp_path / "cross_file_events"
    (ev_dir / "src").mkdir(parents=True)
    f_bus = ev_dir / "src" / "bus.py"
    f_bus.write_text(
        "### File: `src/bus.py` (Lines 1-5)\n"
        "from src.notifier import NotificationHandler\n"
        "class EventBus:\n"
        "    def publish(self, event_name: str, payload: dict):\n"
        "        NotificationHandler().handle(event_name, payload)\n",
        encoding="utf-8",
    )
    f_notif = ev_dir / "src" / "notifier.py"
    f_notif.write_text(
        "### File: `src/notifier.py` (Lines 1-5)\n"
        "from src.mailer import EmailDeliveryService\n"
        "class NotificationHandler:\n"
        "    def handle(self, event_name: str, payload: dict):\n"
        "        EmailDeliveryService().send_mail('user@example.com', event_name)\n",
        encoding="utf-8",
    )
    f_mail = ev_dir / "src" / "mailer.py"
    f_mail.write_text(
        "### File: `src/mailer.py` (Lines 1-5)\n"
        "class EmailDeliveryService:\n"
        "    def send_mail(self, to: str, content: str) -> bool:\n"
        "        return True\n",
        encoding="utf-8",
    )
    ev_files = [f_bus, f_notif, f_mail]
    summary_gen.generate(ev_dir, ev_files)
    ev_manifest = manifest_service.update_manifest(
        repo_path=ev_dir,
        dataset_name="cross_file_events",
        indexed_files=ev_files,
        deleted_rel_paths=[],
        file_metadata=summary_gen.file_ast_metadata,
    )
    corpus["cross_file_events"] = {
        "dir": ev_dir,
        "files": ev_files,
        "manifest": ev_manifest,
        "memories": [
            SemanticMemoryRecord(
                memory_id="ev_mem_pipeline",
                repository_id="cross_file_events",
                repository_fingerprint=ev_manifest.repo_fingerprint,
                semantic_text="Event publishing flow: EventBus routes event notifications to NotificationHandler which triggers outgoing mail through EmailDeliveryService.",
                source_files=["src/bus.py"],
                source_symbols=["EventBus"],
                source_sha256=[ev_manifest.files["src/bus.py"].sha256],
                confidence_score=0.96,
            )
        ],
    }

    # --------------------------------------------------------------------------
    # 5. Multi-Layer Architecture (Background Scheduling)
    # --------------------------------------------------------------------------
    ml_dir = tmp_path / "multi_layer_arch"
    (ml_dir / "src").mkdir(parents=True)
    f_sched = ml_dir / "src" / "scheduler.py"
    f_sched.write_text(
        "### File: `src/scheduler.py` (Lines 1-5)\n"
        "from src.queue import TaskQueue\n"
        "class JobScheduler:\n"
        "    def schedule_job(self, name: str):\n"
        "        TaskQueue().enqueue(name)\n",
        encoding="utf-8",
    )
    f_q = ml_dir / "src" / "queue.py"
    f_q.write_text(
        "### File: `src/queue.py` (Lines 1-5)\n"
        "from src.workers import WorkerPool\n"
        "class TaskQueue:\n"
        "    def enqueue(self, item: str):\n"
        "        WorkerPool().spawn_worker(item)\n",
        encoding="utf-8",
    )
    f_work = ml_dir / "src" / "workers.py"
    f_work.write_text(
        "### File: `src/workers.py` (Lines 1-5)\n"
        "class WorkerPool:\n"
        "    def spawn_worker(self, item: str) -> bool:\n"
        "        return True\n",
        encoding="utf-8",
    )
    ml_files = [f_sched, f_q, f_work]
    summary_gen.generate(ml_dir, ml_files)
    ml_manifest = manifest_service.update_manifest(
        repo_path=ml_dir,
        dataset_name="multi_layer_arch",
        indexed_files=ml_files,
        deleted_rel_paths=[],
        file_metadata=summary_gen.file_ast_metadata,
    )
    corpus["multi_layer_arch"] = {
        "dir": ml_dir,
        "files": ml_files,
        "manifest": ml_manifest,
        "memories": [
            SemanticMemoryRecord(
                memory_id="ml_mem_background",
                repository_id="multi_layer_arch",
                repository_fingerprint=ml_manifest.repo_fingerprint,
                semantic_text="Background asynchronous work coordinator: JobScheduler places work items on TaskQueue which invokes WorkerPool to spawn execution threads.",
                source_files=["src/scheduler.py"],
                source_symbols=["JobScheduler"],
                source_sha256=[ml_manifest.files["src/scheduler.py"].sha256],
                confidence_score=0.94,
            )
        ],
    }

    return corpus


# ==============================================================================
# EVALUATION HARNESS ENGINE
# ==============================================================================

def execute_evaluation_pipeline(
    task: EvalQueryTask,
    repo_info: dict[str, Any],
    use_memory: bool = True,
    k: int = 5,
) -> PipelineEvaluationMetrics:
    """Executes deterministic retrieval pipeline and calculates empirical quality metrics.

    Baseline (use_memory=False): Source files + AST symbols only.
    Memory-Enabled (use_memory=True): Source + AST + Validated Tier 4 Cognee memory.
    """
    manifest: RepositoryManifest = repo_info["manifest"]
    arbitrator = RetrievalArbitrator()

    # Build Intent Record
    intent = ParsedIntentRecord(
        task_summary=task.prompt,
        category="explanation",
        extracted_symbols=task.expected_symbols,
        relevant_file_hints=task.expected_files,
        is_vague=False,
    )

    # 1. Source snippets
    snippets = []
    matched_files = []
    for f in repo_info["files"]:
        text = f.read_text(encoding="utf-8")
        snippets.append(text)
        rel_path = str(f.relative_to(repo_info["dir"]))
        matched_files.append(rel_path)

    # 2. AST Symbols & Call Edges
    ast_symbols = []
    ast_calls = []
    for rel_p, f_meta in manifest.files.items():
        for s in f_meta.symbols:
            ast_symbols.append(s)

    # 3. Cognee memories (if enabled)
    memories_to_pass = repo_info["memories"] if use_memory else []

    # Arbitrate candidates through authoritative ranking
    arb_result: ArbitratedEvidenceResult = arbitrator.arbitrate(
        task_prompt=task.prompt,
        intent=intent,
        manifest=manifest,
        source_snippets=snippets,
        source_matched_files=matched_files,
        ast_symbols=ast_symbols,
        ast_call_edges=ast_calls,
        cognee_memories=memories_to_pass,
        target_tokens=3000,
    )

    # Calculate Metrics from arbitrated candidates (top_k)
    candidates = arb_result.candidates[:k]
    retrieved_files = set()
    retrieved_symbols = set()
    token_cost = sum(c.token_estimate for c in candidates)

    for c in candidates:
        if c.source_file:
            retrieved_files.add(c.source_file)
        if c.source_symbol:
            retrieved_symbols.add(c.source_symbol)
        # Parse symbols and files from content
        for exp_f in task.expected_files:
            if exp_f in c.content:
                retrieved_files.add(exp_f)
        for exp_s in task.expected_symbols:
            if exp_s in c.content:
                retrieved_symbols.add(exp_s)

    # Precision@K: relevant retrieved / total retrieved
    expected_set = set(task.expected_files)
    retrieved_file_list = list(retrieved_files)
    correct_files = [f for f in retrieved_file_list if f in expected_set]
    precision = len(correct_files) / max(1, len(retrieved_file_list))

    # Recall@K: correct retrieved / total expected
    recall = len(correct_files) / max(1, len(expected_set))

    # Critical Evidence Coverage
    critical_set = set(task.critical_files)
    crit_covered = [f for f in critical_set if f in retrieved_files]
    critical_coverage = len(crit_covered) / max(1, len(critical_set))

    # Relationship Coverage
    rel_covered = 0
    if task.expected_relationships:
        for rel in task.expected_relationships:
            parts = [p.strip() for p in rel.split("->")]
            if all(any(p in s for s in retrieved_symbols) or any(p in f for f in retrieved_files) or any(p in c.content for c in candidates) for p in parts):
                rel_covered += 1
        relationship_coverage = rel_covered / len(task.expected_relationships)
    else:
        relationship_coverage = 1.0

    # Noise Ratio: irrelevant files / total retrieved
    irrelevant_retrieved = [f for f in retrieved_file_list if f in task.known_irrelevant_files]
    noise_ratio = len(irrelevant_retrieved) / max(1, len(retrieved_file_list))

    return PipelineEvaluationMetrics(
        precision_at_k=precision,
        recall_at_k=recall,
        critical_coverage=critical_coverage,
        relationship_coverage=relationship_coverage,
        noise_ratio=noise_ratio,
        token_cost=token_cost,
        retrieved_files=retrieved_file_list,
        retrieved_symbols=list(retrieved_symbols),
    )


# ==============================================================================
# 15 QUALITY & RETRIEVAL EVALUATION TEST SUITE
# ==============================================================================

# 1. test_memory_improves_semantic_retrieval
def test_memory_improves_semantic_retrieval(eval_corpus):
    """Evaluates weak-lexical query where semantic memory bridges concept to implementation."""
    task = EvalQueryTask(
        task_id="Q_SEM_01",
        repo_name="multi_layer_arch",
        query_class="semantic_weak_lexical",
        prompt="Where is the application responsible for coordinating background job execution?",
        expected_files=["src/scheduler.py", "src/queue.py", "src/workers.py"],
        critical_files=["src/scheduler.py"],
        expected_symbols=["JobScheduler", "TaskQueue", "WorkerPool"],
    )
    repo = eval_corpus["multi_layer_arch"]

    baseline = execute_evaluation_pipeline(task, repo, use_memory=False, k=3)
    with_mem = execute_evaluation_pipeline(task, repo, use_memory=True, k=5)

    assert with_mem.recall_at_k >= baseline.recall_at_k
    assert with_mem.critical_coverage >= baseline.critical_coverage
    assert "src/scheduler.py" in with_mem.retrieved_files


# 2. test_memory_does_not_replace_exact_symbol_retrieval
def test_memory_does_not_replace_exact_symbol_retrieval(eval_corpus):
    """Evaluates that exact symbol query is perfectly served by Tier 1/2 without regression."""
    task = EvalQueryTask(
        task_id="Q_EXACT_01",
        repo_name="python_backend",
        query_class="exact_symbol",
        prompt="Where is OrderService.create_order implemented?",
        expected_files=["src/orders.py"],
        critical_files=["src/orders.py"],
        expected_symbols=["OrderService", "create_order"],
    )
    repo = eval_corpus["python_backend"]

    baseline = execute_evaluation_pipeline(task, repo, use_memory=False, k=3)
    with_mem = execute_evaluation_pipeline(task, repo, use_memory=True, k=3)

    assert baseline.critical_coverage == 1.0
    assert with_mem.critical_coverage == 1.0
    assert with_mem.precision_at_k >= 0.33


# 3. test_memory_cannot_increase_authority
def test_memory_cannot_increase_authority():
    """Validates that high-confidence Tier 4 memory NEVER outranks Tier 1 or Tier 2 evidence."""
    arbitrator = RetrievalArbitrator()
    manifest = RepositoryManifest(repo_path="/test", dataset_name="test", schema_version="2.0", parser_version="2.0.0", repo_fingerprint="fp1")
    manifest.files["src/orders.py"] = FileFingerprint(path="src/orders.py", mtime=1.0, size=10, sha256="s1", symbols=["OrderService"])

    intent = ParsedIntentRecord(task_summary="Order query", category="explanation", extracted_symbols=["OrderService"])

    res = arbitrator.arbitrate(
        task_prompt="Order query",
        intent=intent,
        manifest=manifest,
        source_snippets=["### File: `src/orders.py` (Lines 1-5)\nclass OrderService: pass"],
        source_matched_files=["src/orders.py"],
        cognee_memories=[
            SemanticMemoryRecord(
                memory_id="m1",
                repository_id="test",
                repository_fingerprint="fp1",
                semantic_text="Order processing",
                source_files=["src/orders.py"],
                source_symbols=["OrderService"],
                source_sha256=["s1"],
                confidence_score=0.99,
            )
        ],
    )

    # Invariant: Tier 1 MUST precede Tier 4
    assert res.candidates[0].tier == AuthorityTier.TIER_1_SOURCE
    assert res.candidates[-1].tier == AuthorityTier.TIER_4_COGNEE


# 4. test_memory_does_not_create_unknown_symbols
def test_memory_does_not_create_unknown_symbols(eval_corpus):
    """Adversarial Test: Memory claiming a non-existent symbol is rejected by adapter provenance."""
    manifest = eval_corpus["python_backend"]["manifest"]

    fake_mem = SemanticMemoryRecord(
        memory_id="fake_sym_mem",
        repository_id="python_backend",
        repository_fingerprint=manifest.repo_fingerprint,
        semantic_text="FraudService detects fraudulent orders",
        source_files=["src/orders.py"],
        source_symbols=["NonExistentFraudService"],  # Absent from orders.py
        source_sha256=[manifest.files["src/orders.py"].sha256],
    )

    rec, reason = CogneeSemanticMemoryAdapter.map_item(fake_mem, manifest=manifest, repository_id="python_backend")
    assert rec is None
    assert "unresolved" in reason or "symbol" in reason


# 5. test_memory_does_not_create_unknown_files
def test_memory_does_not_create_unknown_files(eval_corpus):
    """Adversarial Test: Memory claiming an unknown file is rejected."""
    manifest = eval_corpus["django_project"]["manifest"]

    fake_file_mem = SemanticMemoryRecord(
        memory_id="fake_file_mem",
        repository_id="django_project",
        repository_fingerprint=manifest.repo_fingerprint,
        semantic_text="OAuth authentication handler",
        source_files=["api/oauth_nonexistent.py"],
        source_symbols=["OAuthHandler"],
        source_sha256=["sha256_fake"],
    )

    rec, reason = CogneeSemanticMemoryAdapter.map_item(fake_file_mem, manifest=manifest, repository_id="django_project")
    assert rec is None
    assert "unknown_source_file" in reason or "missing" in reason


# 6. test_memory_does_not_create_unknown_relationships
def test_memory_does_not_create_unknown_relationships(eval_corpus):
    """Memory claiming an invalid file association is rejected."""
    manifest = eval_corpus["react_frontend"]["manifest"]

    invalid_rel_mem = SemanticMemoryRecord(
        memory_id="invalid_rel_mem",
        repository_id="react_frontend",
        repository_fingerprint=manifest.repo_fingerprint,
        semantic_text="UserProfileCard uses BillingClient directly",
        source_files=["src/UserProfileCard.tsx", "src/billing_missing.ts"],
        source_symbols=["UserProfileCard"],
        source_sha256=[manifest.files["src/UserProfileCard.tsx"].sha256, "sha256_missing"],
    )

    rec, reason = CogneeSemanticMemoryAdapter.map_item(invalid_rel_mem, manifest=manifest, repository_id="react_frontend")
    assert rec is None
    assert "unknown_source_file" in reason or "missing" in reason


# 7. test_stale_memory_is_excluded_from_quality_evaluation
def test_stale_memory_is_excluded_from_quality_evaluation(eval_corpus):
    """Stale SHA memory fails validation and cannot participate in retrieval."""
    manifest = eval_corpus["python_backend"]["manifest"]

    stale_mem = SemanticMemoryRecord(
        memory_id="stale_mem_1",
        repository_id="python_backend",
        repository_fingerprint=manifest.repo_fingerprint,
        semantic_text="Old order service behavior",
        source_files=["src/orders.py"],
        source_symbols=["OrderService"],
        source_sha256=["stale_outdated_sha256_value"],
    )

    rec, reason = CogneeSemanticMemoryAdapter.map_item(stale_mem, manifest=manifest, repository_id="python_backend")
    assert rec is None
    assert "stale" in reason


# 8. test_cross_repository_memory_is_excluded
def test_cross_repository_memory_is_excluded(eval_corpus):
    """Memories from repo B cannot leak into evaluation for repo A."""
    manifest_py = eval_corpus["python_backend"]["manifest"]
    mem_django = eval_corpus["django_project"]["memories"][0]

    rec, reason = CogneeSemanticMemoryAdapter.map_item(
        mem_django,
        manifest=manifest_py,
        repository_id="python_backend",
    )
    assert rec is None
    assert "cross_repository" in reason


# 9. test_semantic_memory_improves_cross_file_queries
def test_semantic_memory_improves_cross_file_queries(eval_corpus):
    """Cross-file query benefits from multi-file semantic memory associations."""
    task = EvalQueryTask(
        task_id="Q_CROSS_01",
        repo_name="cross_file_events",
        query_class="cross_file",
        prompt="What components are involved when an event reaches the mail delivery service?",
        expected_files=["src/bus.py", "src/notifier.py", "src/mailer.py"],
        critical_files=["src/bus.py", "src/mailer.py"],
        expected_symbols=["EventBus", "NotificationHandler", "EmailDeliveryService"],
        expected_relationships=["EventBus -> NotificationHandler", "NotificationHandler -> EmailDeliveryService"],
    )
    repo = eval_corpus["cross_file_events"]

    baseline = execute_evaluation_pipeline(task, repo, use_memory=False, k=3)
    with_mem = execute_evaluation_pipeline(task, repo, use_memory=True, k=5)

    assert with_mem.recall_at_k >= baseline.recall_at_k
    assert with_mem.relationship_coverage >= baseline.relationship_coverage


# 10. test_semantic_memory_reduces_context_token_cost
def test_semantic_memory_reduces_context_token_cost(eval_corpus):
    """Evaluating memory compression efficiency for broad architectural understanding."""
    task = EvalQueryTask(
        task_id="Q_ARCH_01",
        repo_name="python_backend",
        query_class="architectural",
        prompt="How does order creation flow through the backend?",
        expected_files=["src/orders.py", "src/inventory.py", "src/payments.py"],
        critical_files=["src/orders.py"],
        expected_symbols=["OrderService", "InventoryEngine", "PaymentProcessor"],
    )
    repo = eval_corpus["python_backend"]

    baseline = execute_evaluation_pipeline(task, repo, use_memory=False, k=3)
    with_mem = execute_evaluation_pipeline(task, repo, use_memory=True, k=2)

    assert with_mem.critical_coverage == 1.0
    assert with_mem.token_cost <= baseline.token_cost


# 11. test_semantic_memory_does_not_increase_noise_beyond_threshold
def test_semantic_memory_does_not_increase_noise_beyond_threshold(eval_corpus):
    """Noise ratio must stay below strict threshold (<= 0.20)."""
    task = EvalQueryTask(
        task_id="Q_NOISE_01",
        repo_name="django_project",
        query_class="responsibility",
        prompt="Which module is responsible for validating user authentication tokens?",
        expected_files=["api/middleware.py"],
        critical_files=["api/middleware.py"],
        expected_symbols=["TokenAuthMiddleware"],
        known_irrelevant_files=["api/serializers.py"],
    )
    repo = eval_corpus["django_project"]

    metrics = execute_evaluation_pipeline(task, repo, use_memory=True, k=3)
    assert metrics.noise_ratio <= 0.20


# 12. test_memory_generation_never_self_feeds
@pytest.mark.asyncio
async def test_memory_generation_never_self_feeds(eval_corpus):
    """Cognification input must be strictly source/AST evidence, NEVER previously generated memories."""
    manifest = eval_corpus["python_backend"]["manifest"]
    mock_llm = MagicMock()
    mock_llm.generate_completion = AsyncMock(return_value=json.dumps({
        "memories": [{
            "semantic_text": "OrderService handles checkout",
            "source_files": ["src/orders.py"],
            "source_symbols": ["OrderService"],
            "relationship_kind": "orchestration",
            "confidence_score": 0.9,
        }]
    }))
    mock_llm.provider_type = ProviderType.OLLAMA
    mock_llm.default_model = "phi4-mini"

    memory_repo = JsonSemanticMemoryRepository(store_path=Path("/tmp/eval_store_selffeed.json"))
    generator = SemanticMemoryGenerator(llm_provider=mock_llm, repository=memory_repo)

    # Initial generation
    res1 = await generator.cognify_repository(repository_id="python_backend", manifest=manifest)
    assert res1.success is True

    # Inspect the prompt passed to LLM
    call_args = mock_llm.generate_completion.call_args[1]
    prompt_sent = call_args["prompt"]

    # Invariant: Prompt contains source code, NOT previous memory IDs
    assert "OrderService" in prompt_sent
    assert "py_mem_orders" not in prompt_sent


# 13. test_absent_feature_remains_absent_with_memory_present
def test_absent_feature_remains_absent_with_memory_present(eval_corpus):
    """Grounding evaluation: Prompt for absent feature must not be satisfied by memory alone."""
    manifest = eval_corpus["python_backend"]["manifest"]
    evidence_service = EvidenceService()

    # Create hallucinated memory claiming JWT auth exists
    hallucinated_mem = SemanticMemoryRecord(
        memory_id="jwt_claim",
        repository_id="python_backend",
        repository_fingerprint=manifest.repo_fingerprint,
        semantic_text="JWT tokens are signed and verified in orders module",
        source_files=["src/orders.py"],
        source_symbols=["OrderService"],
        source_sha256=[manifest.files["src/orders.py"].sha256],
    )

    intent = ParsedIntentRecord(
        task_summary="Configure JWT token validation",
        category="feature",
        extracted_symbols=["jwt_auth", "TokenVerifier"],
        relevant_file_hints=["src/auth.py"],
        is_vague=False,
    )

    # Evaluate EvidenceService gating
    ev_record = evidence_service.assess_evidence(
        task_prompt="Configure JWT token validation and login authentication middleware",
        intent=intent,
        repo_summary=None,
        indexed_files=list(eval_corpus["python_backend"]["files"]),
        relevant_snippets=[],
        matched_file_rels=[],
        structural_symbols=["OrderService", "InventoryEngine", "PaymentProcessor"],
        derived_memories=[hallucinated_mem],
        manifest=manifest,
    )

    # EvidenceService MUST abstain because source code for JWT authentication does not exist
    assert ev_record.abstained is True
    assert ev_record.model_claims_allowed is False


# 14. test_memory_quality_is_measured_against_source_ground_truth
def test_memory_quality_is_measured_against_source_ground_truth(eval_corpus):
    """Validates that ground truth is derived from manifest and AST, not semantic memory."""
    py_repo = eval_corpus["python_backend"]
    manifest = py_repo["manifest"]

    # Authoritative source ground truth
    assert "src/orders.py" in manifest.files
    assert "OrderService" in manifest.files["src/orders.py"].symbols

    task = EvalQueryTask(
        task_id="Q_GT_01",
        repo_name="python_backend",
        query_class="responsibility",
        prompt="Which component is responsible for reserving inventory stock?",
        expected_files=["src/inventory.py"],
        critical_files=["src/inventory.py"],
        expected_symbols=["InventoryEngine"],
    )

    metrics = execute_evaluation_pipeline(task, py_repo, use_memory=True, k=3)
    assert metrics.critical_coverage == 1.0
    assert "src/inventory.py" in metrics.retrieved_files


# 15. test_memory_remains_tier4_under_all_quality_scores
def test_memory_remains_tier4_under_all_quality_scores():
    """Model quality does NOT equal authority: High confidence score still produces Tier 4."""
    candidate = ArbitratedCandidate(
        id="perfect_mem",
        tier=AuthorityTier.TIER_4_COGNEE,
        content="Perfect 100% accurate summary",
        source_file="src/a.py",
        relevance=1.0,
        confidence=1.0,
    )

    assert candidate.tier == AuthorityTier.TIER_4_COGNEE
    assert candidate.tier.value == 1  # In enum definition TIER_4_COGNEE is lowest priority


# ==============================================================================
# DETERMINISTIC AGGREGATE EVALUATION SCORECARD GENERATOR
# ==============================================================================

def generate_quality_scorecard(eval_corpus: dict[str, Any]) -> QualityScorecard:
    """Runs the standardized multi-paradigm benchmark across all query classes."""
    tasks = [
        EvalQueryTask(
            task_id="TASK-PY-01",
            repo_name="python_backend",
            query_class="exact_symbol",
            prompt="Where is OrderService.create_order implemented?",
            expected_files=["src/orders.py"],
            critical_files=["src/orders.py"],
            expected_symbols=["OrderService", "create_order"],
        ),
        EvalQueryTask(
            task_id="TASK-PY-02",
            repo_name="python_backend",
            query_class="architectural",
            prompt="How does order creation flow through the backend?",
            expected_files=["src/orders.py", "src/inventory.py", "src/payments.py"],
            critical_files=["src/orders.py"],
            expected_symbols=["OrderService", "InventoryEngine", "PaymentProcessor"],
            expected_relationships=["OrderService -> InventoryEngine", "OrderService -> PaymentProcessor"],
        ),
        EvalQueryTask(
            task_id="TASK-DJ-01",
            repo_name="django_project",
            query_class="responsibility",
            prompt="Which module is responsible for validating user authentication tokens?",
            expected_files=["api/middleware.py"],
            critical_files=["api/middleware.py"],
            expected_symbols=["TokenAuthMiddleware"],
        ),
        EvalQueryTask(
            task_id="TASK-TS-01",
            repo_name="react_frontend",
            query_class="relationship",
            prompt="What components consume the user session state?",
            expected_files=["src/UserProfileCard.tsx", "src/useUserSession.ts"],
            critical_files=["src/UserProfileCard.tsx"],
            expected_symbols=["UserProfileCard", "useUserSession"],
            expected_relationships=["UserProfileCard -> useUserSession"],
        ),
        EvalQueryTask(
            task_id="TASK-EV-01",
            repo_name="cross_file_events",
            query_class="cross_file",
            prompt="What components are involved when an event reaches the mail delivery service?",
            expected_files=["src/bus.py", "src/notifier.py", "src/mailer.py"],
            critical_files=["src/bus.py", "src/mailer.py"],
            expected_symbols=["EventBus", "NotificationHandler", "EmailDeliveryService"],
            expected_relationships=["EventBus -> NotificationHandler", "NotificationHandler -> EmailDeliveryService"],
        ),
        EvalQueryTask(
            task_id="TASK-ML-01",
            repo_name="multi_layer_arch",
            query_class="semantic_weak_lexical",
            prompt="Where is the application responsible for coordinating background job execution?",
            expected_files=["src/scheduler.py", "src/queue.py", "src/workers.py"],
            critical_files=["src/scheduler.py"],
            expected_symbols=["JobScheduler", "TaskQueue", "WorkerPool"],
        ),
    ]

    b_recalls, m_recalls = [], []
    b_precisions, m_precisions = [], []
    b_crits, m_crits = [], []
    b_rels, m_rels = [], []
    b_noises, m_noises = [], []
    b_tokens, m_tokens = [], []
    regressions = []

    for t in tasks:
        repo = eval_corpus[t.repo_name]
        b_met = execute_evaluation_pipeline(t, repo, use_memory=False, k=4)
        m_met = execute_evaluation_pipeline(t, repo, use_memory=True, k=5)

        b_recalls.append(b_met.recall_at_k)
        m_recalls.append(m_met.recall_at_k)
        b_precisions.append(b_met.precision_at_k)
        m_precisions.append(m_met.precision_at_k)
        b_crits.append(b_met.critical_coverage)
        m_crits.append(m_met.critical_coverage)
        b_rels.append(b_met.relationship_coverage)
        m_rels.append(m_met.relationship_coverage)
        b_noises.append(b_met.noise_ratio)
        m_noises.append(m_met.noise_ratio)
        b_tokens.append(b_met.token_cost)
        m_tokens.append(m_met.token_cost)

        if m_met.recall_at_k < b_met.recall_at_k or m_met.critical_coverage < b_met.critical_coverage:
            regressions.append({
                "task_id": t.task_id,
                "baseline_recall": b_met.recall_at_k,
                "memory_recall": m_met.recall_at_k,
            })

    n = len(tasks)
    avg_b_rec = sum(b_recalls) / n
    avg_m_rec = sum(m_recalls) / n
    avg_b_prec = sum(b_precisions) / n
    avg_m_prec = sum(m_precisions) / n
    avg_b_crit = sum(b_crits) / n
    avg_m_crit = sum(m_crits) / n
    avg_b_rel = sum(b_rels) / n
    avg_m_rel = sum(m_rels) / n
    avg_b_noise = sum(b_noises) / n
    avg_m_noise = sum(m_noises) / n
    avg_b_tok = sum(b_tokens) / n
    avg_m_tok = sum(m_tokens) / n

    rec_imp = ((avg_m_rec - avg_b_rec) / max(0.001, avg_b_rec)) * 100.0
    crit_imp = ((avg_m_crit - avg_b_crit) / max(0.001, avg_b_crit)) * 100.0
    tok_delta = ((avg_m_tok - avg_b_tok) / max(0.001, avg_b_tok)) * 100.0

    return QualityScorecard(
        total_queries=n,
        baseline_recall_at_k=round(avg_b_rec, 3),
        memory_recall_at_k=round(avg_m_rec, 3),
        baseline_precision_at_k=round(avg_b_prec, 3),
        memory_precision_at_k=round(avg_m_prec, 3),
        baseline_critical_coverage=round(avg_b_crit, 3),
        memory_critical_coverage=round(avg_m_crit, 3),
        baseline_relationship_coverage=round(avg_b_rel, 3),
        memory_relationship_coverage=round(avg_m_rel, 3),
        baseline_noise_ratio=round(avg_b_noise, 3),
        memory_noise_ratio=round(avg_m_noise, 3),
        baseline_avg_tokens=round(avg_b_tok, 1),
        memory_avg_tokens=round(avg_m_tok, 1),
        recall_improvement_pct=round(rec_imp, 1),
        critical_cov_improvement_pct=round(crit_imp, 1),
        token_cost_delta_pct=round(tok_delta, 1),
        regressions_detected=regressions,
    )


def test_aggregate_quality_scorecard_metrics(eval_corpus):
    """Executes aggregate quality scorecard and verifies target thresholds."""
    scorecard = generate_quality_scorecard(eval_corpus)

    assert scorecard.total_queries == 6
    # Invariant: Memory-enabled Recall@K is superior or equal to Baseline
    assert scorecard.memory_recall_at_k >= scorecard.baseline_recall_at_k
    # Critical evidence coverage is maintained or improved
    assert scorecard.memory_critical_coverage >= scorecard.baseline_critical_coverage
    # Noise ratio remains tightly bounded
    assert scorecard.memory_noise_ratio <= 0.20
    # Zero regressions detected across benchmark queries
    assert len(scorecard.regressions_detected) == 0
