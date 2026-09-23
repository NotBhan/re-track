"""Context Package synthesis service for RE:Track."""

from dataclasses import replace
import logging
import time

from app.models.responses import ContextPackage, RepositorySummary
from app.services.cognee_service import CogneeService, default_recall_query_type
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
        repository_summary: RepositorySummary | None = None,
        target_tokens: int | None = None,
    ) -> ContextPackage:
        """Generate a Context Package for a developer task.

        Args:
            task: The developer request or question.
            datasets: Dataset names to search.
            top_k: Maximum memories to retrieve.
            repository_summary: Optional repository summary override.
            target_tokens: Optional target token count override.

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
        retrieval_state = "ok"
        retrieval_error: str | None = None
        recall_results = []
        try:
            recall = await self._cognee.recall(
                query_text=task,
                datasets=datasets,
                top_k=top_k,
                # Deterministic retrieval mode: vector/chunk retrieval only. The
                # automatic Cognee query router is disabled so a retrieval operation
                # cannot silently select an LLM-backed strategy.
                query_type=default_recall_query_type(),
                auto_route=False,
            )
            recall_results = recall.results
        except Exception as e:
            # Retrieval failure is reported as a degraded state, never as an empty
            # success. Authoritative tiers (source + AST) still populate the package.
            retrieval_state = "unavailable"
            retrieval_error = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
            logger.warning(
                "Cognee retrieval unavailable (state=%s): %s", retrieval_state, retrieval_error
            )
        retrieval_ms = int((time.monotonic() - recall_start) * 1000)

        builder = PackageBuilder(target_tokens) if target_tokens is not None else self._builder
        effective_summary = repository_summary if repository_summary is not None else self._repository_summary

        package = builder.build(
            task=task,
            results=recall_results,
            repository_summary=effective_summary,
            datasets=datasets,
            retrieval_time_ms=retrieval_ms,
        )

        if package.metadata is not None and (
            package.metadata.retrieval_state != retrieval_state
            or package.metadata.retrieval_error != retrieval_error
        ):
            # ContextPackage/PackageMetadata are frozen dataclasses.
            package = replace(
                package,
                metadata=replace(
                    package.metadata,
                    retrieval_state=retrieval_state,
                    retrieval_error=retrieval_error,
                ),
            )

        logger.info(
            "context package generated | sections=%d | sources=%d | ~%d tokens | recall=%dms | retrieval_state=%s",
            package.section_count,
            package.source_count,
            package.token_estimate,
            retrieval_ms,
            retrieval_state,
        )

        return package
