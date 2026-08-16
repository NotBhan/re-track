"""Context Package synthesis service for RE:Track."""

import logging
import time

from app.models.responses import ContextPackage, RepositorySummary
from app.services.cognee_service import CogneeService
from app.services.package_builder import PackageBuilder

logger = logging.getLogger(__name__)


class ContextService:
    """Retrieves memories and delegates context package assembly."""

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

        # Measure recall time separately from package building
        recall_start = time.monotonic()
        try:
            recall = await self._cognee.recall(
                query_text=task,
                datasets=datasets,
                top_k=top_k,
            )
            recall_results = recall.results
        except Exception as e:
            logger.warning("Cognee recall fallback to local summary: %s", e)
            recall_results = []
        retrieval_ms = int((time.monotonic() - recall_start) * 1000)

        package = self._builder.build(
            task=task,
            results=recall_results,
            repository_summary=self._repository_summary,
            datasets=datasets,
            retrieval_time_ms=retrieval_ms,
        )

        logger.info(
            "context package generated | sections=%d | sources=%d | ~%d tokens | recall=%dms",
            package.section_count,
            package.source_count,
            package.token_estimate,
            retrieval_ms,
        )

        return package
