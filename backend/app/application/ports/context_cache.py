"""Abstract context synthesis cache port."""

from typing import Any, Optional, Protocol


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

    def set(self, key: str, value: Any, repo_path: str = "") -> None:
        """Store synthesized context in cache."""
        ...

    def invalidate_repo(self, repo_path: str) -> int:
        """Invalidate all cached entries for a given repository path."""
        ...

    def clear(self) -> None:
        """Clear all cached entries."""
        ...

    @property
    def stats(self) -> dict[str, Any]:
        """Retrieve cache hit/miss statistics."""
        ...
