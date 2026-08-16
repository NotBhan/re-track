"""Package statistics logger for RE:Track (RefinedEngine Track).

Formats and logs Context Package statistics for demo reporting
and benchmark result recording.
"""

import logging
from datetime import datetime, timezone

from app.models.responses import ContextPackage

logger = logging.getLogger(__name__)


class StatsLogger:
    """Formats and logs Context Package statistics."""

    def format_stats(self, pkg: ContextPackage, repository: str) -> str:
        """Format package statistics as a readable report.

        Args:
            pkg: The generated Context Package.
            repository: Repository name for display.

        Returns:
            Formatted statistics string.
        """
        meta = pkg.metadata
        lines = [
            f"Repository: {repository}",
            f"Task: {pkg.task}",
            "",
            f"Generation Time: {(meta.total_time_ms / 1000):.1f} s" if meta else "Generation Time: unknown",
            "",
            f"Retrieved Memories: {meta.retrieved_memory_count}" if meta else "Retrieved Memories: unknown",
            f"Expanded Memories: 0 (MVP)",
            f"Unique Memories: {meta.deduplicated_count}" if meta else "Unique Memories: unknown",
            "",
            "Sections Generated:",
        ]

        for s in pkg.sections:
            lines.append(f"  \u2713 {s.heading}")

        if not pkg.sections:
            lines.append("  (none)")

        lines.extend([
            "",
            f"Final Tokens: {meta.estimated_tokens}" if meta else "Final Tokens: unknown",
            f"Compression Ratio: {meta.compression_ratio:.0%}" if meta else "Compression Ratio: unknown",
            f"Duplicate Rate: {self._dup_rate(meta)}" if meta else "Duplicate Rate: unknown",
            "",
            f"Validation: {'PASS' if pkg.section_count >= 2 else 'WARN'}",
        ])

        return "\n".join(lines)

    def _dup_rate(self, meta) -> str:
        """Calculate duplicate rate from metadata."""
        if not meta or meta.retrieved_memory_count == 0:
            return "0%"
        duped = meta.retrieved_memory_count - meta.deduplicated_count
        return f"{(duped / meta.retrieved_memory_count):.0%}"

    def log_to_file(self, pkg: ContextPackage, repository: str, path: str) -> None:
        """Write statistics report to a file.

        Args:
            pkg: The generated Context Package.
            repository: Repository name.
            path: Output file path.
        """
        report = self.format_stats(pkg, repository)
        with open(path, "w") as f:
            f.write(report)
        logger.info("Stats logged to %s", path)

    def format_benchmark_report(
        self,
        results: list[dict],
        repository: str,
    ) -> str:
        """Format a complete benchmark report.

        Args:
            results: List of per-question scoring results.
            repository: Repository name.

        Returns:
            Formatted benchmark report string.
        """
        total = len(results)
        passed = sum(1 for r in results if r.get("verdict") == "PASS")
        avg_score = sum(r.get("overall_score", 0) for r in results) / max(total, 1)

        lines = [
            f"# Benchmark Results — {repository}",
            "",
            f"**Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            f"**Repository**: {repository}",
            f"**Questions Evaluated**: {total}",
            "",
            "## Summary",
            "",
            f"- Average Score: {avg_score:.3f}",
            f"- Pass Rate: {passed}/{total} ({passed/max(total,1)*100:.0f}%)",
            "",
            "## Per-Question Results",
            "",
            "| QID | Score | Verdict | Files Found | Symbols Found |",
            "|-----|-------|---------|-------------|---------------|",
        ]

        for r in results:
            qid = r.get("question_id", "?")
            score = r.get("overall_score", 0)
            verdict = r.get("verdict", "?")
            files = len(r.get("file_score", {}).get("found", []))
            symbols = len(r.get("symbol_score", {}).get("found", []))
            lines.append(f"| {qid} | {score:.3f} | {verdict} | {files} | {symbols} |")

        lines.extend([
            "",
            "## Recommendations",
            "",
        ])

        if passed == total:
            lines.append("- All questions passed. Pipeline is performing well.")
        elif passed >= total * 0.7:
            lines.append("- Most questions passed. Review failing questions for retrieval improvements.")
        else:
            lines.append("- Significant failures. Review categorization and retrieval quality.")

        return "\n".join(lines)
