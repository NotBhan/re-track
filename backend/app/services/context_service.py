"""
Context Package generator for AndesContext.

Transforms Cognee memory retrieval into structured Context Packages
suitable for AI coding assistants.

Pipeline:
    Developer Request
        → CogneeService.recall()
        → PackageBuilder (dedup → rank → compress → categorize → budget → render)
        → ContextPackage

No LLM calls. No prompt execution. No autonomous agents.
Only memory retrieval and deterministic package generation.
"""

import logging

from app.models.responses import ContextPackage, RepositorySummary
from app.services.cognee_service import CogneeService
from app.services.package_builder import PackageBuilder

logger = logging.getLogger(__name__)


class ContextService:
    """Generates structured Context Packages from Cognee memory.

    Orchestrates memory retrieval via CogneeService and delegates
    package assembly to PackageBuilder.
    """

    def __init__(
        self,
        cognee_service: CogneeService,
        repository_summary: RepositorySummary | None = None,
        target_tokens: int = 3000,
    ) -> None:
        """Initialize the context service.

        Args:
            cognee_service: Cognee memory service.
            repository_summary: Optional cached repository summary.
            target_tokens: Target token count for budget enforcement.
        """
        self._cognee = cognee_service
        self._repository_summary = repository_summary
        self._builder = PackageBuilder(target_tokens)

    async def generate_context_package(
        self,
        task: str,
        datasets: list[str],
        top_k: int = 20,
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

        recall = await self._cognee.recall(
            query_text=task,
            datasets=datasets,
            top_k=top_k,
        )

        package = self._builder.build(
            task=task,
            results=recall.results,
            repository_summary=self._repository_summary,
            datasets=datasets,
        )

        logger.info(
            "context package generated | sections=%d | sources=%d | ~%d tokens",
            package.section_count,
            package.source_count,
            package.token_estimate,
        )

        return package
