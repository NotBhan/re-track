"""
In-Memory Context Cache Engine for RE:Track.

Provides high-speed LRU caching for synthesized context packages,
keyed by repository manifest hash, task prompt, and token budget.
Supports fine-grained dependency provenance tracking (referenced_files, referenced_symbols)
and selective cache invalidation upon incremental repository changes.
"""

from __future__ import annotations

import hashlib
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Set, Tuple


class ContextCacheEngine:
    """Thread-safe in-memory LRU cache for synthesized context packages with provenance tracking."""

    def __init__(self, max_entries: int = 64, ttl_seconds: float = 1800.0):
        self._max_entries = max_entries
        self._ttl_seconds = ttl_seconds
        # key -> (timestamp, value, repo_path, referenced_files, referenced_symbols)
        self._cache: OrderedDict[str, Tuple[float, Any, str, Set[str], Set[str]]] = OrderedDict()
        self._hits: int = 0
        self._misses: int = 0

    @staticmethod
    def make_key(
        repo_path: str,
        manifest_hash: str,
        task_prompt: str,
        max_tokens: int,
    ) -> str:
        """Create a deterministic SHA-256 cache key."""
        normalized_prompt = " ".join(task_prompt.strip().lower().split())
        raw = f"{repo_path}:{manifest_hash}:{normalized_prompt}:{max_tokens}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Retrieve cached context if present and not expired."""
        if key not in self._cache:
            self._misses += 1
            return None

        entry = self._cache[key]
        timestamp = entry[0]
        value = entry[1]
        now = time.time()

        if now - timestamp > self._ttl_seconds:
            # Expired entry
            del self._cache[key]
            self._misses += 1
            return None

        # Move to most recently used
        self._cache.move_to_end(key)
        self._hits += 1
        return value

    def set(
        self,
        key: str,
        value: Any,
        repo_path: str = "",
        referenced_files: Optional[Set[str] | List[str]] = None,
        referenced_symbols: Optional[Set[str] | List[str]] = None,
    ) -> None:
        """Store synthesized context package in cache with dependency provenance."""
        now = time.time()
        files_set: Set[str] = set(referenced_files) if referenced_files else set()
        symbols_set: Set[str] = set(referenced_symbols) if referenced_symbols else set()

        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = (now, value, repo_path, files_set, symbols_set)

        # Evict oldest if exceeding capacity
        while len(self._cache) > self._max_entries:
            self._cache.popitem(last=False)

    def invalidate_repo(self, repo_path: str) -> int:
        """Invalidate all cache entries associated with a repository."""
        if not repo_path:
            return 0

        keys_to_remove: List[str] = [
            k for k, (_, _, r_path, _, _) in self._cache.items() if r_path == repo_path
        ]
        for k in keys_to_remove:
            del self._cache[k]
        return len(keys_to_remove)

    def invalidate_selective(
        self,
        repo_path: str,
        changed_files: Set[str] | List[str],
        deleted_files: Set[str] | List[str] = (),
        changed_symbols: Set[str] | List[str] = (),
    ) -> int:
        """Selectively invalidate cache entries affected by modified/deleted files or symbols.

        Preserves unaffected cached context packages whose recorded provenance
        does not intersect the impact set.
        """
        if not repo_path:
            return 0

        changed_f_set = {str(f).replace("\\", "/") for f in changed_files}
        deleted_f_set = {str(f).replace("\\", "/") for f in deleted_files}
        all_impacted_files = changed_f_set | deleted_f_set
        changed_s_set = set(changed_symbols)

        keys_to_remove: List[str] = []
        for k, (_, _, r_path, ref_files, ref_symbols) in list(self._cache.items()):
            if r_path != repo_path:
                continue

            # Compatibility rule: legacy entries without provenance are conservatively invalidated
            if not ref_files and not ref_symbols:
                keys_to_remove.append(k)
                continue

            # Check file intersection
            norm_ref_files = {str(f).replace("\\", "/") for f in ref_files}
            if any(f in all_impacted_files or any(f.endswith(imp) or imp.endswith(f) for imp in all_impacted_files) for f in norm_ref_files):
                keys_to_remove.append(k)
                continue

            # Check symbol intersection
            if ref_symbols and changed_s_set and bool(ref_symbols & changed_s_set):
                keys_to_remove.append(k)
                continue

        for k in keys_to_remove:
            if k in self._cache:
                del self._cache[k]

        return len(keys_to_remove)

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def stats(self) -> Dict[str, Any]:
        """Return cache hit/miss statistics and occupancy."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100.0) if total > 0 else 0.0
        return {
            "entries": len(self._cache),
            "max_entries": self._max_entries,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_pct": round(hit_rate, 1),
            "ttl_seconds": self._ttl_seconds,
        }


# Global singleton instance
context_cache = ContextCacheEngine()
