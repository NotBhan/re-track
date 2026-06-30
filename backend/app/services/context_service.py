"""
Context Package generator for AndesContext.

Transforms Cognee memory retrieval into structured Markdown
Context Packages suitable for AI coding assistants.

Pipeline:
    Developer Request
        → CogneeService.recall()
        → Collect Retrieved Memories
        → Remove Duplicates
        → Rank Relevance
        → Group by Category
        → Generate Markdown Context Package
        → Return Result

No LLM calls. No prompt execution. No autonomous agents.
Only memory retrieval and deterministic Markdown generation.
"""

import logging
import re
from typing import Optional

from app.models.errors import CogneeServiceError
from app.models.responses import (
    ContextPackage,
    PackageSection,
    RecallResult,
    RecallResponse,
    SectionType,
)
from app.services.cognee_service import CogneeService

logger = logging.getLogger(__name__)

# File extension patterns for categorization
_CODE_EXTENSIONS = frozenset(
    {".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".yaml", ".yml", ".toml"}
)

# Keyword sets for categorization
_ARCHITECTURE_KEYWORDS = frozenset(
    {
        "architecture",
        "design",
        "pattern",
        "structure",
        "layer",
        "module",
        "component",
        "service",
        "pipeline",
        "workflow",
        "system",
        "infrastructure",
        "deployment",
        "microservice",
        "monolith",
    }
)

_API_KEYWORDS = frozenset(
    {
        "api",
        "endpoint",
        "route",
        "interface",
        "contract",
        "schema",
        "request",
        "response",
        "http",
        "rest",
        "graphql",
        "grpc",
        "rpc",
        "webhook",
    }
)

_CONVENTION_KEYWORDS = frozenset(
    {
        "convention",
        "style",
        "format",
        "linting",
        "naming",
        "indentation",
        "standard",
        "guideline",
        "practice",
        "pattern",
        "boilerplate",
        "template",
    }
)

_DECISION_KEYWORDS = frozenset(
    {
        "decision",
        "rationale",
        "tradeoff",
        "trade-off",
        "chosen",
        "selected",
        "alternative",
        "rejected",
        "adr",
        "why we",
        "reason for",
    }
)


class ContextService:
    """Generates structured Markdown Context Packages from Cognee memory.

    Orchestrates memory retrieval via CogneeService and produces
    deterministic Markdown output without LLM calls.
    """

    def __init__(self, cognee_service: CogneeService) -> None:
        self._cognee = cognee_service

    async def generate_context_package(
        self,
        task: str,
        datasets: list[str],
        top_k: int = 15,
    ) -> ContextPackage:
        """Generate a Context Package for a developer task.

        Args:
            task: The developer request or question.
            datasets: Dataset names to search.
            top_k: Maximum memories to retrieve.

        Returns:
            ContextPackage with structured Markdown content.
        """
        logger.info(
            "generate_context_package | task=%s | datasets=%s | top_k=%d",
            task[:80],
            datasets,
            top_k,
        )

        # 1. Retrieve memories
        recall = await self.retrieve_memory(task, datasets, top_k)

        # 2. Deduplicate
        unique = self.remove_duplicates(recall.results)

        # 3. Rank
        ranked = self.rank_results(unique)

        # 4. Categorize into sections
        sections = self._categorize(ranked)

        # 5. Build markdown
        markdown = self.build_markdown(task, sections)

        package = ContextPackage(
            task=task,
            objective=task,
            markdown=markdown,
            sections=sections,
            source_count=len(ranked),
            dataset=", ".join(datasets),
        )

        logger.info(
            "context package generated | sections=%d | sources=%d | ~%d tokens",
            package.section_count,
            package.source_count,
            package.token_estimate,
        )

        return package

    async def retrieve_memory(
        self,
        task: str,
        datasets: list[str],
        top_k: int = 15,
    ) -> RecallResponse:
        """Retrieve memories relevant to the task.

        Args:
            task: The developer request.
            datasets: Dataset names to search.
            top_k: Maximum results.

        Returns:
            RecallResponse from CogneeService.
        """
        return await self._cognee.recall(
            query_text=task,
            datasets=datasets,
            top_k=top_k,
        )

    def remove_duplicates(
        self,
        results: list[RecallResult],
    ) -> list[RecallResult]:
        """Remove duplicate memories based on text similarity.

        Keeps the first occurrence (highest score from Cognee).
        Uses normalized text comparison for deduplication.
        """
        seen: set[str] = set()
        unique: list[RecallResult] = []
        for r in results:
            key = self._normalize_text(r.text)
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return unique

    def rank_results(
        self,
        results: list[RecallResult],
    ) -> list[RecallResult]:
        """Rank results by relevance score.

        Cognee returns results ordered by relevance. This method
        preserves that order and applies secondary sorting by score.
        If Cognee does not provide ranking metadata, retrieval order
        is preserved.
        """
        return sorted(results, key=lambda r: r.score, reverse=True)

    def build_markdown(
        self,
        task: str,
        sections: list[PackageSection],
    ) -> str:
        """Generate clean Markdown from task and sections.

        Args:
            task: The original developer request.
            sections: Categorized memory sections.

        Returns:
            Formatted Markdown string.
        """
        parts: list[str] = []

        # Task section is always first
        parts.append(f"# Task\n\n{task}")

        # Add each non-empty section
        for section in sections:
            if section.content.strip():
                parts.append(f"# {section.heading}\n\n{section.content}")

        return "\n\n---\n\n".join(parts)

    def _categorize(
        self,
        results: list[RecallResult],
    ) -> list[PackageSection]:
        """Categorize results into package sections.

        Uses keyword matching and file extension detection
        to assign each result to a section category.
        """
        categorized: dict[SectionType, list[str]] = {st: [] for st in SectionType}

        for r in results:
            text = r.text.strip()
            if not text:
                continue

            section = self._classify_memory(r)
            categorized[section].append(text)

        sections: list[PackageSection] = []
        heading_map = {
            SectionType.OVERVIEW: "Repository Overview",
            SectionType.FILES: "Relevant Files",
            SectionType.KNOWLEDGE: "Relevant Knowledge",
            SectionType.ARCHITECTURE: "Architecture Notes",
            SectionType.APIS: "Existing APIs",
            SectionType.CONVENTIONS: "Coding Conventions",
            SectionType.DECISIONS: "Previous Decisions",
            SectionType.REFERENCES: "References",
        }

        for st in SectionType:
            if st == SectionType.TASK:
                continue
            items = categorized[st]
            if not items:
                continue
            content = self._format_section(st, items)
            sections.append(
                PackageSection(
                    section_type=st,
                    heading=heading_map.get(st, st.value.title()),
                    content=content,
                )
            )

        return sections

    def _classify_memory(self, result: RecallResult) -> SectionType:
        """Classify a single memory result into a section type."""
        text_lower = result.text.lower()
        kind = result.kind.lower() if result.kind else ""

        # File references
        if kind == "file" or any(
            text_lower.endswith(ext) for ext in _CODE_EXTENSIONS
        ):
            return SectionType.FILES

        # Architecture
        if self._matches_keywords(text_lower, _ARCHITECTURE_KEYWORDS):
            return SectionType.ARCHITECTURE

        # APIs
        if self._matches_keywords(text_lower, _API_KEYWORDS):
            return SectionType.APIS

        # Conventions
        if self._matches_keywords(text_lower, _CONVENTION_KEYWORDS):
            return SectionType.CONVENTIONS

        # Decisions
        if self._matches_keywords(text_lower, _DECISION_KEYWORDS):
            return SectionType.DECISIONS

        # Default to knowledge
        return SectionType.KNOWLEDGE

    def _matches_keywords(self, text: str, keywords: frozenset[str]) -> bool:
        """Check if text contains any of the given keywords."""
        return any(kw in text for kw in keywords)

    def _format_section(self, section_type: SectionType, items: list[str]) -> str:
        """Format items for a specific section type."""
        if section_type == SectionType.FILES:
            return self._format_file_list(items)
        if section_type == SectionType.REFERENCES:
            return self._format_references(items)
        return self._format_bullet_list(items)

    def _format_file_list(self, items: list[str]) -> str:
        """Format as a concise file listing."""
        lines: list[str] = []
        for item in items:
            # Extract file path if present
            path = self._extract_path(item)
            if path:
                lines.append(f"- `{path}`")
            else:
                lines.append(f"- {item}")
        return "\n".join(lines)

    def _format_bullet_list(self, items: list[str]) -> str:
        """Format as a bullet list."""
        return "\n".join(f"- {item}" for item in items)

    def _format_references(self, items: list[str]) -> str:
        """Format as numbered references."""
        return "\n".join(f"{i}. {item}" for i, item in enumerate(items, 1))

    def _extract_path(self, text: str) -> Optional[str]:
        """Try to extract a file path from memory text."""
        # Look for common path patterns
        match = re.search(r"([/\w.-]+\.\w+)", text)
        return match.group(1) if match else None

    def _normalize_text(self, text: str) -> str:
        """Normalize text for deduplication comparison."""
        return " ".join(text.lower().split())
