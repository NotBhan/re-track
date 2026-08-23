# Incremental / Diff-Aware Indexing Guide

**Product**: RE:Track  
**Feature Set**: Diff-Aware Change Detection & Incremental AST Synthesis  
**Schema Version**: 2.0  
**Parser Version**: 1.0.0  

---

## 1. What is Incremental Indexing?

When working on active codebases, AI coding assistants and developers modify individual files or small sets of files frequently. In traditional indexing systems, every repository scan parses the entire project from scratch, consuming significant CPU, I/O, and latency.

RE:Track's **Incremental / Diff-Aware Indexing Engine** eliminates redundant work by tracking per-file cryptographic hashes, syntax trees, and symbol references in a local, crash-safe manifest (`Manifest 2.0`).

---

## 2. Core Operating Modes

RE:Track automatically selects the optimal execution path during every indexing cycle:

### 1. `NOOP` (No Operation)
- **Trigger**: Repository files have not changed since the last indexed manifest.
- **Guarantee**: **0 source file parses**. All deterministic AST nodes, call graph edges, and summary structures are reused instantly.
- **Latency**: Sub-millisecond (< 1ms).

### 2. `INCREMENTAL`
- **Trigger**: One or more files are added, modified, renamed, or deleted.
- **Guarantee**: Only modified and added files undergo AST parsing. Unchanged files provide their cached symbols directly from the manifest.
- **Relinking**: Call graph edges and references are re-computed with impact-awareness to ensure cross-module calls remain accurate.
- **Cache Invalidation**: Context packages depending on modified files or symbols are selectively evicted, while unaffected packages remain cached.

### 3. `FULL`
- **Trigger**:
  - Explicit user request (`force_reindex=True` or `retrack index --force`).
  - First-time repository onboarding.
  - Manifest corruption or deletion.
  - Manifest schema version upgrade (`!= 2.0`).
  - Parser grammar update (`!= 1.0.0`).
- **Guarantee**: Complete clean-slate repository parsing, full call-graph re-extraction, and full context cache flush.

---

## 3. Change Detection & Rename Handling

RE:Track utilizes a multi-tier change detection strategy:

1. **Git Fast-Path Optimization**:
   - When `.git` is detected, `git status --porcelain=v1` provides fast change detection without traversing unchanged directories.
2. **Deterministic Filesystem Fallback**:
   - If git is unavailable or returns an error, RE:Track falls back to recursive mtime and size comparison against the manifest.
   - Files with changed mtime or size are hashed using SHA-256. If the hash matches the manifest, no parsing occurs.
3. **Rename Detection**:
   - When a file disappears and another appears with the exact same content SHA-256, RE:Track identifies it as a rename operation, preserving symbol metadata without re-parsing.
   - In ambiguous cases (e.g. multiple identical files created simultaneously), RE:Track conservatively treats the change as a delete + add.

---

## 4. Context Synthesis Cache Lifecycle

The in-memory `ContextCacheEngine` stores synthesized context packages for sub-5ms responses.

### Provenance Tracking:
Every cached context package records:
- `referenced_files`: All source files that contributed code snippets or structural context.
- `referenced_symbols`: Target symbols, callers, and callees included in the synthesis.

### Selective Invalidation:
Upon incremental indexing, RE:Track computes the union of modified files, deleted files, and changed symbols:
- Cached packages containing any impacted file or symbol are evicted.
- Unrelated cached packages (e.g., authentication context when modifying payment billing code) survive and continue serving cache hits.

---

## 5. Crash Safety & Atomic Transactions

To prevent partial or corrupted index states during unexpected power loss or process termination:

1. All new AST nodes and symbols are computed in-memory first.
2. The repository outline is updated in Cognee memory.
3. Manifest updates are written to `<manifest_path>.tmp`.
4. The file is flushed to disk via `os.fsync()`.
5. The temporary file is atomically replaced over the canonical manifest via `os.replace()`.

If an indexing job is interrupted prior to step 5, the existing manifest remains valid, and the next scan cleanly repairs state without manual intervention.
