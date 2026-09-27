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


# ---------------------------------------------------------------------------
# Replacement (re-synthesis) — replacing generated content, never appending
# ---------------------------------------------------------------------------


def test_replace_supersedes_the_record_without_creating_another(store, sample_pkg):
    run(store.save(sample_pkg))
    replacement = SavedContextPackage(
        **{
            **sample_pkg.__dict__,
            "markdown": "# Context\n\nRegenerated.",
            "token_estimate": 42,
            "updated_at": "2026-07-01T12:00:00Z",
        }
    )

    replaced = run(store.replace("pkg-001", replacement))

    assert replaced is not None
    assert replaced.markdown == "# Context\n\nRegenerated."
    assert MARKDOWN_SEPARATOR not in replaced.markdown
    assert replaced.token_estimate == 42
    assert replaced.created_at == "2026-06-30T10:00:00Z"
    items = run(store.list_all())
    assert len(items) == 1, "a replacement must not create a second package"
    assert items[0].markdown == "# Context\n\nRegenerated."


def test_replace_preserves_identity_fields(store, sample_pkg):
    run(store.save(sample_pkg))
    replacement = SavedContextPackage(**{**sample_pkg.__dict__, "markdown": "new", "updated_at": "2026-07-01T12:00:00Z"})

    replaced = run(store.replace("pkg-001", replacement))

    assert replaced.id == "pkg-001"
    assert replaced.name == "auth-bug-fix"
    assert replaced.task == "Fix authentication error"
    assert replaced.repository_id == "repo-1"
    assert replaced.repository_name == "my-app"
    assert replaced.tags == ["bug", "auth"]


def test_replace_missing_package_returns_none(store, sample_pkg):
    assert run(store.replace("no-such-id", sample_pkg)) is None


def test_replace_refuses_a_mismatched_replacement(store, sample_pkg):
    run(store.save(sample_pkg))
    other = SavedContextPackage(**{**sample_pkg.__dict__, "id": "pkg-999", "markdown": "other"})

    with pytest.raises(ValueError):
        run(store.replace("pkg-001", other))

    assert run(store.get("pkg-001")).markdown == "# Context\n\nSome context."


def test_replace_failure_leaves_the_previous_package_intact(store, sample_pkg, monkeypatch):
    run(store.save(sample_pkg))
    replacement = SavedContextPackage(**{**sample_pkg.__dict__, "markdown": "regenerated", "updated_at": "later"})

    def failing_save(_packages):
        raise OSError("disk full")

    monkeypatch.setattr(store, "_save_all", failing_save)
    with pytest.raises(OSError):
        run(store.replace("pkg-001", replacement))

    monkeypatch.undo()
    stored = run(store.get("pkg-001"))
    assert stored.markdown == "# Context\n\nSome context.", "a failed replacement must not overwrite the old package"


def test_append_and_replace_are_distinct_operations(store, sample_pkg):
    run(store.save(sample_pkg))
    appended = run(
        store.append("pkg-001", additional_task="Add RBAC", additional_markdown="# More", additional_objective="")
    )
    assert MARKDOWN_SEPARATOR in appended.markdown
    assert appended.task == "Add RBAC"

    replacement = SavedContextPackage(
        **{**appended.__dict__, "markdown": "# Only the regenerated content", "updated_at": "2026-07-02T00:00:00Z"}
    )
    replaced = run(store.replace("pkg-001", replacement))
    assert replaced.markdown == "# Only the regenerated content"
    assert replaced.task == "Add RBAC", "replacement never changes the task the package regenerates"


# ---------------------------------------------------------------------------
# PackageUseCases.replace_context_package — the re-synthesis contract
# ---------------------------------------------------------------------------


@pytest.fixture
def use_cases(store):
    from app.application.use_cases.context_packages import PackageUseCases

    return PackageUseCases(package_repository=store)


def test_use_case_replace_refreshes_generated_fields_and_keeps_the_record(use_cases, store, sample_pkg):
    from app.application.dto import ContextPackageReplaceRequest

    run(store.save(sample_pkg))
    result = run(
        use_cases.replace_context_package(
            "pkg-001",
            ContextPackageReplaceRequest(
                markdown="# Regenerated\n\n- fresh evidence",
                objective="Regenerated objective",
                token_estimate=99,
                total_time_ms=1234.0,
                repository_commit="def5678",
            ),
        )
    )

    assert result.id == "pkg-001"
    assert result.name == "auth-bug-fix"
    assert result.task == "Fix authentication error", "the task being regenerated is never silently changed"
    assert result.markdown == "# Regenerated\n\n- fresh evidence"
    assert result.objective == "Regenerated objective"
    assert result.token_estimate == 99
    assert result.total_time_ms == 1234.0
    assert result.repository_commit == "def5678"
    assert result.retrieved_memories == sample_pkg.retrieved_memories, "unreported fields keep their stored value"
    assert result.section_count == sample_pkg.section_count
    assert result.created_at == sample_pkg.created_at
    assert result.updated_at > sample_pkg.updated_at, "a replacement refreshes updated_at"

    items = run(store.list_all())
    assert len(items) == 1, "re-synthesis updates the package instead of adding another"


def test_use_case_replace_reports_a_missing_package(use_cases):
    from app.application.dto import ContextPackageReplaceRequest

    result = run(use_cases.replace_context_package("gone", ContextPackageReplaceRequest(markdown="x")))

    assert result.error == "NotFoundError"
    assert "gone" in result.message


def test_use_case_replace_keeps_the_old_content_when_the_write_fails(use_cases, store, sample_pkg, monkeypatch):
    from app.application.dto import ContextPackageReplaceRequest

    run(store.save(sample_pkg))
    monkeypatch.setattr(store, "_save_all", lambda _packages: (_ for _ in ()).throw(OSError("read-only store")))

    result = run(use_cases.replace_context_package("pkg-001", ContextPackageReplaceRequest(markdown="# new")))

    assert "read-only store" in result.message
    monkeypatch.undo()
    assert run(store.get("pkg-001")).markdown == "# Context\n\nSome context."
