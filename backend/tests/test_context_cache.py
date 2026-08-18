"""Unit tests for ContextCacheEngine in backend/app/services/context_cache.py."""

import time
import pytest
from app.services.context_cache import ContextCacheEngine


def test_cache_key_determinism():
    key1 = ContextCacheEngine.make_key(
        repo_path="/path/to/repo",
        manifest_hash="m123",
        task_prompt="Explain authentication flow",
        max_tokens=8000,
    )
    key2 = ContextCacheEngine.make_key(
        repo_path="/path/to/repo",
        manifest_hash="m123",
        task_prompt="  explain   authentication   flow  ",
        max_tokens=8000,
    )
    assert key1 == key2
    assert len(key1) == 64  # SHA-256 hex length


def test_cache_set_and_get():
    cache = ContextCacheEngine(max_entries=10, ttl_seconds=60)
    key = "sample_key_1"
    value = {"markdown": "# Context", "tokens": 150}

    assert cache.get(key) is None
    cache.set(key, value, repo_path="/path/to/repo")

    cached_value = cache.get(key)
    assert cached_value == value
    stats = cache.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["entries"] == 1


def test_cache_ttl_expiry():
    cache = ContextCacheEngine(max_entries=5, ttl_seconds=0.05)
    key = "expiring_key"
    cache.set(key, "data", repo_path="/repo")

    assert cache.get(key) == "data"
    time.sleep(0.06)
    assert cache.get(key) is None


def test_cache_invalidation_by_repo():
    cache = ContextCacheEngine(max_entries=10, ttl_seconds=60)
    cache.set("k1", "val1", repo_path="/repo/a")
    cache.set("k2", "val2", repo_path="/repo/a")
    cache.set("k3", "val3", repo_path="/repo/b")

    assert cache.get("k1") == "val1"
    assert cache.get("k3") == "val3"

    removed = cache.invalidate_repo("/repo/a")
    assert removed == 2
    assert cache.get("k1") is None
    assert cache.get("k2") is None
    assert cache.get("k3") == "val3"


def test_cache_lru_eviction():
    cache = ContextCacheEngine(max_entries=2, ttl_seconds=60)
    cache.set("k1", "v1", repo_path="/r")
    cache.set("k2", "v2", repo_path="/r")

    # Access k1 to make k2 the least recently used
    assert cache.get("k1") == "v1"

    # Insert k3 -> should evict k2
    cache.set("k3", "v3", repo_path="/r")

    assert cache.get("k1") == "v1"
    assert cache.get("k2") is None
    assert cache.get("k3") == "v3"
