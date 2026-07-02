"""Tests for SavedContextPackage model and ContextPackageRepository."""

import asyncio
import pytest

from app.models.context_package import SavedContextPackage
from app.services.context_package_repository import (
    JsonContextPackageRepository,
    MARKDOWN_SEPARATOR,
)


@pytest.fixture
def store(tmp_path):
    """Create a JsonContextPackageRepository isolated to a temp directory."""
    return JsonContextPackageRepository(store_path=tmp_path / "pkgs.json")


@pytest.fixture
def sample_pkg():
    """A sample SavedContextPackage for reuse across tests."""
    return SavedContextPackage(
        id="pkg-001",
        name="auth-bug-fix",
        task="Fix authentication error",
        objective="Resolve 403 on login",
        repository_id="repo-1",
        repository_name="my-app",
        repository_branch="main",
        repository_commit="abc1234",
        indexing_version="2.0",
        markdown="# Context\n\nSome context.",
        section_count=3,
        token_estimate=150,
        retrieved_memories=10,
        deduplicated_memories=8,
        compression_ratio=1.25,
        total_time_ms=500,
        created_at="2026-06-30T10:00:00Z",
        updated_at="2026-06-30T10:00:00Z",
        tags=["bug", "auth"],
    )


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_save_and_list(store, sample_pkg):
    run(store.save(sample_pkg))
    items = run(store.list_all())
    assert len(items) == 1
    assert items[0].id == "pkg-001"
    assert items[0].task == "Fix authentication error"


def test_get_package(store, sample_pkg):
    run(store.save(sample_pkg))
    fetched = run(store.get("pkg-001"))
    assert fetched is not None
    assert fetched.name == "auth-bug-fix"
    assert fetched.objective == "Resolve 403 on login"


def test_delete_package(store, sample_pkg):
    run(store.save(sample_pkg))
    deleted = run(store.delete("pkg-001"))
    assert deleted is True
    assert run(store.get("pkg-001")) is None


def test_append_package(store, sample_pkg):
    run(store.save(sample_pkg))
    result = run(
        store.append(
            "pkg-001",
            additional_task="Add RBAC support",
            additional_markdown="# Additional\n\nNew section.",
            additional_objective="Role-based access control",
        )
    )
    assert result is not None
    assert "New section." in result.markdown
    assert result.markdown.startswith("# Context\n\nSome context.")
    assert MARKDOWN_SEPARATOR in result.markdown
    assert result.task == "Add RBAC support"
    assert result.objective == "Role-based access control"


def test_provenance_fields(store, sample_pkg):
    run(store.save(sample_pkg))
    fetched = run(store.get("pkg-001"))
    assert fetched.repository_branch == "main"
    assert fetched.repository_commit == "abc1234"
    assert fetched.indexing_version == "2.0"
    assert fetched.repository_id == "repo-1"
    assert fetched.repository_name == "my-app"


def test_list_sorted_by_date(store):
    p1 = SavedContextPackage(id="p1", name="first", task="t1", created_at="2026-06-30T08:00:00Z")
    p2 = SavedContextPackage(id="p2", name="second", task="t2", created_at="2026-06-30T06:00:00Z")
    p3 = SavedContextPackage(id="p3", name="third", task="t3", created_at="2026-06-30T10:00:00Z")
    run(store.save(p1))
    run(store.save(p2))
    run(store.save(p3))
    items = run(store.list_all())
    dates = [i.created_at for i in items]
    assert dates == sorted(dates)


def test_get_nonexistent_returns_none(store):
    assert run(store.get("no-such-id")) is None


def test_delete_nonexistent_returns_false(store):
    assert run(store.delete("no-such-id")) is False
