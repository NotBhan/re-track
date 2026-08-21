"""Repository management use cases for RE:Track.

Coordinates creating, listing, scanning, deleting repositories, and generating prompt suggestions.
All dependencies are explicitly injected via constructor capability ports.
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
from app.application.ports.indexing_service import IndexingServicePort
from app.application.ports.llm_provider import LLMProviderPort
from app.application.ports.memory import MemoryDatasetPort
from app.application.ports.repository_manager import RepositoryManagerPort
from app.application.ports.repository_metadata import RepositoryMetadataPort
from app.application.ports.summary_generator import SummaryGeneratorPort
from app.models.repository import Repository

logger = logging.getLogger(__name__)


class RepositoryUseCases:
    """Orchestrates repository CRUD, scanning, and prompt recommendations."""

    def __init__(
        self,
        repository_manager: RepositoryManagerPort,
        indexing_service: Optional[IndexingServicePort],
        llm_provider: Optional[LLMProviderPort],
        summary_generator: SummaryGeneratorPort,
        cognee_service: Optional[MemoryDatasetPort] = None,
        metadata_store: Optional[RepositoryMetadataPort] = None,
    ) -> None:
        self._manager = repository_manager
        self._indexing_service = indexing_service
        self._llm_provider = llm_provider
        self._summary_generator = summary_generator
        self._cognee_service = cognee_service
        self._metadata_store = metadata_store

    def _repo_to_response(self, repo: Any) -> RepositoryResponse:
        """Convert a Repository domain object to a response model with full AST and metadata."""
        call_graph_nodes = None
        call_graph_edges = None
        call_graph_status = "not_analyzed"
        call_graph_error = None
        summary = getattr(repo, "summary", "") or ""
        entry_points = getattr(repo, "entry_points", []) or []
        architecture = getattr(repo, "architecture", "") or ""
        components = getattr(repo, "components", []) or []
        dependencies = getattr(repo, "dependencies", []) or []

        metadata = getattr(repo, "metadata", {}) or {}
        if metadata:
            if "call_graph_nodes" in metadata:
                call_graph_nodes = metadata["call_graph_nodes"]
            if "call_graph_edges" in metadata:
                call_graph_edges = metadata["call_graph_edges"]
            if "call_graph_status" in metadata:
                call_graph_status = metadata["call_graph_status"]
            if "call_graph_error" in metadata:
                call_graph_error = metadata["call_graph_error"]

        # Fallback to indexed repo metadata store if not in repo.metadata
        if not call_graph_nodes and self._metadata_store:
            try:
                rec = (
                    self._metadata_store.get_by_path(getattr(repo, "local_path", ""))
                    or self._metadata_store.get_by_id(getattr(repo, "id", ""))
                )
                if rec:
                    if rec.call_graph_nodes:
                        call_graph_nodes = rec.call_graph_nodes
                    if rec.call_graph_edges:
                        call_graph_edges = rec.call_graph_edges
                    if rec.call_graph_status:
                        call_graph_status = rec.call_graph_status
                    if rec.call_graph_error:
                        call_graph_error = rec.call_graph_error
            except Exception:
                pass

        return RepositoryResponse(
            id=getattr(repo, "id", ""),
            name=getattr(repo, "name", ""),
            source_type=getattr(repo, "source_type", "local"),
            source_url=getattr(repo, "source_url", None),
            local_path=getattr(repo, "local_path", ""),
            branch=getattr(repo, "branch", None),
            commit_hash=getattr(repo, "commit_hash", None),
            status=getattr(repo, "status", "ready"),
            languages=getattr(repo, "languages", []) or [],
            frameworks=getattr(repo, "frameworks", []) or [],
            file_count=getattr(repo, "file_count", 0) or 0,
            size_bytes=getattr(repo, "size_bytes", 0) or 0,
            indexed_at=getattr(repo, "indexed_at", None),
            error_message=getattr(repo, "error_message", None),
            summary=summary,
            entry_points=entry_points,
            architecture=architecture,
            components=components,
            dependencies=dependencies,
            metadata=metadata,
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
            if hasattr(self._manager, "import_repo"):
                repo = self._manager.import_repo(
                    name=request.name,
                    path=request.local_path or "",
                    branch=None,
                ) if "source_type" not in getattr(self._manager.import_repo, "__code__", type("", (), {"co_varnames": ()})).co_varnames else self._manager.import_repo(
                    source_type=request.source_type,
                    source_url=request.source_url,
                    local_path=request.local_path,
                    name=request.name,
                )
            else:
                raise ValueError("RepositoryManager does not support repository import")

            elapsed = time.monotonic() - start
            logger.info("use_case: create_repository() complete | id=%s | %.2fs", getattr(repo, "id", ""), elapsed)
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
            scan = getattr(self._manager, "scan", getattr(self._manager, "scan_local", None))(repo_id)
            elapsed = time.monotonic() - start
            logger.info("use_case: scan_repository() complete | repo=%s | %.2fs", repo_id, elapsed)
            return ScanResultResponse(
                success=True,
                languages=getattr(scan, "languages", []),
                frameworks=getattr(scan, "frameworks", []),
                file_count=getattr(scan, "file_count", 0),
                total_size_bytes=getattr(scan, "total_size_bytes", 0),
                git_branch=getattr(scan, "git_branch", None),
                git_commit=getattr(scan, "git_commit", None),
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
            repo = getattr(self._manager, "get", getattr(self._manager, "get_by_id", None))(repo_id)
            if not repo:
                return ErrorResponse(error="NotFoundError", message=f"Repository {repo_id} not found")
            status = getattr(repo, "status", "ready")
            return {
                "success": True,
                "repo_id": repo_id,
                "status": status.value if hasattr(status, "value") else status,
                "error": getattr(repo, "error_message", None),
            }
        except Exception as e:
            return ErrorResponse(error=type(e).__name__, message=str(e))

    async def delete_repository(self, repo_id: str) -> dict | ErrorResponse:
        """Delete a managed repository and clean up memory."""
        start = time.monotonic()
        logger.info("use_case: delete_repository() | repo_id=%s", repo_id)
        try:
            repo = getattr(self._manager, "get", getattr(self._manager, "get_by_id", None))(repo_id)
            dataset_name = getattr(repo, "name", None) if repo else None

            success = self._manager.delete(repo_id)
            if not success:
                return ErrorResponse(
                    error="NotFoundError",
                    message=f"Repository {repo_id} not found",
                )

            # Clean from repo metadata store
            if self._metadata_store:
                self._metadata_store.delete(repo_id)
                if dataset_name:
                    self._metadata_store.delete(dataset_name)

            # Optionally clean dataset from Cognee memory
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
            r_id = getattr(r, "id", "")
            r_name = getattr(r, "name", "")
            r_path = getattr(r, "local_path", "")
            if r_id == repo_id or r_name == repo_id or (r_path and Path(r_path).name == repo_id):
                repo = r
                break

        name = getattr(repo, "name", "this repository") if repo else "this repository"
        langs = ", ".join(getattr(repo, "languages", [])) if (repo and getattr(repo, "languages", None)) else "code"
        frameworks = ", ".join(getattr(repo, "frameworks", [])) if (repo and getattr(repo, "frameworks", None)) else ""
        components = getattr(repo, "components", []) if (repo and getattr(repo, "components", None)) else []

        # Extract actual verified AST symbols (classes, functions, components)
        real_symbols = []
        repo_metadata = getattr(repo, "metadata", {}) or {}
        if repo and repo_metadata and isinstance(repo_metadata.get("call_graph_nodes"), list):
            real_symbols = [
                n["label"] for n in repo_metadata["call_graph_nodes"]
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
                is_reachable = getattr(p_health, "is_reachable", False)
                if is_reachable:
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
