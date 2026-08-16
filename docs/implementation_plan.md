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

---

# Current Status

Current Milestone: **Milestone 6 — Polish**

Completed services:

- CogneeService ✅
- IndexingService (delta + .gitignore filtering) ✅
- ContextService ✅
- PackageBuilder ✅
- BudgetManager ✅
- MarkdownRenderer ✅
- RepositorySummaryGenerator (Depth-2.5 + call graph) ✅
- CallGraphExtractor (embedded, Python AST + React/TS) ✅
- Pipeline stages (dedup, rank, compress, categorize, references) ✅
- StatsLogger ✅
- API layer (commands + schemas) ✅
- React frontend (Dashboard, Memory, Benchmarks, Settings) ✅
- CallGraphView (interactive force-directed SVG) ✅

---

# Development Workflow

Every implementation task should follow this workflow:

```
Plan

↓

Implement

↓

Review

↓

Test

↓

Update Documentation

↓

Commit
```

---

# Current Status

Current Milestone:

**Milestone 3 — Frontend Foundation**

Current Objective:

Expose the backend through a desktop interface with React + Tauri.

Completed:

- CogneeService ✅
- IndexingService ✅
- ContextService ✅
- Backend structure ✅
- Cognee integration verified ✅
- End-to-end pipeline tested ✅
- API layer (commands + schemas) ✅
- API test suite ✅
