"""Scorecard and benchmark report formatting utilities for Context Engine evaluation."""

import json
from pathlib import Path
from typing import Optional, TextIO

from .evaluator import SuiteEvaluationSummary, TaskEvaluationResult


class EvaluationReporter:
    """Formats evaluation results into terminal tables and Markdown reports."""

    @staticmethod
    def format_terminal_summary(summary: SuiteEvaluationSummary) -> str:
        """Format a rich terminal scorecard summary."""
        lines = [
            "\n" + "=" * 80,
            "                  RE:TRACK CONTEXT ENGINE EVALUATION SCORECARD                  ",
            "=" * 80,
            f" Total Tasks Evaluated : {summary.total_tasks}",
            f" Passed Tasks          : {summary.passed_tasks} ({summary.pass_rate * 100:.1f}%)",
            f" Failed Tasks          : {summary.failed_tasks}",
            "-" * 80,
            f" Mean Precision@K      : {summary.mean_precision_at_k:.3f}",
            f" Mean Recall@K         : {summary.mean_recall_at_k:.3f}",
            f" Mean Critical Coverage: {summary.mean_critical_coverage:.3f}",
            f" Mean Noise Ratio      : {summary.mean_noise_ratio:.3f}",
            f" Mean Compression Ratio: {summary.mean_compression_ratio:.2f}x",
            f" Mean Retrieval Latency: {summary.mean_retrieval_time_ms:.1f} ms",
            f" Mean Total Latency    : {summary.mean_total_time_ms:.1f} ms",
            "-" * 80,
            " Category Breakdown:",
        ]

        for cat, stats in summary.category_breakdown.items():
            lines.append(
                f"   - {cat:<18} | Pass: {int(stats['passed'])}/{int(stats['total'])} ({stats['pass_rate']*100:.0f}%) "
                f"| P@K: {stats['mean_precision']:.2f} | R@K: {stats['mean_recall']:.2f} | Crit: {stats['mean_critical_coverage']:.2f}"
            )

        lines.append("-" * 80)
        lines.append(" Per-Task Highlights:")
        for r in summary.task_results:
            status = "PASS" if r.passed else "FAIL"
            reasons = f" ({', '.join(r.failure_reasons)})" if r.failure_reasons else ""
            lines.append(
                f"   [{status}] {r.task_id:<14} | P@K: {r.precision_at_k:.2f} | R@K: {r.recall_at_k:.2f} "
                f"| Crit: {r.critical_evidence_coverage:.2f} | Noise: {r.noise_ratio:.2f}{reasons}"
            )

        lines.append("=" * 80 + "\n")
        return "\n".join(lines)

    @staticmethod
    def generate_markdown_report(summary: SuiteEvaluationSummary, output_path: Optional[Path | str] = None) -> str:
        """Generate a full GitHub-flavored Markdown evaluation report."""
        md_lines = [
            "# RE:Track Context Engine — Phase 7 Baseline Evaluation Report",
            "",
            f"**Total Tasks**: {summary.total_tasks} | **Passed**: {summary.passed_tasks} ({summary.pass_rate * 100:.1f}%) | **Failed**: {summary.failed_tasks}",
            "",
            "## 1. Aggregate Metric Summary",
            "",
            "| Metric | Measured Score | Target Threshold | Status |",
            "| :--- | :--- | :--- | :--- |",
            f"| **Precision@K** | `{summary.mean_precision_at_k:.3f}` | `>= 0.400` | {'✅ PASS' if summary.mean_precision_at_k >= 0.40 else '⚠️ ATTENTION'} |",
            f"| **Recall@K** | `{summary.mean_recall_at_k:.3f}` | `>= 0.500` | {'✅ PASS' if summary.mean_recall_at_k >= 0.50 else '⚠️ ATTENTION'} |",
            f"| **Critical Evidence Coverage** | `{summary.mean_critical_coverage:.3f}` | `>= 0.600` | {'✅ PASS' if summary.mean_critical_coverage >= 0.60 else '⚠️ ATTENTION'} |",
            f"| **Noise Ratio** | `{summary.mean_noise_ratio:.3f}` | `<= 0.200` | {'✅ PASS' if summary.mean_noise_ratio <= 0.20 else '⚠️ HIGH NOISE'} |",
            f"| **Compression Ratio** | `{summary.mean_compression_ratio:.2f}x` | `>= 5.0x` | {'✅ PASS' if summary.mean_compression_ratio >= 5.0 else '⚠️ PASS'} |",
            f"| **Average Retrieval Latency** | `{summary.mean_retrieval_time_ms:.1f} ms` | `<= 500 ms` | {'✅ PASS' if summary.mean_retrieval_time_ms <= 500 else '⚠️ PASS'} |",
            "",
            "## 2. Category Performance Breakdown",
            "",
            "| Category | Total Tasks | Pass Rate | Mean P@K | Mean R@K | Mean Critical Coverage | Mean Noise |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ]

        for cat, stats in summary.category_breakdown.items():
            md_lines.append(
                f"| **{cat}** | {int(stats['total'])} | {stats['pass_rate']*100:.1f}% | "
                f"`{stats['mean_precision']:.3f}` | `{stats['mean_recall']:.3f}` | "
                f"`{stats['mean_critical_coverage']:.3f}` | `{stats['mean_noise_ratio']:.3f}` |"
            )

        md_lines.extend([
            "",
            "## 3. Individual Task Evaluation Results",
            "",
            "| Task ID | Category | Verdict | P@K | R@K | Crit Cov | Noise | Tokens | Latency | Missing Critical |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ])

        for r in summary.task_results:
            missing_crit = ", ".join(r.missing_critical_files + r.missing_critical_symbols) or "None"
            md_lines.append(
                f"| `{r.task_id}` | {r.category} | **{r.verdict}** | `{r.precision_at_k:.2f}` | "
                f"`{r.recall_at_k:.2f}` | `{r.critical_evidence_coverage:.2f}` | `{r.noise_ratio:.2f}` | "
                f"{r.context_tokens} | {r.total_time_ms:.0f}ms | {missing_crit} |"
            )

        report_content = "\n".join(md_lines)

        if output_path:
            p = Path(output_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(report_content, encoding="utf-8")

        return report_content
