# RE:Track — Architectural Decision Records (ADR Log)

> **Document Status**: Active Record  
> **Date**: 2026-08-20  
> **Governing Framework**: DOX (Documentation-Oriented eXecution)

---

## Decision Index

- [ADR-001: Core Context Engine & Interface Separation](#adr-001-core-context-engine--interface-separation) *(Status: Proposed)*
- [ADR-002: Cognee as an Infrastructure Adapter (MemoryPort)](#adr-002-cognee-as-an-infrastructure-adapter-memoryport) *(Status: Proposed)*
- [ADR-003: Headless CLI Priority Before TUI](#adr-003-headless-cli-priority-before-tui) *(Status: Proposed)*
- [ADR-004: Deterministic AST & Graph Analysis as Core Domain](#adr-004-deterministic-ast--graph-analysis-as-core-domain) *(Status: Accepted / Baseline)*
- [ADR-007: Application & Use-Case Layer Boundary](#adr-007-application--use-case-layer-boundary) *(Status: Accepted / Implemented in Phase 1)*
- [ADR-008: Inbound Boundary Stabilization](#adr-008-inbound-boundary-stabilization) *(Status: Accepted / Implemented in Phase 2)*
- [ADR-009: Decoupled Outbound Adapters](#adr-009-decoupled-outbound-adapters) *(Status: Accepted / Implemented in Phase 3)*
- [ADR-010: Canonical Storage Migration & Compatibility](#adr-010-canonical-storage-migration--compatibility) *(Status: Accepted / Implemented in Phase 4)*
- [ADR-011: Domain Model Refinement & Port Segregation](#adr-011-domain-model-refinement--port-segregation) *(Status: Accepted / Implemented in Phase 5)*
- [ADR-012: Composition Root Lifecycle & FastAPI Route Modularization](#adr-012-composition-root-lifecycle--fastapi-route-modularization-phase-6) *(Status: Accepted / Implemented in Phase 6)*
- [ADR-013: Empirical Evaluation & Benchmark Ground Truth Standardization](#adr-013-empirical-evaluation--benchmark-ground-truth-standardization-phase-7) *(Status: Accepted / Implemented in Phase 7)*
- [ADR-014: Controlled Retrieval Optimization Experiments](#adr-014-controlled-retrieval-optimization-experiments-phase-7e) *(Status: Accepted / Completed in Phase 7E)*
- [ADR-015: MCP Server Inbound Driving Adapter](#adr-015-mcp-server-inbound-driving-adapter-phase-8a) *(Status: Accepted / Implemented in Phase 8A)*
- [ADR-016: MCP Production Hardening & Trust Boundary Enforcement](#adr-016-mcp-production-hardening--trust-boundary-enforcement-phase-8b) *(Status: Accepted / Implemented in Phase 8B)*
- [ADR-017: MCP Operational Lifecycle & Reliability Hardening](#adr-017-mcp-operational-lifecycle--reliability-hardening-phase-8c) *(Status: Accepted / Implemented in Phase 8C)*

---

## ADR-001: Core Context Engine & Interface Separation

### Status
**Proposed**

### Context
Currently, context generation and synthesis logic are intermingled with HTTP request/response handling in `app.api.commands` (2,158 lines) and `app.server`. RE:Track must be capable of running embedded in external tools, headless in CLI workflows, via MCP servers for coding agents, or in desktop GUI mode without depending on a running web server.

### Decision
Extract the core context synthesis, retrieval pipeline, budgeting, and AST parsing into an independent domain module (`app.core.engine`) that has zero dependencies on FastAPI, Uvicorn, Tauri, or HTTP transport layers.

### Consequences
- **Positive**: Enables headless execution, automated scripting, clean testing, and lightweight MCP server integration.
- **Negative**: Requires clean interface boundaries and factory patterns to wire dependency injection.

---

## ADR-002: Cognee as an Infrastructure Adapter (MemoryPort)

### Status
**Proposed**

### Context
Cognee SDK currently permeates multiple layers of the backend, with direct calls to `cognee.remember()`, `cognee.recall()`, `cognee.datasets`, LanceDB connections, and Kùzu graph engines scattered across services and commands. If Cognee changes its internal APIs or if alternative vector/graph backends are introduced, the entire codebase is affected.

### Decision
Isolate all Cognee interactions behind an abstract `MemoryPort` interface. Cognee will serve as an infrastructure adapter (`CogneeMemoryAdapter`) that implements `MemoryPort`. Application use cases will interact solely with `MemoryPort`.

### Consequences
- **Positive**: Decouples domain logic from third-party SDK quirks, simplifies mocking during unit tests, and allows swapping or upgrading storage engines.
- **Negative**: Requires defining explicit domain DTOs to translate Cognee SDK objects into clean internal representations.

---

## ADR-003: Headless CLI Priority Before TUI

### Status
**Proposed**

### Context
Developers need fast terminal access to RE:Track. While a rich Textual-based TUI is attractive, building a full interactive TUI before the CLI risks entangling UI concerns with core domain logic prematurely.

### Decision
Prioritize the implementation and stabilization of a robust, headless CLI (Phase 4) before building any TUI (Phase 8). The CLI will serve as the first decoupled proof-of-concept for the core engine.

### Consequences
- **Positive**: Validates engine independence immediately with minimal frontend overhead; enables piping output to stdout, files, or agent scripts.
- **Negative**: Interactive terminal browsing is deferred to Phase 8.

---

## ADR-004: Deterministic AST & Graph Analysis as Core Domain

### Status
**Accepted (Active in Baseline)**

### Context
Relying purely on LLM inference to understand repository structure is slow, expensive, non-deterministic, and prone to hallucinated symbol relationships.

### Decision
All repository structure, file outline generation, symbol discovery, and call graph relationship tracking must be performed deterministically via Python's standard `ast` module and regex-based AST parsers. LLMs are reserved strictly for semantic query intent extraction and synthesis assistance.

### Consequences
- **Positive**: Instant indexing ($< 200\text{ms}$), 100% deterministic reproducibility, zero token consumption during indexing, and zero hallucinated code calls.
- **Negative**: AST parsers must be maintained for supported languages (Python, TypeScript, JavaScript).

---

## ADR-005: Truth Boundary Guarantee Between Backend & Frontend

### Status
**Accepted (Active in Baseline)**

### Context
In AI tooling, frontends often mask missing or loading backend data by rendering mock/synthetic nodes or estimating metrics locally, creating a false perception of system state.

### Decision
The backend is the sole authority for repository analysis, graph identity, memory statistics, benchmark measurements, and hardware telemetry. The frontend must NEVER invent missing nodes/edges, infer status from empty arrays, substitute static metrics, or recover missing data with synthetic fallbacks.

### Consequences
- **Positive**: Absolute data integrity; developers and agents can trust that every displayed node, edge, and token metric corresponds to real data.
- **Negative**: UI states must gracefully handle genuine empty states and backend error conditions.

---

## ADR-006: Hexagonal Ports & Adapters Architecture for Infrastructure

### Status
**Proposed**

### Context
The backend currently exhibits mixed dependency directions: API layers call services, services call SDKs directly, and commands manage persistence files directly on disk.

### Decision
Adopt Hexagonal Architecture (Ports and Adapters) for the backend:
- **Core Domain**: Pure logic (`ContextEngine`, `ASTAnalyzer`, `Pipeline`, `BudgetManager`).
- **Application Layer**: Use case interactors (`GenerateContextUseCase`, `IndexRepositoryUseCase`).
- **Inbound Adapters (Driving)**: FastAPI HTTP routes, Typer CLI commands, MCP server tools.
- **Outbound Adapters (Driven)**: `CogneeMemoryAdapter`, `OpenAIModelAdapter`, `CGCGraphAdapter`, `JsonPersistenceAdapter`.

### Consequences
- **Positive**: Clean separation of concerns, high testability, modular pluggability of providers.
- **Negative**: Introduces boilerplate DTOs and interface abstractions.

---

## ADR-007: Application & Use-Case Layer Boundary

### Status
**Accepted / Implemented (Phase 1)**

### Context
`backend/app/api/commands.py` had accumulated 2,158 lines containing HTTP response shaping, concurrency locks, caching, prompt heuristics, file store operations, and service coordination. To allow CLI and future MCP adapters to invoke workflows cleanly, business orchestration needed to be separated from inbound transport logic.

### Decision
Extract all business workflows into explicit use case classes under `backend/app/application/use_cases/`:
- `ContextUseCases`: Context generation (`generate_context`), agent context synthesis (`get_agent_context`), and LRU cache orchestration.
- `IndexingUseCases`: Incremental indexing (`index_repository`), concurrency locking, and summary listing (`get_repository_summaries`).
- `RepositoryUseCases`: Repository CRUD, AST scanning, progress polling, deletion, and AST-grounded prompt suggestions.
- `MemoryUseCases`: Dataset listing, document data items, cognify extraction, memory statistics, graph introspection, vector introspection, and dashboard telemetry.
- `PackageUseCases`: Context Package CRUD and append operations.
- `SystemUseCases`: Health checks, hardware telemetry (RAM/CPU/GPU), app settings, and provider hot-reloading.
- `BenchmarkUseCases`: Authoritative benchmark suite execution.

All use cases receive their dependencies explicitly via constructors. `backend/app/application/container.py` acts as the composition root. `commands.py` is maintained as a thin backward-compatibility facade to ensure existing tests and callers continue working without modification.

### Consequences
- **Positive**:
  - Clear architectural boundary: application layer does not import FastAPI, CLI, or low-level storage drivers.
  - Testability: All use cases can be directly instantiated and tested in isolation with mocked dependencies.
  - Zero behavioral change: All 25 HTTP endpoints, CLI commands, and test suites run unchanged.
- **Negative**:
  - Requires maintaining the `commands.py` facade until all callers are migrated to use case interfaces in subsequent phases.

---

## ADR-008: Application DTO Ownership & Core Boundary Isolation

### Status
**Accepted / Implemented (Phase 2)**

### Context
Following Phase 1, `app.application` had achieved structural decomposition, but still had architectural coupling:
1. Use cases imported request/response schemas from `app.api.schemas`.
2. `get_agent_context()` contained low-level source searching, file reading, and inline `ContextService(...)` instantiation.
3. `IndexingUseCases`, `RepositoryUseCases`, and `MemoryUseCases` performed raw JSON filesystem I/O against `~/.retrack/indexed_repos.json`.
4. `ApplicationContainer` imported `app.api.benchmarks` at runtime.

### Decision
1. **Application-Owned DTOs**: Create `backend/app/application/dto/` (`common.py`, `context.py`, `indexing.py`, `repositories.py`, `memory.py`, `packages.py`, `system.py`, `benchmarks.py`) to own all application contracts. `app.api.schemas` acts as a backward-compatibility facade re-exporting these DTOs.
2. **Persistence Abstraction**: Introduce `RepositoryMetadataStore` (Protocol) and `JsonRepositoryMetadataStore` under `app/services/repository_metadata_store.py`. Inject the store into use cases, removing all direct `Path.write_text()` and `json.loads()` from application orchestration.
3. **Source Search Service**: Extract source scanning and snippet extraction from `ContextUseCases` into `SourceSearchService` (`app/services/source_search_service.py`).
4. **Eliminate Inline Service Construction**: Extend `ContextService.generate_context_package()` to accept optional `repository_summary` and `target_tokens`, enabling direct delegation from `ContextUseCases`.
5. **Benchmark Service Relocation**: Move core benchmark suite execution to `app/services/benchmark_service.py` with constructor DI. `app.api.benchmarks` remains as a compatibility wrapper.
6. **Enforce Boundary Invariants**: Update AST static analysis tests in `test_application_boundary.py` to forbid any imports of `app.api`, `fastapi`, `starlette`, `app.server`, `app.cli`, `kuzu`, `lancedb`, or `cognee.api.v1` in `app/application/*`.

### Consequences
- **Positive**:
  - `app.application` is completely decoupled from `app.api` and web frameworks (0 AST boundary violations).
  - Use cases represent pure domain orchestration and can be run in any headless environment (CLI, test runner, background worker).
  - 100% backward compatibility maintained for all 25 HTTP routes, CLI commands, and test suites.
- **Negative**:
  - Two layers of schema re-exports exist during transition (`app.application.dto` $\rightarrow$ `app.api.schemas`).

---

## ADR-009: Application Ports & Infrastructure Adapters (Phase 3)

### Status
Accepted

### Context
Phase 1 established the Application Use-Case boundary, and Phase 2 established Application Layer transport independence and DTO ownership. However, use cases still depended directly on concrete service class implementations (`app.services.*`), repository metadata was stored as untyped dictionaries, and filesystem operations and hardware telemetry were coupled to standard-library/OS specifics.

### Decision
1. **Typed Repository Domain Entity**: Define `IndexedRepositoryRecord` under `app.application.domain.repository.py` with typed fields for repository metadata, architecture layers, components, and call graph status.
2. **Explicit Capability Ports (`app.application.ports.*`)**:
   - Define Python `Protocol` interfaces for all infrastructure and service capabilities: `FileSystemPort`, `RepositoryMetadataPort`, `MemoryPort`, `SourceSearchPort`, `ContextServicePort`, `IndexingServicePort`, `RepositoryManagerPort`, `LLMProviderPort`, `ContextPackageRepositoryPort`, `CGCServicePort`, `IntentParserPort`, `SummaryGeneratorPort`, `ContextCachePort`, `HardwareTelemetryPort`, and `BenchmarkRunnerPort`.
3. **Infrastructure Adapters (`app.services.*`)**:
   - Introduce `LocalFileSystemAdapter` implementing `FileSystemPort`.
   - Introduce `LocalHardwareTelemetryAdapter` implementing `HardwareTelemetryPort`.
   - Update `JsonRepositoryMetadataStore` to implement `RepositoryMetadataPort` with typed `IndexedRepositoryRecord` domain models.
   - Refactor `SourceSearchService` to depend on `FileSystemPort`.
4. **Use-Case Dependency Inversion**:
   - Refactor all seven use-case classes under `app.application.use_cases/` so that constructors declare abstract port dependencies rather than concrete service classes.
   - Forbid all imports of `app.services` in `app.application.use_cases/`.
5. **Composition Root (`app.application.container.py`)**:
   - Wire concrete infrastructure adapters into use cases at the composition root.
6. **AST Architectural Invariant Checks**:
   - Expand `test_application_boundary.py` to enforce that `app.application.use_cases/`, `app.application.ports/`, and `app.application.domain/` have zero imports from `app.services` or external framework/database modules.

### Consequences
- **Positive**:
  - Core application layer depends purely on capability contracts (Inversion of Control).
  - Use cases can be tested in complete isolation using lightweight fake port implementations without database or filesystem access.
  - Domain records are strongly typed, eliminating untyped dictionary leakage.
  - Zero behavioral regressions; all API routes, CLI commands, and test suites remain 100% compatible.
- **Negative**:
  - Increased number of protocol definitions requiring maintenance as capability contracts evolve.

---

## ADR-010: Storage Compatibility & Non-Destructive Legacy Fallback Architecture (Phase 4)

### Status
**Accepted / Implemented (Phase 4)**

### Context
RE:Track evolved from a predecessor named Andes, which persisted data under `~/.andes/`. To guarantee seamless backward compatibility without data loss or corruption, RE:Track requires a strictly enforced dual-path storage policy across user-level configuration, repository metadata, context packages, manifests, and cloned repository working trees. Furthermore, importing `app.services` previously loaded heavyweight vendor frameworks eagerly due to eager top-level imports in `app/services/__init__.py` (DEBT-004).

### Decision
1. **Canonical vs Legacy Storage Domains**:
   - `~/.retrack/` is the **canonical writable storage** location for all user application state (`indexed_repos.json`, `repositories.json`, `context_packages.json`, `settings.json`, `manifests/`, `repos/`).
   - `~/.andes/` is a **strictly read-only legacy compatibility fallback**.
   - `<repo>/.retrack/` is the canonical repository-local metadata directory, with `<repo>/.andes/` as read-only fallback.
2. **Read/Write Operations Contract**:
   - **Read Precedence**: Check canonical storage first. If absent, fall back to legacy storage. If both are absent, return clean empty defaults.
   - **Write Exclusivity**: All new writes, updates, and deletions target canonical storage exclusively.
   - **Legacy Immutability**: Legacy storage is observationally read-only. Legacy files and working trees must never be deleted, renamed, overwritten, mutated, or silently migrated into canonical storage.
3. **Atomic Persistence**:
   - Implement temporary file (`.tmp`) + flush + `fsync` + atomic replace for all JSON storage adapters (`JsonRepositoryMetadataStore`, `RepositoryManager`, `JsonContextPackageRepository`, `Settings`, `ManifestService`).
4. **Clone Safety**:
   - New GitHub clones target `~/.retrack/repos/`.
   - Existing legacy clones in `~/.andes/repos/` are treated as read-only inspection targets. Scanning and AST analysis execute non-mutating file walks and `git rev-parse` only (no `git pull`, `git checkout`, or directory writes against legacy trees).
   - Deleting a repository registration removes it from canonical metadata JSON only; it never deletes clone directories on disk.
5. **DEBT-004 Packaging Cleanup**:
   - Replace eager imports in `app/services/__init__.py` with dynamic `__getattr__` exports so importing `app.services` or individual adapters does not eagerly load `cognee`, `fastapi`, or `starlette`.

### Consequences
- **Positive**:
  - 100% data preservation and transparent compatibility for existing users with legacy `.andes` state.
  - Zero side-effect legacy fallback (verified by byte-for-byte SHA256 immutability tests).
  - Clean service package import isolation without transitive web-framework loading.
  - Complete test isolation in isolated unit tests.
- **Negative**:
  - Persistence adapters maintain explicit dual-path fallback logic until legacy format support is deprecated in future major versions.

---

## ADR-011: Domain Model Refinement & Memory Port Capability Segregation

### Status
Accepted (Phase 5)

### Context
Following the stabilization of application boundaries in Phase 3 and storage compatibility in Phase 4, three debts remained in the domain and port models:
1. **DEBT-005**: `MemoryPort` exposed an overly broad interface (13 methods) returning unstructured, dynamic dictionaries (`dict[str, Any]` and `list[dict[str, Any]]`), forcing use cases to know the internal dictionary keys returned by the Cognee infrastructure service.
2. **DEBT-006**: `IndexedRepositoryRecord` contained untyped `architecture: list[dict[str, Any]]` and `components: list[dict[str, Any]]` collections, weakening domain type guarantees while interacting with JSON metadata stores.
3. **DEBT-007**: `IntentParserPort` contained `@staticmethod def rule_based_fallback` directly on the Protocol interface, and `ContextUseCases` duplicated regex and keyword parsing in a private helper.

### Decision
1. **Memory Capability Segregation**:
   - Decompose `MemoryPort` into five focused capability protocols in `app/application/ports/memory.py`:
     - `MemoryLifecyclePort`: `is_initialized`, `initialize()`
     - `MemoryIngestionPort`: `add()`, `remember()`
     - `MemoryRetrievalPort`: `recall()`
     - `MemoryDatasetPort`: `list_datasets()`, `get_dataset_data()`, `forget()`, `forget_data_item()`
     - `MemoryTopologyPort`: `cognify()`, `get_stats()`, `get_graph()`, `get_vectors()`
   - Maintain a composite `MemoryPort` inheriting from the capability protocols to preserve complete backwards compatibility.
   - Refactor use cases (`SystemUseCases`, `RepositoryUseCases`) to depend on the narrowest capability protocol required.
2. **Typed Memory Domain Entities**:
   - Define typed domain dataclasses in `app/application/domain/memory.py`: `MemoryDatasetRecord`, `MemoryDataItemRecord`, `MemoryGraphNodeRecord`, `MemoryGraphEdgeRecord`, `MemoryGraphRecord`, and `MemoryVectorStatsRecord`.
   - Ensure use cases and adapters support both typed domain records and dict fallbacks polymorphically.
3. **Typed Repository Substructures**:
   - Define `ArchitectureLayerRecord` (`icon: str = "Layers"`, `label: str = ""`) and `ComponentRecord` (`path: str = ""`, `centrality: str = "core"`) in `app/application/domain/repository.py`.
   - Update `IndexedRepositoryRecord` to type `architecture: list[ArchitectureLayerRecord]` and `components: list[ComponentRecord]`.
   - Implement tolerant `from_dict()` and `to_dict()` methods that seamlessly parse legacy format inputs (strings or dicts) without migration or schema breakages.
4. **Pure Heuristic Intent Extraction**:
   - Define `ParsedIntentRecord` in `app/application/domain/intent.py`.
   - Define `parse_intent_heuristics(prompt: str) -> ParsedIntentRecord` as a pure, deterministic, side-effect-free domain function.
   - Remove static method from `IntentParserPort` protocol and remove duplicated fallback logic from `ContextUseCases`.

### Consequences
- **Positive**:
  - Application use cases depend on fine-grained, cohesive capability contracts rather than monolithic ports.
  - Domain records guarantee strong type safety for repository metadata, intent extraction, and memory structures.
  - 100% backward compatibility preserved for historical `indexed_repos.json` and `.andes` fallback data.
  - Zero framework dependencies inside `app.application.domain` and `app.application.ports`.
- **Negative**:
  - Additional domain model classes to maintain in the domain package.

---

## ADR-012: Composition Root Lifecycle & FastAPI Route Modularization (Phase 6)

### Status
**Accepted / Implemented (Phase 6)**

### Context
In earlier phases, `ApplicationContainer` was eagerly instantiated as a module-level global singleton (`_container = ApplicationContainer()`) upon importing `app.application.container` (DEBT-003). This created hidden side effects during module load, coupled unit tests to global runtime state, and obscured dependency graph construction. Concurrently, `app/server.py` had accumulated 384 lines containing monolithic route definitions, inline HTTP logic, CORS configuration, and lifespan management.

### Decision
1. **Composition Root Lifecycle & Isolation (DEBT-003 Resolution)**:
   - Eliminate eager module-level container instantiation. `_container` is initialized to `None` at import time.
   - Introduce explicit factory method `ApplicationContainer.create(settings: Optional[Settings] = None) -> ApplicationContainer`.
   - Provide `get_container()`, `set_container()`, and `reset_container()` scoped strictly to composition, API, CLI, and test boundaries.
   - Enforce via AST verification that domain models, application use cases, and ports NEVER import `get_container()` or use it as a service locator.
2. **FastAPI Route Modularization**:
   - Split monolithic `server.py` into cohesive domain routers under `app/api/routers/`:
     - `system.py`: `/health`, `/status`, `/dashboard/stats`, `/provider/update`
     - `repositories.py`: `/repos`, `/repos` (POST), `/repos/{repo_id}/scan`, `/repos/{repo_id}/progress`, `/repos/{repo_id}` (DELETE), `/repos/{repo_id}/prompts`, `/repositories`
     - `context.py`: `/index`, `/context`, `/api/v1/context`
     - `memory.py`: `/datasets`, `/datasets/{dataset_id}/items`, `/forget`, `/memory/stats`, `/memory/graph`, `/memory/vectors`, `/memory/cognify`
     - `packages.py`: `/packages`, `/packages` (POST), `/packages/{package_id}`, `/packages/{package_id}` (DELETE), `/packages/{package_id}/append`
     - `benchmarks.py`: `/benchmarks/run`
     - `settings.py`: `/settings`, `/settings/cognee`
     - `__init__.py`: Router package exports and `register_routers(app: FastAPI)` helper.
3. **Application Server Assembly**:
   - Simplify `app/server.py` to a clean assembly file (< 80 lines) configuring lifespan management, CORS middleware, and `register_routers()`.
4. **Backward Compatibility Preservation**:
   - Retain `app.api.commands` as a backward-compatible CLI facade dynamically resolving the active container without global state leaks.
   - Maintain 100% parity across all 29 HTTP operations (status codes, response schemas, error formatting, path parameters).

### Consequences
- **Positive**:
   - Zero import-time side effects when loading `container.py` or application modules.
   - Clean separation between HTTP transport routing and core application use cases.
   - High modularity for API maintenance with independent, cohesive router files.
   - Full test isolation through `set_container()` and `reset_container()`.
   - Comprehensive test suite (14 dedicated Phase 6 tests, 356 total passed).

---

## ADR-013: Empirical Evaluation & Benchmark Ground Truth Standardization (Phase 7)

### Status
**Accepted / Implemented (Phase 7)**

### Context
Following the completion of structural refactoring in Phases 1–6, RE:Track needed a trustworthy, reproducible method to evaluate the retrieval quality, precision, recall, and evidence coverage of the Context Engine. Prior benchmarks suffered from path disconnects (`benchmarks/retrack` vs `benchmarks/andescontext`), synthetic mock data scoring that bypassed live components, and hardcoded placeholder accuracy summaries (`"Not evaluated (no ground truth set)"`).

### Decision
1. **Canonical Golden Task Benchmark Dataset**:
   - Establish `benchmarks/retrack/golden_tasks.json` containing 20 high-quality tasks across four core categories (Architecture, Bug Localization, Feature Addition, Refactoring).
   - Define exact ground-truth expected files, critical files, expected symbols, critical symbols, and negative/irrelevant files based on manual code inspection.
   - Maintain `benchmarks/andescontext/` as a backward-compatible legacy fallback.
2. **Pure Evaluation Engine**:
   - Implement `tests/evaluation/evaluator.py` containing deterministic algorithms for Precision@K, Recall@K, Critical Evidence Coverage, Noise Ratio, and Token Compression.
   - Zero dependencies on Cognee or heavy infrastructure in the evaluation math.
3. **Automated Evaluation Test Suite**:
   - Construct `tests/evaluation/test_context_engine_eval.py` and `reporter.py` to execute real Context Engine components without synthetic mock shortcuts, generating an empirical baseline scorecard (`benchmarks/retrack/context_engine_baseline_scorecard.md`).
4. **Dynamic API Benchmark Reporting**:
   - Update `BenchmarkService` in `app/services/benchmark_service.py` to dynamically load ground-truth tasks and calculate empirical critical evidence coverage rather than returning static placeholder strings.

### Consequences
- **Positive**:
   - Empirical baseline established across 20 real tasks (Mean Compression: 19.73x, Mean Retrieval Latency: 15.0ms, Mean Noise: 0.013).
   - 100% backend test pass rate (365 passed, 0 skipped, 0 failed).
   - Transparent measurement of retrieval gaps to guide future retrieval optimizations.
- **Negative**:
   - Requires maintaining golden task ground truth alongside codebase evolutions.

---

## ADR-014: Controlled Retrieval Optimization Experiments (Phase 7E)

### Status
**Accepted / Completed (Phase 7E)**

### Context
Phase 7D diagnostic traces identified retrieval bottlenecks across the 20 golden tasks. Before implementing broad architectural changes or multi-hop AST resolvers, Phase 7E was commissioned to experimentally isolate 7 key hypotheses against the live `ContextUseCases.get_agent_context` production pipeline using `NullContextCache`.

### Decision
1. **Resolved Evaluation Metric Discrepancies**:
   - Codified `tests/evaluation/evaluator.py` as the sole evaluation authority.
   - Defined $K=10$ as the evaluation cut-off window.
   - Documented the exact causes of precision/recall variance between live pipeline and isolated script executions.
2. **Experimental Matrix Classifications**:
   - **AST Complete File Indexing (500 Nodes)**: `PROVEN` (+10.4% Recall, +9.2% Critical Coverage, 259ms build time).
   - **Deterministic Intent Priors**: `PROVEN` (Pass rate increased from 40% to 70%, Critical Coverage to 0.650 without LLM latency).
   - **Repository Summary Fingerprint Caching**: `PROVEN` (9.3x speedup, 246ms -> 26.6ms).
   - **Dynamic Candidate Trimming ($K < 10$)**: `REJECTED` (Degraded recall from 0.49 to 0.26).
   - **Static Test-File Scoring Penalty**: `REJECTED` (Suppressed required test evidence in diagnostic tasks).
   - **CGC Subprocess Architecture**: `PROVEN BOTTLENECK` (2135ms mean latency prohibits CLI subprocess in hot path).
3. **Completion Gate Verdict**:
   - Phase 7 (Context Engine Validation) is verified and complete. All baseline invariants, empirical metrics, and optimization paths are documented.

---

## ADR-015: MCP Server Inbound Driving Adapter (Phase 8A)

### Status
**Accepted / Implemented (Phase 8A)**

### Context
External AI coding assistants (such as Claude Code, Cursor, Antigravity, and Gemini CLI) require access to RE:Track's persistent repository memory, deterministic AST call graphs, architectural summaries, and high-precision context packages through the standardized Model Context Protocol (MCP) over stdio.

### Decision
1. **Hexagonal Driving Adapter Placement**:
   - Implement MCP strictly as an inbound/driving transport adapter in `backend/app/mcp/` (`server.py`, `tools.py`, `__init__.py`).
   - The MCP layer imports *only* Application Use Cases, DTOs, the composition root container, and the official MCP SDK. Zero direct imports of databases, Cognee, or concrete infrastructure services.
2. **Standardized MVP Tool Surface (5 Tools)**:
   - `get_agent_context`: Token-budgeted context package synthesis with caller/callee graphs and symbol references.
   - `get_repository_summary`: High-level architectural knowledge, tech stack, key components, and entry points.
   - `get_ast_call_graph`: Deterministic AST call graph (nodes and directed edges) with optional path prefix filtering.
   - `search_repository_code`: High-speed symbol and keyword search across repository source files.
   - `list_indexed_repositories`: Lists all registered repositories with metadata and status.
3. **No Subprocess Bottleneck Invariant**:
   - Spawning `cgc` as an external subprocess in the synchronous retrieval path is prohibited (Phase 7E finding: ~2135ms mean latency).
   - The MCP adapter strictly utilizes the in-process `RepositorySummaryGenerator` and `SourceSearchService` via `ContextUseCases` and `RepositoryUseCases`.
4. **Canonical Entry Point**:
   - Expose stdio server through `python -m app.mcp`, `python mcp_server.py`, and `retrack mcp` CLI command.

### Consequences
- **Positive**:
   - Full MCP protocol compatibility with Claude Code, Cursor, Antigravity, and other MCP clients.
   - Zero duplication of retrieval, ranking, AST extraction, or formatting logic.
   - Sub-100ms warm response times through in-process caching.
   - Verified by 12 comprehensive unit, boundary, and protocol tests.
- **Negative**:
   - Adds `mcp>=1.0.0` dependency to backend.

---

## ADR-016: MCP Production Hardening & Trust Boundary Enforcement (Phase 8B)

### Status
**Accepted / Implemented (Phase 8B)**

### Context
A hostile production-boundary audit of Phase 8A identified security vulnerabilities and boundary gaps: arbitrary host directory scanning, symlink escapes, cross-repository dataset collision for matching directory basenames, eager concurrency rejection, and unhandled exception leaks across JSON-RPC.

### Decision
1. **Workspace Authorization Boundary**:
   - Define `WorkspaceAuthorizationPort` and `WorkspaceAuthorizationService`.
   - Restrict MCP access to explicitly registered repositories and configured `RETRACK_WORKSPACE_ROOTS`.
   - Prohibit access to root filesystems (`/`, `C:\`), system directories (`/etc`, `/proc`, `/sys`), and credential stores (`~/.ssh`, `~/.gnupg`).
   - Prune symlinks escaping the authorized repository boundary during discovery and indexing.
2. **Dataset Identity & Memory Isolation**:
   - Implement deterministic collision-proof dataset identifiers: `{sanitized_basename}_{path_sha256_10hex}` via `derive_dataset_name()`.
   - Physically isolate memory across distinct repositories with identical folder basenames.
3. **Bounded Concurrency & Queueing**:
   - Implement `BoundedConcurrencyGuard` with `max_concurrent=1`, `max_queue=5`, and `timeout=30.0s`.
   - Replace eager rejection with FIFO queueing; reject on queue saturation with retryable `BusyError`.
4. **Exception Isolation Boundary**:
   - Encapsulate all MCP tool handlers in exception boundaries mapping unexpected errors to sanitized, structured error DTOs (`ValidationError`, `AuthorizationError`, `ConnectionError`, `InternalError`).

---

## ADR-017: MCP Operational Lifecycle & Reliability Hardening (Phase 8C)

### Status
**Accepted / Implemented (Phase 8C)**

### Context
Operational reliability testing revealed that the concurrency guard was instantiated per-use-case factory call rather than shared across MCP requests, logging defaulted to stdout (risking JSON-RPC framing corruption), and stdin EOF handling needed graceful process termination.

### Decision
1. **Process-Scoped Shared Concurrency Guard**:
   - Instantiated singleton `BoundedConcurrencyGuard` on `ApplicationContainer` and injected into `ContextUseCases`.
   - Enforced single-worker execution with 5-slot FIFO queueing across all simultaneous MCP requests.
2. **Stdio Protocol & Logging Separation**:
   - Configured `setup_logging` to write strictly to `sys.stderr` across all modules (including Cognee and structlog).
   - Dedicated `sys.stdout` exclusively to clean, uncorrupted JSON-RPC frames.
3. **Graceful Stdio EOF & Signal Shutdown**:
   - Hardened `run_mcp_stdio` to terminate cleanly within 0.15s on stdin EOF, `SIGINT`, `SIGTERM`, or asyncio task cancellation.
4. **Verified Same-Process Automatic Provider Recovery**:
   - Confirmed deterministic tools operate independently of LLM reachability.
   - Proved that when a failed LLM provider is restored, subsequent context synthesis calls recover automatically in the same running MCP process without restart.

