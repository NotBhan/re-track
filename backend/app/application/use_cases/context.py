"""Context generation use cases for RE:Track.

Coordinates interactive Context Package assembly and external AI coding agent middleware.
All dependencies are explicitly injected via constructor capability ports.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import functools
import logging
import os
from pathlib import Path
import re
import threading
import time
from typing import Any, Callable, Optional, Sequence

from app.application.domain.arbitration import ArbitratedCandidate, AuthorityTier
from app.application.domain.dataset_identity import derive_dataset_name
from app.application.domain.evidence import EvidenceRecord, EvidenceState
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
from app.application.ports.memory import MemoryPort, SemanticMemoryRepositoryPort
from app.application.ports.source_search import SourceSearchPort
from app.application.ports.summary_generator import SummaryGeneratorPort
from app.application.ports.workspace_authorization import WorkspaceAuthorizationPort
from app.core.logging import log_event
from app.models.errors import CogneeServiceError
from app.services.context_compactor import ContextCompactor, derive_task_terms
from app.services.evidence_service import EvidenceService
from app.services.retrieval_arbitrator import RetrievalArbitrator
from app.services.token_budget import estimate_tokens, plan_context_budget

logger = logging.getLogger(__name__)

#: Sentinel returned when the client disconnected and work was cancelled.
_CLIENT_DISCONNECTED = object()

#: Fixed synthesis instructions. These are the model-side half of the context
#: budget: their token cost is measured (never guessed) and reserved before any
#: repository evidence is packed, so a budget claim always covers the whole
#: request rather than just the repository slice.
_SYNTH_SYSTEM_PROMPT = (
    "You are an expert repository-intelligence coding assistant. "
    "Your mission is to synthesize high-precision, task-specific context answering the developer's exact request.\n"
    "STRICT GROUNDING RULES:\n"
    "1. Rely ONLY on the authoritative repository evidence, source snippets, and AST symbols provided below.\n"
    "2. Answer the developer's specific task directly. Do NOT merely summarize the whole repository.\n"
    "3. Identify the exact files, entry points, and functions/classes that must be inspected or modified.\n"
    "4. Explain the call flow and interactions between the identified components.\n"
    "5. If any dependencies or evidence are missing or uncertain, explicitly state what is missing."
)

_SYNTH_OUTPUT_FORMAT = (
    "## Required Output Format\n"
    "Synthesize structured context for this task:\n"
    "1. **Task Analysis & Entry Points**: Direct answer to the task and where execution begins.\n"
    "2. **Key Components & Functions**: Relevant symbols, their roles, and callers/callees.\n"
    "3. **Proposed Action / Modifications**: Specific functions/classes to inspect, modify, or add.\n"
    "4. **Architectural Constraints & Observations**: Edge cases, missing evidence, or potential pitfalls."
)

# Repository walking, AST parsing and snippet extraction are synchronous CPU/IO work.
# They are offloaded so the event loop (and therefore concurrent IPC such as health
# polling) stays responsive. The pool is explicitly bounded and process-owned:
# `asyncio.to_thread` would instead grow the loop's default executor to
# min(32, cpu_count + 4) threads and retain them for the process lifetime.
_OFFLOAD_MAX_WORKERS = 2
_offload_executor: Optional[ThreadPoolExecutor] = None
_offload_executor_lock = threading.Lock()


def get_offload_executor() -> ThreadPoolExecutor:
    """Return the bounded, lazily created executor used for blocking repository work."""
    global _offload_executor
    if _offload_executor is None:
        with _offload_executor_lock:
            if _offload_executor is None:
                _offload_executor = ThreadPoolExecutor(
                    max_workers=_OFFLOAD_MAX_WORKERS,
                    thread_name_prefix="retrack-offload",
                )
    return _offload_executor


def shutdown_offload_executor() -> None:
    """Release offload worker threads (called from composition-root shutdown)."""
    global _offload_executor
    with _offload_executor_lock:
        executor, _offload_executor = _offload_executor, None
    if executor is not None:
        executor.shutdown(wait=False)


async def run_offloaded(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Run synchronous work on the bounded offload pool without blocking the loop."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(get_offload_executor(), functools.partial(fn, *args, **kwargs))


def build_synthesis_user_prompt(
    task_prompt: str,
    task_summary: str,
    category: str,
    target_entities: Sequence[str],
    symbols: Sequence[str],
    evidence_text: str,
    include_task: bool = True,
) -> str:
    """Build the synthesis user prompt.

    The same builder produces the prompt sent to the model and the prompt used to
    measure the fixed prompt overhead, so the budget accounting cannot drift from
    what is actually requested.

    ``include_task=False`` omits the verbatim developer task. Budget planning uses
    that form to measure the *fixed* scaffolding, because the task prompt is
    accounted for separately as ``task_prompt_tokens``. Measuring the scaffold
    with the task included would count the task twice and silently shrink the
    repository-evidence allowance by the size of the task prompt.
    """
    task_block = f"# Developer Task\n{task_prompt}\n\n" if include_task else ""
    return (
        f"{task_block}"
        f"## Intent Understanding\n"
        f"- Objective: {task_summary}\n"
        f"- Category: {category}\n"
        f"- Target Entities: {', '.join(target_entities) or 'General'}\n"
        f"- Identified Symbols: {', '.join(symbols) or 'None'}\n\n"
        f"## Authoritative Repository Evidence\n{evidence_text}\n\n"
        f"{_SYNTH_OUTPUT_FORMAT}"
    )


#: Renderer separates package parts with this delimiter.
_PACKAGE_DELIMITER = "\n\n---\n\n"
_TASK_SECTION_RE = re.compile(r"^#\s+(Task|Objective)\b", re.IGNORECASE)


def build_derived_recall_candidate(package: Any) -> list[ArbitratedCandidate]:
    """Adapt the deterministic recall package into the lowest-authority evidence tier.

    The package's rendered markdown is derived retrieval (Cognee recall → dedup →
    rank → compress → render), so it belongs below every source, AST and validated
    memory candidate. Modelling it as a candidate — instead of appending it after
    the budget — means it is reduced or dropped first when the budget is tight, and
    the task/objective preamble (already reproduced at the top of the package and
    in the model prompt) is not duplicated inside the evidence.
    """
    markdown = str(getattr(package, "markdown", "") or "").strip()
    if not markdown:
        return []
    blocks = [block.strip() for block in markdown.split(_PACKAGE_DELIMITER)]
    kept = [block for block in blocks if block and not _TASK_SECTION_RE.match(block)]
    body = "\n\n".join(kept).strip()
    if len(body) < 20:
        return []
    return [
        ArbitratedCandidate(
            id="recall:package",
            tier=AuthorityTier.TIER_4_COGNEE,
            content=body,
            source_file="",
            relationship_kind="recall_package",
            relevance=0.3,
            confidence=0.5,
            specificity=0.4,
            is_valid=True,
            token_estimate=max(1, len(body) // 4),
        )
    ]


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
        """Attempt to acquire execution slot within queue limit and timeout.

        If this returns ``(True, None)`` the caller owns the slot until ``release()``.
        There is no suspension point between a successful acquisition and that
        return, so a cancelled or disconnected waiter can never strand a slot: a
        cancelled waiter either never acquired it, or is unwound through the
        caller's own ``finally`` block which releases it.
        """
        async with self._lock:
            if self._waiting_count >= self._max_queue:
                return False, "BusyError"
            self._waiting_count += 1

        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=self._timeout)
        except asyncio.TimeoutError:
            return False, "TimeoutError"
        finally:
            self._waiting_count -= 1

        return True, None

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
        semantic_memory_repository: Optional[SemanticMemoryRepositoryPort] = None,
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
        self._semantic_memory_repository = semantic_memory_repository
        self._last_tier3_telemetry: dict[str, Any] = {}
        self._compactor = ContextCompactor()
        self._guard = concurrency_guard or BoundedConcurrencyGuard(
            max_concurrent=max_concurrent,
            max_queue=max_queue,
            timeout=queue_timeout,
        )

    @property
    def last_tier3_telemetry(self) -> dict[str, Any]:
        """Telemetry from the most recent Tier-3 LanceDB/Kùzu retrieval invocation."""
        return dict(self._last_tier3_telemetry)

    async def _await_or_disconnect(
        self,
        awaitable: Any,
        disconnect_probe: Optional[Callable[[], Any]] = None,
        poll_interval: float = 0.25,
    ) -> Any:
        """Await `awaitable`, aborting it if the client disconnects.

        Cancelling the in-flight work closes the provider HTTP request, so the local
        model stops generating instead of completing output nobody will receive.
        Returns the `_CLIENT_DISCONNECTED` sentinel when the client went away.
        """
        if disconnect_probe is None:
            return await awaitable

        task = asyncio.ensure_future(awaitable)
        try:
            while True:
                done, _ = await asyncio.wait({task}, timeout=poll_interval)
                if task in done:
                    return task.result()
                try:
                    gone = await disconnect_probe()
                except Exception:
                    gone = False
                if gone:
                    task.cancel()
                    try:
                        await task
                    except BaseException:  # noqa: BLE001 - cancellation/timeout during teardown
                        pass
                    logger.info("client disconnected; cancelled in-flight context synthesis")
                    return _CLIENT_DISCONNECTED
        finally:
            if not task.done():
                task.cancel()

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
        log_event(
            logger,
            logging.INFO,
            "context_generation_started",
            component="context_engine",
            operation="generate_context",
            task_length=len(request.task),
            datasets_count=len(request.datasets),
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
                retrieval_state=getattr(meta, "retrieval_state", "ok") if meta else "ok",
                retrieval_error=getattr(meta, "retrieval_error", None) if meta else None,
                reference_count=len(references),
                section_headings=headings,
                model_invoked=False,
                provider_identity=None,
                model_name=None,
                inference_status="not_configured",
                fallback_used=True,
                fallback_reason="Deterministic retrieval pipeline (model-free)",
                inference_time_ms=0,
            )
            log_event(
                logger,
                logging.INFO,
                "context_generation_completed",
                component="context_engine",
                operation="generate_context",
                duration_ms=total_ms,
                model_invoked=False,
                fallback_used=True,
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
        disconnect_probe: Optional[Callable[[], Any]] = None,
    ) -> AgentContextResponse | ErrorResponse:
        """Generate compact, high-precision context for external AI coding agents.

        Parses prompt intent, checks file relevance, synthesizes semantic
        memory via Cognee, and builds a compact Markdown Context Package.

        Args:
            disconnect_probe: Optional awaitable returning True once the caller has
                gone away (e.g. FastAPI ``Request.is_disconnected``). When supplied,
                in-flight provider work is cancelled on disconnect instead of
                completing output nobody will receive.
        """
        start = time.monotonic()
        logger.info("use_case: get_agent_context() | prompt=%s", request.task_prompt[:80])
        log_event(
            logger,
            logging.INFO,
            "context_generation_started",
            component="context_engine",
            operation="get_agent_context",
            task_prompt_length=len(request.task_prompt),
            repository_path=request.repository_path,
        )

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

                # Gather intent, repository summary, and provider health
                async def _get_intent():
                    if self._intent_parser:
                        return await self._intent_parser.parse_intent(request.task_prompt)
                    fallback_record = parse_intent_heuristics(request.task_prompt)
                    fallback_record.model_invoked = False
                    fallback_record.provider_identity = None
                    fallback_record.model_name = None
                    fallback_record.inference_status = "not_configured"
                    fallback_record.fallback_used = True
                    fallback_record.fallback_reason = "No intent parser configured"
                    fallback_record.inference_time_ms = 0
                    return fallback_record

                async def _get_repo_summary():
                    # Repository walking and AST parsing are synchronous CPU/IO work.
                    # Run them on a worker thread so concurrent IPC (health polling,
                    # status, telemetry) is not blocked while a package is assembled.
                    raw_files = await run_offloaded(self._indexing_service.discover_files, repo_path)
                    indexed = await run_offloaded(self._indexing_service.filter_files, raw_files, repo_path)
                    if asyncio.iscoroutinefunction(self._summary_generator.generate):
                        summary = await self._summary_generator.generate(repo_path, indexed)
                    else:
                        summary = await run_offloaded(self._summary_generator.generate, repo_path, indexed)
                    return indexed, summary

                async def _get_provider_health():
                    if self._llm_provider:
                        try:
                            return await self._llm_provider.check_health()
                        except Exception:
                            return None
                    return None

                gathered = await self._await_or_disconnect(
                    asyncio.gather(
                        _get_intent(),
                        _get_repo_summary(),
                        _get_provider_health(),
                    ),
                    disconnect_probe,
                )
                if gathered is _CLIENT_DISCONNECTED:
                    return ErrorResponse(
                        error="ClientDisconnected",
                        message="Client disconnected; context synthesis was cancelled.",
                    )
                intent, (indexed_files, repo_summary), health_status = gathered

                # Retrieve graph context and base context package
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

                async def _get_semantic_memories():
                    if self._cognee_service is not None and hasattr(self._cognee_service, "retrieve_semantic_memory"):
                        try:
                            return await self._cognee_service.retrieve_semantic_memory(
                                repository_id=dataset_name,
                                query_text=request.task_prompt,
                                manifest=manifest_obj,
                                top_k=15,
                                repository_store=self._semantic_memory_repository,
                            )
                        except Exception as e:
                            logger.warning("Cognee semantic retrieval warning: %s", e)
                    if self._semantic_memory_repository is not None:
                        try:
                            return self._semantic_memory_repository.get_by_repository(
                                repository_id=dataset_name,
                                manifest=manifest_obj,
                                include_stale=False,
                            )
                        except Exception as e:
                            logger.warning("Semantic memory repository fallback warning: %s", e)
                            return []
                    return []

                tier3_telemetry: dict[str, Any] = {
                    "tier3_retrieval_attempted": False,
                    "tier3_retrieval_succeeded": False,
                    "tier3_items_received": 0,
                    "tier3_items_accepted": 0,
                    "tier3_items_rejected": 0,
                    "tier3_rejection_reasons": {},
                    "tier3_lancedb_count": 0,
                    "tier3_kuzu_count": 0,
                    "tier3_lancedb_state": "unavailable",
                    "tier3_kuzu_state": "unavailable",
                    "tier3_retrieval_error": None,
                }

                async def _get_tier3_memories():
                    tier3_telemetry["tier3_retrieval_attempted"] = True
                    if self._cognee_service is not None and hasattr(self._cognee_service, "retrieve_tier3_lancedb_kuzu"):
                        try:
                            res = await self._cognee_service.retrieve_tier3_lancedb_kuzu(
                                repository_id=dataset_name,
                                query_text=request.task_prompt,
                                manifest=manifest_obj,
                                top_k=15,
                                telemetry=tier3_telemetry,
                            )
                            if hasattr(res, "candidates"):
                                return res.candidates
                            return list(res)
                        except Exception as e:
                            logger.warning("Tier-3 LanceDB/Kuzu retrieval warning: %s", e)
                            tier3_telemetry["tier3_retrieval_error"] = str(e)
                            tier3_telemetry["tier3_retrieval_succeeded"] = False
                            return []
                    return []

                gathered_retrieval = await self._await_or_disconnect(
                    asyncio.gather(
                        _query_cgc(),
                        _generate_package(),
                        _get_semantic_memories(),
                        _get_tier3_memories(),
                    ),
                    disconnect_probe,
                )
                if gathered_retrieval is _CLIENT_DISCONNECTED:
                    return ErrorResponse(
                        error="ClientDisconnected",
                        message="Client disconnected; context synthesis was cancelled.",
                    )
                structural_res, package, semantic_memories, tier3_memories = gathered_retrieval
                # NOTE: `package` is the deterministic recall package. Its rendered
                # markdown is no longer concatenated into the agent context (that path
                # had no budget and dropped the tail of its last section); the
                # compactor below packs the same retrieval evidence with an explicit
                # budget. The recall invocation itself is retained unchanged so
                # retrieval behaviour is untouched by this change.
                self._last_tier3_telemetry = dict(tier3_telemetry)
                log_event(
                    logger,
                    logging.INFO,
                    "context_tier3_retrieval_completed",
                    component="context_engine",
                    operation="get_agent_context",
                    attempted=tier3_telemetry.get("tier3_retrieval_attempted", False),
                    succeeded=tier3_telemetry.get("tier3_retrieval_succeeded", False),
                    items_received=tier3_telemetry.get("tier3_items_received", 0),
                    items_accepted=tier3_telemetry.get("tier3_items_accepted", 0),
                    items_rejected=tier3_telemetry.get("tier3_items_rejected", 0),
                    lancedb_count=tier3_telemetry.get("tier3_lancedb_count", 0),
                    kuzu_count=tier3_telemetry.get("tier3_kuzu_count", 0),
                    lancedb_state=tier3_telemetry.get("tier3_lancedb_state", "unknown"),
                    kuzu_state=tier3_telemetry.get("tier3_kuzu_state", "unknown"),
                )
                # Rank snippets and matching files
                t_rank_start = time.perf_counter()
                relevant_snippets = []
                matched_file_rels = []
                search_terms: list[str] = []
                if self._source_search:
                    search_terms = self._source_search.build_search_terms(
                        task_prompt=request.task_prompt,
                        extracted_symbols=intent.extracted_symbols,
                        relevant_file_hints=intent.relevant_file_hints,
                        target_entities=getattr(intent, "target_entities", []),
                    )
                    # Synchronous multi-file reads + regex scoring; keep off the loop.
                    relevant_snippets, matched_file_rels = await run_offloaded(
                        self._source_search.extract_relevant_snippets,
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

                # Arbitrate retrieved multi-modal evidence (Phase 10D.5)
                symbols_found = structural_res.symbols_found if structural_res else []
                call_edges = [
                    f"{caller} -> {sym}"
                    for caller in (structural_res.callers if structural_res else [])
                    for sym in (structural_res.symbols_found if structural_res else [])
                ]

                arbitrated_result = RetrievalArbitrator.arbitrate(
                    task_prompt=request.task_prompt,
                    intent=intent,
                    manifest=manifest_obj,
                    source_snippets=relevant_snippets,
                    source_matched_files=matched_file_rels,
                    ast_symbols=symbols_found,
                    ast_call_edges=call_edges,
                    lancedb_kuzu_memories=tier3_memories or [],
                    cognee_memories=semantic_memories or [],
                    target_tokens=target_tokens,
                    reserve_authoritative_budget=True,
                )

                # Assess evidence and evaluate gate using arbitrated result
                evidence = EvidenceService.assess_evidence(
                    task_prompt=request.task_prompt,
                    intent=intent,
                    repo_summary=repo_summary,
                    indexed_files=indexed_files,
                    relevant_snippets=arbitrated_result.authoritative_snippets or relevant_snippets,
                    matched_file_rels=arbitrated_result.authoritative_files or matched_file_rels,
                    structural_symbols=arbitrated_result.authoritative_symbols or symbols_found,
                    structural_relationships=arbitrated_result.authoritative_relationships or call_edges,
                    manifest=manifest_obj,
                    arbitrated_result=arbitrated_result,
                )

                log_event(
                    logger,
                    logging.INFO,
                    "context_evidence_collection_completed",
                    component="context_engine",
                    operation="get_agent_context",
                    evidence_state=evidence.evidence_state,
                    evidence_score=evidence.evidence_score,
                    evidence_file_count=len(evidence.evidence_files),
                    evidence_symbol_count=len(evidence.evidence_symbols),
                    evidence_relationship_count=len(evidence.evidence_relationships),
                    abstained=evidence.abstained,
                )

                quant_warning = health_status.quantization_warning if health_status else None
                elapsed_ms = int((time.monotonic() - start) * 1000)

                # Abstain if evidence is insufficient
                if evidence.abstained:
                    log_event(
                        logger,
                        logging.INFO,
                        "context_evidence_gate_rejected",
                        component="context_engine",
                        operation="get_agent_context",
                        evidence_state=evidence.evidence_state,
                        evidence_score=evidence.evidence_score,
                        missing_evidence_count=len(evidence.missing_evidence),
                    )
                    log_event(
                        logger,
                        logging.INFO,
                        "context_model_invocation_skipped",
                        component="context_engine",
                        operation="get_agent_context",
                        reason="abstained_insufficient_evidence",
                    )
                    log_event(
                        logger,
                        logging.INFO,
                        "context_abstained_insufficient_evidence",
                        component="context_engine",
                        operation="get_agent_context",
                        evidence_state=evidence.evidence_state,
                        abstention_reason=evidence.abstention_reason,
                    )

                    abstention_markdown = EvidenceService.build_abstention_package(
                        task_prompt=request.task_prompt,
                        intent=intent,
                        evidence=evidence,
                    )

                    response = AgentContextResponse(
                        success=True,
                        context_markdown=abstention_markdown,
                        task_summary=intent.task_summary,
                        intent_category=intent.category,
                        extracted_symbols=evidence.evidence_symbols,
                        callers=[],
                        callees=[],
                        related_files=evidence.evidence_files,
                        quantization_warning=quant_warning,
                        estimated_tokens=len(abstention_markdown) // 4,
                        generation_time_ms=elapsed_ms,
                        retrieval_time_ms=retrieval_time_ms,
                        ranking_time_ms=ranking_time_ms,
                        synthesis_time_ms=0,
                        total_time_ms=elapsed_ms,
                        model_invoked=False,
                        provider_identity=getattr(intent, "provider_identity", None),
                        model_name=getattr(intent, "model_name", None),
                        inference_status=getattr(intent, "inference_status", "not_configured"),
                        fallback_used=True,
                        fallback_reason=(
                            getattr(intent, "fallback_reason", None)
                            if getattr(intent, "inference_status", "") in ("model_not_available", "model_mismatch")
                            else "Deterministic abstention: insufficient repository evidence"
                        ),
                        inference_time_ms=getattr(intent, "inference_time_ms", 0),
                        evidence_state=evidence.evidence_state,
                        evidence_score=evidence.evidence_score,
                        evidence_confidence=evidence.evidence_confidence,
                        evidence_files=evidence.evidence_files,
                        evidence_symbols=evidence.evidence_symbols,
                        evidence_relationships=evidence.evidence_relationships,
                        observed_evidence=evidence.observed_evidence,
                        missing_evidence=evidence.missing_evidence,
                        abstained=True,
                        abstention_reason=evidence.abstention_reason,
                        model_claims_allowed=False,
                    )

                    log_event(
                        logger,
                        logging.INFO,
                        "context_generation_completed",
                        component="context_engine",
                        operation="get_agent_context",
                        duration_ms=elapsed_ms,
                        model_invoked=False,
                        fallback_used=True,
                        inference_status=response.inference_status,
                        abstained=True,
                    )

                    self._cache.set(
                        cache_key,
                        response,
                        repo_path=str(repo_path),
                        referenced_files=evidence.evidence_files,
                        referenced_symbols=evidence.evidence_symbols,
                    )
                    return response

                # Synthesize and sanitize grounded markdown
                log_event(
                    logger,
                    logging.INFO,
                    "context_evidence_gate_passed",
                    component="context_engine",
                    operation="get_agent_context",
                    evidence_state=evidence.evidence_state,
                    evidence_score=evidence.evidence_score,
                )

                t_synth_start = time.perf_counter()

                # ------------------------------------------------------------------
                # Budget-aware evidence packing.
                #
                # This replaces tail truncation. The complete ranked candidate set
                # is collected (no positional eviction) and the compactor decides
                # what the requested budget buys: mandatory task-linked evidence is
                # placed first, oversized artifacts are reduced through an explicit
                # level ladder that keeps their provenance, and lower-authority
                # evidence yields first when the budget is tight.
                # ------------------------------------------------------------------
                packing_result = RetrievalArbitrator.arbitrate(
                    task_prompt=request.task_prompt,
                    intent=intent,
                    manifest=manifest_obj,
                    source_snippets=relevant_snippets,
                    source_matched_files=matched_file_rels,
                    ast_symbols=symbols_found,
                    ast_call_edges=call_edges,
                    lancedb_kuzu_memories=tier3_memories or [],
                    cognee_memories=semantic_memories or [],
                    target_tokens=target_tokens,
                    reserve_authoritative_budget=True,
                    collect_all=True,
                )

                all_related = list(dict.fromkeys(
                    matched_file_rels + (structural_res.related_files if structural_res else [])
                ))

                # One consistent token-accounting model: the requested budget is
                # split into task prompt, fixed prompt overhead, generation
                # reservation and the repository-evidence allowance. The scaffold
                # is measured WITHOUT the task text because `task_prompt_tokens`
                # already accounts for it; including it here would double count it
                # and shrink the evidence allowance below what the budget allows.
                will_invoke_model = self._llm_provider is not None
                budget_plan = plan_context_budget(
                    requested_tokens=target_tokens,
                    task_prompt=request.task_prompt,
                    fixed_overhead_text=_SYNTH_SYSTEM_PROMPT + build_synthesis_user_prompt(
                        task_prompt=request.task_prompt,
                        task_summary=intent.task_summary,
                        category=intent.category,
                        target_entities=getattr(intent, "target_entities", []),
                        symbols=evidence.evidence_symbols or intent.extracted_symbols,
                        evidence_text="",
                        include_task=False,
                    ),
                    model_reserved=will_invoke_model,
                )

                def _pack_evidence(
                    output_reservation_override: Optional[int] = None,
                    include_derived_recall: bool = False,
                ):
                    """Pack the ranked evidence against the budget (optionally around a known answer)."""
                    candidates = list(packing_result.candidates)
                    if include_derived_recall:
                        candidates += build_derived_recall_candidate(package)
                    return self._compactor.compact(
                        candidates=candidates,
                        plan=budget_plan,
                        task_prompt=request.task_prompt,
                        title=intent.task_summary,
                        task_terms=search_terms or derive_task_terms(
                            request.task_prompt, list(intent.extracted_symbols)
                        ),
                        task_symbols=list(intent.extracted_symbols),
                        task_files=list(intent.relevant_file_hints) + list(matched_file_rels[:4]),
                        relevant_files=all_related,
                        missing_evidence=evidence.missing_evidence,
                        output_reservation_override=output_reservation_override,
                    )

                compacted = _pack_evidence()

                log_event(
                    logger,
                    logging.INFO,
                    "context_compaction_completed",
                    component="context_engine",
                    operation="get_agent_context",
                    requested_tokens=compacted.report.requested_tokens,
                    evidence_budget_tokens=compacted.report.evidence_budget_tokens,
                    pre_compaction_tokens=compacted.report.pre_compaction_tokens,
                    evidence_tokens=compacted.report.evidence_tokens,
                    candidates_before=compacted.report.candidates_before,
                    candidates_after=compacted.report.candidates_after,
                    omitted_count=len(compacted.report.omitted),
                    reduced_count=len(compacted.report.reduced),
                    mandatory_evidence_fit=compacted.report.mandatory_evidence_fit,
                    budget_satisfied=compacted.report.budget_satisfied,
                )

                synth_model_invoked = False
                synth_model_name = None
                synth_provider_identity = None
                synth_inference_status = "not_configured"
                synth_fallback_used = True
                synth_fallback_reason = "No active LLM provider configured"
                synth_inference_time_ms = 0
                final_markdown = ""

                # Task-Specific Context Synthesis via LLM Provider
                if self._llm_provider:
                    p_type = getattr(self._llm_provider, "provider_type", None)
                    synth_provider_identity = p_type.value if hasattr(p_type, "value") else str(p_type or "llm_provider")
                    synth_model_name = getattr(self._llm_provider, "default_model", None)

                    evidence_text = compacted.evidence_markdown or "General repository structure and indexed files."
                    synth_user_prompt = build_synthesis_user_prompt(
                        task_prompt=request.task_prompt,
                        task_summary=intent.task_summary,
                        category=intent.category,
                        target_entities=getattr(intent, "target_entities", []),
                        symbols=evidence.evidence_symbols or intent.extracted_symbols,
                        evidence_text=evidence_text,
                    )

                    try:
                        t_model_start = time.perf_counter()
                        # The generation budget is the budget's explicit output
                        # reservation — never the input context budget.
                        generation_budget = budget_plan.output_reservation_tokens or min(target_tokens, 8192)
                        synth_raw = await self._await_or_disconnect(
                            self._llm_provider.generate_completion(
                                prompt=synth_user_prompt,
                                system_prompt=_SYNTH_SYSTEM_PROMPT,
                                model=synth_model_name,
                                temperature=0.1,
                                max_tokens=generation_budget,
                            ),
                            disconnect_probe,
                        )
                        if synth_raw is _CLIENT_DISCONNECTED:
                            return ErrorResponse(
                                error="ClientDisconnected",
                                message="Client disconnected; context synthesis was cancelled.",
                            )
                        synth_inference_time_ms = int((time.perf_counter() - t_model_start) * 1000)

                        # Strip thinking tags. A reasoning model truncated by the
                        # generation reservation ends mid-trace with no closing
                        # tag, so an unclosed block is dropped rather than
                        # delivered as if it were the answer.
                        synth_clean = re.sub(r"<think>.*?</think>", "", synth_raw, flags=re.DOTALL).strip()
                        synth_clean = re.sub(r"\[THINKING\].*?\[/THINKING\]", "", synth_clean, flags=re.DOTALL).strip()
                        if "<think>" in synth_clean:
                            synth_clean = synth_clean.split("<think>", 1)[0].strip()
                        if "[THINKING]" in synth_clean:
                            synth_clean = synth_clean.split("[THINKING]", 1)[0].strip()

                        if synth_clean and len(synth_clean) > 20:
                            actual_model = getattr(self._llm_provider, "last_invoked_model", None) or synth_model_name
                            synth_model_invoked = True
                            synth_model_name = actual_model
                            synth_inference_status = "completed"
                            synth_fallback_used = False
                            synth_fallback_reason = None

                            # Re-pack the evidence around the answer the model
                            # actually produced, so the delivered package fits the
                            # requested budget. The answer is never truncated to
                            # make room for evidence — evidence is what yields.
                            compacted = _pack_evidence(output_reservation_override=estimate_tokens(synth_clean))

                            # Task-specific synthesis leads; the packed evidence set
                            # that grounded it travels with it.
                            final_markdown = compacted.compose(synth_clean)
                    except Exception as e:
                        logger.warning("LLM task context synthesis failed, falling back to deterministic assembly: %s", e)
                        synth_fallback_used = True
                        synth_fallback_reason = f"Model synthesis error: {e}"

                # Fallback to the deterministic compacted package if the model was
                # not invoked. The deterministic recall package contributes as the
                # lowest-authority tier, so it is reduced or dropped first.
                if not final_markdown:
                    compacted = _pack_evidence(output_reservation_override=0, include_derived_recall=True)
                    final_markdown = compacted.deterministic_markdown

                # Sanitize reasoning tags
                final_markdown = EvidenceService.sanitize_and_validate_grounded_response(
                    raw_markdown=final_markdown,
                    evidence=evidence,
                    indexed_files=indexed_files,
                )

                # Measure the delivered document against the requested budget.
                compaction_report = compacted.observe_final(final_markdown)

                synthesis_time_ms = int((time.perf_counter() - t_synth_start) * 1000)
                elapsed_ms = int((time.monotonic() - start) * 1000)

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
                    estimated_tokens=compaction_report.final_tokens,
                    generation_time_ms=elapsed_ms,
                    retrieval_time_ms=retrieval_time_ms,
                    ranking_time_ms=ranking_time_ms,
                    synthesis_time_ms=synthesis_time_ms,
                    total_time_ms=elapsed_ms,
                    model_invoked=synth_model_invoked or getattr(intent, "model_invoked", False),
                    provider_identity=synth_provider_identity or getattr(intent, "provider_identity", None),
                    model_name=synth_model_name or getattr(intent, "model_name", None),
                    inference_status=synth_inference_status if synth_model_invoked else getattr(intent, "inference_status", "not_configured"),
                    fallback_used=synth_fallback_used and getattr(intent, "fallback_used", False),
                    fallback_reason=synth_fallback_reason if not synth_model_invoked else None,
                    inference_time_ms=synth_inference_time_ms or getattr(intent, "inference_time_ms", 0),
                    evidence_state=evidence.evidence_state,
                    evidence_score=evidence.evidence_score,
                    evidence_confidence=evidence.evidence_confidence,
                    evidence_files=evidence.evidence_files or all_related,
                    evidence_symbols=evidence.evidence_symbols or intent.extracted_symbols,
                    evidence_relationships=evidence.evidence_relationships or call_edges,
                    observed_evidence=evidence.observed_evidence,
                    missing_evidence=evidence.missing_evidence,
                    abstained=False,
                    abstention_reason=None,
                    model_claims_allowed=True,
                    compaction=compaction_report.to_dict(),
                )

                log_event(
                    logger,
                    logging.INFO,
                    "context_generation_completed",
                    component="context_engine",
                    operation="get_agent_context",
                    duration_ms=elapsed_ms,
                    model_invoked=response.model_invoked,
                    fallback_used=response.fallback_used,
                    inference_status=response.inference_status,
                    abstained=False,
                )

                # Cache response
                self._cache.set(
                    cache_key,
                    response,
                    repo_path=str(repo_path),
                    referenced_files=evidence.evidence_files or all_related,
                    referenced_symbols=list(intent.extracted_symbols),
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
                raw_files = await run_offloaded(self._indexing_service.discover_files, repo_path)
                indexed_files = await run_offloaded(self._indexing_service.filter_files, raw_files, repo_path)
            else:
                repo_canon = repo_path.resolve()
                indexed_files = [
                    p for p in repo_path.rglob("*")
                    if p.is_file() and not p.name.startswith(".")
                    and p.resolve().is_relative_to(repo_canon)
                ]

            results: list[SourceSearchResultItem] = []
            if self._source_search:
                raw_results = await run_offloaded(
                    self._source_search.search,
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
