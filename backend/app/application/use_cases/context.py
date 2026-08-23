"""Context generation use cases for RE:Track.

Coordinates interactive Context Package assembly and external AI coding agent middleware.
All dependencies are explicitly injected via constructor capability ports.
"""

import asyncio
import logging
from pathlib import Path
import time
from typing import Any, Callable, Optional

from app.application.dto import (
    AgentContextRequest,
    AgentContextResponse,
    ContextResponse,
    ErrorResponse,
    GenerateContextRequest,
    SourceSearchResponse,
    SourceSearchResultItem,
)
from app.application.ports.cgc_service import CGCServicePort
from app.application.ports.context_cache import ContextCachePort
from app.application.ports.context_service import ContextServicePort
from app.application.ports.filesystem import FileSystemPort
from app.application.ports.indexing_service import IndexingServicePort
from app.application.ports.intent_parser import IntentParserPort
from app.application.ports.llm_provider import LLMProviderPort
from app.application.ports.memory import MemoryPort
from app.application.domain.dataset_identity import derive_dataset_name
from app.application.domain.intent import parse_intent_heuristics
from app.application.dto import (
    AgentContextRequest,
    AgentContextResponse,
    ContextResponse,
    ErrorResponse,
    GenerateContextRequest,
    SourceSearchResponse,
    SourceSearchResultItem,
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
from app.application.ports.workspace_authorization import WorkspaceAuthorizationPort
from app.models.errors import CogneeServiceError

logger = logging.getLogger(__name__)


class BoundedConcurrencyGuard:
    """Explicit bounded concurrency queue with timeout, queue limits, and cancellation support."""

    def __init__(self, max_concurrent: int = 1, max_queue: int = 5, timeout: float = 30.0) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._max_queue = max_queue
        self._timeout = timeout
        self._waiting_count = 0
        self._lock = asyncio.Lock()

    @property
    def waiting_count(self) -> int:
        return self._waiting_count

    async def acquire(self) -> tuple[bool, Optional[str]]:
        """Attempt to acquire execution slot within queue limit and timeout."""
        async with self._lock:
            if self._waiting_count >= self._max_queue:
                return False, "BusyError"
            self._waiting_count += 1

        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=self._timeout)
            return True, None
        except asyncio.TimeoutError:
            return False, "TimeoutError"
        except asyncio.CancelledError:
            raise
        finally:
            async with self._lock:
                self._waiting_count -= 1

    def release(self) -> None:
        """Release acquired execution slot."""
        self._semaphore.release()


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
        context_gen_lock: Optional[asyncio.Lock] = None,
        ensure_services_fn: Optional[Callable[[], None]] = None,
        source_search: Optional[SourceSearchPort] = None,
        filesystem: Optional[FileSystemPort] = None,
        workspace_auth: Optional[WorkspaceAuthorizationPort] = None,
        concurrency_guard: Optional[BoundedConcurrencyGuard] = None,
        max_concurrent: int = 1,
        max_queue: int = 5,
        queue_timeout: float = 30.0,
    ) -> None:
        self._context_service = context_service
        self._cognee_service = cognee_service
        self._indexing_service = indexing_service
        self._intent_parser = intent_parser
        self._llm_provider = llm_provider
        self._cgc_service = cgc_service
        self._summary_generator = summary_generator
        self._cache = context_cache
        self._ensure_services = ensure_services_fn or (lambda: None)
        self._source_search = source_search
        self._fs = filesystem
        self._workspace_auth = workspace_auth
        self._guard = concurrency_guard or BoundedConcurrencyGuard(
            max_concurrent=max_concurrent,
            max_queue=max_queue,
            timeout=queue_timeout,
        )

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
            if self._workspace_auth:
                is_auth, reason = self._workspace_auth.is_path_authorized(request.repository_path)
                if not is_auth:
                    return ErrorResponse(
                        error="AuthorizationError",
                        message=reason or f"Access denied to unauthorized repository path: {request.repository_path}",
                    )

            self._ensure_services()
            if self._indexing_service is None or self._cognee_service is None or self._context_service is None:
                raise CogneeServiceError("Backend services not initialized.")

            acquired, err = await self._guard.acquire()
            if not acquired:
                if err == "BusyError":
                    logger.warning("use_case: get_agent_context() rejected | queue full")
                    return ErrorResponse(
                        error="BusyError",
                        message="Context synthesis queue is full. Maximum concurrent requests reached. Please retry shortly.",
                    )
                elif err == "TimeoutError":
                    logger.warning("use_case: get_agent_context() timed out waiting for queue slot")
                    return ErrorResponse(
                        error="TimeoutError",
                        message="Context synthesis request timed out waiting for an execution slot.",
                    )
                return ErrorResponse(
                    error="ConcurrencyError",
                    message="Context synthesis execution slot unavailable. Please wait a moment.",
                )

            try:
                repo_path = Path(request.repository_path).resolve()
                dataset_name = derive_dataset_name(repo_path, request.dataset_name)
                target_tokens = request.max_tokens or 8000

                # 0. Check in-memory context synthesis cache (< 5ms hit)
                manifest_hash = ""
                try:
                    from app.services.manifest_service import ManifestService
                    m_svc = getattr(self._indexing_service, "_manifest_service", None) or ManifestService()
                    manifest_obj = m_svc.load_manifest(repo_path)
                    if manifest_obj:
                        manifest_hash = manifest_obj.repo_fingerprint
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
                    return parse_intent_heuristics(request.task_prompt)

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

                if not (structural_res and getattr(structural_res, "symbols_found", None)) and repo_summary:
                    structural_res = self._extract_ast_call_context(
                        repo_summary=repo_summary,
                        target_symbols=intent.extracted_symbols,
                        relevant_file_hints=list(intent.relevant_file_hints) + matched_file_rels[:4],
                    )
                retrieval_time_ms = int((time.perf_counter() - t_retrieval_start) * 1000)

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

                # Store in high-speed synthesis cache with dependency provenance
                ref_files = list(files_for_prompt) if "files_for_prompt" in locals() else []
                ref_symbols = list(intent.extracted_symbols) if "intent" in locals() and intent else []
                if "ast_context" in locals() and ast_context and hasattr(ast_context, "symbols_found"):
                    ref_symbols.extend(ast_context.symbols_found)

                self._cache.set(
                    cache_key,
                    response,
                    repo_path=str(repo_path),
                    referenced_files=ref_files,
                    referenced_symbols=ref_symbols,
                )
                return response
            finally:
                self._guard.release()

        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: get_agent_context() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Failed to generate agent context: {e}",
            )

    async def search_repository_code(
        self,
        repository_path: str,
        query: str,
        limit: int = 10,
    ) -> SourceSearchResponse | ErrorResponse:
        """Search repository code for matching symbols and keywords with relevance ranking."""
        start = time.monotonic()
        logger.info("use_case: search_repository_code() | path=%s | query=%s", repository_path, query[:50])
        try:
            if self._workspace_auth:
                is_auth, reason = self._workspace_auth.is_path_authorized(repository_path)
                if not is_auth:
                    return ErrorResponse(
                        error="AuthorizationError",
                        message=reason or f"Access denied to unauthorized repository path: {repository_path}",
                    )

            repo_path = Path(repository_path).resolve()
            if not repo_path.exists():
                return ErrorResponse(
                    error="ValidationError",
                    message=f"Repository path does not exist: {repository_path}",
                )
            if not repo_path.is_dir():
                return ErrorResponse(
                    error="ValidationError",
                    message=f"Repository path is not a directory: {repository_path}",
                )
            if not query.strip():
                return ErrorResponse(
                    error="ValidationError",
                    message="Search query must not be empty",
                )

            if self._indexing_service:
                raw_files = self._indexing_service.discover_files(repo_path)
                indexed_files = self._indexing_service.filter_files(raw_files, repo_path)
            else:
                repo_canon = repo_path.resolve()
                indexed_files = [
                    p for p in repo_path.rglob("*")
                    if p.is_file() and not p.name.startswith(".")
                    and p.resolve().is_relative_to(repo_canon)
                ]

            results: list[SourceSearchResultItem] = []
            if self._source_search:
                raw_results = self._source_search.search(
                    repo_path=repo_path,
                    indexed_files=indexed_files,
                    query=query,
                    limit=limit,
                )
                results = [
                    SourceSearchResultItem(
                        file_path=r["file_path"],
                        score=r["score"],
                        matched_symbols=r.get("matched_symbols", []),
                        snippet=r.get("snippet", ""),
                    )
                    for r in raw_results
                ]

            elapsed = time.monotonic() - start
            logger.info("use_case: search_repository_code() complete | results=%d | %.2fs", len(results), elapsed)

            return SourceSearchResponse(
                success=True,
                repository_path=str(repo_path),
                query=query,
                results=results,
                total_results=len(results),
            )
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: search_repository_code() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Failed to search repository code: {e}",
            )

    @staticmethod
    def _extract_ast_call_context(
        repo_summary: Any,
        target_symbols: list[str],
        relevant_file_hints: list[str] = (),
    ) -> Optional["_ASTStructuralContext"]:
        """Extract callers, callees, and structurally coupled files from in-memory AST call graph."""
        nodes = getattr(repo_summary, "call_graph_nodes", None)
        if not nodes:
            return None

        symbols_found: list[str] = []
        callers: list[str] = []
        callees: list[str] = []
        related_files: list[str] = []

        nodes_by_id = {n.id: n for n in nodes}
        nodes_by_label: dict[str, list[Any]] = {}
        for n in nodes:
            nodes_by_label.setdefault(n.label, []).append(n)
            nodes_by_label.setdefault(n.label.lower(), []).append(n)

        matched_nodes: list[Any] = []
        for s in target_symbols:
            s_low = s.lower()
            if s_low in nodes_by_label:
                for n in nodes_by_label[s_low]:
                    if n not in matched_nodes:
                        matched_nodes.append(n)
                        if n.label not in symbols_found:
                            symbols_found.append(n.label)

        for hint in relevant_file_hints:
            hint_clean = hint.lower().lstrip("./")
            for n in nodes:
                if getattr(n, "file", None) and (n.file.lower() == hint_clean or n.file.lower().endswith("/" + hint_clean)):
                    if n not in matched_nodes and len(matched_nodes) < 10:
                        matched_nodes.append(n)
                        if n.label not in symbols_found:
                            symbols_found.append(n.label)

        matched_node_ids = {n.id for n in matched_nodes}

        for n in matched_nodes:
            if getattr(n, "file", None) and n.file not in related_files:
                related_files.append(n.file)

        edges = getattr(repo_summary, "call_graph_edges", None)
        if edges:
            for edge in edges:
                if edge.target in matched_node_ids:
                    src_node = nodes_by_id.get(edge.source)
                    caller_label = src_node.label if src_node else edge.source
                    if caller_label not in callers:
                        callers.append(caller_label)
                    if src_node and getattr(src_node, "file", None) and src_node.file not in related_files:
                        related_files.append(src_node.file)

                if edge.source in matched_node_ids:
                    tgt_node = nodes_by_id.get(edge.target)
                    callee_label = tgt_node.label if tgt_node else edge.target
                    if callee_label not in callees:
                        callees.append(callee_label)
                    if tgt_node and getattr(tgt_node, "file", None) and tgt_node.file not in related_files:
                        related_files.append(tgt_node.file)

        if not symbols_found and not related_files:
            return None

        return _ASTStructuralContext(
            symbols_found=symbols_found[:12],
            callers=callers[:10],
            callees=callees[:10],
            related_files=related_files[:15],
        )


class _ASTStructuralContext:
    """Internal AST structural context container."""

    def __init__(
        self,
        symbols_found: list[str],
        callers: list[str],
        callees: list[str],
        related_files: list[str],
    ) -> None:
        self.symbols_found = symbols_found
        self.callers = callers
        self.callees = callees
        self.related_files = related_files

    def to_markdown(self) -> str:
        """Format structural AST relationships as compact Markdown."""
        lines = []
        if self.symbols_found:
            lines.append(f"**Identified AST Symbols**: {', '.join(f'`{s}`' for s in self.symbols_found)}")
        if self.callers:
            lines.append("\n**Callers (Upstream Invocations)**:")
            for c in self.callers[:10]:
                lines.append(f"- `{c}`")
        if self.callees:
            lines.append("\n**Callees (Downstream Invocations)**:")
            for c in self.callees[:10]:
                lines.append(f"- `{c}`")
        if self.related_files:
            lines.append("\n**Structurally Coupled Files**:")
            for f in self.related_files[:10]:
                lines.append(f"- `{f}`")
        return "\n".join(lines)
