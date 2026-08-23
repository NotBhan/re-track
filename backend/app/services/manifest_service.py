"""
Manifest management for incremental repository indexing in RE:Track.

Tracks file modification times, sha256 checksums, language, symbols, AST nodes,
and dataset mappings to detect file additions, modifications, deletions, and renames.
Provides atomic, crash-safe persistence and deterministic repository fingerprints.
"""

from dataclasses import asdict, dataclass, field
import hashlib
import json
import logging
import os
from pathlib import Path
import subprocess
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

MANIFEST_SCHEMA_VERSION = "2.0"
PARSER_VERSION = "2.0.0"


@dataclass
class FileFingerprint:
    """Metadata and deterministic AST fingerprint for a single indexed file."""

    path: str  # Normalized POSIX relative path
    mtime: float
    size: int
    sha256: str
    language: str = ""
    symbols: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    ast_nodes: list[dict[str, Any]] = field(default_factory=list)
    ast_edges: list[dict[str, Any]] = field(default_factory=list)
    last_indexed_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "mtime": self.mtime,
            "size": self.size,
            "sha256": self.sha256,
            "language": self.language,
            "symbols": list(self.symbols),
            "imports": list(self.imports),
            "ast_nodes": list(self.ast_nodes),
            "ast_edges": list(self.ast_edges),
            "last_indexed_at": self.last_indexed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FileFingerprint":
        return cls(
            path=data.get("path", ""),
            mtime=float(data.get("mtime", 0.0)),
            size=int(data.get("size", 0)),
            sha256=data.get("sha256", ""),
            language=data.get("language", ""),
            symbols=list(data.get("symbols", [])),
            imports=list(data.get("imports", [])),
            ast_nodes=list(data.get("ast_nodes", [])),
            ast_edges=list(data.get("ast_edges", [])),
            last_indexed_at=float(data.get("last_indexed_at", 0.0)),
        )


@dataclass
class RepositoryManifest:
    """Persistent manifest representing the validated indexed state of a repository."""

    repo_path: str
    dataset_name: str
    schema_version: str = MANIFEST_SCHEMA_VERSION
    parser_version: str = PARSER_VERSION
    repo_fingerprint: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    files: dict[str, FileFingerprint] = field(default_factory=dict)

    def compute_fingerprint(self) -> str:
        """Compute a deterministic SHA-256 fingerprint from schema, parser, and file identities."""
        hasher = hashlib.sha256()
        header = f"{self.schema_version}:{self.parser_version}:{self.repo_path}"
        hasher.update(header.encode("utf-8"))

        for rel_path in sorted(self.files.keys()):
            fp = self.files[rel_path]
            entry_str = f"|{rel_path}:{fp.sha256}:{fp.size}:{fp.language}"
            hasher.update(entry_str.encode("utf-8"))

        self.repo_fingerprint = hasher.hexdigest()[:16]
        return self.repo_fingerprint

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo_path": self.repo_path,
            "dataset_name": self.dataset_name,
            "schema_version": self.schema_version,
            "parser_version": self.parser_version,
            "repo_fingerprint": self.repo_fingerprint or self.compute_fingerprint(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "files": {p: fp.to_dict() for p, fp in self.files.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RepositoryManifest":
        files = {
            p: FileFingerprint.from_dict(fp_data)
            for p, fp_data in data.get("files", {}).items()
        }
        manifest = cls(
            repo_path=data.get("repo_path", ""),
            dataset_name=data.get("dataset_name", ""),
            schema_version=data.get("schema_version", "1.0"),
            parser_version=data.get("parser_version", "1.0.0"),
            repo_fingerprint=data.get("repo_fingerprint", ""),
            created_at=float(data.get("created_at", 0.0)),
            updated_at=float(data.get("updated_at", 0.0)),
            files=files,
        )
        if not manifest.repo_fingerprint:
            manifest.compute_fingerprint()
        return manifest


@dataclass
class IndexDelta:
    """Differences between working tree and last known manifest."""

    added: list[Path] = field(default_factory=list)
    modified: list[Path] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)  # Relative paths
    unchanged: list[Path] = field(default_factory=list)
    renamed: list[tuple[str, Path]] = field(default_factory=list)  # (old_rel_path, new_path)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.modified or self.deleted or self.renamed)

    @property
    def total_changed(self) -> int:
        return len(self.added) + len(self.modified) + len(self.deleted) + len(self.renamed)


class ManifestService:
    """Stores and computes file-level diff manifests for repositories."""

    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        legacy_storage_dir: Optional[Path] = None,
    ) -> None:
        if storage_dir is None:
            self._storage_dir = Path.home() / ".retrack" / "manifests"
            self._legacy_storage_dir = Path(legacy_storage_dir) if legacy_storage_dir is not None else (Path.home() / ".andes" / "manifests")
        else:
            self._storage_dir = Path(storage_dir)
            self._legacy_storage_dir = Path(legacy_storage_dir) if legacy_storage_dir is not None else None
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_manifest_path(self, repo_path: Path) -> Path:
        canonical = str(repo_path.resolve())
        repo_id = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
        return self._storage_dir / f"{repo_id}.json"

    def _get_legacy_manifest_path(self, repo_path: Path) -> Optional[Path]:
        if self._legacy_storage_dir is None:
            return None
        canonical = str(repo_path.resolve())
        repo_id = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
        return self._legacy_storage_dir / f"{repo_id}.json"

    def load_manifest(self, repo_path: Path) -> Optional[RepositoryManifest]:
        """Load manifest from disk if it exists and passes validation.

        Triggers a full rebuild if:
        - Manifest file is corrupted or unreadable.
        - Schema version mismatch.
        - Parser version mismatch.
        - Repository identity mismatch.
        """
        canonical_repo = str(repo_path.resolve())
        manifest_file = self._get_manifest_path(repo_path)
        raw_data: Optional[dict[str, Any]] = None

        if manifest_file.exists():
            try:
                with open(manifest_file, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
            except Exception as e:
                logger.warning("Manifest corrupted or unreadable %s: %s | triggering full rebuild", manifest_file, e)
                return None

        if raw_data is None:
            legacy_file = self._get_legacy_manifest_path(repo_path)
            if legacy_file is not None and legacy_file.exists():
                try:
                    with open(legacy_file, "r", encoding="utf-8") as f:
                        raw_data = json.load(f)
                except Exception as e:
                    logger.warning("Legacy manifest unreadable %s: %s", legacy_file, e)

        if raw_data is None:
            return None

        try:
            manifest = RepositoryManifest.from_dict(raw_data)

            # Invariant 1: Repository identity must match
            if manifest.repo_path != canonical_repo:
                logger.warning(
                    "Manifest repository path mismatch (%s != %s) | triggering full rebuild",
                    manifest.repo_path,
                    canonical_repo,
                )
                return None

            # Invariant 2: Schema version must match
            if manifest.schema_version != MANIFEST_SCHEMA_VERSION:
                logger.info(
                    "Manifest schema version mismatch (%s != %s) | triggering full rebuild",
                    manifest.schema_version,
                    MANIFEST_SCHEMA_VERSION,
                )
                return None

            # Invariant 3: Parser version must match
            if manifest.parser_version != PARSER_VERSION:
                logger.info(
                    "Manifest parser version mismatch (%s != %s) | triggering full rebuild",
                    manifest.parser_version,
                    PARSER_VERSION,
                )
                return None

            return manifest
        except Exception as e:
            logger.warning("Failed to validate manifest: %s | triggering full rebuild", e)
            return None

    def save_manifest(self, manifest: RepositoryManifest) -> None:
        """Persist manifest to canonical disk atomically with os.fsync and temporary file replace."""
        manifest_file = self._get_manifest_path(Path(manifest.repo_path))
        manifest.updated_at = time.time()
        manifest.compute_fingerprint()

        try:
            self._storage_dir.mkdir(parents=True, exist_ok=True)
            tmp_path = manifest_file.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(manifest.to_dict(), f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            tmp_path.replace(manifest_file)
            logger.debug("Saved manifest atomically to %s | fingerprint=%s", manifest_file, manifest.repo_fingerprint)
        except Exception as e:
            logger.error("Failed to write manifest %s: %s", manifest_file, e)
            raise

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

    def _try_git_change_detection(
        self,
        repo_path: Path,
        manifest: RepositoryManifest,
    ) -> Optional[dict[str, str]]:
        """Attempt fast Git-aware change detection when .git exists.

        Returns a dictionary mapping relative paths to git status codes, or None if git is unavailable.
        """
        git_dir = repo_path / ".git"
        if not git_dir.exists():
            return None

        try:
            res = subprocess.run(
                ["git", "status", "--porcelain=v1", "-uall"],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                timeout=2.0,
            )
            if res.returncode != 0:
                return None

            git_changes: dict[str, str] = {}
            for line in res.stdout.splitlines():
                if len(line) < 4:
                    continue
                code = line[:2].strip()
                path_part = line[3:].strip()
                if " -> " in path_part:
                    # Rename
                    path_part = path_part.split(" -> ")[-1].strip()
                # Normalize relative path
                norm_rel = str(Path(path_part).as_posix())
                git_changes[norm_rel] = code

            return git_changes
        except Exception as e:
            logger.debug("Git change detection skipped: %s", e)
            return None

    def compute_delta(
        self,
        repo_path: Path,
        discovered_files: list[Path],
    ) -> tuple[IndexDelta, Optional[RepositoryManifest]]:
        """Compute added, modified, deleted, unchanged, and renamed files.

        Uses Git metadata as an optimization if available, with deterministic
        filesystem comparison (mtime + size + SHA-256) as authoritative fallback.
        """
        repo_path = repo_path.resolve()
        manifest = self.load_manifest(repo_path)

        if manifest is None:
            # First time indexing or full rebuild triggered: all discovered files are added
            delta = IndexDelta(added=list(discovered_files))
            return delta, None

        current_rel_paths: dict[str, Path] = {}
        for f in discovered_files:
            try:
                rel = str(f.resolve().relative_to(repo_path).as_posix())
                current_rel_paths[rel] = f
            except ValueError:
                continue

        known_rel_paths = set(manifest.files.keys())
        current_set = set(current_rel_paths.keys())

        raw_deleted_set = known_rel_paths - current_set
        raw_added_set = current_set - known_rel_paths
        common_set = current_set & known_rel_paths

        modified: list[Path] = []
        unchanged: list[Path] = []

        # Check common files for modifications
        for rel in common_set:
            full_path = current_rel_paths[rel]
            fingerprint = manifest.files[rel]
            try:
                stat = full_path.stat()
                # Fast path: if mtime AND size match, file is unchanged
                if stat.st_mtime == fingerprint.mtime and stat.st_size == fingerprint.size:
                    unchanged.append(full_path)
                else:
                    # Content hash check
                    current_hash = self.compute_sha256(full_path)
                    if current_hash != fingerprint.sha256:
                        modified.append(full_path)
                    else:
                        # Mtime changed but content identical
                        unchanged.append(full_path)
            except Exception:
                modified.append(full_path)

        # Rename detection: match SHA-256 of raw_deleted against raw_added
        renamed: list[tuple[str, Path]] = []
        final_added: list[Path] = []
        final_deleted: list[str] = list(raw_deleted_set)

        # Build hash-to-added-paths map
        added_by_hash: dict[str, list[tuple[str, Path]]] = {}
        for rel in raw_added_set:
            full_path = current_rel_paths[rel]
            h = self.compute_sha256(full_path)
            if h:
                added_by_hash.setdefault(h, []).append((rel, full_path))

        matched_added_rels: set[str] = set()
        matched_deleted_rels: set[str] = set()

        for del_rel in raw_deleted_set:
            del_fp = manifest.files[del_rel]
            del_hash = del_fp.sha256
            if del_hash in added_by_hash and len(added_by_hash[del_hash]) == 1:
                # Unambiguous 1-to-1 rename
                new_rel, new_path = added_by_hash[del_hash][0]
                if new_rel not in matched_added_rels:
                    renamed.append((del_rel, new_path))
                    matched_added_rels.add(new_rel)
                    matched_deleted_rels.add(del_rel)

        final_deleted = [p for p in raw_deleted_set if p not in matched_deleted_rels]
        final_added = [current_rel_paths[p] for p in raw_added_set if p not in matched_added_rels]

        delta = IndexDelta(
            added=final_added,
            modified=modified,
            deleted=final_deleted,
            unchanged=unchanged,
            renamed=renamed,
        )
        return delta, manifest

    def update_manifest(
        self,
        repo_path: Path,
        dataset_name: str,
        indexed_files: list[Path],
        deleted_rel_paths: list[str],
        existing_manifest: Optional[RepositoryManifest] = None,
        file_metadata: Optional[dict[str, dict[str, Any]]] = None,
        renamed_pairs: Optional[list[tuple[str, Path]]] = None,
    ) -> RepositoryManifest:
        """Update and atomically persist manifest with newly indexed files, deletions, and AST metadata."""
        now = time.time()
        repo_path = repo_path.resolve()

        if existing_manifest:
            manifest = existing_manifest
            manifest.dataset_name = dataset_name
            manifest.repo_path = str(repo_path)
        else:
            manifest = RepositoryManifest(
                repo_path=str(repo_path),
                dataset_name=dataset_name,
                created_at=now,
                updated_at=now,
            )

        # Handle renames: transfer existing AST metadata to new relative path
        if renamed_pairs:
            for old_rel, new_path in renamed_pairs:
                try:
                    new_rel = str(new_path.resolve().relative_to(repo_path).as_posix())
                    if old_rel in manifest.files:
                        old_fp = manifest.files.pop(old_rel)
                        stat = new_path.stat()
                        old_fp.path = new_rel
                        old_fp.mtime = stat.st_mtime
                        old_fp.size = stat.st_size
                        old_fp.last_indexed_at = now
                        manifest.files[new_rel] = old_fp
                except Exception as er:
                    logger.warning("Failed to transfer renamed manifest entry %s -> %s: %s", old_rel, new_path, er)

        # Remove deleted
        for rel in deleted_rel_paths:
            manifest.files.pop(rel, None)

        # Add/update indexed files
        meta_dict = file_metadata or {}
        for f in indexed_files:
            try:
                rel = str(f.resolve().relative_to(repo_path).as_posix())
                stat = f.stat()
                sha = self.compute_sha256(f)
                file_meta = meta_dict.get(rel, {})

                language = file_meta.get("language", manifest.files.get(rel, FileFingerprint(rel, 0, 0, "")).language)
                symbols = file_meta.get("symbols", manifest.files.get(rel, FileFingerprint(rel, 0, 0, "")).symbols)
                imports = file_meta.get("imports", manifest.files.get(rel, FileFingerprint(rel, 0, 0, "")).imports)
                ast_nodes = file_meta.get("ast_nodes", manifest.files.get(rel, FileFingerprint(rel, 0, 0, "")).ast_nodes)
                ast_edges = file_meta.get("ast_edges", manifest.files.get(rel, FileFingerprint(rel, 0, 0, "")).ast_edges)

                manifest.files[rel] = FileFingerprint(
                    path=rel,
                    mtime=stat.st_mtime,
                    size=stat.st_size,
                    sha256=sha,
                    language=language,
                    symbols=list(symbols),
                    imports=list(imports),
                    ast_nodes=list(ast_nodes),
                    ast_edges=list(ast_edges),
                    last_indexed_at=now,
                )
            except Exception as e:
                logger.warning("Failed to record fingerprint for %s: %s", f, e)

        self.save_manifest(manifest)
        return manifest
