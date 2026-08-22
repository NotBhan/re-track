"""Automated tests verifying the deterministic Benchmark Regression Gate contract.

Invariants:
1. Baseline scorecard constants match the authoritative Phase 7/8 benchmarks scorecard.
2. Tolerances are mathematically bounded to prevent silent performance regressions.
3. Violations provide granular attribution on precision, recall, coverage, and noise.
4. Serialized benchmark results are machine-readable JSON artifacts.
"""

import json
from pathlib import Path
import tempfile

import pytest

from app.evaluation.benchmark_gate import (
    BenchmarkBaseline,
    BenchmarkRegressionGate,
    RegressionGateResult,
)


def test_benchmark_baseline_contract():
    """Verify BenchmarkBaseline metrics match the authoritative Phase 7 scorecard."""
    baseline = BenchmarkBaseline()
    assert baseline.mean_precision_at_k == 0.141
    assert baseline.mean_recall_at_k == 0.434
    assert baseline.mean_critical_coverage == 0.496
    assert baseline.mean_noise_ratio == 0.010
    assert baseline.total_tasks == 20
    assert baseline.precision_tolerance == 0.050
    assert baseline.recall_tolerance == 0.050
    assert baseline.coverage_tolerance == 0.050
    assert baseline.max_noise_ratio == 0.050


def test_benchmark_regression_gate_passes_on_baseline():
    """Verify that exact baseline scores pass the regression gate with zero violations."""
    gate = BenchmarkRegressionGate()
    result = gate.evaluate(
        mean_precision_at_k=0.141,
        mean_recall_at_k=0.434,
        mean_critical_coverage=0.496,
        mean_noise_ratio=0.010,
        total_tasks=20,
    )
    assert result.passed is True
    assert len(result.violations) == 0
    assert "Gate Verdict: PASSED" in result.summary_text


def test_benchmark_regression_detection_precision():
    """Verify regression gate fails when Precision@K drops below baseline - tolerance (0.091)."""
    gate = BenchmarkRegressionGate()
    result = gate.evaluate(
        mean_precision_at_k=0.085,  # Regressed
        mean_recall_at_k=0.434,
        mean_critical_coverage=0.496,
        mean_noise_ratio=0.010,
        total_tasks=20,
    )
    assert result.passed is False
    assert len(result.violations) == 1
    assert result.violations[0].metric_name == "mean_precision_at_k"
    assert "Mean Precision@K regressed" in result.violations[0].message


def test_benchmark_regression_detection_recall():
    """Verify regression gate fails when Recall@K drops below baseline - tolerance (0.384)."""
    gate = BenchmarkRegressionGate()
    result = gate.evaluate(
        mean_precision_at_k=0.141,
        mean_recall_at_k=0.350,  # Regressed
        mean_critical_coverage=0.496,
        mean_noise_ratio=0.010,
        total_tasks=20,
    )
    assert result.passed is False
    assert len(result.violations) == 1
    assert result.violations[0].metric_name == "mean_recall_at_k"
    assert "Mean Recall@K regressed" in result.violations[0].message


def test_benchmark_regression_detection_coverage():
    """Verify regression gate fails when Critical Coverage drops below baseline - tolerance (0.446)."""
    gate = BenchmarkRegressionGate()
    result = gate.evaluate(
        mean_precision_at_k=0.141,
        mean_recall_at_k=0.434,
        mean_critical_coverage=0.400,  # Regressed
        mean_noise_ratio=0.010,
        total_tasks=20,
    )
    assert result.passed is False
    assert len(result.violations) == 1
    assert result.violations[0].metric_name == "mean_critical_coverage"
    assert "Mean Critical Evidence Coverage regressed" in result.violations[0].message


def test_benchmark_regression_detection_noise():
    """Verify regression gate fails when Noise Ratio spikes above max allowed threshold (0.050)."""
    gate = BenchmarkRegressionGate()
    result = gate.evaluate(
        mean_precision_at_k=0.141,
        mean_recall_at_k=0.434,
        mean_critical_coverage=0.496,
        mean_noise_ratio=0.080,  # Spiked noise
        total_tasks=20,
    )
    assert result.passed is False
    assert len(result.violations) == 1
    assert result.violations[0].metric_name == "mean_noise_ratio"
    assert "Mean Noise Ratio spiked" in result.violations[0].message


def test_benchmark_regression_detection_category_collapse():
    """Verify regression gate detects if a category coverage collapses to zero."""
    gate = BenchmarkRegressionGate()
    category_breakdown = {
        "architecture": {"mean_precision": 0.18, "mean_recall": 0.37, "mean_critical_coverage": 0.417},
        "refactoring": {"mean_precision": 0.00, "mean_recall": 0.00, "mean_critical_coverage": 0.00},  # Collapsed
    }
    result = gate.evaluate(
        mean_precision_at_k=0.141,
        mean_recall_at_k=0.434,
        mean_critical_coverage=0.496,
        mean_noise_ratio=0.010,
        total_tasks=20,
        category_breakdown=category_breakdown,
    )
    assert result.passed is False
    assert any(v.metric_name == "category_critical_coverage_refactoring" for v in result.violations)


def test_benchmark_gate_json_serialization():
    """Verify regression gate report can be serialized to machine-readable JSON."""
    gate = BenchmarkRegressionGate()
    result = gate.evaluate(
        mean_precision_at_k=0.141,
        mean_recall_at_k=0.434,
        mean_critical_coverage=0.496,
        mean_noise_ratio=0.010,
        total_tasks=20,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = Path(tmpdir) / "artifacts" / "benchmark_results.json"
        saved_path = result.save_json(out_file)
        assert saved_path.exists()
        
        data = json.loads(saved_path.read_text(encoding="utf-8"))
        assert data["passed"] is True
        assert data["measured_metrics"]["mean_precision_at_k"] == 0.141
        assert data["baseline_metrics"]["mean_precision_at_k"] == 0.141
        assert len(data["violations"]) == 0
