"""Assembles Context Packages from pipeline output.

Orchestrates the retrieval pipeline stages and package assembly:
1. Deduplication
2. Ranking
3. Compression
4. Categorization
5. Reference Resolution
6. Section Building
7. Budget Enforcement
8. Markdown Rendering

Contains minimal business logic — delegates to dedicated stages.
"""

import logging
import time
from datetime import datetime, timezone

from app.models.responses import (
    ContextPackage,
    PackageMetadata,
    PackageSection,
    RecallResult,
    RepositorySummary,
)
from app.services.budget_manager import BudgetManager
from app.services.pipeline.categorization import Categorizer
from app.services.pipeline.compression import Compressor
from app.services.pipeline.dedup import Deduplicator
from app.services.pipeline.ranking import Ranker
from app.services.pipeline.references import ReferenceResolver
from app.services.renderer import MarkdownRenderer

logger = logging.getLogger(__name__)

# Section heading mappings
_HEADINGS = {
    "files": "Relevant Files",
    "architecture": "Architecture",
    "apis": "Existing APIs",
    "conventions": "Coding Conventions",
    "decisions": "Previous Decisions",
    "knowledge": "Implementation Notes",
}

# Priority mappings per section type
_PRIORITIES = {
    "files": 5,
    "architecture": 4,
    "knowledge": 4,
    "apis": 3,
    "decisions": 3,
    "conventions": 2,
}


class PackageBuilder:
    """Assembles a Context Package from recall results.

    Orchestrates the full pipeline from raw RecallResults to a
    complete ContextPackage with metadata and rendered Markdown.
    """

    def __init__(self, target_tokens: int = 3000) -> None:
        """Initialize the package builder.

        Args:
            target_tokens: Target token count for budget enforcement.
        """
        self._dedup = Deduplicator()
        self._ranker = Ranker()
        self._compressor = Compressor()
        self._categorizer = Categorizer()
        self._resolver = ReferenceResolver()
        self._budget = BudgetManager(target_tokens)
        self._renderer = MarkdownRenderer()

    def build(
        self,
        task: str,
        results: list[RecallResult],
        repository_summary: RepositorySummary | None,
        datasets: list[str],
        retrieval_time_ms: int = 0,
    ) -> ContextPackage:
        """Build a complete Context Package.

        Pipeline:
        1. Deduplicate
        2. Rank
        3. Compress
        4. Categorize
        5. Build sections
        6. Apply budget
        7. Resolve references
        8. Render Markdown

        Args:
            task: Developer request.
            results: Raw recall results from Cognee.
            repository_summary: Optional cached summary.
            datasets: Dataset names used.
            retrieval_time_ms: Time spent in Cognee recall (ms).

        Returns:
            Complete ContextPackage with metadata and Markdown.
        """
        start = time.monotonic()

        # Phase 1: Retrieval pipeline
        deduped = self._dedup.deduplicate(results)
        ranked = self._ranker.rank(deduped)
        compressed = self._compressor.compress(ranked)
        categories = self._categorizer.categorize(compressed)

        # Phase 2: Package assembly
        sections = self._build_sections(categories)
        budgeted = self._budget.apply(sections)
        references = self._resolver.resolve(compressed)

        # Phase 3: Render
        objective = task if len(task) <= 100 else task[:97] + "..."
        markdown = self._renderer.render(task, objective, budgeted, references, repository_summary)

        elapsed_ms = int((time.monotonic() - start) * 1000)

        metadata = PackageMetadata(
            package_version="1.0",
            repository_summary_version=repository_summary.version if repository_summary else "none",
            generated_at=datetime.now(timezone.utc).isoformat(),
            datasets_used=datasets,
            retrieved_memory_count=len(results),
            deduplicated_count=len(deduped),
            compressed_count=len(compressed),
            compression_ratio=self._budget.last_compression_ratio,
            estimated_tokens=len(markdown) // 4,
            pipeline_version="1.0",
            retrieval_time_ms=retrieval_time_ms,
            total_time_ms=elapsed_ms,
        )

        return ContextPackage(
            task=task,
            objective=objective,
            sections=budgeted,
            references=references,
            metadata=metadata,
            repository_summary=repository_summary,
            markdown=markdown,
            source_count=len(compressed),
            dataset=", ".join(datasets),
        )

    def _build_sections(
        self, categories: dict[str, list[RecallResult]]
    ) -> list[PackageSection]:
        """Convert categorized results into PackageSections.

        Args:
            categories: Section type to results mapping.

        Returns:
            List of PackageSection objects.
        """
        sections = []
        for section_type, results in categories.items():
            if not results:
                continue

            content = self._format_content(section_type, results)

            sections.append(PackageSection(
                section_type=section_type,
                heading=_HEADINGS.get(section_type, section_type.title()),
                content=content,
                priority=_PRIORITIES.get(section_type, 2),
                source_sections=["Component Context"],
                reference_count=len(results),
            ))

        return sections

    def _format_content(self, section_type: str, results: list[RecallResult]) -> str:
        """Format results for a specific section type with reasoning tags stripped.

        Args:
            section_type: Section type identifier.
            results: Results to format.

        Returns:
            Formatted content string.
        """
        if section_type == "files":
            return self._format_files(results)

        import re
        cleaned_lines = []
        for r in results:
            text = r.text.strip()
            # Strip <think>...</think> blocks from reasoning models
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
            if text:
                # If text already has markdown bullets/headings, preserve indentation
                if text.startswith(("-", "*", "#")):
                    cleaned_lines.append(text)
                else:
                    cleaned_lines.append(f"- {text}")
        return "\n\n".join(cleaned_lines) if any("\n" in l for l in cleaned_lines) else "\n".join(cleaned_lines)

    def _format_files(self, results: list[RecallResult]) -> str:
        """Format file results as a concise listing.

        Args:
            results: File results to format.

        Returns:
            Markdown bullet list of file paths.
        """
        lines = []
        for r in results:
            path = r.text.strip()
            if path:
                lines.append(f"- `{path}`")
        return "\n".join(lines)
