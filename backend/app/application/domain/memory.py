"""Domain entities for semantic, vector, and graph memory in RE:Track."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class StorageSubsystemState(str, Enum):
    """Authoritative operational state of a memory or storage subsystem."""

    NOT_CONFIGURED = "not_configured"
    INITIALIZING = "initializing"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    STALE = "stale"
    UNAVAILABLE = "unavailable"
    CORRUPT = "corrupt"


@dataclass
class MemoryProvenance:
    """Provenance metadata anchoring derived memory to authoritative repository source."""

    repository_id: str = ""
    repository_fingerprint: str = ""
    source_file: str = ""
    source_sha256: str = ""
    source_symbol: Optional[str] = None
    relationship_kind: Optional[str] = None
    indexed_at: float = 0.0
    parser_version: str = "2.0.0"
    manifest_version: str = "2.0"
    evidence_status: str = "verified_authoritative"  # 'verified_authoritative', 'derived_projection', 'stale', 'invalid'

    def is_valid_for_manifest(self, manifest: Any) -> bool:
        """Validate whether this provenance record matches the active repository manifest."""
        if not manifest or not hasattr(manifest, "files"):
            return False

        # If manifest has a computed fingerprint, it must match
        if self.repository_fingerprint and getattr(manifest, "repo_fingerprint", None):
            if self.repository_fingerprint != manifest.repo_fingerprint:
                return False

        # Source file must exist in manifest
        norm_path = self.source_file.replace("\\", "/").lstrip("./")
        if norm_path not in manifest.files:
            return False

        fp = manifest.files[norm_path]

        # Source SHA-256 must match if recorded
        if self.source_sha256 and getattr(fp, "sha256", None):
            if self.source_sha256 != fp.sha256:
                return False

        # Symbol must exist in file if specified
        if self.source_symbol and getattr(fp, "symbols", None):
            if self.source_symbol not in fp.symbols:
                return False

        return True

    def to_dict(self) -> dict[str, Any]:
        """Serialize provenance record to dictionary format."""
        return {
            "repository_id": self.repository_id,
            "repository_fingerprint": self.repository_fingerprint,
            "source_file": self.source_file,
            "source_sha256": self.source_sha256,
            "source_symbol": self.source_symbol,
            "relationship_kind": self.relationship_kind,
            "indexed_at": self.indexed_at,
            "parser_version": self.parser_version,
            "manifest_version": self.manifest_version,
            "evidence_status": self.evidence_status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryProvenance":
        """Construct provenance record from dictionary format."""
        return cls(
            repository_id=str(data.get("repository_id", "")),
            repository_fingerprint=str(data.get("repository_fingerprint", "")),
            source_file=str(data.get("source_file", "")),
            source_sha256=str(data.get("source_sha256", "")),
            source_symbol=data.get("source_symbol"),
            relationship_kind=data.get("relationship_kind"),
            indexed_at=float(data.get("indexed_at", 0.0)),
            parser_version=str(data.get("parser_version", "2.0.0")),
            manifest_version=str(data.get("manifest_version", "2.0")),
            evidence_status=str(data.get("evidence_status", "verified_authoritative")),
        )


@dataclass
class MemoryDatasetRecord:
    """Domain model representing a persistent dataset in memory."""

    id: str
    name: str
    type: str = "repository"
    size_bytes: Optional[int] = None
    created_at: Optional[str] = None
    file_count: int = 0
    source_path: Optional[str] = None
    storage_state: str = StorageSubsystemState.HEALTHY.value
    provenance: Optional[MemoryProvenance] = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize dataset record to dictionary format."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at,
            "file_count": self.file_count,
            "source_path": self.source_path,
            "storage_state": self.storage_state,
            "provenance": self.provenance.to_dict() if self.provenance else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryDatasetRecord":
        """Construct dataset record from dictionary format."""
        prov_raw = data.get("provenance")
        prov = MemoryProvenance.from_dict(prov_raw) if isinstance(prov_raw, dict) else None
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            type=str(data.get("type", "repository")),
            size_bytes=data.get("size_bytes"),
            created_at=data.get("created_at"),
            file_count=int(data.get("file_count", 0)),
            source_path=data.get("source_path"),
            storage_state=str(data.get("storage_state", StorageSubsystemState.HEALTHY.value)),
            provenance=prov,
        )


@dataclass
class MemoryDataItemRecord:
    """Domain model representing a document/file item inside a dataset."""

    id: str
    name: str
    mime_type: str = "text/plain"
    data_size: int = 0
    created_at: Optional[str] = None
    extension: str = ""
    content_hash: str = ""
    pipeline_status: dict[str, Any] = field(default_factory=dict)
    provenance: Optional[MemoryProvenance] = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize data item record to dictionary format."""
        return {
            "id": self.id,
            "name": self.name,
            "mime_type": self.mime_type,
            "data_size": self.data_size,
            "created_at": self.created_at,
            "extension": self.extension,
            "content_hash": self.content_hash,
            "pipeline_status": self.pipeline_status,
            "provenance": self.provenance.to_dict() if self.provenance else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryDataItemRecord":
        """Construct data item record from dictionary format."""
        prov_raw = data.get("provenance")
        prov = MemoryProvenance.from_dict(prov_raw) if isinstance(prov_raw, dict) else None
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            mime_type=str(data.get("mime_type", "text/plain")),
            data_size=int(data.get("data_size", 0)),
            created_at=data.get("created_at"),
            extension=str(data.get("extension", "")),
            content_hash=str(data.get("content_hash", "")),
            pipeline_status=dict(data.get("pipeline_status", {})),
            provenance=prov,
        )


@dataclass
class MemoryGraphNodeRecord:
    """Domain model for a knowledge graph entity node."""

    id: str
    label: str
    kind: str = "entity"
    type: Optional[str] = None
    properties: dict[str, Any] = field(default_factory=dict)
    provenance: Optional[MemoryProvenance] = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize graph node record to dictionary format."""
        return {
            "id": self.id,
            "label": self.label,
            "kind": self.kind,
            "type": self.type,
            "properties": self.properties,
            "provenance": self.provenance.to_dict() if self.provenance else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryGraphNodeRecord":
        """Construct graph node record from dictionary format."""
        prov_raw = data.get("provenance")
        prov = MemoryProvenance.from_dict(prov_raw) if isinstance(prov_raw, dict) else None
        return cls(
            id=str(data.get("id", "")),
            label=str(data.get("label", "")),
            kind=str(data.get("kind", "entity")),
            type=data.get("type"),
            properties=dict(data.get("properties", {})),
            provenance=prov,
        )


@dataclass
class MemoryGraphEdgeRecord:
    """Domain model for a knowledge graph relationship edge."""

    source: str
    target: str
    kind: str = "relates_to"
    relationship_type: Optional[str] = None
    properties: dict[str, Any] = field(default_factory=dict)
    provenance: Optional[MemoryProvenance] = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize graph edge record to dictionary format."""
        return {
            "source": self.source,
            "target": self.target,
            "kind": self.kind,
            "relationship_type": self.relationship_type,
            "properties": self.properties,
            "provenance": self.provenance.to_dict() if self.provenance else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryGraphEdgeRecord":
        """Construct graph edge record from dictionary format."""
        prov_raw = data.get("provenance")
        prov = MemoryProvenance.from_dict(prov_raw) if isinstance(prov_raw, dict) else None
        return cls(
            source=str(data.get("source", "")),
            target=str(data.get("target", "")),
            kind=str(data.get("kind", "relates_to")),
            relationship_type=data.get("relationship_type"),
            properties=dict(data.get("properties", {})),
            provenance=prov,
        )


@dataclass
class MemoryGraphRecord:
    """Domain model representing complete knowledge graph topology."""

    nodes: list[MemoryGraphNodeRecord] = field(default_factory=list)
    edges: list[MemoryGraphEdgeRecord] = field(default_factory=list)
    storage_state: str = StorageSubsystemState.HEALTHY.value

    def to_dict(self) -> dict[str, Any]:
        """Serialize full graph record to dictionary format."""
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "storage_state": self.storage_state,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryGraphRecord":
        """Construct graph record from dictionary format."""
        raw_nodes = data.get("nodes", [])
        nodes = [
            n if isinstance(n, MemoryGraphNodeRecord) else MemoryGraphNodeRecord.from_dict(n)
            for n in raw_nodes if isinstance(n, (dict, MemoryGraphNodeRecord))
        ]
        raw_edges = data.get("edges", [])
        edges = [
            e if isinstance(e, MemoryGraphEdgeRecord) else MemoryGraphEdgeRecord.from_dict(e)
            for e in raw_edges if isinstance(e, (dict, MemoryGraphEdgeRecord))
        ]
        return cls(
            nodes=nodes,
            edges=edges,
            storage_state=str(data.get("storage_state", StorageSubsystemState.HEALTHY.value)),
        )


@dataclass
class MemoryVectorStatsRecord:
    """Domain model for vector embeddings and table metadata."""

    tables: list[dict[str, Any]] = field(default_factory=list)
    total_vectors: int = 0
    embedding_model: Optional[str] = None
    embedding_dimensions: int = 768
    storage_state: str = StorageSubsystemState.HEALTHY.value

    def to_dict(self) -> dict[str, Any]:
        """Serialize vector stats record to dictionary format."""
        return {
            "tables": self.tables,
            "total_vectors": self.total_vectors,
            "embedding_model": self.embedding_model,
            "embedding_dimensions": self.embedding_dimensions,
            "storage_state": self.storage_state,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryVectorStatsRecord":
        """Construct vector stats record from dictionary format."""
        return cls(
            tables=list(data.get("tables", [])),
            total_vectors=int(data.get("total_vectors", 0)),
            embedding_model=data.get("embedding_model"),
            embedding_dimensions=int(data.get("embedding_dimensions", 768)),
            storage_state=str(data.get("storage_state", StorageSubsystemState.HEALTHY.value)),
        )
