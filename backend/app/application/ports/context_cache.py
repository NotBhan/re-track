"""Abstract context synthesis cache port."""

from typing import Any, Optional, Protocol, Sequence, Set


class ContextCachePort(Protocol):
    """Port for caching synthesized context packages by deterministic prompt hash."""

    @staticmethod
    def make_key(
        repo_path: str,
        manifest_hash: str,
        task_prompt: str,
        max_tokens: int,
    ) -> str:
        """Generate a deterministic cache key."""
        ...

    def get(self, key: str) -> Optional[Any]:
        """Retrieve cached value if present and unexpired."""
        ...

    def set(
        self,
        key: str,
        value: Any,
        repo_path: str = "",
        referenced_files: Optional[Set[str] | Sequence[str]] = None,
        referenced_symbols: Optional[Set[str] | Sequence[str]] = None,
    ) -> None:
        """Store synthesized context in cache with provenance."""
        ...

    def invalidate_repo(self, repo_path: str) -> int:
        """Invalidate all cached entries for a given repository path."""
        ...

    def invalidate_selective(
        self,
        repo_path: str,
        changed_files: Set[str] | Sequence[str],
        deleted_files: Set[str] | Sequence[str] = (),
        changed_symbols: Set[str] | Sequence[str] = (),
    ) -> int:
        """Selectively invalidate cache entries affected by modified/deleted files or symbols."""
        ...

    def clear(self) -> None:
        """Clear all cached entries."""
        ...

    @property
    def stats(self) -> dict[str, Any]:
        """Retrieve cache hit/miss statistics."""
        ...
