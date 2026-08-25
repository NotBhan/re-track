"""Tests for RE:Track Phase 10C expanded multi-repository retrieval benchmark.

Validates that all 36 golden tasks across 12 retrieval categories pass evaluation
against the 6 synthetic benchmark repositories.
"""

from pathlib import Path
import pytest

from app.evaluation.expanded_benchmark import (
    ExpandedBenchmarkEvaluator,
    ExpandedBenchmarkRunner,
)


@pytest.fixture(scope="module")
def benchmark_paths():
    corpus_dir = Path(__file__).parent.parent.parent / "benchmarks" / "corpus"
    golden_tasks_file = Path(__file__).parent.parent.parent / "benchmarks" / "expanded" / "golden_tasks.json"
    return corpus_dir, golden_tasks_file


def test_golden_tasks_file_loads(benchmark_paths):
    _, golden_tasks_file = benchmark_paths
    assert golden_tasks_file.exists(), f"Missing golden tasks file: {golden_tasks_file}"
    tasks = ExpandedBenchmarkEvaluator.load_golden_tasks(golden_tasks_file)
    assert len(tasks) == 36


def test_expanded_benchmark_suite_execution(benchmark_paths, tmp_path):
    corpus_dir, golden_tasks_file = benchmark_paths
    results_file = tmp_path / "results.json"
    scorecard_file = tmp_path / "scorecard.md"

    runner = ExpandedBenchmarkRunner(
        corpus_dir=corpus_dir,
        golden_tasks_file=golden_tasks_file,
        results_output_file=results_file,
        scorecard_output_file=scorecard_file,
    )
    summary = runner.run_suite()

    assert summary.total_tasks == 36
    assert summary.passed_tasks == 36
    assert summary.failed_tasks == 0
    assert summary.pass_rate == 1.0
    assert summary.mean_recall_at_k >= 0.90
    assert summary.mean_critical_coverage == 1.0
    assert summary.mean_relationship_coverage >= 0.90
    assert results_file.exists()
    assert scorecard_file.exists()
