"""Deterministic Benchmark Regression Gate for RE:Track CI/CD.

Enforces retrieval performance contracts against the frozen Phase 7/8 scorecard baseline.
Fails CI builds whenever quantitative metrics regress beyond mathematically established tolerances.

Baseline Invariants (from benchmarks/retrack/context_engine_baseline_scorecard.md):
- Mean Precision@K: 0.141
- Mean Recall@K: 0.434
- Mean Critical Evidence Coverage: 0.496
- Mean Noise Ratio: 0.010

Tolerances:
- Precision tolerance: -0.050 (Minimum allowable: 0.091)
- Recall tolerance: -0.050 (Minimum allowable: 0.384)
- Coverage tolerance: -0.050 (Minimum allowable: 0.446)
- Noise threshold: 0.050 (Maximum allowable: 0.050)
"""

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class BenchmarkBaseline:
    """Authoritative Phase 7/8 scorecard baseline metrics."""

    mean_precision_at_k: float = 0.141
    mean_recall_at_k: float = 0.434
    mean_critical_coverage: float = 0.496
    mean_noise_ratio: float = 0.010
    total_tasks: int = 20

    # Release-policy tolerances bounded by single-task discrete step size (1/N = 0.050 for N=20 tasks)
    # Allows minor single-task edge-case fluctuation while strictly preventing multi-task structural regression.
    precision_tolerance: float = 0.050
    recall_tolerance: float = 0.050
    coverage_tolerance: float = 0.050
    max_noise_ratio: float = 0.050


@dataclass
class RegressionViolation:
    """Description of a specific metric regression violation."""

    metric_name: str
    baseline_value: float
    measured_value: float
    allowed_threshold: float
    delta: float
    category: Optional[str] = None
    task_id: Optional[str] = None
    message: str = ""


@dataclass
class RegressionGateResult:
    """Complete report of benchmark regression gate evaluation."""

    passed: bool
    violations: List[RegressionViolation] = field(default_factory=list)
    measured_metrics: Dict[str, Any] = field(default_factory=dict)
    baseline_metrics: Dict[str, Any] = field(default_factory=dict)
    category_metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)
    summary_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "violations": [asdict(v) for v in self.violations],
            "measured_metrics": self.measured_metrics,
            "baseline_metrics": self.baseline_metrics,
            "category_metrics": self.category_metrics,
            "summary_text": self.summary_text,
        }

    def save_json(self, destination: Path | str) -> Path:
        dest_path = Path(destination)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return dest_path


class BenchmarkRegressionGate:
    """Enforces retrieval benchmark quality contracts and detects regressions."""

    def __init__(self, baseline: Optional[BenchmarkBaseline] = None):
        self.baseline = baseline or BenchmarkBaseline()

    def evaluate(
        self,
        mean_precision_at_k: float,
        mean_recall_at_k: float,
        mean_critical_coverage: float,
        mean_noise_ratio: float,
        total_tasks: int = 20,
        category_breakdown: Optional[Dict[str, Dict[str, float]]] = None,
        task_results: Optional[List[Any]] = None,
    ) -> RegressionGateResult:
        """Evaluate measured benchmark metrics against baseline tolerances."""
        violations: List[RegressionViolation] = []

        # 1. Total tasks validation
        if total_tasks < self.baseline.total_tasks:
            violations.append(
                RegressionViolation(
                    metric_name="total_tasks",
                    baseline_value=float(self.baseline.total_tasks),
                    measured_value=float(total_tasks),
                    allowed_threshold=float(self.baseline.total_tasks),
                    delta=float(total_tasks - self.baseline.total_tasks),
                    message=(
                        f"Evaluated task count ({total_tasks}) is less than canonical benchmark baseline "
                        f"({self.baseline.total_tasks})."
                    ),
                )
            )

        # 2. Precision@K threshold
        min_precision = self.baseline.mean_precision_at_k - self.baseline.precision_tolerance
        if mean_precision_at_k < min_precision:
            violations.append(
                RegressionViolation(
                    metric_name="mean_precision_at_k",
                    baseline_value=self.baseline.mean_precision_at_k,
                    measured_value=mean_precision_at_k,
                    allowed_threshold=min_precision,
                    delta=mean_precision_at_k - self.baseline.mean_precision_at_k,
                    message=(
                        f"Mean Precision@K regressed to {mean_precision_at_k:.4f}, below minimum allowed threshold "
                        f"of {min_precision:.4f} (baseline: {self.baseline.mean_precision_at_k:.4f} - tolerance {self.baseline.precision_tolerance:.4f})."
                    ),
                )
            )

        # 3. Recall@K threshold
        min_recall = self.baseline.mean_recall_at_k - self.baseline.recall_tolerance
        if mean_recall_at_k < min_recall:
            violations.append(
                RegressionViolation(
                    metric_name="mean_recall_at_k",
                    baseline_value=self.baseline.mean_recall_at_k,
                    measured_value=mean_recall_at_k,
                    allowed_threshold=min_recall,
                    delta=mean_recall_at_k - self.baseline.mean_recall_at_k,
                    message=(
                        f"Mean Recall@K regressed to {mean_recall_at_k:.4f}, below minimum allowed threshold "
                        f"of {min_recall:.4f} (baseline: {self.baseline.mean_recall_at_k:.4f} - tolerance {self.baseline.recall_tolerance:.4f})."
                    ),
                )
            )

        # 4. Critical Evidence Coverage threshold
        min_coverage = self.baseline.mean_critical_coverage - self.baseline.coverage_tolerance
        if mean_critical_coverage < min_coverage:
            violations.append(
                RegressionViolation(
                    metric_name="mean_critical_coverage",
                    baseline_value=self.baseline.mean_critical_coverage,
                    measured_value=mean_critical_coverage,
                    allowed_threshold=min_coverage,
                    delta=mean_critical_coverage - self.baseline.mean_critical_coverage,
                    message=(
                        f"Mean Critical Evidence Coverage regressed to {mean_critical_coverage:.4f}, below minimum "
                        f"allowed threshold of {min_coverage:.4f} (baseline: {self.baseline.mean_critical_coverage:.4f} - tolerance {self.baseline.coverage_tolerance:.4f})."
                    ),
                )
            )

        # 5. Noise Ratio threshold
        if mean_noise_ratio > self.baseline.max_noise_ratio:
            violations.append(
                RegressionViolation(
                    metric_name="mean_noise_ratio",
                    baseline_value=self.baseline.mean_noise_ratio,
                    measured_value=mean_noise_ratio,
                    allowed_threshold=self.baseline.max_noise_ratio,
                    delta=mean_noise_ratio - self.baseline.mean_noise_ratio,
                    message=(
                        f"Mean Noise Ratio spiked to {mean_noise_ratio:.4f}, exceeding maximum allowed threshold "
                        f"of {self.baseline.max_noise_ratio:.4f} (baseline: {self.baseline.mean_noise_ratio:.4f})."
                    ),
                )
            )

        # 6. Category-level analysis & task attribution
        if category_breakdown:
            for cat_name, cat_scores in category_breakdown.items():
                cat_p = cat_scores.get("mean_precision", cat_scores.get("precision", 0.0))
                cat_r = cat_scores.get("mean_recall", cat_scores.get("recall", 0.0))
                cat_cov = cat_scores.get("mean_critical_coverage", cat_scores.get("critical_coverage", 0.0))
                # Alert if any single category completely collapses to zero
                if cat_cov == 0.0 and self.baseline.mean_critical_coverage > 0.1:
                    violations.append(
                        RegressionViolation(
                            metric_name=f"category_critical_coverage_{cat_name}",
                            baseline_value=0.300,
                            measured_value=cat_cov,
                            allowed_threshold=0.100,
                            delta=cat_cov - 0.300,
                            category=cat_name,
                            message=f"Category '{cat_name}' critical evidence coverage completely collapsed to 0.00.",
                        )
                    )

        passed = len(violations) == 0

        # Construct human-readable summary text
        lines = [
            "=" * 70,
            "RE:Track Retrieval Benchmark Regression Gate Report",
            "=" * 70,
            f"Gate Verdict: {'PASSED (Within Tolerances)' if passed else 'FAILED (Regression Detected)'}",
            f"Evaluated Tasks: {total_tasks} (Baseline: {self.baseline.total_tasks})",
            "",
            "Aggregate Metric Performance vs. Frozen Baseline:",
            f"- Precision@K: {mean_precision_at_k:.4f} (Baseline: {self.baseline.mean_precision_at_k:.4f}, Min: {min_precision:.4f})",
            f"- Recall@K:    {mean_recall_at_k:.4f} (Baseline: {self.baseline.mean_recall_at_k:.4f}, Min: {min_recall:.4f})",
            f"- Critical Cov:{mean_critical_coverage:.4f} (Baseline: {self.baseline.mean_critical_coverage:.4f}, Min: {min_coverage:.4f})",
            f"- Noise Ratio: {mean_noise_ratio:.4f} (Baseline: {self.baseline.mean_noise_ratio:.4f}, Max: {self.baseline.max_noise_ratio:.4f})",
            "",
        ]

        if violations:
            lines.append("Violations Identified:")
            for v in violations:
                lines.append(f"  [X] {v.metric_name}: {v.message}")
            lines.append("")
        else:
            lines.append("No metric regressions detected. Retrieval performance is within baseline tolerances.")
            lines.append("")

        summary_text = "\n".join(lines)

        return RegressionGateResult(
            passed=passed,
            violations=violations,
            measured_metrics={
                "mean_precision_at_k": mean_precision_at_k,
                "mean_recall_at_k": mean_recall_at_k,
                "mean_critical_coverage": mean_critical_coverage,
                "mean_noise_ratio": mean_noise_ratio,
                "total_tasks": total_tasks,
            },
            baseline_metrics={
                "mean_precision_at_k": self.baseline.mean_precision_at_k,
                "mean_recall_at_k": self.baseline.mean_recall_at_k,
                "mean_critical_coverage": self.baseline.mean_critical_coverage,
                "mean_noise_ratio": self.baseline.mean_noise_ratio,
                "total_tasks": self.baseline.total_tasks,
            },
            category_metrics=category_breakdown or {},
            summary_text=summary_text,
        )
