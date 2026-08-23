# Phase 10A Architecture Audit — Incremental / Diff-Aware Indexing

**Phase**: 10A  
**Title**: Incremental / Diff-Aware Indexing Subsystem  
**Status**: COMPLETED & VERIFIED  
**Date**: 2026-08-23  
**Contract Authority**: Root `AGENTS.md`, `docs/architecture.md`, `docs/development_plan.md`

---

## 1. Executive Summary & Objective

In Phases 8–9, RE:Track established a hardened FastMCP stdio interface, deterministic AST extraction, and a 3-tier memory model. However, subsequent mutations to repository source files triggered broad rescans and cache purges.

**Phase 10A** resolves this scalability constraint by implementing a production-grade **Incremental / Diff-Aware Indexing Subsystem**.

### Core Achievements:
1. **Three Operating Modes**:
   - **`NOOP`**: When the repository is unchanged, zero source-content AST parsing occurs (`files_parsed == 0`), while reusing the persisted deterministic index and context cache.
   - **`INCREMENTAL`**: Parses only added and modified files, loads unchanged file AST nodes/symbols directly from the manifest, purges deleted file state, and relinks call edges without touching unchanged files on disk.
   - **`FULL`**: Deterministic clean-slate rebuild triggered explicitly via `force_reindex=True` or automatically upon manifest corruption, schema version mismatch, parser version mismatch, or repository identity mismatch.
2. **Deterministic Manifest 2.0**:
   - Schema version `2.0`, Parser version `1.0.0`.
   - Per-file fingerprints recording SHA-256, size, mtime, language, AST nodes, AST edges, and symbol signatures.
   - Atomic persistence via `.tmp` staging, `os.fsync()`, and POSIX file replacement.
   - Rename detection via content hash matching with conservative delete+add fallback for ambiguous multi-file renames.
   - Git-aware fast path (`git status --porcelain=v1`) with authoritative filesystem inspection fallback.
3. **Dependency-Aware Cache Invalidation**:
   - `ContextCacheEngine` enhanced with provenance metadata (`referenced_files` and `referenced_symbols`).
   - Selective invalidation (`invalidate_selective`) purges only context packages dependent on modified/deleted files or symbols, preserving unrelated cached packages.
4. **Memory Boundary Contract**:
   - Ingests high-level repository architecture outlines into Cognee memory.
   - Strictly respects the Truth Boundary Guarantee: no unsupported per-file mutation claims inside Cognee.
5. **Security & Crash Invariants**:
   - Workspace authorization re-validated on all access paths.
   - External symlinks pruned during discovery.
   - Multi-repo dataset identity isolation preserved (`derive_dataset_name`).
   - Uncommitted operations safely aborted and healed on subsequent runs.

---

## 2. Architecture & Data Flow

```text
               Repository Mutation
                       │
                       ▼
        Git Fast-Path / FS Scan (mtime + size + SHA-256)
                       │
                       ▼
           Manifest Delta Computation
                       │
      ┌────────────────┼────────────────┐
      ▼                ▼                ▼
   [ NOOP ]     [ INCREMENTAL ]      [ FULL ]
 (0 AST Parses)  (Parse Δ Files)  (Parse All Files)
      │                │                │
      │                ▼                │
      │         Impact Relinking        │
      │                │                │
      │                ▼                │
      │       Selective Invalidation    ▼
      │      (ContextCacheEngine)  Invalidate Repo
      │                │                │
      │                ▼                ▼
      │       Transactional Cognee Outline Ingestion
      │                │
      │                ▼
      │       Atomic Manifest Write (.tmp -> fsync -> rename)
      │                │
      └────────────────┼────────────────┘
                       ▼
            Ready for Fast Retrieval
```

---

## 3. Manifest Schema v2.0 Specification

Stored in `<storage_dir>/<repo_id_hash>.json` (default: `~/.retrack/manifests/`):

```json
{
  "repo_path": "/home/user/my-project",
  "dataset_name": "my-project_a1b2c3d4e5",
  "schema_version": "2.0",
  "parser_version": "1.0.0",
  "repo_fingerprint": "9f83acb172e819a0",
  "created_at": 1787473000.0,
  "updated_at": 1787473050.0,
  "files": {
    "src/services/auth.py": {
      "rel_path": "src/services/auth.py",
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "size": 1024,
      "mtime": 1787473045.0,
      "language": "python",
      "symbols": ["AuthService", "verify_token"],
      "imports": ["models.user"],
      "ast_nodes": [
        {
          "id": "src.services.auth.AuthService",
          "label": "AuthService",
          "file": "src/services/auth.py",
          "kind": "class",
          "line": 1,
          "docstring": "Core AuthService"
        }
      ],
      "ast_edges": [],
      "last_indexed_at": 1787473050.0
    }
  }
}
```

### Automatic Full Rebuild Invariants:
1. **Unreadable / Corrupt JSON**: Triggers full clean-slate rebuild.
2. **Schema Version Mismatch**: `manifest.schema_version != "2.0"` -> full rebuild.
3. **Parser Version Mismatch**: `manifest.parser_version != "1.0.0"` -> full rebuild.
4. **Repository Identity Mismatch**: `manifest.repo_path != requested_path` -> full rebuild.

---

## 4. Verification Evidence & Test Matrix

Phase 10A implementation is backed by **27 dedicated automated test cases** across 7 test modules:

| Test Module | Coverage Area | Tests | Status |
| :--- | :--- | :---: | :---: |
| `tests/test_incremental_manifest.py` | Manifest 2.0 serialization, deterministic fingerprint, rename detection, corruption recovery, version mismatch triggers | 8 | PASSED |
| `tests/test_incremental_ast_updates.py` | 0-parse NOOP, 1-file edit parsing, incremental additions, deleted file node purge, JSX render resolution | 6 | PASSED |
| `tests/test_incremental_cache_invalidation.py` | Deterministic key derivation, provenance matching, selective eviction, legacy entry conservative invalidation | 5 | PASSED |
| `tests/test_incremental_failure_recovery.py` | Mid-indexing abort recovery, uncommitted staging rollback, orphaned `.tmp` overwrite, convergence | 3 | PASSED |
| `tests/test_incremental_security.py` | Workspace authorization boundary enforcement, symlink containment, multi-repo manifest isolation | 3 | PASSED |
| `tests/test_incremental_semantic_memory.py` | Cognee architecture outline synchronization, dataset isolation, NOOP bypass | 1 | PASSED |
| `tests/test_incremental_performance.py` | Empirical parse counts and wall-clock benchmarks on 50-file repository | 1 | PASSED |
| **Total Phase 10A Suite** | **Comprehensive Incremental Subsystem** | **27** | **27 / 27 PASSED** |

### Regression Gate Status:
- **Baseline Contract Tests**: `tests/test_benchmark_baseline_contract.py` — **8/8 PASSED** (frozen golden benchmarks intact).
- **Core Pytest Suite**: 76 core tests passing in ~5.0s.
- **Frontend Behavioral Suite**: `npx vitest run` — **12 test files / 50 tests PASSED** in 4.10s.
- **Frontend Production Build**: `npm run build` — **PASSED** (0 TypeScript / bundling errors).

---

## 5. Empirical Performance Measurements

Measurements captured on a 50-module repository (`tests/test_incremental_performance.py`):

| Operation | Files Discovered | Files Parsed | Files Reused | Processing Time | Speedup vs Initial |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Initial Full Index** | 50 | 50 | 0 | ~14.2 ms | 1.0x (Baseline) |
| **NOOP Reindex (Unchanged)** | 50 | **0** | **50** | **~0.6 ms** | **23.6x** |
| **Single File Edit** | 50 | **1** | **49** | **~1.8 ms** | **7.9x** |
| **Single File Addition** | 51 | **1** | **50** | **~2.1 ms** | **6.8x** |
| **Single File Deletion** | 49 | **0** | **49** | **~1.1 ms** | **12.9x** |
| **File Rename (No Edit)** | 50 | **0** | **50** | **~0.9 ms** | **15.7x** |

---

## 6. Audit Verdict

Phase 10A successfully satisfies all production requirements, reliability invariants, and architectural contracts without regressions to existing Phase 8/9 capabilities.

**Status**: **COMPLETE & FROZEN**
