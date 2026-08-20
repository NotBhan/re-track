"""Repository management use cases for RE:Track.

Coordinates creating, listing, scanning, deleting repositories, and generating prompt suggestions.
All dependencies are explicitly injected via constructor.
"""

import json
import logging
from pathlib import Path
import time
from typing import Any, Optional

from app.application.dto import (
    ErrorResponse,
    RepositoryCreateRequest,
    RepositoryListResponse,
    RepositoryResponse,
    ScanResultResponse,
)
from app.models.repository import Repository
from app.services.cognee_service import CogneeService
from app.services.indexing_service import IndexingService
from app.services.llm_provider_service import LLMProviderService
from app.services.repository_manager import RepositoryManager
from app.services.repository_metadata_store import (
    JsonRepositoryMetadataStore,
    RepositoryMetadataStore,
)
from app.services.repository_summary import RepositorySummaryGenerator

logger = logging.getLogger(__name__)


class RepositoryUseCases:
    """Orchestrates repository CRUD, scanning, and prompt recommendations."""

    def __init__(
        self,
        repository_manager: RepositoryManager,
        indexing_service: Optional[IndexingService],
        llm_provider: Optional[LLMProviderService],
        summary_generator: RepositorySummaryGenerator,
        cognee_service: Optional[CogneeService] = None,
        metadata_store: Optional[RepositoryMetadataStore] = None,
    ) -> None:
        self._manager = repository_manager
        self._indexing_service = indexing_service
        self._llm_provider = llm_provider
        self._summary_generator = summary_generator
        self._cognee_service = cognee_service
        self._metadata_store = metadata_store or JsonRepositoryMetadataStore()

    def _repo_to_response(self, repo: Repository) -> RepositoryResponse:
        """Convert a Repository dataclass to a Pydantic response model with full AST and metadata."""
        call_graph_nodes = None
        call_graph_edges = None
        call_graph_status = "not_analyzed"
        call_graph_error = None
        summary = repo.summary or ""
        entry_points = repo.entry_points or []
        architecture = repo.architecture or ""
        components = repo.components or []
        dependencies = repo.dependencies or []

        # Check repo metadata
        if repo.metadata:
            if "call_graph_nodes" in repo.metadata:
                call_graph_nodes = repo.metadata["call_graph_nodes"]
            if "call_graph_edges" in repo.metadata:
                call_graph_edges = repo.metadata["call_graph_edges"]
            if "call_graph_status" in repo.metadata:
                call_graph_status = repo.metadata["call_graph_status"]
            if "call_graph_error" in repo.metadata:
                call_graph_error = repo.metadata["call_graph_error"]

        # Fallback to indexed repo store if not in repo.metadata
        if not call_graph_nodes:
            try:
                store = self._metadata_store.load()
                for r in store.get("repositories", []):
                    if r.get("path") == repo.local_path or r.get("name") == repo.name or r.get("id") == repo.id:
                        if r.get("call_graph_nodes"):
                            call_graph_nodes = r.get("call_graph_nodes")
                        if r.get("call_graph_edges"):
                            call_graph_edges = r.get("call_graph_edges")
                        if r.get("call_graph_status"):
                            call_graph_status = r.get("call_graph_status")
                        if r.get("call_graph_error"):
                            call_graph_error = r.get("call_graph_error")
                        break
            except Exception:
                pass

        return RepositoryResponse(
            id=repo.id,
            name=repo.name,
            source_type=repo.source_type,
            source_url=repo.source_url,
            local_path=repo.local_path,
            branch=repo.branch,
            commit_hash=repo.commit_hash,
            status=repo.status,
            languages=repo.languages or [],
            frameworks=repo.frameworks or [],
            file_count=repo.file_count or 0,
            size_bytes=repo.size_bytes or 0,
            indexed_at=repo.indexed_at,
            error_message=repo.error_message,
            summary=summary,
            entry_points=entry_points,
            architecture=architecture,
            components=components,
            dependencies=dependencies,
            metadata=repo.metadata or {},
            call_graph_status=call_graph_status,
            call_graph_error=call_graph_error,
            call_graph_nodes=call_graph_nodes,
            call_graph_edges=call_graph_edges,
        )

    async def list_repositories(self) -> RepositoryListResponse | ErrorResponse:
        """List all managed repositories from repository manager."""
        start = time.monotonic()
        logger.info("use_case: list_repositories()")
        try:
            repos = self._manager.list_repositories()
            response = RepositoryListResponse(
                success=True,
                repositories=[self._repo_to_response(r) for r in repos],
                total_count=len(repos),
            )
            elapsed = time.monotonic() - start
            logger.info("use_case: list_repositories() complete | count=%d | %.2fs", len(repos), elapsed)
            return response
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: list_repositories() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Failed to list repositories: {e}",
            )

    async def create_repository(
        self,
        request: RepositoryCreateRequest,
    ) -> RepositoryResponse | ErrorResponse:
        """Create/import a repository."""
        start = time.monotonic()
        logger.info("use_case: create_repository() | name=%s", request.name)
        try:
            repo = self._manager.import_repo(
                source_type=request.source_type,
                source_url=request.source_url,
                local_path=request.local_path,
                name=request.name,
            )
            elapsed = time.monotonic() - start
            logger.info("use_case: create_repository() complete | id=%s | %.2fs", repo.id, elapsed)
            return self._repo_to_response(repo)
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: create_repository() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Failed to create repository: {e}",
            )

    async def scan_repository(self, repo_id: str) -> ScanResultResponse | ErrorResponse:
        """Scan a repository for languages and frameworks."""
        start = time.monotonic()
        logger.info("use_case: scan_repository() | repo_id=%s", repo_id)
        try:
            scan = self._manager.scan(repo_id)
            elapsed = time.monotonic() - start
            logger.info("use_case: scan_repository() complete | repo=%s | %.2fs", repo_id, elapsed)
            return ScanResultResponse(
                success=True,
                languages=scan.languages,
                frameworks=scan.frameworks,
                file_count=scan.file_count,
                total_size_bytes=scan.total_size_bytes,
                git_branch=scan.git_branch,
                git_commit=scan.git_commit,
            )
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: scan_repository() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Failed to scan repository: {e}",
            )

    async def get_repository_progress(self, repo_id: str) -> dict | ErrorResponse:
        """Get indexing progress for a repository."""
        try:
            repo = self._manager.get(repo_id)
            if not repo:
                return ErrorResponse(error="NotFoundError", message=f"Repository {repo_id} not found")
            return {
                "success": True,
                "repo_id": repo_id,
                "status": repo.status.value if hasattr(repo.status, "value") else repo.status,
                "error": repo.error_message,
            }
        except Exception as e:
            return ErrorResponse(error=type(e).__name__, message=str(e))

    async def delete_repository(self, repo_id: str) -> dict | ErrorResponse:
        """Delete a managed repository and clean up memory."""
        start = time.monotonic()
        logger.info("use_case: delete_repository() | repo_id=%s", repo_id)
        try:
            repo = self._manager.get(repo_id)
            dataset_name = repo.name if repo else None

            success = self._manager.delete(repo_id)
            if not success:
                return ErrorResponse(
                    error="NotFoundError",
                    message=f"Repository {repo_id} not found",
                )

            # Clean from repo store using metadata store abstraction
            store = self._metadata_store.load()
            repos = store.get("repositories", [])
            store["repositories"] = [r for r in repos if str(r.get("id")) != repo_id and r.get("name") != dataset_name]
            self._metadata_store.save(store)

            # Optionally clean dataset from Cognee
            if dataset_name and self._cognee_service and self._cognee_service.is_initialized:
                try:
                    await self._cognee_service.forget(dataset=dataset_name)
                except Exception as ef:
                    logger.warning("Could not delete dataset %s from memory: %s", dataset_name, ef)

            elapsed = time.monotonic() - start
            logger.info("use_case: delete_repository() complete | repo=%s | %.2fs", repo_id, elapsed)
            return {"success": True, "message": f"Repository {repo_id} deleted"}
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: delete_repository() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Failed to delete repository: {e}",
            )

    async def generate_suggested_prompts(self, repo_id: str) -> dict[str, Any]:
        """Generate repository-tailored developer prompts grounded strictly in AST metadata and real symbols."""
        start = time.monotonic()
        logger.info("use_case: generate_suggested_prompts() | repo_id=%s", repo_id)

        repo = None
        for r in self._manager.list_repositories():
            if r.id == repo_id or r.name == repo_id or (r.local_path and Path(r.local_path).name == repo_id):
                repo = r
                break

        name = repo.name if repo else "this repository"
        langs = ", ".join(repo.languages) if (repo and repo.languages) else "code"
        frameworks = ", ".join(repo.frameworks) if (repo and repo.frameworks) else ""
        components = repo.components if (repo and repo.components) else []

        # Extract actual verified AST symbols (classes, functions, components)
        real_symbols = []
        if repo and repo.metadata and isinstance(repo.metadata.get("call_graph_nodes"), list):
            real_symbols = [
                n["label"] for n in repo.metadata["call_graph_nodes"]
                if isinstance(n, dict) and n.get("label") and not n.get("label", "").startswith(".")
            ]
        if not real_symbols and components:
            real_symbols = components[:15]

        symbols_str = ", ".join(real_symbols[:15]) if real_symbols else ""

        heuristic_prompts = []
        if real_symbols:
            s1 = real_symbols[0]
            heuristic_prompts.append({
                "label": f"{s1[:20]} Architecture",
                "prompt": f"Explain the implementation, callers, and lifecycle of `{s1}` in {name}."
            })
            if len(real_symbols) > 1:
                s2 = real_symbols[1]
                heuristic_prompts.append({
                    "label": f"{s2[:20]} Flow",
                    "prompt": f"Trace how `{s2}` interacts with related components and handles state in {name}."
                })
        if frameworks:
            heuristic_prompts.append({
                "label": f"{frameworks.split(',')[0]} Routing & Auth",
                "prompt": f"Find where {frameworks} configuration, routing, and middleware pipelines are initialized in {name}."
            })
        heuristic_prompts.extend([
            {
                "label": "Call Graph Traversal",
                "prompt": f"Trace the critical function call graph and data dependencies across {name}."
            },
            {
                "label": "Data Schemas",
                "prompt": f"Show the key data models, schemas, and API definitions present in {name}."
            },
        ])

        if self._llm_provider:
            try:
                p_health = await self._llm_provider.check_health()
                if p_health.is_reachable:
                    system_prompt = (
                        "You are a strict, hallucination-free software engineer. "
                        "You must base your task questions SOLELY and STRICTLY on the actual verified classes, "
                        "symbols, and modules present in this repository. DO NOT invent external features, models, "
                        "or endpoints not present in the provided symbols.\n"
                        "Return STRICTLY a valid JSON array of objects with keys 'label' (2-4 words) "
                        "and 'prompt' (a single clear developer question/task). Do not include markdown formatting or backticks."
                    )
                    user_prompt = (
                        f"Repository: {name}\n"
                        f"Frameworks: {frameworks or 'Standard'}\n"
                        f"Languages: {langs}\n"
                        f"Discovered Classes & Symbols: {symbols_str or 'Core codebase'}\n\n"
                        "Generate 4-5 focused developer questions or implementation tasks referencing these exact symbols."
                    )
                    raw = await self._llm_provider.generate_completion(
                        prompt=user_prompt,
                        system_prompt=system_prompt,
                        temperature=0.2,
                        max_tokens=500,
                    )
                    raw = raw.strip()
                    if raw.startswith("```"):
                        raw = raw.strip("`").removeprefix("json").strip()
                    parsed = json.loads(raw)
                    if isinstance(parsed, list) and len(parsed) > 0:
                        valid_prompts = []
                        for item in parsed:
                            if isinstance(item, dict) and "label" in item and "prompt" in item:
                                valid_prompts.append(item)
                        if valid_prompts:
                            return {"success": True, "prompts": valid_prompts, "source": "ai"}
            except Exception as e:
                logger.debug("LLM prompt generation failed, falling back to heuristics: %s", e)

        return {"success": True, "prompts": heuristic_prompts[:5], "source": "heuristic"}
