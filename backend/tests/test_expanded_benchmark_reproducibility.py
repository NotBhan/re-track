"""Tests for RE:Track expanded benchmark reproducibility and determinism.

Verifies that consecutive runs against the benchmark corpus produce bitwise identical
summary metrics, precision, recall, and task verdicts.
"""

from pathlib import Path
import pytest

from app.evaluation.expanded_benchmark import ExpandedBenchmarkRunner


def test_expanded_benchmark_reproducibility(tmp_path):
    corpus_dir = Path(__file__).parent.parent.parent / "benchmarks" / "corpus"
    golden_tasks_file = Path(__file__).parent.parent.parent / "benchmarks" / "expanded" / "golden_tasks.json"

    out1_res = tmp_path / "run1_results.json"
    out1_score = tmp_path / "run1_scorecard.md"
    runner1 = ExpandedBenchmarkRunner(
        corpus_dir=corpus_dir,
        golden_tasks_file=golden_tasks_file,
        results_output_file=out1_res,
        scorecard_output_file=out1_score,
    )
    summary1 = runner1.run_suite()

    out2_res = tmp_path / "run2_results.json"
    out2_score = tmp_path / "run2_scorecard.md"
    runner2 = ExpandedBenchmarkRunner(
        corpus_dir=corpus_dir,
        golden_tasks_file=golden_tasks_file,
        results_output_file=out2_res,
        scorecard_output_file=out2_score,
    )
    summary2 = runner2.run_suite()

    assert summary1.total_tasks == summary2.total_tasks
    assert summary1.passed_tasks == summary2.passed_tasks
    assert summary1.pass_rate == summary2.pass_rate
    assert summary1.mean_precision_at_k == summary2.mean_precision_at_k
    assert summary1.mean_recall_at_k == summary2.mean_recall_at_k
    assert summary1.mean_critical_coverage == summary2.mean_critical_coverage
    assert summary1.mean_noise_ratio == summary2.mean_noise_ratio
    assert summary1.mean_relationship_coverage == summary2.mean_relationship_coverage
