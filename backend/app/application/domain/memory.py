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


@dataclass
class SemanticMemoryRecord:
    """Canonical domain entity for Cognee-derived semantic memory records in RE:Track.

    Invariants:
    - Strictly derived (Tier-4 representation).
    - Cannot claim or become Tier-1/Tier-2 authoritative repository evidence.
    - Must possess verifiable repository provenance anchoring it to one or more source files.
    - Invalidated upon source file modification, deletion, or symbol removal.
    """

    memory_id: str
    repository_id: str
    repository_fingerprint: str
    semantic_text: str
    source_files: list[str] = field(default_factory=list)
    source_symbols: list[str] = field(default_factory=list)
    source_sha256: list[str] = field(default_factory=list)
    relationship_kind: Optional[str] = None
    generated_by: str = "cognee_pipeline"
    generated_at: float = 0.0
    evidence_status: str = "derived_projection"
    is_derived: bool = True
    is_authoritative: bool = False
    confidence_score: float = 1.0

    def validate_against_manifest(self, manifest: Any) -> tuple[bool, str]:
        """Validate whether this semantic memory record is valid against the active repository manifest."""
        if not manifest or not hasattr(manifest, "files") or not manifest.files:
            return False, "missing_manifest"

        if not self.repository_id or not self.repository_fingerprint:
            return False, "missing_repository_provenance"

        if not self.source_files:
            return False, "missing_source_files"

        # Check repository fingerprint match
        if getattr(manifest, "repo_fingerprint", None) and self.repository_fingerprint != manifest.repo_fingerprint:
            return False, "cross_repository_fingerprint_mismatch"

        # Check repository dataset_name / repo_id match if available
        if getattr(manifest, "dataset_name", None) and self.repository_id:
            if manifest.dataset_name != self.repository_id and manifest.dataset_name != self.repository_id.replace("/", "_"):
                return False, "cross_repository_id_mismatch"

        # Validate all referenced source files exist in manifest with matching SHAs
        for idx, f_path in enumerate(self.source_files):
            norm_path = f_path.replace("\\", "/").lstrip("./")
            if norm_path not in manifest.files:
                return False, f"source_file_deleted:{norm_path}"

            fp = manifest.files[norm_path]
            if idx < len(self.source_sha256):
                expected_sha = self.source_sha256[idx]
                if expected_sha and getattr(fp, "sha256", None) and expected_sha != fp.sha256:
                    return False, f"source_sha256_stale:{norm_path}"

        # Validate all referenced symbols exist in manifest
        if self.source_symbols:
            known_symbols: set[str] = set()
            for f_path in self.source_files:
                norm_path = f_path.replace("\\", "/").lstrip("./")
                file_fp = manifest.files.get(norm_path)
                if file_fp and getattr(file_fp, "symbols", None):
                    known_symbols.update(file_fp.symbols)

            for sym in self.source_symbols:
                if sym not in known_symbols:
                    return False, f"source_symbol_missing:{sym}"

        return True, "valid"

    def is_valid_for_manifest(self, manifest: Any) -> bool:
        """Boolean predicate for manifest validity."""
        valid, _ = self.validate_against_manifest(manifest)
        return valid

    def to_dict(self) -> dict[str, Any]:
        """Serialize semantic memory record to dictionary format."""
        return {
            "memory_id": self.memory_id,
            "repository_id": self.repository_id,
            "repository_fingerprint": self.repository_fingerprint,
            "semantic_text": self.semantic_text,
            "source_files": list(self.source_files),
            "source_symbols": list(self.source_symbols),
            "source_sha256": list(self.source_sha256),
            "relationship_kind": self.relationship_kind,
            "generated_by": self.generated_by,
            "generated_at": self.generated_at,
            "evidence_status": self.evidence_status,
            "is_derived": True,
            "is_authoritative": False,
            "confidence_score": self.confidence_score,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SemanticMemoryRecord":
        """Construct semantic memory record from dictionary format."""
        return cls(
            memory_id=str(data.get("memory_id", "")),
            repository_id=str(data.get("repository_id", "")),
            repository_fingerprint=str(data.get("repository_fingerprint", "")),
            semantic_text=str(data.get("semantic_text", "")),
            source_files=list(data.get("source_files", [])),
            source_symbols=list(data.get("source_symbols", [])),
            source_sha256=list(data.get("source_sha256", [])),
            relationship_kind=data.get("relationship_kind"),
            generated_by=str(data.get("generated_by", "cognee_pipeline")),
            generated_at=float(data.get("generated_at", 0.0)),
            evidence_status=str(data.get("evidence_status", "derived_projection")),
            is_derived=True,
            is_authoritative=False,
            confidence_score=float(data.get("confidence_score", 1.0)),
        )

    def to_provenance(self) -> MemoryProvenance:
        """Convert primary provenance anchoring to MemoryProvenance model."""
        return MemoryProvenance(
            repository_id=self.repository_id,
            repository_fingerprint=self.repository_fingerprint,
            source_file=self.source_files[0] if self.source_files else "",
            source_sha256=self.source_sha256[0] if self.source_sha256 else "",
            source_symbol=self.source_symbols[0] if self.source_symbols else None,
            relationship_kind=self.relationship_kind,
            indexed_at=self.generated_at,
            evidence_status=self.evidence_status,
        )


@dataclass
class SemanticMemoryGenerationInput:
    """Input payload for semantic memory generation, containing only verified repository evidence."""

    repository_id: str
    repository_fingerprint: str
    manifest_fingerprint: str
    source_files: list[str] = field(default_factory=list)
    source_snippets: dict[str, str] = field(default_factory=dict)
    ast_symbols: dict[str, list[str]] = field(default_factory=dict)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    source_sha256: dict[str, str] = field(default_factory=dict)
    frameworks: list[str] = field(default_factory=list)
    task_intent: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "repository_id": self.repository_id,
            "repository_fingerprint": self.repository_fingerprint,
            "manifest_fingerprint": self.manifest_fingerprint,
            "source_files": list(self.source_files),
            "source_snippets": dict(self.source_snippets),
            "ast_symbols": {k: list(v) for k, v in self.ast_symbols.items()},
            "relationships": list(self.relationships),
            "source_sha256": dict(self.source_sha256),
            "frameworks": list(self.frameworks),
            "task_intent": self.task_intent,
        }

    @classmethod
    def from_manifest(
        cls,
        manifest: Any,
        file_filter: Optional[list[str]] = None,
        source_snippets: Optional[dict[str, str]] = None,
        task_intent: Optional[str] = None,
        frameworks: Optional[list[str]] = None,
    ) -> "SemanticMemoryGenerationInput":
        """Construct generation input from an active RepositoryManifest."""
        if not manifest or not hasattr(manifest, "files"):
            return cls(
                repository_id="",
                repository_fingerprint="",
                manifest_fingerprint="",
            )

        repo_id = getattr(manifest, "dataset_name", "default")
        repo_fp = getattr(manifest, "repo_fingerprint", "") or ""

        target_files = file_filter or list(manifest.files.keys())
        norm_files: list[str] = []
        ast_symbols: dict[str, list[str]] = {}
        source_sha256: dict[str, str] = {}
        relationships: list[dict[str, Any]] = []

        for f_path in target_files:
            norm_path = f_path.replace("\\", "/").lstrip("./")
            if norm_path in manifest.files:
                norm_files.append(norm_path)
                fp = manifest.files[norm_path]
                if getattr(fp, "symbols", None):
                    ast_symbols[norm_path] = list(fp.symbols)
                if getattr(fp, "sha256", None):
                    source_sha256[norm_path] = fp.sha256
                if getattr(fp, "ast_edges", None):
                    relationships.extend(fp.ast_edges)

        snippets = {}
        if source_snippets:
            for k, v in source_snippets.items():
                norm_k = k.replace("\\", "/").lstrip("./")
                if norm_k in manifest.files:
                    snippets[norm_k] = v

        return cls(
            repository_id=repo_id,
            repository_fingerprint=repo_fp,
            manifest_fingerprint=repo_fp,
            source_files=norm_files,
            source_snippets=snippets,
            ast_symbols=ast_symbols,
            relationships=relationships,
            source_sha256=source_sha256,
            frameworks=list(frameworks or []),
            task_intent=task_intent,
        )


@dataclass
class SemanticMemoryGenerationTelemetry:
    """Truthful observability telemetry for a semantic memory generation run."""

    model_invoked: bool = False
    provider_identity: str = ""
    model_name: str = ""
    inference_status: str = "not_configured"  # 'success', 'insufficient_evidence', 'not_configured', 'provider_unavailable', 'generation_failed', 'no_valid_memories', 'noop'
    inference_time_ms: float = 0.0
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    candidate_count: int = 0
    validated_count: int = 0
    persisted_count: int = 0
    rejected_count: int = 0
    rejection_reasons: list[str] = field(default_factory=list)
    llm_invocation_count: int = 0
    invalidated_count: int = 0
    preserved_count: int = 0
    regenerated_count: int = 0
    renamed_count: int = 0
    mode: str = "full"  # 'full', 'incremental', 'noop', 'rename_only', 'deletion_only'

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_invoked": self.model_invoked,
            "provider_identity": self.provider_identity,
            "model_name": self.model_name,
            "inference_status": self.inference_status,
            "inference_time_ms": self.inference_time_ms,
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
            "candidate_count": self.candidate_count,
            "validated_count": self.validated_count,
            "persisted_count": self.persisted_count,
            "rejected_count": self.rejected_count,
            "rejection_reasons": list(self.rejection_reasons),
            "llm_invocation_count": self.llm_invocation_count,
            "invalidated_count": self.invalidated_count,
            "preserved_count": self.preserved_count,
            "regenerated_count": self.regenerated_count,
            "renamed_count": self.renamed_count,
            "mode": self.mode,
        }


@dataclass
class SemanticMemoryGenerationResult:
    """Result object for semantic memory generation and cognification."""

    success: bool
    status: str  # 'success', 'insufficient_evidence', 'not_configured', 'provider_unavailable', 'generation_failed', 'no_valid_memories', 'noop'
    records: list[SemanticMemoryRecord] = field(default_factory=list)
    telemetry: SemanticMemoryGenerationTelemetry = field(default_factory=SemanticMemoryGenerationTelemetry)
    message: str = ""
    vector_indexed: bool = False
    dataset_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "status": self.status,
            "records": [r.to_dict() for r in self.records],
            "telemetry": self.telemetry.to_dict(),
            "message": self.message,
            "vector_indexed": self.vector_indexed,
            "dataset_name": self.dataset_name,
        }

