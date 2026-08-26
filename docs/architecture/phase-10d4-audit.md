# Phase 10D.4 Architectural Audit: Database & Memory Integration — Truth Alignment

## 1. Executive Summary

Phase 10D.4 establishes a strict **Truth Hierarchy and Provenance Boundary** across all persistent and derived storage layers in RE:Track. It enforces the fundamental architectural contract that derived storage layers (LanceDB vector space, Kùzu graph topology, Cognee semantic datasets, and in-memory context caches) may never invent, hallucinate, or substitute repository truth when authoritative filesystem and AST source evidence is absent or divergent.

---

## 2. Layer Authority Architecture

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

### Authoritative vs Derived Layers

| Layer Classification | Storage Technology / Path | Responsibility & Boundary |
|---|---|---|
| **Authoritative** | Local Filesystem Source Trees | Ground truth code contents, file paths, modification times. |
| **Authoritative** | `ManifestService` (`~/.retrack/manifests/*.json`) | Schema 2.0 SHA-256 fingerprints, AST symbols, language metadata. |
| **Authoritative** | Deterministic AST Engine (`RepositorySummaryGenerator`) | Pure parse-time `CallNode` and `CallEdge` definitions. |
| **Derived** | LanceDB (`~/.retrack/lancedb/`) | Vector projections of code chunks for semantic similarity. |
| **Derived** | Kùzu (`~/.retrack/kuzu/`) | Property graph representations of topological relationships. |
| **Derived** | Cognee Semantic Memory | Staged dataset items and multi-modal recall records. |
| **Derived / Ephemeral** | `ContextCacheEngine` | In-memory LRU cache with fine-grained symbol/file invalidation. |

---

## 3. Hard Invariants Enforced

1. **Derived Memory Subordination**: Derived memory cannot create repository truth.
2. **No Fallback Fabrication**: Missing source or AST evidence cannot be repaired or inferred by memory retrieval.
3. **Stale Provenance Exclusion**: Any memory record whose `source_file` does not exist in `RepositoryManifest` or whose `source_sha256` does not match `FileFingerprint.sha256` is marked `stale` and strictly excluded from `EvidenceService`.
4. **Invalidation upon Modification/Deletion**: Modifying or deleting source files immediately invalidates corresponding derived memory records.
5. **Cross-Repository Isolation**: Derived memories are tagged with immutable repository fingerprints (`repository_fingerprint`), preventing cross-workspace leakage.
6. **Storage Outage Resilience**: LanceDB, Kùzu, or Cognee unavailability, corruption, or write lock degrades vector/semantic features gracefully while deterministic AST and source retrieval remains 100% operational.
7. **Synthesis Grounding**: LLM synthesis cannot promote unverified memory into authoritative repository evidence.

---

## 4. Verification Evidence & Test Suites

The Phase 10D.4 truth alignment contract is validated across multiple layers of the test suite:

- **`test_memory_truth_alignment.py`** (8/8 tests passing):
  - `test_fresh_indexing_provenance_validation`: Validates provenance generation against manifest.
  - `test_modified_file_invalidates_stale_memory`: Tests SHA-256 mismatch invalidation.
  - `test_deleted_file_disappears_from_memory_evidence`: Ensures deleted files are pruned from evidence.
  - `test_cross_repository_memory_isolation`: Prevents memory leakage across repository boundaries.
  - `test_symbol_absence_invalidates_provenance`: Invalidates provenance when symbol is absent.
  - `test_storage_subsystem_outage_resilience`: Validates deterministic AST operation during DB outages.
  - `test_stale_memory_cannot_satisfy_evidence_service`: Prevents stale memory from satisfying evidence gates.
  - `test_storage_subsystem_state_reporting`: Verifies truthful state reporting across all storage layers.
- **`test_context_grounding_runtime_acceptance.py`** (4/4 tests passing): Runtime model invocation with evidence gating.
- **Benchmark Baseline & Expanded Contracts** (12/12 tests passing).
- **AST Integrity Test Suite** (4/4 tests passing).
- **Frontend Vitest Journey Tests** (51/51 tests passing).
- **Frontend Production Build** (`npm run build`: 0 TypeScript / bundle errors).

---

## 5. Persistence Migration & Schema Caveats

> [!CAUTION]
> **Persistence Schema Caution**:
> Physical persistence schema coverage across every individual LanceDB, Kùzu, and Cognee record was verified logically through provenance metadata validation and memory mock adapters.
> Full datastore-level on-disk migration across historical multi-version database files is not claimed without physical database storage inspection tooling.

---

## 6. Next Milestone: Phase 10D.5

### Focus: End-to-End Retrieval Arbitration
- **Core Principle**: Combine deterministic AST/source evidence, validated memory projections, and model synthesis into one unified, ranked evidence pipeline.
- **Guarantee**: Enforce strict authority ranking so lower-authority derived memory or heuristic suggestions never displace or override higher-authority source truth.
