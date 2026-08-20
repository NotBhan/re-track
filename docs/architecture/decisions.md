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
- [ADR-005: Truth Boundary Guarantee Between Backend & Frontend](#adr-005-truth-boundary-guarantee-between-backend--frontend) *(Status: Accepted / Baseline)*
- [ADR-006: Hexagonal Ports & Adapters Architecture for Infrastructure](#adr-006-hexagonal-ports--adapters-architecture-for-infrastructure) *(Status: Proposed)*

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
