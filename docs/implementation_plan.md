# RE:Track Implementation Plan

## Purpose

This document defines the implementation roadmap for RE:Track (RefinedEngine Track).

It translates the project vision and architecture into concrete development milestones.

Each milestone should produce a working, testable increment of the application.

---

# Guiding Principle

Implement vertical slices.

Each completed milestone should improve the working application rather than only expanding the codebase.

Avoid implementing infrastructure that is not immediately required.

---

# Milestone 1 — Backend Foundation ✅

## Goal

Create the production backend and establish Cognee integration.

### Tasks

- Configure Python backend structure
- Configure Ollama with phi3:mini
- Install Cognee 1.2.2
- Configure local databases (LanceDB, Kuzu, SQLite)
- Implement CogneeService
- Implement IndexingService
- Implement ContextService
- Verify remember()
- Verify recall()
- Verify improve()
- Verify forget()
- End-to-end pipeline test

### Deliverables

- Production backend (`backend/app/`)
- CogneeService — thin wrapper around Cognee APIs
- IndexingService — repository file discovery, filtering, batching
- ContextService — memory retrieval, dedup, ranking, Markdown generation
- Verified Cognee integration with phi3:mini
- Structured logging, error handling, type hints

Status: **Completed**

---

# Milestone 2 — API Layer (Backend Commands) ✅

## Goal

Expose backend services through a command API for Tauri IPC.

### Tasks

- Define command interface
- Implement health/status commands
- Implement indexing commands
- Implement context generation commands
- Implement forget commands
- Error handling for IPC
- Response serialization

### Deliverables

- Command API layer (`backend/app/api/`)
- Async commands: health, get_backend_status, index_repository, generate_context, forget_dataset, get_repository_summaries
- Pydantic request/response schemas
- Structured error responses
- Request validation
- Execution time logging
- Comprehensive test suite (284+ tests passing)

Status: **Completed**

---

# Milestone 3 — Frontend Foundation ✅

## Goal

Expose the backend through a desktop interface.

### Pages Delivered

- Dashboard (Prompt Workbench + Repository AST Map)
- Memory viewer
- Benchmarks
- Settings

### Deliverables

- Functional Tauri + React + Vite application
- Vercel Geist monochrome aesthetic
- Backend integration via Tauri IPC
- Repository store with indexed repo list
- Health/status telemetry in Settings
- Live hardware monitoring (RAM, CPU, GPU VRAM)

Status: **Completed**

---

# Milestone 4 — Repository Knowledge Layer ✅

## Goal

Build the Depth-2.5 structural map and call graph extraction.

### Tasks

- `.gitignore`-aware dynamic file filtering
- Depth-2.5 directory map (root → subfolders → AST symbols)
- Python AST class/function extraction
- React/Vite/Next/Vue component detection
- Repository name dropdown for fast switching
- Fixed card layout stability on selection change

### Deliverables

- `RepositorySummaryGenerator._build_repo_map` — framework-aware grouping
- `RepositorySummaryGenerator._extract_components` — Python AST + React regex
- Gitignore integration in `IndexingService.scan_repository`
- Repository AST Map tab in Dashboard
- Dynamic "N AST & Directory Entries" count badge

Status: **Completed**

---

# Milestone 5 — Call Graph ✅

## Goal

Extract real function/class/component dependency graphs and render them interactively.

### Tasks

- Add `CallNode`, `CallEdge` dataclasses to `responses.py`
- Implement `_build_call_graph` in `RepositorySummaryGenerator`
  - Python: `ast.ClassDef`, `ast.FunctionDef`, `ast.AsyncFunctionDef`, `ast.Call` visitor
  - React/TS: export component regex, relative import edges, JSX renders edges
- Persist `call_graph_nodes` + `call_graph_edges` in repo metadata store
- Add `CallGraphNode`, `CallGraphEdge` types to `src/types/repository.ts`
- Build `CallGraphView.tsx` — pure React + SVG force-directed graph
  - Spring simulation (repulsion + link springs + centering + damping at 60 fps)
  - Node shapes: square=class, diamond=component, circle=function/method
  - Edge styles: solid=calls, dashed=imports, thick=inherits, dotted=renders
  - Drag nodes, scroll-to-zoom, pan, tooltip, legend
- Directory List / Call Graph sub-tab toggle in Repository AST Map

### Deliverables

- Backend call graph extraction (Python + React/TS)
- `CallGraphView.tsx` — interactive force-directed SVG component
- Repository AST Map now has two sub-views: Directory List and Call Graph
- Zero external graph library dependencies

Status: **Completed**

---

# Milestone 6 — Polish (In Progress)

## Goal

Prepare for demonstration and production use.

### Remaining Tasks

- [ ] Redesign Memory, Benchmarks, Settings pages in Geist style
- [ ] Add persistent node positions (localStorage) in CallGraphView
- [ ] Export call graph as PNG/SVG
- [ ] Session memory (SessionService)
- [ ] Performance improvements for large graphs (>80 nodes: pagination or cluster view)

Status: **In Progress**

---

# Development Order

```
Backend Foundation         ✅
API Layer                  ✅
Frontend Foundation        ✅
Repository Knowledge       ✅
Call Graph                 ✅
Polish                     In Progress
```

---

# Definition of Done

A milestone is considered complete when:

- Functionality works as intended.
- Code has been reviewed.
- Documentation is updated.
- AGENTS.md has been checked.
- No known critical issues remain.

# Milestone 6 — Hexagonal Architecture & Modular Routing ✅

## Goal

Decouple business use cases from transport frameworks and enforce strict dependency inversion.

### Deliverables

- Inbound Driving Adapters (FastAPI routers, Headless CLI, MCP stdio server).
- Application Use Cases (`ContextUseCases`, `IndexingUseCases`, `RepositoryUseCases`, `MemoryUseCases`, `PackageUseCases`, `SystemUseCases`).
- Pure Domain Ports (`MemoryPort`, `SourceSearchPort`, `WorkspaceAuthorizationPort`, `MetadataStorePort`, `FileSystemPort`, `HardwareTelemetryPort`).
- Centralized composition root (`ApplicationContainer`) with lifespan hooks and zero global singletons.
- Modular domain routers under `backend/app/api/routers/`.

Status: **Completed**

---

# Milestone 7 — Empirical Benchmarking & Ground Truth Evaluation ✅

## Goal

Establish reproducible ground truth benchmarks and evaluate Context Engine retrieval quality.

### Deliverables

- Golden task dataset (`benchmarks/retrack/golden_tasks.json`, 20 curated tasks).
- Pure evaluation engine (`tests/evaluation/evaluator.py`) measuring Precision@K, Recall@K, Critical Evidence Coverage, and Noise Ratio.
- Automated evaluation runner & reporting suite (`tests/evaluation/test_context_engine_eval.py`).
- Phase 7E controlled retrieval experiments (proven AST indexing, intent priors, fingerprint caching; CGC subprocess prohibited on hot path).

Status: **Completed**

---

# Milestone 8 — Model Context Protocol (MCP) Server & Operational Hardening ✅

## Goal

Provide high-precision repository memory, AST call graphs, and context packages to external AI coding agents over standardized stdio transport with strict security and operational boundaries.

### Deliverables

- **Phase 8A (MCP Inbound Adapter)**: FastMCP stdio server (`backend/app/mcp/`) exposing 5 tools (`get_agent_context`, `get_repository_summary`, `get_ast_call_graph`, `search_repository_code`, `list_indexed_repositories`).
- **Phase 8B (Security & Trust Boundary Hardening)**: Workspace authorization boundary (`WorkspaceAuthorizationService`), symlink containment, collision-proof dataset identity isolation (`derive_dataset_name`), bounded context concurrency guard, and sanitized exception isolation.
- **Phase 8C (Operational Lifecycle & Reliability Hardening)**: Process-scoped shared concurrency guard, stderr-only logging isolation, clean stdio EOF/signal termination (< 0.15s), and verified automatic same-process LLM provider recovery.

Status: **Completed (Production Ready)**

---

# Current Status

Current Phase: **Phase 8C Completed — Production Ready**

Completed Components:
- `ApplicationContainer` (Composition Root) ✅
- `ContextUseCases` & `BoundedConcurrencyGuard` ✅
- `IndexingUseCases` & `IndexingService` ✅
- `RepositoryUseCases` & `RepositoryManager` ✅
- `MemoryUseCases` & `CogneeMemoryAdapter` ✅
- `PackageUseCases` & `ContextPackageRepository` ✅
- `SystemUseCases` & Hardware Telemetry ✅
- `WorkspaceAuthorizationService` (Filesystem & Symlink Containment) ✅
- `RepositorySummaryGenerator` (2-Pass Deterministic AST Resolver) ✅
- `SourceSearchService` (In-Process Fast Symbol & Keyword Search) ✅
- `MCPServer` & 5 Standardized MCP Tools ✅
- React + Vite + Tauri Frontend (Context Studio, Knowledge Explorer, Memory, Benchmarks, Settings) ✅
- 415 passing backend unit, integration, and security tests ✅
- Clean frontend TypeScript compile & Vite build ✅
