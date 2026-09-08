# Phase 10D.7: Release Candidate Architecture & Specification Conformance Audit

**Date**: 2026-09-08  
**Status**: `10D.7_READY_TO_FREEZE`  
**Execution Mode**: `verify_then_freeze`  
**DOX Contract Authority**: Root `AGENTS.md` and `src/AGENTS.md`

---

## 1. Executive Summary

Phase 10D.7 executes the final release-candidate verification and freeze gate for RE:Track. The frontend implementation has been systematically verified against approved Decision Logs 1–12, Sections 1–6, the Cross-Section Consistency Specification, and frozen Phase 10D.6 backend contracts.

All tests, builds, and native checks pass with zero regressions. Crucially, the **Phase 10D.6 backend is 100% frozen** (`git diff -- backend` is clean with zero modifications).

---

## 2. Frozen 4-Pillar Unified Architecture

### Pillar 1: `/workspace` (Active Repository Scope)
- **Scope**: Tied to `useRepositoryStore.selectedId`. When `selectedId === null`, renders the truthful repository catalog / selection state with all repository-scoped requests strictly blocked.
- **Sub-Navigation Tabs**:
  1. `Overview`: Real metadata (path, languages, frameworks, indexing timestamp, total file and byte counts).
  2. `Lifecycle`: Canonical 4-stage lifecycle stepper:
     $$\text{Scan} \longrightarrow \text{Manifest} \longrightarrow \text{AST Extraction} \longrightarrow \text{Cognification}$$
     *Prohibition enforced*: No legacy `discovered`/`scanned`/`indexed`/`synthesized` terminology.
  3. `AST`: Authoritative 5-state AST call graph view (`not_analyzed`, `analyzing`, `analyzed`, `zero_edges`, `failed`).
     - Real backend-derived `call_graph_nodes` and `call_graph_edges` only.
     - Presentation bounded to 50 nodes with interactive 1-hop neighbor expansion; source graph is never truncated.
  4. `Manifest & Evidence`: Exact file paths, SHA-256 digests, file sizes, and symbol counts directly from backend manifest.

### Pillar 2: `/studio` (Active Repository Scope)
- **Scope**: Tied to `useRepositoryStore.selectedId`. When `selectedId === null`, displays `"Repository Required"` with context synthesis disabled.
- **3-Column Architecture**:
  1. `Input Workbench`: Suggested prompt presets, custom intent input, token budget slider, synthesis trigger.
  2. `Retrieval Arbitration & Evidence`: Displays the 4 authoritative retrieval tiers:
     - `Tier 1: Filesystem Source`
     - `Tier 2: Manifest / AST`
     - `Tier 3: LanceDB / Kùzu`
     - `Tier 4: Cognee Semantic Memory`
     Displays evidence confidence only when provided by the backend. Displays backend abstention reason and `model_claims_allowed` status truthfully.
  3. `Context Package & History`: Progressive markdown reveal, package token and latency telemetry, copy/export controls, and repository-scoped `PackageHistoryDrawer`.
- **Runtime Identity Truth**: When synthesis is abstained or skipped, the executing model strictly displays `"None (No executions)"` or `"Skipped"`. It never defaults to the configured or active model.

### Pillar 3: `/memory` (Active Repository Scope)
- **Scope**: Tied to `useRepositoryStore.selectedId`. When `selectedId === null`, blocks all memory queries.
- **Derived Storage Truth Boundary**:
  - Prominently displays the Derived Storage Notice:
    > *"All records in this view are derived artifacts subordinate to Tier 1 Filesystem Source and Tier 2 Manifest/AST truth."*
- **Tabs**:
  1. `Semantic Records`: Ingested file records with SHA-256 verification and `ProvenanceDrawer`.
  2. `Vector Space`: Vector embeddings with cosine similarity (strictly never conflated with evidence confidence).
  3. `Knowledge Graph`: Cognee semantic entity/concept graph (explicitly distinguished from the Workspace AST call graph).

### Pillar 4: `/system` (Global Scope)
- **Scope**: Global and persistent; completely independent of active repository selection.
- **Tabs**:
  1. `Provider & Runtime`: Exposes three separate model identities:
     - `Configured Model`: Persisted setting.
     - `Verified Active Model`: Live probe status.
     - `Last Executing Model`: Populated only when execution actually occurred.
     Non-mutating probe isolation verified; provider switching follows `applying` $\to$ `verifying` $\to$ `active` / `failure`.
  2. `Storage & Subsystems`: Real backend health metrics. Hardware fields display `"Unavailable"` when telemetry is absent, strictly rejecting synthetic zeroes.
  3. `Benchmarks`: Deterministic token baseline evaluation, compression ratios, and latency distributions.
  4. `Diagnostics`: Live endpoint ping and IPC bridge verification.

---

## 3. Route Contract & Legacy Cleanup

### Canonical Routes
- `/workspace`
- `/studio`
- `/memory`
- `/system`

### Query-Preserving Legacy Redirects
- `/` $\longrightarrow$ `/workspace` (preserves query params)
- `/context-builder` $\longrightarrow$ `/studio` (preserves query params)
- `/knowledge/:repoId` $\longrightarrow$ `/workspace?repo=:repoId&tab=ast` (preserves query params)
- `/packages` $\longrightarrow$ `/studio?tab=history` (preserves query params)
- `/benchmarks` $\longrightarrow$ `/system?tab=benchmarks` (preserves query params)
- `/settings` $\longrightarrow$ `/system?tab=runtime` (preserves query params)

### Dead Legacy Page Removal
The following duplicate/obsolete standalone pages were safely deleted:
- `src/pages/Repositories.tsx`
- `src/pages/KnowledgeExplorer.tsx`
- `src/pages/ContextPackages.tsx`
- `src/pages/Settings.tsx`

---

## 4. Verification Matrix

| Verification Target | Command | Result | Pass Count |
|---|---|---|---|
| Full Backend Test Suite | `cd backend && uv run pytest tests/ -q` | **PASSED** | 866 / 866 |
| Deterministic AST Integrity | `cd backend && uv run pytest tests/test_ast_integrity.py -v` | **PASSED** | 4 / 4 |
| Frontend Vitest Suite | `npm test -- --run` | **PASSED** | 81 / 81 (14 files) |
| 4-Pillars Conformance Suite | `npx vitest run src/test/journeys/journey-4pillars-redesign.test.tsx` | **PASSED** | 24 / 24 |
| API Contract & Truth Boundary | `npx vitest run src/test/journeys/api-contract-and-desktop.test.tsx` | **PASSED** | 5 / 5 |
| Frontend Production Build | `npm run build` (`tsc && vite build`) | **PASSED** | 0 errors |
| Native Tauri Compilation | `cargo check --manifest-path src-tauri/Cargo.toml` | **PASSED** | 0 errors |
| Backend Freeze Audit | `git diff -- backend` | **CLEAN** | 0 changes |

---

## 5. Freeze Recommendation

Phase 10D.7 has verified all functional and architectural requirements of the 4-Pillar Unified Architecture. The codebase conforms to every approved specification without exception.

**Final Status**: **`10D.7_READY_TO_FREEZE`**
