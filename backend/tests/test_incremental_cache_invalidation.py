"""Tests for Phase 10A Dependency-Aware Context Cache Invalidation."""

from pathlib import Path
import pytest

from app.services.context_cache import ContextCacheEngine


def test_cache_key_generation():
    key1 = ContextCacheEngine.make_key(
        repo_path="/path/to/repo",
        manifest_hash="abc12345",
        task_prompt="Implement authentication service",
        max_tokens=8000,
    )
    key2 = ContextCacheEngine.make_key(
        repo_path="/path/to/repo",
        manifest_hash="abc12345",
        task_prompt="  implement   authentication service  ",
        max_tokens=8000,
    )
    assert key1 == key2


def test_unrelated_file_change_preserves_cache():
    """Modifying an unrelated file does NOT invalidate cache entries that do not depend on it."""
    cache = ContextCacheEngine()
    repo = "/test/repo"
    
    key_auth = cache.make_key(repo, "hash1", "authenticate user", 8000)
    cache.set(
        key=key_auth,
        value={"package": "auth_context"},
        repo_path=repo,
        referenced_files=["services/auth.py", "models/user.py"],
        referenced_symbols=["AuthService", "verify_token"],
    )

    # Invalidate unrelated change: utils.py modified
    removed = cache.invalidate_selective(
        repo_path=repo,
        changed_files=["utils.py"],
        deleted_files=[],
        changed_symbols=["helper"],
    )

    assert removed == 0
    assert cache.get(key_auth) == {"package": "auth_context"}


def test_related_file_change_invalidates_dependent_entries():
    """Modifying a referenced file or symbol invalidates only the dependent cache entry."""
    cache = ContextCacheEngine()
    repo = "/test/repo"

    key_auth = cache.make_key(repo, "hash1", "authenticate user", 8000)
    cache.set(
        key=key_auth,
        value={"package": "auth_context"},
        repo_path=repo,
        referenced_files=["services/auth.py"],
        referenced_symbols=["AuthService"],
    )

    key_billing = cache.make_key(repo, "hash1", "process payment", 8000)
    cache.set(
        key=key_billing,
        value={"package": "billing_context"},
        repo_path=repo,
        referenced_files=["services/billing.py"],
        referenced_symbols=["BillingService"],
    )

    # Invalidate auth.py modification
    removed = cache.invalidate_selective(
        repo_path=repo,
        changed_files=["services/auth.py"],
        deleted_files=[],
        changed_symbols=["AuthService"],
    )

    assert removed == 1
    assert cache.get(key_auth) is None  # Evicted
    assert cache.get(key_billing) == {"package": "billing_context"}  # Preserved!


def test_deleted_file_invalidates_dependent_entries():
    """Deleting a file invalidates entries referencing that file."""
    cache = ContextCacheEngine()
    repo = "/test/repo"

    key_auth = cache.make_key(repo, "hash1", "authenticate user", 8000)
    cache.set(
        key=key_auth,
        value={"package": "auth_context"},
        repo_path=repo,
        referenced_files=["services/auth.py"],
    )

    removed = cache.invalidate_selective(
        repo_path=repo,
        changed_files=[],
        deleted_files=["services/auth.py"],
    )

    assert removed == 1
    assert cache.get(key_auth) is None


def test_legacy_cache_entry_without_provenance_is_conservatively_invalidated():
    """Entries without provenance metadata are conservatively evicted when selective invalidation runs."""
    cache = ContextCacheEngine()
    repo = "/test/repo"

    key_legacy = cache.make_key(repo, "hash1", "old query", 8000)
    # Stored without referenced_files or referenced_symbols
    cache.set(key=key_legacy, value={"legacy": True}, repo_path=repo)

    removed = cache.invalidate_selective(
        repo_path=repo,
        changed_files=["anything.py"],
    )

    assert removed == 1
    assert cache.get(key_legacy) is None
