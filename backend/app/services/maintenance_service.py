"""Maintenance, migration, and reset service for RE:Track.

Provides explicit, safe data migration from legacy ~/.andes/ to canonical ~/.retrack/,
and scoped reset utilities (cache, state, all) with mandatory confirmation safeguards
and automated pre-reset backups. Never modifies user source repositories.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import logging
from pathlib import Path
import shutil
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ResetScope(str, Enum):
    """Scope of data reset."""

    CACHE = "cache"
    STATE = "state"
    ALL = "all"


@dataclass
class ResetResult:
    """Summary of a reset operation."""

    success: bool
    scope: ResetScope
    backup_path: Optional[str] = None
    deleted_files: list[str] = field(default_factory=list)
    reinitialized_files: list[str] = field(default_factory=list)
    message: str = ""


@dataclass
class MigrationItem:
    """Item identified for legacy migration."""

    source_path: str
    target_path: str
    item_type: str  # "file" or "directory"
    size_bytes: int


@dataclass
class MigrationResult:
    """Summary of a legacy migration operation."""

    success: bool
    dry_run: bool
    backup_path: Optional[str] = None
    items_migrated: list[MigrationItem] = field(default_factory=list)
    skipped_items: list[str] = field(default_factory=list)
    total_bytes_migrated: int = 0
    message: str = ""


class MaintenanceService:
    """Service handling state resets and legacy data migration."""

    def __init__(
        self,
        retrack_dir: Optional[Path | str] = None,
        legacy_dir: Optional[Path | str] = None,
    ):
        self._retrack_dir = Path(retrack_dir) if retrack_dir is not None else Path.home() / ".retrack"
        self._legacy_dir = Path(legacy_dir) if legacy_dir is not None else Path.home() / ".andes"

    def create_backup(self, prefix: str = "backup") -> Path:
        """Create a timestamped snapshot of current ~/.retrack state."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_dir = self._retrack_dir / "backups" / f"{prefix}_{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)

        if not self._retrack_dir.exists():
            return backup_dir

        for item in self._retrack_dir.iterdir():
            if item.name == "backups":
                continue
            dest = backup_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            elif item.is_file():
                shutil.copy2(item, dest)

        return backup_dir

    def reset_data(self, scope: ResetScope, confirm: bool = False) -> ResetResult:
        """Perform a scoped reset of RE:Track runtime state.

        Args:
            scope: ResetScope (CACHE, STATE, ALL).
            confirm: Must be True for STATE and ALL resets.

        Returns:
            ResetResult detailing deleted and re-initialized state.

        Raises:
            ValueError: If confirmation is missing for STATE or ALL resets.
        """
        deleted_files: list[str] = []
        reinitialized_files: list[str] = []

        if scope == ResetScope.CACHE:
            cache_dir = self._retrack_dir / "cache"
            if cache_dir.exists() and cache_dir.is_dir():
                for item in cache_dir.iterdir():
                    if item.is_file() or item.is_symlink():
                        deleted_files.append(str(item))
                        item.unlink()
                    elif item.is_dir():
                        deleted_files.append(str(item))
                        shutil.rmtree(item)
            else:
                cache_dir.mkdir(parents=True, exist_ok=True)

            return ResetResult(
                success=True,
                scope=scope,
                deleted_files=deleted_files,
                message=f"Cache cleared successfully ({len(deleted_files)} files/folders purged).",
            )

        # STATE and ALL require explicit confirmation
        if not confirm:
            raise ValueError(
                f"Resetting {scope.value} requires explicit confirmation (--confirm flag). "
                "This action clears registered repository metadata and packages."
            )

        # Create a safety backup first
        backup_path = self.create_backup(prefix=f"pre_reset_{scope.value}")

        if scope == ResetScope.STATE:
            # 1. Clear manifests
            manifests_dir = self._retrack_dir / "manifests"
            if manifests_dir.exists():
                for m in manifests_dir.glob("*.json"):
                    deleted_files.append(str(m))
                    m.unlink()

            # 2. Reset repository metadata files
            for fname in ["indexed_repos.json", "repositories.json"]:
                fpath = self._retrack_dir / fname
                fpath.write_text("[]")
                reinitialized_files.append(str(fpath))

            # 3. Reset packages file
            pkg_file = self._retrack_dir / "context_packages.json"
            pkg_file.write_text("{}")
            reinitialized_files.append(str(pkg_file))

            # 4. Clear cache
            cache_dir = self._retrack_dir / "cache"
            if cache_dir.exists():
                for c in cache_dir.iterdir():
                    if c.is_file():
                        c.unlink()
                    elif c.is_dir():
                        shutil.rmtree(c)

            return ResetResult(
                success=True,
                scope=scope,
                backup_path=str(backup_path),
                deleted_files=deleted_files,
                reinitialized_files=reinitialized_files,
                message=(
                    f"Application state reset complete. Backup created at {backup_path}. "
                    "User source repositories remain untouched."
                ),
            )

        elif scope == ResetScope.ALL:
            # Clear all state and restore default configuration
            manifests_dir = self._retrack_dir / "manifests"
            if manifests_dir.exists():
                for m in manifests_dir.iterdir():
                    deleted_files.append(str(m))
                    if m.is_dir():
                        shutil.rmtree(m)
                    else:
                        m.unlink()

            cache_dir = self._retrack_dir / "cache"
            if cache_dir.exists():
                for c in cache_dir.iterdir():
                    deleted_files.append(str(c))
                    if c.is_dir():
                        shutil.rmtree(c)
                    else:
                        c.unlink()

            # Reset files
            for fname in ["indexed_repos.json", "repositories.json"]:
                fpath = self._retrack_dir / fname
                fpath.write_text("[]")
                reinitialized_files.append(str(fpath))

            pkg_file = self._retrack_dir / "context_packages.json"
            pkg_file.write_text("{}")
            reinitialized_files.append(str(pkg_file))

            # Reset settings.json
            from app.services.bootstrap_service import BootstrapService
            bs = BootstrapService(retrack_dir=self._retrack_dir, legacy_dir=self._legacy_dir)
            settings_file = self._retrack_dir / "settings.json"
            if settings_file.exists():
                settings_file.unlink()
            bs.initialize(check_provider=False)
            reinitialized_files.append(str(settings_file))

            return ResetResult(
                success=True,
                scope=scope,
                backup_path=str(backup_path),
                deleted_files=deleted_files,
                reinitialized_files=reinitialized_files,
                message=(
                    f"Full RE:Track environment reset complete. Backup saved at {backup_path}. "
                    "User source repositories remain untouched."
                ),
            )

        raise ValueError(f"Unknown reset scope: {scope}")

    def migrate_legacy_data(self, dry_run: bool = False) -> MigrationResult:
        """Migrate legacy ~/.andes data to canonical ~/.retrack.

        Copies records without altering or deleting legacy files.

        Args:
            dry_run: If True, only lists discoverable migration items without writing.

        Returns:
            MigrationResult detailing what was or would be migrated.
        """
        if not self._legacy_dir.exists() or not self._legacy_dir.is_dir():
            return MigrationResult(
                success=True,
                dry_run=dry_run,
                message=f"No legacy storage directory found at {self._legacy_dir}.",
            )

        items_to_migrate: list[MigrationItem] = []
        skipped_items: list[str] = []
        total_bytes = 0

        # Scan legacy items
        for item in self._legacy_dir.iterdir():
            target = self._retrack_dir / item.name
            if item.is_file():
                size = item.stat().st_size
                items_to_migrate.append(
                    MigrationItem(
                        source_path=str(item),
                        target_path=str(target),
                        item_type="file",
                        size_bytes=size,
                    )
                )
                total_bytes += size
            elif item.is_dir():
                # For directories like manifests/
                dir_size = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
                items_to_migrate.append(
                    MigrationItem(
                        source_path=str(item),
                        target_path=str(target),
                        item_type="directory",
                        size_bytes=dir_size,
                    )
                )
                total_bytes += dir_size

        if not items_to_migrate:
            return MigrationResult(
                success=True,
                dry_run=dry_run,
                message=f"Legacy directory {self._legacy_dir} is empty. Nothing to migrate.",
            )

        if dry_run:
            return MigrationResult(
                success=True,
                dry_run=True,
                items_migrated=items_to_migrate,
                total_bytes_migrated=total_bytes,
                message=f"Dry run: Found {len(items_to_migrate)} legacy item(s) ({total_bytes} bytes) ready for migration.",
            )

        # Actual migration
        backup_path = self.create_backup(prefix="pre_migration")

        for item in items_to_migrate:
            src = Path(item.source_path)
            dst = Path(item.target_path)

            if src.is_file():
                # Merge JSON lists or objects if target exists
                if dst.exists() and src.suffix == ".json":
                    try:
                        src_data = json.loads(src.read_text())
                        dst_data = json.loads(dst.read_text())

                        if isinstance(src_data, list) and isinstance(dst_data, list):
                            # Merge repository lists by repo_path, id, name, or content hash
                            merged = list(dst_data)
                            def _get_key(item: Any) -> str:
                                if isinstance(item, dict):
                                    return str(
                                        item.get("id")
                                        or item.get("path")
                                        or item.get("repo_path")
                                        or item.get("name")
                                        or json.dumps(item, sort_keys=True)
                                    )
                                return str(item)

                            existing_ids = {_get_key(r) for r in dst_data}
                            for r in src_data:
                                r_key = _get_key(r)
                                if r_key not in existing_ids:
                                    merged.append(r)
                                    existing_ids.add(r_key)
                            dst.write_text(json.dumps(merged, indent=2))
                        elif isinstance(src_data, dict) and isinstance(dst_data, dict):
                            # Merge packages or settings dicts
                            merged_dict = {**src_data, **dst_data}
                            dst.write_text(json.dumps(merged_dict, indent=2))
                        else:
                            shutil.copy2(src, dst)
                    except Exception:
                        shutil.copy2(src, dst)
                else:
                    shutil.copy2(src, dst)
            elif src.is_dir():
                dst.mkdir(parents=True, exist_ok=True)
                for sub in src.iterdir():
                    sub_dst = dst / sub.name
                    if sub.is_file() and not sub_dst.exists():
                        shutil.copy2(sub, sub_dst)
                    elif sub.is_dir() and not sub_dst.exists():
                        shutil.copytree(sub, sub_dst)

        return MigrationResult(
            success=True,
            dry_run=False,
            backup_path=str(backup_path),
            items_migrated=items_to_migrate,
            total_bytes_migrated=total_bytes,
            message=(
                f"Successfully migrated {len(items_to_migrate)} legacy item(s) into {self._retrack_dir}. "
                f"Backup created at {backup_path}. Legacy files in {self._legacy_dir} remain unmodified."
            ),
        )
