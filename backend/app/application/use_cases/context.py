"""Context generation use cases for RE:Track.

Coordinates interactive Context Package assembly and external AI coding agent middleware.
All dependencies are explicitly injected via constructor capability ports.
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
from app.application.ports.cgc_service import CGCServicePort
from app.application.ports.context_cache import ContextCachePort
from app.application.ports.context_service import ContextServicePort
from app.application.ports.filesystem import FileSystemPort
from app.application.ports.indexing_service import IndexingServicePort
from app.application.ports.intent_parser import IntentParserPort
from app.application.ports.llm_provider import LLMProviderPort
from app.application.ports.memory import MemoryPort
from app.application.ports.source_search import SourceSearchPort
from app.application.ports.summary_generator import SummaryGeneratorPort
from app.models.errors import CogneeServiceError

logger = logging.getLogger(__name__)


def _rule_based_fallback_intent(prompt: str):
    """Fast, LLM-free rule-based intent parser for zero-hallucination fallback."""
    from pydantic import BaseModel, Field

    class _FallbackIntent(BaseModel):
        task_summary: str
        category: str = "general"
        extracted_symbols: list[str] = Field(default_factory=list)
        relevant_file_hints: list[str] = Field(default_factory=list)
        is_vague: bool = False

    lowered = prompt.lower()
    category = "general"
    if any(w in lowered for w in ["fix", "bug", "error", "issue", "fail", "crash"]):
        category = "bug_fix"
    elif any(w in lowered for w in ["add", "create", "implement", "build", "new"]):
        category = "feature_addition"
    elif any(w in lowered for w in ["refactor", "clean", "structure", "rename", "move"]):
        category = "refactoring"

    # Extract symbols with backticks or identifiers
    import re
    backticked = re.findall(r"`([a-zA-Z_][a-zA-Z0-9_\.]*)`", prompt)
    hints = re.findall(r"([a-zA-Z0-9_\-\./]+\.[a-zA-Z0-9]+)", prompt)

    return _FallbackIntent(
        task_summary=prompt.strip().split("\n")[0][:120],
        category=category,
        extracted_symbols=list(dict.fromkeys(backticked)),
        relevant_file_hints=list(dict.fromkeys(hints)),
        is_vague=len(prompt.split()) < 5,
    )


class ContextUseCases:
    """Orchestrates interactive and agent context package synthesis workflows."""

    def __init__(
        self,
        context_service: Optional[ContextServicePort],
        cognee_service: Optional[MemoryPort],
        indexing_service: Optional[IndexingServicePort],
        intent_parser: Optional[IntentParserPort],
        llm_provider: Optional[LLMProviderPort],
        cgc_service: Optional[CGCServicePort],
        summary_generator: SummaryGeneratorPort,
        context_cache: ContextCachePort,
        context_gen_lock: asyncio.Lock,
        ensure_services_fn: Callable[[], None],
        source_search: Optional[SourceSearchPort] = None,
        filesystem: Optional[FileSystemPort] = None,
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
        self._source_search = source_search
        self._fs = filesystem

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

            meta = getattr(package, "metadata", None)
            retrieved = getattr(meta, "retrieved_memory_count", 0) if meta else 0
            deduped = getattr(meta, "deduplicated_count", 0) if meta else 0
            compressed = getattr(meta, "compressed_count", 0) if meta else 0
            ratio = getattr(meta, "compression_ratio", 1.0) if meta else 1.0
            retrieval_ms = getattr(meta, "retrieval_time_ms", 0) if meta else 0
            total_ms = getattr(meta, "total_time_ms", 0) if meta else int((time.monotonic() - start) * 1000)
            sections = getattr(package, "sections", []) or []
            headings = [s.heading for s in sections if hasattr(s, "heading")]
            references = getattr(package, "references", []) or []

            response = ContextResponse(
                success=True,
                task=getattr(package, "task", request.task),
                objective=getattr(package, "objective", ""),
                markdown=getattr(package, "markdown", ""),
                section_count=getattr(package, "section_count", len(sections)),
                source_count=getattr(package, "source_count", 0),
                token_estimate=getattr(package, "token_estimate", len(getattr(package, "markdown", "")) // 4),
                dataset=getattr(package, "dataset", ", ".join(request.datasets)),
                retrieved_memories=retrieved,
                deduplicated_memories=deduped,
                compressed_memories=compressed,
                compression_ratio=ratio,
                retrieval_time_ms=retrieval_ms,
                total_time_ms=total_ms,
                reference_count=len(references),
                section_headings=headings,
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
        """Generate compact, high-precision context for external AI coding agents.

        Parses prompt intent, checks file relevance, synthesizes semantic
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
                if self._fs and self._fs.exists(manifest_file):
                    try:
                        manifest_hash = str(self._fs.get_mtime(manifest_file))
                    except Exception:
                        pass
                elif manifest_file.exists():
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
                    return _rule_based_fallback_intent(request.task_prompt)

                async def _get_repo_summary():
                    raw_files = self._indexing_service.discover_files(repo_path)
                    indexed = self._indexing_service.filter_files(raw_files, repo_path)
                    summary = await self._summary_generator.generate(repo_path, indexed) if asyncio.iscoroutinefunction(self._summary_generator.generate) else self._summary_generator.generate(repo_path, indexed)
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
                relevant_snippets = []
                matched_file_rels = []
                if self._source_search:
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
