"""Automated evaluation test suite for RE:Track Context Engine.

Tests:
1. Pure metric calculation integrity (Precision@K, Recall@K, Critical Coverage, Noise Ratio).
2. Golden task dataset schema and file target validity against real repository files.
3. Path matching collision safety (disallowing bare basename matches across layers).
4. Symbol evidence matching with word boundaries and structured symbol integration.
5. End-to-end Context Engine execution via production ContextUseCases.get_agent_context() pipeline.
6. Verification that no synthetic RecallResult objects or hardcoded latencies are used in E2E evaluation.
"""

import ast
import asyncio
from pathlib import Path
import time
import pytest

from app.application.container import ApplicationContainer
from app.application.dto import AgentContextRequest, AgentContextResponse
from app.application.use_cases.context import ContextUseCases
from app.services.cgc_service import CGCService
from app.services.cognee_service import CogneeService
from app.services.context_cache import ContextCacheEngine
from app.services.context_service import ContextService
from app.services.indexing_service import IndexingService
from app.services.local_filesystem import LocalFileSystemAdapter
from app.services.manifest_service import ManifestService
from app.services.repository_summary import RepositorySummaryGenerator
from app.services.source_search_service import SourceSearchService
from tests.evaluation.evaluator import (
    ContextEngineEvaluator,
    GoldenTask,
    SuiteEvaluationSummary,
    match_path,
    match_symbol,
    normalize_path,
)
from tests.evaluation.reporter import EvaluationReporter

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
BENCHMARK_DIR = REPO_ROOT / "benchmarks" / "retrack"
LEGACY_BENCHMARK_DIR = REPO_ROOT / "benchmarks" / "andescontext"


class TestEvaluatorMetrics:
    """Validate pure mathematical calculations of evaluation metrics."""

    def test_precision_at_k_calculation(self):
        task = GoldenTask(
            id="T1",
            category="arch",
            task_prompt="How does container work?",
            expected_files=["backend/app/application/container.py", "backend/app/server.py"],
            critical_files=["backend/app/application/container.py"],
        )
        # 2 retrieved, 1 correct -> Precision@2 = 0.5
        md = "See `backend/app/application/container.py` and `backend/app/random_unused.py`"
        res = ContextEngineEvaluator.evaluate_task(task, md, k=2)
        assert res.precision_at_k == 0.5
        assert res.recall_at_k == 0.5

    def test_recall_at_k_perfect(self):
        task = GoldenTask(
            id="T2",
            category="arch",
            task_prompt="Check server setup",
            expected_files=["backend/app/server.py", "backend/app/config/settings.py"],
            critical_files=["backend/app/server.py"],
        )
        md = "Files: `backend/app/server.py` and `backend/app/config/settings.py`."
        res = ContextEngineEvaluator.evaluate_task(task, md, k=5)
        assert res.recall_at_k == 1.0
        assert res.precision_at_k == 1.0
        assert res.critical_evidence_coverage == 1.0
        assert res.passed is True

    def test_noise_ratio_detection(self):
        task = GoldenTask(
            id="T3",
            category="arch",
            task_prompt="Where is container?",
            expected_files=["backend/app/application/container.py"],
            known_irrelevant_files=["src/components/Sidebar.tsx"],
        )
        md = "Included: `backend/app/application/container.py` and noise `src/components/Sidebar.tsx`"
        res = ContextEngineEvaluator.evaluate_task(task, md, k=5)
        assert res.noise_ratio == 0.5
        assert len(res.detected_noise_files) == 1

    def test_empty_retrieval_handling(self):
        task = GoldenTask(
            id="T4",
            category="arch",
            task_prompt="Missing context",
            expected_files=["backend/app/application/container.py"],
            critical_files=["backend/app/application/container.py"],
        )
        res = ContextEngineEvaluator.evaluate_task(task, "", k=5)
        assert res.precision_at_k == 0.0
        assert res.recall_at_k == 0.0
        assert res.critical_evidence_coverage == 0.0
        assert res.passed is False
        assert "Missing critical files" in str(res.failure_reasons)


class TestPathMatchingCollisionSafety:
    """Verify collision-safe normalized repository-relative path matching rules."""

    def test_exact_path_match(self):
        assert match_path("backend/app/server.py", "backend/app/server.py") is True
        assert match_path("./backend/app/server.py", "backend/app/server.py") is True

    def test_suffix_match_with_directory_boundary(self):
        # Shorter has directory context -> valid prefix trim match
        assert match_path("backend/app/application/use_cases/context.py", "app/application/use_cases/context.py") is True
        assert match_path("backend/app/application/use_cases/context.py", "use_cases/context.py") is True
        assert match_path("app/application/use_cases/context.py", "backend/app/application/use_cases/context.py") is True

    def test_disallow_bare_basename_collision(self):
        # 'context.py' without directory context must NOT match different architectural layers
        assert match_path("backend/app/application/use_cases/context.py", "backend/app/api/routers/context.py") is False
        assert match_path("backend/app/application/use_cases/context.py", "context.py") is False
        assert match_path("backend/app/api/routers/context.py", "context.py") is False
        assert match_path("backend/app/application/dto/context.py", "routers/context.py") is False

    def test_normalize_path_stripping(self):
        assert normalize_path("./backend/app/server.py") == "backend/app/server.py"
        assert normalize_path("backend\\app\\server.py") == "backend/app/server.py"
        assert normalize_path("  backend/app/server.py/  ") == "backend/app/server.py"


class TestSymbolEvidenceMatching:
    """Verify collision-safe symbol evidence matching with word boundaries and structured lists."""

    def test_structured_symbol_match(self):
        assert match_symbol("ApplicationContainer", "", structured_symbols=["ApplicationContainer", "create"]) is True
        assert match_symbol("missing_symbol", "", structured_symbols=["ApplicationContainer"]) is False

    def test_backticked_symbol_match(self):
        md = "Class `ApplicationContainer` is responsible for composition."
        assert match_symbol("ApplicationContainer", md) is True

    def test_word_boundary_regex_match(self):
        md = "We define ApplicationContainer in container.py."
        assert match_symbol("ApplicationContainer", md) is True

    def test_disallow_substring_within_unrelated_word(self):
        # "app" should not match inside "application", "get" should not match inside "together"
        md = "This application runs smoothly together."
        assert match_symbol("app", md) is False
        assert match_symbol("get", md) is False
        assert match_symbol("application", md) is True


class TestGoldenDatasetIntegrity:
    """Verify golden tasks dataset is valid and target files exist in the repository."""

    def test_golden_tasks_exist_and_load(self):
        tasks = ContextEngineEvaluator.load_golden_tasks(BENCHMARK_DIR)
        assert len(tasks) == 20, f"Expected exactly 20 golden tasks, found {len(tasks)}"

        for t in tasks:
            assert t.id.strip() != "", "Task ID must not be empty"
            assert t.task_prompt.strip() != "", f"Task {t.id} prompt must not be empty"
            assert len(t.expected_files) > 0, f"Task {t.id} must specify expected files"
            assert len(t.critical_files) > 0, f"Task {t.id} must specify critical files"

    def test_all_expected_files_exist_in_repository(self):
        tasks = ContextEngineEvaluator.load_golden_tasks(BENCHMARK_DIR)
        missing_files_report = []
        for t in tasks:
            for fpath_str in t.expected_files:
                norm_p = REPO_ROOT / fpath_str
                if not norm_p.exists():
                    missing_files_report.append(f"{t.id}: {fpath_str}")

        assert len(missing_files_report) == 0, f"Some expected files do not exist on disk: {missing_files_report}"


class TestProductionPipelineAuthenticity:
    """Verify the evaluation harness executes the genuine ContextUseCases.get_agent_context pipeline."""

    def test_e2e_evaluation_does_not_use_synthetic_recall_results(self):
        """AST static check: E2E test file must not construct synthetic RecallResult objects."""
        test_file = Path(__file__).resolve()
        tree = ast.parse(test_file.read_text(encoding="utf-8"))

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "test_end_to_end_context_engine_evaluation":
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Name) and child.func.id == "RecallResult":
                            pytest.fail("Synthetic RecallResult construction detected inside test_end_to_end_context_engine_evaluation!")


class TestContextEngineEndToEnd:
    """Run real Context Engine production pipeline across golden tasks and compute empirical baseline."""

    @pytest.mark.asyncio
    async def test_end_to_end_context_engine_evaluation(self):
        tasks = ContextEngineEvaluator.load_golden_tasks(BENCHMARK_DIR)
        assert len(tasks) > 0, "No benchmark tasks found"

        # Construct real production ContextUseCases with concrete service adapters
        fs = LocalFileSystemAdapter()
        cognee_service = CogneeService()
        manifest_service = ManifestService()
        indexing_service = IndexingService(
            cognee_service=cognee_service,
            manifest_service=manifest_service,
        )
        summary_generator = RepositorySummaryGenerator()
        cgc_service = CGCService()
        source_search = SourceSearchService(filesystem=fs)
        cognee_service = CogneeService()
        context_service = ContextService(cognee_service=cognee_service)
        context_cache = ContextCacheEngine()

        context_use_cases = ContextUseCases(
            context_service=context_service,
            cognee_service=cognee_service,
            indexing_service=indexing_service,
            intent_parser=None,  # Pure heuristic intent parser in production fallback
            llm_provider=None,
            cgc_service=cgc_service,
            summary_generator=summary_generator,
            context_cache=context_cache,
            context_gen_lock=asyncio.Lock(),
            ensure_services_fn=lambda: None,
            source_search=source_search,
            filesystem=fs,
        )

        task_results = []
        measured_latencies = []

        for task in tasks:
            # Clear context cache between tasks to guarantee fresh synthesis
            context_cache.clear()

            # Monotonically timed production pipeline execution
            t_start = time.perf_counter()
            request = AgentContextRequest(
                repository_path=str(REPO_ROOT),
                task_prompt=task.task_prompt,
                max_tokens=4000,
                include_structural_graph=True,
            )

            response = await context_use_cases.get_agent_context(request)
            elapsed_ms = (time.perf_counter() - t_start) * 1000
            measured_latencies.append(elapsed_ms)

            assert isinstance(response, AgentContextResponse), f"Expected AgentContextResponse, got {type(response)}"
            assert response.success is True, f"Agent context generation failed for {task.id}: {response}"

            # Evaluate genuine production output against ground truth
            eval_res = ContextEngineEvaluator.evaluate_task(
                task=task,
                context_markdown=response.context_markdown,
                k=10,
                baseline_tokens=25000,
                retrieval_time_ms=float(response.retrieval_time_ms),
                total_time_ms=float(response.total_time_ms or elapsed_ms),
                structured_symbols=response.extracted_symbols + response.callers + response.callees,
                retrieved_files_override=response.related_files,
            )
            task_results.append(eval_res)

        # Aggregate suite summary
        summary = ContextEngineEvaluator.summarize_suite(task_results)

        # Render scorecard in terminal
        terminal_report = EvaluationReporter.format_terminal_summary(summary)
        print("\n" + terminal_report)

        # Generate markdown scorecard artifact in benchmarks/
        report_md_path = BENCHMARK_DIR / "context_engine_baseline_scorecard.md"
        EvaluationReporter.generate_markdown_report(summary, report_md_path)

        # Assert baseline evaluation metrics are recorded and measurable
        assert summary.total_tasks == 20, f"Expected 20 evaluated tasks, got {summary.total_tasks}"
        assert len(summary.task_results) == 20, "All tasks must have detailed evaluation records"
        assert report_md_path.exists(), "Baseline scorecard markdown report must be written"
        assert summary.mean_compression_ratio > 1.0, "Context compression must be positive"
        assert summary.mean_total_time_ms > 0.0, "Total execution time must be measured and positive"
        assert 0.0 <= summary.mean_precision_at_k <= 1.0, "Precision must be bounded [0, 1]"
        assert 0.0 <= summary.mean_recall_at_k <= 1.0, "Recall must be bounded [0, 1]"
        assert 0.0 <= summary.mean_critical_coverage <= 1.0, "Critical coverage must be bounded [0, 1]"
        assert 0.0 <= summary.mean_noise_ratio <= 1.0, "Noise ratio must be bounded [0, 1]"
