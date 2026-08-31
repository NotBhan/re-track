"""Persistent repository adapter for validated SemanticMemoryRecord entities.

Implements SemanticMemoryRepositoryPort with atomic JSON filesystem storage,
strict repository isolation, provenance validation before write, and active
manifest revalidation on load without synthetic repair.
"""

import copy
import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

from app.application.domain.memory import SemanticMemoryRecord
from app.application.ports.memory import SemanticMemoryRepositoryPort

logger = logging.getLogger(__name__)


class JsonSemanticMemoryRepository(SemanticMemoryRepositoryPort):
    """Durable JSON filesystem repository for SemanticMemoryRecord entities.

    Invariants:
    - Persists ONLY records that pass provenance validation.
    - Isolates records by repository_id.
    - Preserves derived-only invariants (generated_by='cognee_pipeline', is_derived=True, is_authoritative=False).
    - Revalidates records against active manifest on load without silently repairing stale records.
    - Guarantees atomic, crash-safe persistence.
    """

    def __init__(
        self,
        store_path: Optional[Path | str] = None,
        legacy_store_path: Optional[Path | str] = None,
    ) -> None:
        if store_path is None:
            self._store_path = Path.home() / ".retrack" / "semantic_memory.json"
            self._legacy_store_path = (
                Path(legacy_store_path)
                if legacy_store_path is not None
                else (Path.home() / ".andes" / "semantic_memory.json")
            )
        else:
            self._store_path = Path(store_path)
            self._legacy_store_path = Path(legacy_store_path) if legacy_store_path is not None else None

    @property
    def store_path(self) -> Path:
        return self._store_path

    def load_raw(self) -> dict[str, Any]:
        """Load the raw JSON dictionary from disk with legacy fallback."""
        if self._store_path.exists():
            try:
                content = self._store_path.read_text(encoding="utf-8")
                data = json.loads(content)
                if isinstance(data, dict) and "repositories" in data:
                    return data
                elif isinstance(data, list):
                    # Migration from flat list format
                    grouped: dict[str, list[dict[str, Any]]] = {}
                    for item in data:
                        if isinstance(item, dict):
                            r_id = str(item.get("repository_id", "default"))
                            grouped.setdefault(r_id, []).append(item)
                    return {"version": "1.0", "repositories": grouped}
            except Exception as e:
                logger.warning("Failed to load semantic memory store from %s: %s", self._store_path, e)
                return {"version": "1.0", "repositories": {}}

        if self._legacy_store_path is not None and self._legacy_store_path.exists():
            try:
                content = self._legacy_store_path.read_text(encoding="utf-8")
                data = json.loads(content)
                if isinstance(data, dict) and "repositories" in data:
                    return data
            except Exception as e:
                logger.warning("Failed to load legacy semantic memory store from %s: %s", self._legacy_store_path, e)
                return {"version": "1.0", "repositories": {}}

        return {"version": "1.0", "repositories": {}}

    def save_raw(self, data: dict[str, Any]) -> None:
        """Persist raw dictionary to disk atomically using temporary file and fsync."""
        try:
            self._store_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self._store_path.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            tmp_path.replace(self._store_path)
        except Exception as e:
            logger.error("Failed to save semantic memory store to %s: %s", self._store_path, e)
            raise

    def _validate_record(
        self,
        record: SemanticMemoryRecord,
        manifest: Optional[Any] = None,
    ) -> tuple[bool, str]:
        """Verify provenance and domain invariants before persistence."""
        if not isinstance(record, SemanticMemoryRecord):
            return False, "invalid_record_type"

        # Mandatory domain invariants
        if not record.memory_id or not str(record.memory_id).strip():
            return False, "missing_memory_id"

        if not record.repository_id or not str(record.repository_id).strip():
            return False, "missing_repository_id"

        if not record.repository_fingerprint or not str(record.repository_fingerprint).strip():
            return False, "missing_repository_fingerprint"

        if not record.semantic_text or not str(record.semantic_text).strip():
            return False, "empty_semantic_text"

        if not record.source_files:
            return False, "missing_source_files"

        if not record.source_sha256:
            return False, "missing_source_sha256"

        if len(record.source_files) != len(record.source_sha256):
            return False, "source_files_sha_count_mismatch"

        # Invariant enforcement: strictly derived
        if not record.is_derived or record.is_authoritative:
            return False, "authoritative_status_forbidden"

        if record.generated_by != "cognee_pipeline":
            return False, "invalid_generator"

        if record.evidence_status not in ("derived_projection", "stale"):
            return False, "invalid_evidence_status"

        # Validate against manifest if provided
        if manifest is not None:
            valid, reason = record.validate_against_manifest(manifest)
            if not valid:
                return False, reason

        return True, "valid"

    def save(
        self,
        record: SemanticMemoryRecord,
        manifest: Optional[Any] = None,
    ) -> tuple[bool, str]:
        """Persist a single validated SemanticMemoryRecord."""
        valid, reason = self._validate_record(record, manifest=manifest)
        if not valid:
            logger.warning(
                "SemanticMemoryRecord %s rejected before persistence: reason=%s",
                getattr(record, "memory_id", "unknown"),
                reason,
            )
            return False, reason

        raw = self.load_raw()
        repos = raw.setdefault("repositories", {})
        repo_records = repos.setdefault(record.repository_id, [])

        # Upsert: deduplicate by memory_id
        record_dict = record.to_dict()
        updated = False
        for idx, existing in enumerate(repo_records):
            if existing.get("memory_id") == record.memory_id:
                repo_records[idx] = record_dict
                updated = True
                break

        if not updated:
            repo_records.append(record_dict)

        self.save_raw(raw)
        return True, "valid"

    def upsert(
        self,
        record: SemanticMemoryRecord,
        manifest: Optional[Any] = None,
    ) -> tuple[bool, str]:
        """Upsert a single validated SemanticMemoryRecord."""
        return self.save(record, manifest=manifest)

    def save_all(
        self,
        records: list[SemanticMemoryRecord],
        manifest: Optional[Any] = None,
    ) -> tuple[int, list[str]]:
        """Persist a batch of validated SemanticMemoryRecords."""
        if not records:
            return 0, []

        raw = self.load_raw()
        repos = raw.setdefault("repositories", {})
        saved_count = 0
        reasons: list[str] = []

        for rec in records:
            valid, reason = self._validate_record(rec, manifest=manifest)
            if not valid:
                logger.warning(
                    "SemanticMemoryRecord %s rejected in batch save: reason=%s",
                    getattr(rec, "memory_id", "unknown"),
                    reason,
                )
                reasons.append(f"rejected:{getattr(rec, 'memory_id', 'unknown')}:{reason}")
                continue

            repo_records = repos.setdefault(rec.repository_id, [])
            rec_dict = rec.to_dict()
            updated = False
            for idx, existing in enumerate(repo_records):
                if existing.get("memory_id") == rec.memory_id:
                    repo_records[idx] = rec_dict
                    updated = True
                    break

            if not updated:
                repo_records.append(rec_dict)

            saved_count += 1
            reasons.append("valid")

        if saved_count > 0:
            self.save_raw(raw)

        return saved_count, reasons

    def get(
        self,
        memory_id: str,
        repository_id: Optional[str] = None,
        manifest: Optional[Any] = None,
    ) -> Optional[SemanticMemoryRecord]:
        """Retrieve a specific record by its ID, optionally validating against manifest."""
        raw = self.load_raw()
        repos = raw.get("repositories", {})

        target_repos = [repository_id] if repository_id else list(repos.keys())

        for r_id in target_repos:
            for item in repos.get(r_id, []):
                if item.get("memory_id") == memory_id:
                    record = SemanticMemoryRecord.from_dict(item)
                    if manifest is not None:
                        valid, _ = record.validate_against_manifest(manifest)
                        if not valid:
                            return None
                    return record
        return None

    def get_by_repository(
        self,
        repository_id: str,
        manifest: Optional[Any] = None,
        include_stale: bool = False,
    ) -> list[SemanticMemoryRecord]:
        """Retrieve all records for a repository, optionally validating against manifest."""
        raw = self.load_raw()
        repos = raw.get("repositories", {})
        raw_items = repos.get(repository_id, [])

        results: list[SemanticMemoryRecord] = []

        for item in raw_items:
            record = SemanticMemoryRecord.from_dict(item)

            if manifest is None:
                results.append(record)
                continue

            valid, reason = record.validate_against_manifest(manifest)
            if valid:
                # Retain valid derived projection
                record.evidence_status = "derived_projection"
                results.append(record)
            elif include_stale:
                # Return marked as stale metadata without mutating authoritative source
                stale_copy = copy.deepcopy(record)
                stale_copy.evidence_status = "stale"
                results.append(stale_copy)
            else:
                logger.debug(
                    "Excluding stale semantic memory record %s: reason=%s",
                    record.memory_id,
                    reason,
                )

        return results

    def load_all(
        self,
        manifest: Optional[Any] = None,
        include_stale: bool = False,
    ) -> list[SemanticMemoryRecord]:
        """Retrieve all persisted records across all repositories."""
        raw = self.load_raw()
        repos = raw.get("repositories", {})

        results: list[SemanticMemoryRecord] = []
        for r_id in repos:
            results.extend(
                self.get_by_repository(
                    repository_id=r_id,
                    manifest=manifest,
                    include_stale=include_stale,
                )
            )
        return results

    def delete(
        self,
        memory_id: str,
        repository_id: Optional[str] = None,
    ) -> bool:
        """Delete a record by its memory ID."""
        raw = self.load_raw()
        repos = raw.get("repositories", {})
        deleted = False

        target_repos = [repository_id] if repository_id else list(repos.keys())

        for r_id in target_repos:
            items = repos.get(r_id, [])
            filtered = [it for it in items if it.get("memory_id") != memory_id]
            if len(filtered) < len(items):
                repos[r_id] = filtered
                deleted = True

        if deleted:
            self.save_raw(raw)
        return deleted

    def delete_by_repository(self, repository_id: str) -> int:
        """Delete all records associated with a repository."""
        raw = self.load_raw()
        repos = raw.get("repositories", {})

        if repository_id in repos:
            count = len(repos[repository_id])
            del repos[repository_id]
            self.save_raw(raw)
            return count
        return 0

    def clear(self) -> None:
        """Clear all stored semantic memory records."""
        self.save_raw({"version": "1.0", "repositories": {}})


# Backward compatibility alias
SemanticMemoryRepository = JsonSemanticMemoryRepository
