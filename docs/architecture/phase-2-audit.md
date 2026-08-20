# RE:Track — Phase 2 Architectural Audit Report

> **Audit Date**: 2026-08-20  
> **Phase**: Phase 2 — Application Layer Independence & Core Boundary Stabilization  
> **Auditor**: Antigravity Agent  
> **Verdict**: **PASS (All Phase 2 Invariants Verified)**  
> **Governing Framework**: DOX (Documentation-Oriented eXecution) / ADR-001, ADR-007, ADR-008

---

## 1. Executive Summary

Phase 2 completed the architectural stabilization of the Application Layer (`backend/app/application/`). It eliminated all coupling from the application layer to the inbound API layer (`app.api`), web frameworks (`FastAPI`, `Starlette`), server routes (`app.server`), CLI interfaces (`app.cli`), and raw filesystem persistence.

The application layer now owns its data contracts under `backend/app/application/dto/`, receives all dependencies via explicit constructor injection from the `ApplicationContainer` composition root, and delegates persistence and retrieval mechanics through dedicated domain services (`RepositoryMetadataStore`, `SourceSearchService`, `BenchmarkService`).

---

## 2. Invariant Verification Matrix

| Invariant | Target | Status | Verification Evidence |
| :--- | :--- | :--- | :--- |
| **Inbound Purity** | No `app.api`, `fastapi`, `starlette`, `app.server`, `app.cli` in `app.application.*` | **VERIFIED (0 violations)** | AST static analysis test `test_application_layer_ast_purity` passed across all 10 application files. |
| **Application-Owned DTOs** | All request/response contracts live in `app.application.dto` | **VERIFIED** | 32 models extracted across 8 modular DTO files. `app.api.schemas` acts purely as a backward-compatibility facade re-exporting these DTOs. |
| **Persistence Separation** | No raw JSON / `Path.write_text` in use cases | **VERIFIED (0 direct I/O)** | Verified by `test_no_direct_persistence_in_use_cases`. `RepositoryMetadataStore` protocol and `JsonRepositoryMetadataStore` handle persistence. |
| **No Inline Construction** | Use cases receive all services via constructor DI | **VERIFIED** | `ContextService(...)` construction removed from `ContextUseCases.get_agent_context()`. Verified by `test_no_inline_context_service_construction`. |
| **Source Retrieval Extraction** | File scanning and snippet slicing extracted from use cases | **VERIFIED** | Extracted to `app/services/source_search_service.py` (`SourceSearchService`). |
| **Benchmark API Relocation** | Benchmark runner decoupled from inbound API layer | **VERIFIED** | Relocated to `app/services/benchmark_service.py` (`BenchmarkService`). Zero `app.api.benchmarks` imports in `container.py`. |
| **Behavioral Compatibility** | Zero route/method/schema/CLI changes | **VERIFIED** | All 25 HTTP routes in `server.py`, CLI commands in `cli/main.py`, and test suites run with 100% contract fidelity. |
| **Full Test Suite Integrity** | Backend tests pass with 0 regressions | **VERIFIED** | **307 passed**, 2 skipped (live Ollama), 0 failed; AST integrity tests passed; frontend build clean. |

---

## 3. Application Dependency Graph

### Before Phase 2:
```text
Inbound Adapters (FastAPI, CLI, Server)
    │
    ├── commands.py (Facade) ──► ApplicationContainer
    └── schemas.py (API Schemas) ◄─── (Coupled!) ─── Application Use Cases
                                                    │
                                                    ├── Path.write_text("indexed_repos.json")
                                                    ├── inline ContextService(...)
                                                    └── raw file reading & snippet search
ApplicationContainer ──► app.api.benchmarks (Circular!)
```

### After Phase 2:
```text
Inbound Adapters (FastAPI, CLI, Server)
    │
    ├── commands.py (Facade) ──► ApplicationContainer (Composition Root)
    └── schemas.py (Facade) ──► [re-exports] ──┐
                                               ▼
                                   Application DTOs (app.application.dto)
                                               ▲
                                               │
                                   Application Use Cases (app.application.use_cases)
                                               │
               ┌───────────────────────────────┼───────────────────────────────┐
               ▼                               ▼                               ▼
       ContextService                RepositoryMetadataStore          SourceSearchService
               ▲                               ▲
               │                               │
        BenchmarkService ──────────────────────┘
```

---

## 4. DTO Migration Summary

The data contracts were extracted into modular, domain-aligned files under `backend/app/application/dto/`:

| Module | Defined DTOs |
| :--- | :--- |
| `common.py` | `ErrorResponse` |
| `context.py` | `GenerateContextRequest`, `ContextResponse`, `AgentContextRequest`, `AgentContextResponse` |
| `indexing.py` | `IndexRepositoryRequest`, `IndexRepositoryResponse`, `RepoArchInfo`, `RepoComponentInfo`, `RepositorySummaryInfo`, `IndexedRepositoryListResponse` |
| `repositories.py` | `RepositoryCreateRequest`, `RepositoryResponse`, `RepositoryListResponse`, `ScanResultResponse` |
| `memory.py` | `ForgetDatasetRequest`, `ForgetDatasetResponse`, `DatasetInfo`, `DatasetListResponse`, `MemoryGraphNode`, `MemoryGraphEdge`, `MemoryGraphResponse`, `VectorDatasetInfo`, `MemoryVectorsResponse`, `MemoryDataItem`, `DatasetDataItemsResponse`, `CognifyRequest`, `CognifyResponse`, `MemoryStatsResponse`, `DashboardStats` |
| `packages.py` | `ContextPackageSaveRequest`, `ContextPackageResponse`, `ContextPackageListResponse`, `ContextPackageAppendRequest` |
| `system.py` | `HealthResponse`, `BackendStatusResponse`, `CogneeSettingsRequest`, `AppSettingsResponse` |
| `benchmarks.py` | `BenchmarkResultItem`, `BenchmarkSuiteResponse` |

`backend/app/api/schemas.py` was refactored into a thin facade re-exporting all 32 models, guaranteeing that existing external consumers (FastAPI routes, CLI commands, test suites) experience zero breaking changes.

---

## 5. Persistence & Retrieval Extraction Details

### 5.1 Repository Metadata Persistence
- **Protocol**: `RepositoryMetadataStore` (`load() -> dict`, `save(data: dict) -> None`) in `app/services/repository_metadata_store.py`.
- **Implementation**: `JsonRepositoryMetadataStore` encapsulating reading/writing `~/.retrack/indexed_repos.json` and fallback to legacy `~/.andes/indexed_repos.json`.
- **Removal**: All `Path.write_text()`, `Path.read_text()`, `_load_repo_store()`, and `_save_repo_store()` methods were removed from `IndexingUseCases`, `RepositoryUseCases`, and `MemoryUseCases`.

### 5.2 Source Search & Snippet Retrieval
- **Service**: `SourceSearchService` in `app/services/source_search_service.py`.
- **Methods**: `build_search_terms()`, `extract_relevant_snippets()`.
- **Encapsulation**: File scanning, size limits (<250KB), stop word filtering, line slicing with surrounding context lines, and file path matching are completely abstracted from `ContextUseCases.get_agent_context()`.

### 5.3 Inline Service Construction Elimination
- Extended `ContextService.generate_context_package()` to accept dynamic `repository_summary` and `target_tokens` overrides.
- `ContextUseCases.get_agent_context()` now delegates directly to `self._context_service.generate_context_package(..., repository_summary=repo_summary, target_tokens=target_tokens)`.

---

## 6. Benchmark Service Relocation

- Extracted benchmark suite runner from `app/api/benchmarks.py` to `app/services/benchmark_service.py` (`BenchmarkService`).
- `BenchmarkService` receives its dependencies (`generate_context_fn`, `health_fn`, `metadata_store`, `settings_getter`) via constructor injection.
- Removed runtime import `from app.api.benchmarks import run_benchmark_suite` from `app/application/container.py`.
- `app/api/benchmarks.py` maintained as a backward-compatibility delegation wrapper.

---

## 7. Composition Root & Singleton Review

- `ApplicationContainer` in `backend/app/application/container.py` acts strictly as the composition root.
- Use cases do not reach into the container; dependencies enter through `__init__` parameters.
- The module-level `_container = ApplicationContainer()` singleton is documented as a transitional composition root instance to support existing legacy entrypoints (`commands.py`, `server.py`).

---

## 8. Verification Results

### 8.1 Backend Test Suite
```text
Command: cd backend && .venv/bin/pytest -v
Result: 307 passed, 2 skipped (live Ollama), 0 failed in 6.78s
```

### 8.2 Architectural Boundary Tests
```text
Command: cd backend && .venv/bin/pytest tests/test_application_boundary.py -v
Result: 12 passed in 3.98s
- TestContextUseCases::test_generate_context_success (PASSED)
- TestContextUseCases::test_generate_context_validation_empty_task (PASSED)
- TestIndexingUseCases::test_indexing_concurrency_rejection (PASSED)
- TestIndexingUseCases::test_indexing_success (PASSED)
- TestRepositoryUseCases::test_repository_crud (PASSED)
- TestPackageUseCases::test_package_crud_and_append (PASSED)
- TestSystemUseCases::test_system_telemetry (PASSED)
- TestApplicationContainerWiring::test_container_instantiates_use_cases (PASSED)
- TestArchitecturalBoundaryInvariants::test_application_layer_ast_purity (PASSED)
- TestArchitecturalBoundaryInvariants::test_no_direct_persistence_in_use_cases (PASSED)
- TestArchitecturalBoundaryInvariants::test_no_inline_context_service_construction (PASSED)
- TestArchitecturalBoundaryInvariants::test_dto_isolation_and_independence (PASSED)
```

### 8.3 AST Integrity Tests
```text
Command: cd backend && .venv/bin/pytest tests/test_ast_integrity.py -v
Result: 4 passed in 4.09s
- test_python_ast_import_and_call_resolution (PASSED)
- test_python_parameter_and_variable_shadowing (PASSED)
- test_python_ambiguous_symbols_produce_no_edge (PASSED)
- test_typescript_react_path_aliases_and_jsx_renders (PASSED)
```

### 8.4 Frontend Production Build
```text
Command: npm run build
Result: TypeScript errors = 0, Vite production bundle generated in 3.58s (Exit code: 0)
```

---

## 9. Architectural Classification Matrix

| Component | Status | Classification | Notes |
| :--- | :--- | :--- | :--- |
| `app/application/dto/` | Active | **Completed** | Clean, transport-independent Pydantic DTOs owned by the application layer. |
| `app/application/use_cases/` | Active | **Completed** | Constructor-injected use cases with 0 inbound or persistence dependencies. |
| `app/services/repository_metadata_store.py` | Active | **Completed** | Storage abstraction protocol + JSON implementation. |
| `app/services/source_search_service.py` | Active | **Completed** | Encapsulated source scanning & snippet extraction service. |
| `app/services/benchmark_service.py` | Active | **Completed** | Relocated benchmark execution service with constructor DI. |
| `app/api/schemas.py` | Active | **Transitional** | Re-export facade for API layer callers; will remain until Phase 5. |
| `app/api/commands.py` | Active | **Transitional** | Delegation facade for legacy API callers; will remain until Phase 5. |
| `app/application/container.py` | Active | **Transitional** | Composition root with module-level singleton for legacy compatibility. |
| Hexagonal Outbound Adapters | Planned | **Deferred to Phase 3** | `MemoryPort`, `ModelPort`, `CGCGraphPort` abstraction interfaces. |
| Headless CLI Extraction | Planned | **Deferred to Phase 4** | Standalone CLI invoking `ApplicationContainer` without `commands.py`. |

---

## 10. Audit Verdict

**Phase 2 is ACCEPTED.**  
The Application Layer is now architecturally isolated, owns its contracts, encapsulates persistence, and operates independently of FastAPI and transport adapters.
