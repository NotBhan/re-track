"""Domain entities for semantic, vector, and graph memory in RE:Track."""

from dataclasses import dataclass, field
from typing import Any, Optional


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
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryDatasetRecord":
        """Construct dataset record from dictionary format."""
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            type=str(data.get("type", "repository")),
            size_bytes=data.get("size_bytes"),
            created_at=data.get("created_at"),
            file_count=int(data.get("file_count", 0)),
            source_path=data.get("source_path"),
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
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryDataItemRecord":
        """Construct data item record from dictionary format."""
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            mime_type=str(data.get("mime_type", "text/plain")),
            data_size=int(data.get("data_size", 0)),
            created_at=data.get("created_at"),
            extension=str(data.get("extension", "")),
            content_hash=str(data.get("content_hash", "")),
            pipeline_status=dict(data.get("pipeline_status", {})),
        )


@dataclass
class MemoryGraphNodeRecord:
    """Domain model for a knowledge graph entity node."""

    id: str
    label: str
    kind: str = "entity"
    type: Optional[str] = None
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize graph node record to dictionary format."""
        return {
            "id": self.id,
            "label": self.label,
            "kind": self.kind,
            "type": self.type,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryGraphNodeRecord":
        """Construct graph node record from dictionary format."""
        return cls(
            id=str(data.get("id", "")),
            label=str(data.get("label", "")),
            kind=str(data.get("kind", "entity")),
            type=data.get("type"),
            properties=dict(data.get("properties", {})),
        )


@dataclass
class MemoryGraphEdgeRecord:
    """Domain model for a knowledge graph relationship edge."""

    source: str
    target: str
    kind: str = "relates_to"
    relationship_type: Optional[str] = None
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize graph edge record to dictionary format."""
        return {
            "source": self.source,
            "target": self.target,
            "kind": self.kind,
            "relationship_type": self.relationship_type,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryGraphEdgeRecord":
        """Construct graph edge record from dictionary format."""
        return cls(
            source=str(data.get("source", "")),
            target=str(data.get("target", "")),
            kind=str(data.get("kind", "relates_to")),
            relationship_type=data.get("relationship_type"),
            properties=dict(data.get("properties", {})),
        )


@dataclass
class MemoryGraphRecord:
    """Domain model representing complete knowledge graph topology."""

    nodes: list[MemoryGraphNodeRecord] = field(default_factory=list)
    edges: list[MemoryGraphEdgeRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize full graph record to dictionary format."""
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
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
        return cls(nodes=nodes, edges=edges)


@dataclass
class MemoryVectorStatsRecord:
    """Domain model for vector embeddings and table metadata."""

    tables: list[str] = field(default_factory=list)
    total_vectors: int = 0
    embedding_model: Optional[str] = None
    embedding_dimensions: int = 768

    def to_dict(self) -> dict[str, Any]:
        """Serialize vector stats record to dictionary format."""
        return {
            "tables": self.tables,
            "total_vectors": self.total_vectors,
            "embedding_model": self.embedding_model,
            "embedding_dimensions": self.embedding_dimensions,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryVectorStatsRecord":
        """Construct vector stats record from dictionary format."""
        return cls(
            tables=list(data.get("tables", [])),
            total_vectors=int(data.get("total_vectors", 0)),
            embedding_model=data.get("embedding_model"),
            embedding_dimensions=int(data.get("embedding_dimensions", 768)),
        )
