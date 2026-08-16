"""
Manifest management for incremental repository indexing in RE:Track.

Tracks file modification times, sha256 checksums, and dataset mappings
to detect file additions, modifications, and deletions.
"""

from dataclasses import asdict, dataclass, field
import hashlib
import json
import logging
from pathlib import Path
import time
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class FileFingerprint:
    """Metadata fingerprint for a single indexed file."""

    path: str
    mtime: float
    size: int
    sha256: str
    last_indexed_at: float


@dataclass
class RepositoryManifest:
    """Persistent manifest representing the indexed state of a repository."""

    repo_path: str
    dataset_name: str
    created_at: float
    updated_at: float
    files: dict[str, FileFingerprint] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "repo_path": self.repo_path,
            "dataset_name": self.dataset_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "files": {p: asdict(fp) for p, fp in self.files.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RepositoryManifest":
        files = {
            p: FileFingerprint(**fp_data)
            for p, fp_data in data.get("files", {}).items()
        }
        return cls(
            repo_path=data["repo_path"],
            dataset_name=data["dataset_name"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            files=files,
        )


@dataclass
class IndexDelta:
    """Differences between working tree and last known manifest."""

    added: list[Path] = field(default_factory=list)
    modified: list[Path] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)  # Relative paths
    unchanged: list[Path] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.modified or self.deleted)

    @property
    def total_changed(self) -> int:
        return len(self.added) + len(self.modified) + len(self.deleted)


class ManifestService:
    """Stores and computes file-level diff manifests for repositories."""

    def __init__(self, storage_dir: Optional[Path] = None) -> None:
        if storage_dir is None:
            self._storage_dir = Path.home() / ".retrack" / "manifests"
        else:
            self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_manifest_path(self, repo_path: Path) -> Path:
        canonical = str(repo_path.resolve())
        repo_id = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
        return self._storage_dir / f"{repo_id}.json"

    def load_manifest(self, repo_path: Path) -> Optional[RepositoryManifest]:
        """Load manifest from disk if it exists."""
        manifest_file = self._get_manifest_path(repo_path)
        if not manifest_file.exists():
            return None
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return RepositoryManifest.from_dict(data)
        except Exception as e:
            logger.warning("Failed to read manifest %s: %s", manifest_file, e)
            return None

    def save_manifest(self, manifest: RepositoryManifest) -> None:
        """Persist manifest to disk."""
        manifest_file = self._get_manifest_path(Path(manifest.repo_path))
        manifest.updated_at = time.time()
        try:
            with open(manifest_file, "w", encoding="utf-8") as f:
                json.dump(manifest.to_dict(), f, indent=2)
            logger.debug("Saved manifest to %s", manifest_file)
        except Exception as e:
            logger.error("Failed to write manifest %s: %s", manifest_file, e)

    @staticmethod
    def compute_sha256(file_path: Path) -> str:
        """Compute SHA256 checksum of a file."""
        hasher = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.warning("Failed to compute hash for %s: %s", file_path, e)
            return ""

    def compute_delta(
        self,
        repo_path: Path,
        discovered_files: list[Path],
    ) -> tuple[IndexDelta, Optional[RepositoryManifest]]:
        """Compute added, modified, deleted, and unchanged files."""
        repo_path = repo_path.resolve()
        manifest = self.load_manifest(repo_path)

        if manifest is None:
            # First time indexing: all discovered files are added
            delta = IndexDelta(added=list(discovered_files))
            return delta, None

        current_rel_paths: dict[str, Path] = {}
        for f in discovered_files:
            try:
                rel = str(f.resolve().relative_to(repo_path))
                current_rel_paths[rel] = f
            except ValueError:
                continue

        known_rel_paths = set(manifest.files.keys())
        current_set = set(current_rel_paths.keys())

        deleted = list(known_rel_paths - current_set)
        added = [current_rel_paths[p] for p in (current_set - known_rel_paths)]
        modified: list[Path] = []
        unchanged: list[Path] = []

        # Check existing files for changes using mtime first, then sha256
        for rel in current_set & known_rel_paths:
            full_path = current_rel_paths[rel]
            fingerprint = manifest.files[rel]
            try:
                stat = full_path.stat()
                # If mtime or size changed, check content hash
                if stat.st_mtime != fingerprint.mtime or stat.st_size != fingerprint.size:
                    current_hash = self.compute_sha256(full_path)
                    if current_hash != fingerprint.sha256:
                        modified.append(full_path)
                    else:
                        unchanged.append(full_path)
                else:
                    unchanged.append(full_path)
            except Exception:
                modified.append(full_path)

        delta = IndexDelta(
            added=added,
            modified=modified,
            deleted=deleted,
            unchanged=unchanged,
        )
        return delta, manifest

    def update_manifest(
        self,
        repo_path: Path,
        dataset_name: str,
        indexed_files: list[Path],
        deleted_rel_paths: list[str],
        existing_manifest: Optional[RepositoryManifest] = None,
    ) -> RepositoryManifest:
        """Update and persist manifest with newly indexed files and deletions."""
        now = time.time()
        repo_path = repo_path.resolve()

        if existing_manifest:
            manifest = existing_manifest
            manifest.dataset_name = dataset_name
        else:
            manifest = RepositoryManifest(
                repo_path=str(repo_path),
                dataset_name=dataset_name,
                created_at=now,
                updated_at=now,
            )

        # Remove deleted
        for rel in deleted_rel_paths:
            manifest.files.pop(rel, None)

        # Add/update indexed
        for f in indexed_files:
            try:
                rel = str(f.resolve().relative_to(repo_path))
                stat = f.stat()
                sha = self.compute_sha256(f)
                manifest.files[rel] = FileFingerprint(
                    path=rel,
                    mtime=stat.st_mtime,
                    size=stat.st_size,
                    sha256=sha,
                    last_indexed_at=now,
                )
            except Exception as e:
                logger.warning("Failed to record fingerprint for %s: %s", f, e)

        self.save_manifest(manifest)
        return manifest
