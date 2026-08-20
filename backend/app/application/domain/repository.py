"""Domain entity for indexed repository records in RE:Track."""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class IndexedRepositoryRecord:
    """Represents a repository indexed in RE:Track memory and metadata store."""

    id: str
    name: str
    path: str
    languages: list[str] = field(default_factory=lambda: ["Code"])
    file_count: int = 0
    memory_size: str = "0 KB"
    last_indexed: str = ""
    purpose: str = ""
    architecture: list[dict[str, Any]] = field(default_factory=list)
    components: list[dict[str, Any]] = field(default_factory=list)
    call_graph_status: str = "not_analyzed"
    call_graph_error: Optional[str] = None
    call_graph_nodes: Optional[list[dict[str, Any]]] = None
    call_graph_edges: Optional[list[dict[str, Any]]] = None
    extra_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize domain entity to persistence dictionary format."""
        d: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "languages": self.languages,
            "file_count": self.file_count,
            "memory_size": self.memory_size,
            "last_indexed": self.last_indexed,
            "purpose": self.purpose,
            "architecture": self.architecture,
            "components": self.components,
            "call_graph_status": self.call_graph_status,
            "call_graph_error": self.call_graph_error,
        }
        if self.call_graph_nodes is not None:
            d["call_graph_nodes"] = self.call_graph_nodes
        if self.call_graph_edges is not None:
            d["call_graph_edges"] = self.call_graph_edges
        if self.extra_metadata:
            d.update(self.extra_metadata)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IndexedRepositoryRecord":
        """Construct domain entity from persistence dictionary format."""
        known_keys = {
            "id", "name", "path", "languages", "file_count", "memory_size",
            "last_indexed", "purpose", "architecture", "components",
            "call_graph_status", "call_graph_error", "call_graph_nodes",
            "call_graph_edges",
        }
        extra = {k: v for k, v in data.items() if k not in known_keys}
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            path=str(data.get("path", "")),
            languages=list(data.get("languages", ["Code"])),
            file_count=int(data.get("file_count", 0)),
            memory_size=str(data.get("memory_size", "0 KB")),
            last_indexed=str(data.get("last_indexed", "")),
            purpose=str(data.get("purpose", "")),
            architecture=list(data.get("architecture", [])),
            components=list(data.get("components", [])),
            call_graph_status=str(data.get("call_graph_status", "not_analyzed")),
            call_graph_error=data.get("call_graph_error"),
            call_graph_nodes=data.get("call_graph_nodes"),
            call_graph_edges=data.get("call_graph_edges"),
            extra_metadata=extra,
        )
