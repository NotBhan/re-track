`# RE:Track — Phase 5 Architectural Audit Report
## Domain Model & Port Refinement (DEBT-005, DEBT-006, DEBT-007)

**Audit Date**: 2026-08-21  
**Lead Auditor**: Principal Software Architect & Systems Engineer  
**Status**: **COMPLETE / PASS**  
**Governing Documents**:
- `docs/architecture/refactoring-roadmap.md`
- `docs/architecture/decisions.md` (ADR-001 through ADR-011)
- `docs/architecture/phase-4-audit.md`

---

## 1. Executive Summary

Phase 5 targeted the deep structural refinement of RE:Track's Application and Domain boundaries by resolving three debts explicitly deferred from Phases 3 and 4:
1. **DEBT-005 (MemoryPort Capability Segregation & Typed Models)**: Decomposed the monolithic 13-method `MemoryPort` into 5 cohesive capability protocols and introduced strongly typed domain records (`MemoryDatasetRecord`, `MemoryDataItemRecord`, `MemoryGraphRecord`, `MemoryVectorStatsRecord`).
2. **DEBT-006 (IndexedRepositoryRecord Substructure Typing)**: Defined `ArchitectureLayerRecord` and `ComponentRecord` domain models, replacing untyped `list[dict[str, Any]]` while preserving 100% backward-compatible deserialization of historical JSON files.
3. **DEBT-007 (Intent Parser Domain Model & Pure Extractor)**: Extracted `ParsedIntentRecord` and a pure, deterministic `parse_intent_heuristics(prompt)` domain extractor, eliminating static methods from `IntentParserPort` protocol and removing duplicated private fallback code from `ContextUseCases`.

All architectural boundaries, AST purity constraints, and Phase 4 storage compatibility contracts (`~/.retrack/` canonical, `~/.andes/` read-only fallback) were strictly maintained.

---

## 2. Technical Audit & Resolutions

### 2.1 DEBT-005: MemoryPort Capability Segregation
- **Problem**: `MemoryPort` was an overly broad interface exposing 13 methods with dictionary-shaped return contracts. Use cases had to know internal dictionary keys returned by Cognee.
- **Resolution**:
  - `MemoryLifecyclePort`: `is_initialized`, `initialize()`
  - `MemoryIngestionPort`: `add()`, `remember()`
  - `MemoryRetrievalPort`: `recall()`
  - `MemoryDatasetPort`: `list_datasets()`, `get_dataset_data()`, `forget()`, `forget_data_item()`
  - `MemoryTopologyPort`: `cognify()`, `get_stats()`, `get_graph()`, `get_vectors()`
  - `MemoryPort`: Composite protocol inheriting all 5 capability protocols for seamless backward compatibility.
  - Consumers refactored to smallest required capability: `SystemUseCases` $\to$ `MemoryLifecyclePort`, `RepositoryUseCases` $\to$ `MemoryDatasetPort`.
  - Domain records created in `app/application/domain/memory.py` with polymorphic support in use cases.

### 2.2 DEBT-006: IndexedRepositoryRecord Substructure Typing
- **Problem**: `architecture` and `components` in `IndexedRepositoryRecord` were untyped `list[dict[str, Any]]`.
- **Resolution**:
  - Created `ArchitectureLayerRecord` (`icon: str = "Layers"`, `label: str = ""`) and `ComponentRecord` (`path: str = ""`, `centrality: str = "core"`).
  - Updated `IndexedRepositoryRecord` to use typed collections.
  - Implemented tolerant `from_dict()` / `to_dict()` methods capable of deserializing raw dicts, string lists, or typed records without requiring persistence migrations.

### 2.3 DEBT-007: Intent Parser Protocol Cleanup & Domain Extraction
- **Problem**: `IntentParserPort` defined `@staticmethod def rule_based_fallback` directly on the Protocol interface, and `ContextUseCases` duplicated fallback extraction in a private function.
- **Resolution**:
  - Defined `ParsedIntentRecord` in `app/application/domain/intent.py`.
  - Created pure deterministic domain function `parse_intent_heuristics(prompt: str) -> ParsedIntentRecord` with zero I/O and zero framework dependencies.
  - Cleaned `IntentParserPort` protocol to specify only `async def parse_intent(self, prompt: str) -> ParsedIntentRecord`.
  - Replaced duplicate private fallback in `ContextUseCases` with a direct call to `parse_intent_heuristics`.

---

## 3. Verification & Metrics

| Test Suite | Tests Executed | Passed | Skipped | Failed | Result |
|---|---|---|---|---|---|
| Phase 5 Domain Refinement (`test_domain_refinement.py`) | 15 | 15 | 0 | 0 | **PASS** |
| Application Boundary Tests (`test_application_boundary.py`) | 18 | 18 | 0 | 0 | **PASS** |
| AST Integrity Tests (`test_ast_integrity.py`) | 4 | 4 | 0 | 0 | **PASS** |
| Storage Compatibility Tests (`test_storage_compatibility.py`) | 14 | 14 | 0 | 0 | **PASS** |
| Full Backend Regression Suite (`tests/`) | 344 | 342 | 2 (Ollama live) | 0 | **PASS** |
| Frontend Production Build (`npm run build`) | TypeScript & Vite | Clean (2.99s) | 0 | 0 | **PASS** |

---

## 4. Architectural Invariant Summary

1. **Domain Purity**: `app.application.domain` imports 0 infrastructure, vendor framework, or database libraries.
2. **Port Purity**: `app.application.ports` contains only pure abstract `Protocol` definitions without implementation code or static methods.
3. **Capability Inversion**: Use cases depend on fine-grained capability protocols rather than monolithic services.
4. **Storage Invariance**: `~/.retrack/` canonical writable storage and `~/.andes/` read-only legacy storage remain untouched and byte-for-byte immutable.

---

## 5. Remaining Architectural Debt (Deferred to Phase 6)

- **DEBT-003**: Global module-level `_container` singleton in `container.py` (deferred to Phase 6 composition root overhaul).
- **FastAPI Router Modularization**: Splitting `server.py` into distinct sub-routers under `app/api/routers/` (Phase 6).
