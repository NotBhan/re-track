"""Context generation use cases for RE:Track.

Coordinates interactive Context Package assembly and external AI coding agent middleware.
All dependencies are explicitly injected via constructor.
"""

import asyncio
import logging
from pathlib import Path
import time
from typing import Callable, Optional

from app.application.dto import (
    AgentContextRequest,
    AgentContextResponse,
    ContextResponse,
    ErrorResponse,
    GenerateContextRequest,
)
from app.models.errors import CogneeServiceError
from app.services.cgc_service import CGCService
from app.services.cognee_service import CogneeService
from app.services.context_cache import ContextCacheEngine
from app.services.context_service import ContextService
from app.services.indexing_service import IndexingService
from app.services.intent_parser import IntentParserService
from app.services.llm_provider_service import LLMProviderService
from app.services.repository_summary import RepositorySummaryGenerator
from app.services.source_search_service import SourceSearchService

logger = logging.getLogger(__name__)


class ContextUseCases:
    """Orchestrates interactive and agent context package synthesis workflows."""

    def __init__(
        self,
        context_service: Optional[ContextService],
        cognee_service: Optional[CogneeService],
        indexing_service: Optional[IndexingService],
        intent_parser: Optional[IntentParserService],
        llm_provider: Optional[LLMProviderService],
        cgc_service: Optional[CGCService],
        summary_generator: RepositorySummaryGenerator,
        context_cache: ContextCacheEngine,
        context_gen_lock: asyncio.Lock,
        ensure_services_fn: Callable[[], None],
        source_search: Optional[SourceSearchService] = None,
    ) -> None:
        self._context_service = context_service
        self._cognee_service = cognee_service
        self._indexing_service = indexing_service
        self._intent_parser = intent_parser
        self._llm_provider = llm_provider
        self._cgc_service = cgc_service
        self._summary_generator = summary_generator
        self._cache = context_cache
        self._lock = context_gen_lock
        self._ensure_services = ensure_services_fn
        self._source_search = source_search or SourceSearchService()

    async def generate_context(
        self,
        request: GenerateContextRequest,
    ) -> ContextResponse | ErrorResponse:
        """Generate a Context Package for a developer task.

        Validates query is non-empty, datasets are provided,
        then delegates to ContextService.
        """
        start = time.monotonic()
        logger.info(
            "use_case: generate_context() | task=%s | datasets=%s | top_k=%d",
            request.task[:80],
            request.datasets,
            request.top_k,
        )

        try:
            self._ensure_services()
            if self._context_service is None:
                raise CogneeServiceError("ContextService is not initialized.")

            if not request.task.strip():
                raise ValueError("Task must not be empty")
            if not request.datasets:
                raise ValueError("at least one dataset must be provided")

            package = await self._context_service.generate_context_package(
                task=request.task,
                datasets=request.datasets,
                top_k=request.top_k or 20,
            )

            response = ContextResponse(
                success=True,
                task=package.task,
                objective=package.objective,
                markdown=package.markdown,
                section_count=package.section_count,
                source_count=package.source_count,
                token_estimate=package.token_estimate,
                dataset=package.dataset,
                retrieved_memories=package.metadata.retrieved_memory_count if package.metadata else 0,
                deduplicated_memories=package.metadata.deduplicated_count if package.metadata else 0,
                compressed_memories=package.metadata.compressed_count if package.metadata else 0,
                compression_ratio=package.metadata.compression_ratio if package.metadata else 1.0,
                retrieval_time_ms=package.metadata.retrieval_time_ms if package.metadata else 0,
                total_time_ms=package.metadata.total_time_ms if package.metadata else 0,
                reference_count=len(package.references),
                section_headings=[s.heading for s in package.sections],
            )

            elapsed = time.monotonic() - start
            logger.info(
                "use_case: generate_context() complete | sources=%d | ~%d tokens | %.2fs",
                package.source_count,
                package.token_estimate,
                elapsed,
            )
            return response

        except ValueError as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: generate_context() validation error | %.2fs | %s", elapsed, e)
            raise
        except CogneeServiceError as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: generate_context() service error | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Context generation failed: {e}",
            )
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: generate_context() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Context generation failed: {e}",
            )

    async def get_agent_context(
        self,
        request: AgentContextRequest,
    ) -> AgentContextResponse | ErrorResponse:
        """Generate an optimized context package for an external coding agent.

        Parses intent, retrieves structural code graphs via CGC, fetches semantic
        memory via Cognee, and builds a compact Markdown Context Package.
        """
        start = time.monotonic()
        logger.info("use_case: get_agent_context() | prompt=%s", request.task_prompt[:80])

        try:
            self._ensure_services()
            if self._indexing_service is None or self._cognee_service is None or self._context_service is None:
                raise CogneeServiceError("Backend services not initialized.")

            if self._lock.locked():
                logger.warning("use_case: get_agent_context() rejected | synthesis already in progress")
                return ErrorResponse(
                    error="ConcurrencyError",
                    message="Context synthesis is already running for a task. Please wait a moment.",
                )

            async with self._lock:
                repo_path = Path(request.repository_path).resolve()
                dataset_name = request.dataset_name or repo_path.name
                target_tokens = request.max_tokens or 8000

                # 0. Check in-memory context synthesis cache (< 5ms hit)
                manifest_hash = ""
                manifest_file = repo_path / ".andes" / "manifest.json"
                if manifest_file.exists():
                    try:
                        manifest_hash = str(manifest_file.stat().st_mtime)
                    except Exception:
                        pass

                cache_key = self._cache.make_key(
                    repo_path=str(repo_path),
                    manifest_hash=manifest_hash,
                    task_prompt=request.task_prompt,
                    max_tokens=target_tokens,
                )
                cached_resp = self._cache.get(cache_key)
                if cached_resp is not None and isinstance(cached_resp, AgentContextResponse):
                    logger.info(
                        "use_case: get_agent_context() [CACHE HIT] | prompt=%s | %.1fms",
                        request.task_prompt[:50],
                        (time.monotonic() - start) * 1000,
                    )
                    return cached_resp

                # 1. Parallel Step: Parse intent + generate repo summary + check provider health
                async def _get_intent():
                    if self._intent_parser:
                        return await self._intent_parser.parse_intent(request.task_prompt)
                    from app.services.intent_parser import IntentParserService
                    return IntentParserService.rule_based_fallback(request.task_prompt)

                async def _get_repo_summary():
                    raw_files = self._indexing_service.discover_files(repo_path)
                    indexed = self._indexing_service.filter_files(raw_files, repo_path)
                    summary = self._summary_generator.generate(repo_path, indexed)
                    return indexed, summary

                async def _get_provider_health():
                    if self._llm_provider:
                        try:
                            return await self._llm_provider.check_health()
                        except Exception:
                            return None
                    return None

                intent, (indexed_files, repo_summary), health_status = await asyncio.gather(
                    _get_intent(),
                    _get_repo_summary(),
                    _get_provider_health(),
                )

                # 2. Parallel Step: CGC Structural Query + Cognee Context Synthesis (Retrieval Stage)
                t_retrieval_start = time.perf_counter()

                async def _query_cgc():
                    if request.include_structural_graph and self._cgc_service:
                        try:
                            return await self._cgc_service.query_structural_context(
                                repo_path=repo_path,
                                target_symbols=intent.extracted_symbols,
                            )
                        except Exception as e:
                            logger.warning("CGC query warning: %s", e)
                            return None
                    return None

                async def _generate_package():
                    return await self._context_service.generate_context_package(
                        task=request.task_prompt,
                        datasets=[dataset_name],
                        top_k=15,
                        repository_summary=repo_summary,
                        target_tokens=target_tokens,
                    )

                structural_res, package = await asyncio.gather(
                    _query_cgc(),
                    _generate_package(),
                )
                retrieval_time_ms = int((time.perf_counter() - t_retrieval_start) * 1000)

                # 3. Direct AST & symbol relevance search across repository files (Ranking Stage)
                t_rank_start = time.perf_counter()
                search_terms = self._source_search.build_search_terms(
                    task_prompt=request.task_prompt,
                    extracted_symbols=intent.extracted_symbols,
                    relevant_file_hints=intent.relevant_file_hints,
                )
                relevant_snippets, matched_file_rels = self._source_search.extract_relevant_snippets(
                    repo_path=repo_path,
                    indexed_files=indexed_files,
                    search_terms=search_terms,
                )
                ranking_time_ms = int((time.perf_counter() - t_rank_start) * 1000)

                # 4. Merge snippets and structural graph into Markdown output (Synthesis Stage)
                t_synth_start = time.perf_counter()
                quant_warning = health_status.quantization_warning if health_status else None

                final_markdown = package.markdown
                if relevant_snippets:
                    final_markdown += "\n\n---\n\n# Relevant Code Snippets & Target Implementations\n\n" + "\n\n".join(relevant_snippets)

                if structural_res and structural_res.symbols_found:
                    struct_md = structural_res.to_markdown()
                    if struct_md:
                        final_markdown += f"\n\n---\n\n# Structural Code Relationships\n\n{struct_md}\n"

                synthesis_time_ms = int((time.perf_counter() - t_synth_start) * 1000)
                elapsed_ms = int((time.monotonic() - start) * 1000)

                all_related = list(dict.fromkeys(
                    matched_file_rels + (structural_res.related_files if structural_res else [])
                ))

                response = AgentContextResponse(
                    success=True,
                    context_markdown=final_markdown,
                    task_summary=intent.task_summary,
                    intent_category=intent.category,
                    extracted_symbols=intent.extracted_symbols,
                    callers=structural_res.callers if structural_res else [],
                    callees=structural_res.callees if structural_res else [],
                    related_files=all_related,
                    quantization_warning=quant_warning,
                    estimated_tokens=len(final_markdown) // 4,
                    generation_time_ms=elapsed_ms,
                    retrieval_time_ms=retrieval_time_ms,
                    ranking_time_ms=ranking_time_ms,
                    synthesis_time_ms=synthesis_time_ms,
                    total_time_ms=elapsed_ms,
                )

                # Store in high-speed synthesis cache
                self._cache.set(cache_key, response, repo_path=str(repo_path))
                return response

        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: get_agent_context() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Failed to generate agent context: {e}",
            )
