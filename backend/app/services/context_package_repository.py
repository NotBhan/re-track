"""Abstract repository for SavedContextPackage persistence and JSON implementation."""

import fcntl
import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from app.models.context_package import SavedContextPackage

MARKDOWN_SEPARATOR = "\n\n---\n\n"


class ContextPackageRepository(ABC):
    """Abstract interface for SavedContextPackage persistence."""

    @abstractmethod
    async def save(self, package: SavedContextPackage) -> SavedContextPackage:
        ...

    @abstractmethod
    async def get(self, package_id: str) -> Optional[SavedContextPackage]:
        ...

    @abstractmethod
    async def list_all(self) -> list[SavedContextPackage]:
        ...

    @abstractmethod
    async def delete(self, package_id: str) -> bool:
        ...

    @abstractmethod
    async def append(
        self,
        package_id: str,
        additional_task: str,
        additional_markdown: str,
        additional_objective: str = "",
    ) -> Optional[SavedContextPackage]:
        ...


class JsonContextPackageRepository(ContextPackageRepository):
    """JSON file-backed implementation of ContextPackageRepository.

    Stores packages in a single JSON file with atomic writes and file locking
    for thread safety. Default path: ~/.andes/context_packages.json
    """

    def __init__(self, store_path: str | Path | None = None):
        if store_path is None:
            store_path = Path.home() / ".andes" / "context_packages.json"
        self._store_path = Path(store_path)

    def _load(self) -> dict[str, dict]:
        if not self._store_path.exists():
            return {}
        try:
            with open(self._store_path, "r") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    return {}
                return data
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_all(self, packages: dict[str, dict]) -> None:
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._store_path.with_suffix(".tmp")
        with open(tmp_path, "w") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                json.dump(packages, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        tmp_path.replace(self._store_path)

    @staticmethod
    def _to_dict(pkg: SavedContextPackage) -> dict:
        return {
            "id": pkg.id,
            "name": pkg.name,
            "task": pkg.task,
            "objective": pkg.objective,
            "repository_id": pkg.repository_id,
            "repository_name": pkg.repository_name,
            "repository_branch": pkg.repository_branch,
            "repository_commit": pkg.repository_commit,
            "indexing_version": pkg.indexing_version,
            "markdown": pkg.markdown,
            "section_count": pkg.section_count,
            "token_estimate": pkg.token_estimate,
            "retrieved_memories": pkg.retrieved_memories,
            "deduplicated_memories": pkg.deduplicated_memories,
            "compression_ratio": pkg.compression_ratio,
            "total_time_ms": pkg.total_time_ms,
            "created_at": pkg.created_at,
            "updated_at": pkg.updated_at,
            "tags": pkg.tags,
        }

    @staticmethod
    def _from_dict(data: dict) -> SavedContextPackage:
        return SavedContextPackage(
            id=data.get("id", ""),
            name=data.get("name", ""),
            task=data.get("task", ""),
            objective=data.get("objective", ""),
            repository_id=data.get("repository_id", ""),
            repository_name=data.get("repository_name", ""),
            repository_branch=data.get("repository_branch", ""),
            repository_commit=data.get("repository_commit", ""),
            indexing_version=data.get("indexing_version", ""),
            markdown=data.get("markdown", ""),
            section_count=data.get("section_count", 0),
            token_estimate=data.get("token_estimate", 0),
            retrieved_memories=data.get("retrieved_memories", 0),
            deduplicated_memories=data.get("deduplicated_memories", 0),
            compression_ratio=data.get("compression_ratio", 0.0),
            total_time_ms=data.get("total_time_ms", 0),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            tags=data.get("tags", []),
        )

    async def save(self, package: SavedContextPackage) -> SavedContextPackage:
        packages = self._load()
        packages[package.id] = self._to_dict(package)
        self._save_all(packages)
        return package

    async def get(self, package_id: str) -> Optional[SavedContextPackage]:
        packages = self._load()
        data = packages.get(package_id)
        if data is None:
            return None
        return self._from_dict(data)

    async def list_all(self) -> list[SavedContextPackage]:
        packages = self._load()
        result = [self._from_dict(d) for d in packages.values()]
        result.sort(key=lambda p: p.created_at)
        return result

    async def delete(self, package_id: str) -> bool:
        packages = self._load()
        if package_id not in packages:
            return False
        del packages[package_id]
        self._save_all(packages)
        return True

    async def append(
        self,
        package_id: str,
        additional_task: str,
        additional_markdown: str,
        additional_objective: str = "",
    ) -> Optional[SavedContextPackage]:
        packages = self._load()
        data = packages.get(package_id)
        if data is None:
            return None

        pkg = self._from_dict(data)
        pkg.markdown += MARKDOWN_SEPARATOR + additional_markdown
        pkg.task = additional_task
        if additional_objective:
            pkg.objective = additional_objective

        packages[package_id] = self._to_dict(pkg)
        self._save_all(packages)
        return pkg
