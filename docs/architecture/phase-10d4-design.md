# Phase 10D.4 Architecture Design: Database & Memory Integration

## 1. Executive Summary

Phase 10D.4 establishes a strict **Truth Hierarchy and Provenance Boundary** across all persistent stores in RE:Track:
- **Filesystem & Manifest 2.0 (AST)**: Authoritative source of truth for repository structure, files, symbols, and code.
- **LanceDB**: Derived vector projection for semantic search and embedding chunks.
- **Kùzu**: Derived graph projection for topological querying and structural relationships.
- **Cognee Memory**: Derived semantic memory layer for dataset management and multi-modal recall.
- **ContextCacheEngine**: High-speed in-memory LRU cache with fine-grained AST dependency provenance.

No derived database or memory store may ever manufacture repository files, symbols, relationships, or features.

---

## 2. Truth Hierarchy & Authority Precedence

```
┌────────────────────────────────────────────────────────┐
│ Level 1: Filesystem Source (Authoritative Source Code) │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│ Level 2: Manifest 2.0 + Deterministic AST              │
│ (FileFingerprints, ast_nodes, symbols, imports)        │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│ Level 3: Derived Projections (LanceDB & Kùzu)          │
│ (Vector embeddings, topological call graph cache)       │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│ Level 4: Cognee Semantic Memory                        │
│ (Dataset document items, semantic recall chunks)       │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│ Level 5: LLM Synthesis                                 │
│ (Grounded markdown generation, bounded context)        │
└────────────────────────────────────────────────────────┘
```

### Precedence Rules
1. **Higher layers always override lower layers**: An AST symbol or file in Manifest 2.0 always supersedes any vector chunk or graph edge in LanceDB or Kùzu.
2. **Missing authoritative evidence cannot be repaired by lower layers**: If a symbol or subsystem is absent in Level 1 & Level 2, LanceDB/Kùzu/Cognee results cannot create it, and LLM inference cannot fabricate it.
3. **Database failure ≠ Repository evidence absence**: If LanceDB or Kùzu is unavailable or corrupt, deterministic source search and AST analysis continue operating truthfully.

---

## 3. Data Store Ownership & Authority Matrix

| Information Class | Authoritative Datastore | Derived Projections | Provenance Tagging |
|---|---|---|---|
| **Repository Files & Hashes** | Local Filesystem + `ManifestService` | `MemoryDataItemRecord` | `path`, `mtime`, `size`, `sha256` |
| **AST Symbols & Definitions** | `tree-sitter` / `RepositorySummaryGenerator` | Manifest `FileFingerprint.symbols` | `source_file`, `source_symbol`, `language` |
| **Call Graphs & Dependencies** | Deterministic AST Call Graph Engine | Kùzu Graph Engine (`MemoryGraphRecord`) | `source_node`, `target_node`, `relationship_type` |
| **Vector Embeddings** | Deterministic Chunker + Embedding Engine | LanceDB (`MemoryVectorStatsRecord`) | `file_path`, `content_hash`, `chunk_index` |
| **Context Packages** | `ContextCacheEngine` (In-Memory LRU) | Disk Cache (`~/.retrack/cache/`) | `manifest_hash`, `referenced_files`, `referenced_symbols` |

---

## 4. Memory Provenance Schema Contract

Every derived entity in LanceDB, Kùzu, or Cognee must satisfy the `MemoryProvenance` contract:

```python
@dataclass
class MemoryProvenance:
    repository_id: str                          # Canonical SHA-256 repository identifier
    repository_fingerprint: str                 # 16-char deterministic Manifest fingerprint
    source_file: str                            # Normalized POSIX relative file path
    source_symbol: Optional[str] = None         # AST symbol name (function/class)
    relationship_kind: Optional[str] = None     # e.g., 'calls', 'imports', 'defines', 'chunk'
    indexed_at: float = 0.0                     # Timestamp of indexing
    parser_version: str = "2.0.0"               # AST parser schema version
    manifest_version: str = "2.0"               # Manifest schema version
    evidence_status: str = "verified_authoritative" # 'verified_authoritative' | 'derived_projection' | 'stale'
```

### Validation Rule
During retrieval, if a retrieved memory item's `source_file` does not exist in the current `RepositoryManifest`, or if its `content_hash` does not match the current `FileFingerprint.sha256`, the item is marked `stale` and excluded from `EvidenceService` evaluation.

---

## 5. Subsystem Failure States & Telemetry

Both backend use cases and frontend status indicators must faithfully report storage health using explicit states:

```python
class StorageSubsystemState(str, Enum):
    NOT_CONFIGURED = "not_configured"  # Storage provider not enabled
    INITIALIZING = "initializing"      # Directory creation or migration in progress
    HEALTHY = "healthy"                # Open connection, readable tables, matching schema
    DEGRADED = "degraded"              # Primary available, optional feature (e.g. vector search) degraded
    STALE = "stale"                    # Memory contains out-of-date records pending re-index
    UNAVAILABLE = "unavailable"        # Connection refused or process offline
    CORRUPT = "corrupt"                # Database file unreadable or invalid format
```

---

## 6. Incremental Mutation & Invalidation Lifecycle

When `ManifestService` detects changes via `IndexDelta`:
1. **Added File**: Parsed by AST engine -> appended to Manifest -> chunked into LanceDB -> cached packages unaffected.
2. **Modified File**: Re-parsed by AST engine -> Manifest updated -> LanceDB records for that file replaced -> `ContextCacheEngine.invalidate_selective(repo_path, changed_files=[file_path])` purges only affected context packages.
3. **Deleted File**: Manifest drops file -> derived records in LanceDB/Kùzu referencing file invalidated -> `ContextCacheEngine.invalidate_selective(repo_path, deleted_files=[file_path])` purges all affected packages.
4. **Renamed File**: Manifest maps old path to new path via identical SHA-256 -> derived vector records updated with new path without re-embedding.

---

## 7. Zero Synthetic Fallbacks in Frontend

Frontend `src/pages/Memory.tsx` and `src/stores/memory-store.ts` must:
- Render actual table lists, vector row counts, and graph node counts returned by the backend.
- Display `0 files`, `0 vectors`, or `not extracted` when no datasets or graphs exist, rather than inventing mock nodes or static placeholder numbers.
