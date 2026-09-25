# RE:Track Architecture

## Overview

RE:Track (RefinedEngine Track) is a local-first desktop application that provides persistent memory and deterministic context synthesis for AI-assisted software development.

The system separates user interaction, business logic, deterministic code topology analysis, memory orchestration, and persistent storage into independent layers.

Rather than directly exposing memory backends to the frontend, all interactions occur through backend services responsible for indexing repositories, extracting AST relationships, managing sessions, retrieving memory, and generating token-budgeted Context Packages.

---

# # High-Level Architecture (Hexagonal / Ports & Adapters)

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                INBOUND / DRIVING ADAPTERS                              │
├──────────────────────────────┬──────────────────────────────┬──────────────────────────┤
│      Desktop UI (Tauri)      │         Headless CLI         │   MCP Server (stdio)     │
│    React + Vite + Tailwind   │      Typer / Argparse        │  FastMCP 5 Tools Surface │
└──────────────┬───────────────┴──────────────┬───────────────┴─────────────┬────────────┘
               │                              │                             │
               ▼                              ▼                             ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        COMPOSITION ROOT (ApplicationContainer)                         │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                 APPLICATION USE CASES                                  │
│                                                                                        │
│  • ContextUseCases           ✅ Retrieval, ranking, synthesis & BoundedConcurrencyGuard│
│  • IndexingUseCases          ✅ Discovery, filtering, manifest fingerprinting, cognify │
│  • RepositoryUseCases        ✅ Catalog CRUD, summary generation, AST call graph       │
│  • MemoryUseCases            ✅ Dataset isolation, multi-tier inspection, forget       │
│  • PackageUseCases           ✅ Versioned context package storage, export, comparison  │
│  • SystemUseCases            ✅ Provider reachability & hardware telemetry              │
└──────────────┬──────────────────────────────┬─────────────────────────────┬────────────┘
               │                              │                             │
               ▼                              ▼                             ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                             OUTBOUND PORTS (Domain Interfaces)                         │
├──────────────────────────────┬──────────────────────────────┬──────────────────────────┤
│    MemoryPort / Cognee       │  SourceSearch / AST Engine   │  WorkspaceAuthorization  │
│  MetadataStore / Filesystem  │  ContextPackageRepository    │    HardwareTelemetry     │
└──────────────┬───────────────┴──────────────┬───────────────┴─────────────┬────────────┘
               │                              │                             │
               ▼                              ▼                             ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                           DRIVEN / INFRASTRUCTURE ADAPTERS                             │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  • CogneeMemoryAdapter       → LanceDB (Vectors) + Kùzu (Knowledge Graph) + SQLite     │
│  • RepositorySummaryGenerator→ 2-Pass Deterministic AST Call Graph Resolver            │
│  • SourceSearchService       → In-process regex/token source search & symbol matching  │
│  • WorkspaceAuthorizationSvc → Path containment & symlink escape defense-in-depth      │
│  • LocalFilesystemAdapter    → Canonical ~/.retrack/ & legacy metadata stores          │
│  • HardwareTelemetryAdapter  → GPU detection (NVIDIA/ROCm/Apple) & RAM pressure meter  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

# Architectural Principles

The architecture follows six primary principles:

1. **Truth Boundary Authority**: The backend is the sole authority for repository analysis, graph identity, memory statistics, benchmark measurements, and hardware telemetry. The frontend and MCP clients never synthesize fallback data or mask unknown states.
2. **Hexagonal Driving Boundary**: Use cases are completely isolated from HTTP, CLI, and MCP transport concerns. Swapping or adding an inbound interface requires zero domain changes.
3. **Defense-in-Depth Trust Boundary**: External MCP clients are restricted to registered repositories or configured workspace roots (`RETRACK_WORKSPACE_ROOTS`). System files and escaping symlinks are rejected.
4. **Deterministic Static Certainty**: AST and call graph analysis prioritize static certainty over graph completeness. Ambiguous symbols produce no internal edge.
5. **Collision-Proof Dataset Identity**: Context memory is partitioned via `{sanitized_name}_{path_sha256_10hex}` to physically prevent cross-repository memory pollution.
6. **Explicit Context Budgeting**: A requested context budget is split into task prompt, fixed prompt overhead, generation reservation and an evidence allowance, then filled by deterministic, evidence-aware packing that follows the truth hierarchy. Oversized evidence is progressively reduced with its provenance intact — never tail-truncated, and never dropped silently. See `docs/architecture/context-compaction.md`.

---

# Layer Responsibilities

## 1. Inbound Driving Adapters

- **FastAPI Modular Routers (`backend/app/api/routers/`)**: Exposes REST endpoints for the desktop Tauri interface across 7 domain modules.
- **Headless CLI (`backend/app/cli/`)**: Standalone terminal interface for indexing, searching, and generating context packages.
- **MCP Stdio Server (`backend/app/mcp/`)**: FastMCP stdio interface exposing 5 standardized tools with strict stderr logging and clean EOF/signal shutdown semantics.

## 2. Application Layer & Use Cases

- **ContextUseCases**: Coordinates memory retrieval, AST topology injection, line-boundary compression, and markdown rendering under a shared `BoundedConcurrencyGuard` (`max_concurrent=1`, `max_queue=5`, `timeout=30.0s`).
- **IndexingUseCases**: Traverses repository files, enforces `.gitignore`/`.agentignore`, creates SHA256 file fingerprints, and coordinates Cognee ingestion.
- **RepositoryUseCases**: Manages repository registrations, status lifecycles, and triggers 2-pass deterministic AST summary generation.
- **WorkspaceAuthorizationService**: Validates repository paths against registered roots and configured `RETRACK_WORKSPACE_ROOTS`, pruning symlink escapes.

## 3. Driven Infrastructure Adapters

- **RepositorySummaryGenerator**: Multi-language 2-pass AST call graph resolver (Python ClassDef/FunctionDef/Call, TypeScript/React JSX renders) with absolute graph integrity (`CallEdge.source/target` exist in `node_ids`).
- **CogneeMemoryAdapter**: Bridges `MemoryPort` to Cognee memory lifecycle (`remember`, `recall`, `improve`, `forget`), LanceDB, and Kùzu.
- **ContextPackageRepository**: Manages persistent JSON stores for synthesized context packages.

---

# Frontend Interface Topology

All inbound interface implementations live under `frontend/` and are separate adapters over the same backend contract. No interface owns domain logic, and interfaces never depend on each other.

```text
frontend/
├── gui/       Tauri + React desktop application (Vite root; bundle → dist/)
│   ├── index.html
│   ├── public/
│   └── src/   → renders via Tauri IPC (@tauri-apps/api) and src/lib/api.ts
├── cli/       Command-line interface (plain Node ESM, zero dependencies)
├── tui/       Terminal user interface (plain Node ESM, ANSI presentation)
└── shared/    Interface-agnostic backend contract client (used by cli + tui)
```

Dependency rules:

- `gui/` → Tauri IPC → backend. It imports neither `cli/`, `tui/`, nor `shared/`.
- `cli/` and `tui/` → `shared/backend-client.mjs` → backend HTTP contract.
- `tui/` never imports React/Tauri; `cli/` never imports GUI/TUI presentation.
- Repository indexing, AST extraction, retrieval, ranking, and memory statistics are never re-implemented in `frontend/`.

Retrieval-mode contract (derived memory):

- Every retrieval tier is **vector/chunk retrieval**. `CogneeService.recall` always passes an
  explicit `SearchType` (`CHUNKS`) with `auto_route=False`, so Cognee's rule-based query
  router can never substitute an LLM-backed strategy such as `GRAPH_COMPLETION_COT` for a
  retrieval operation.
- The **embedding provider identity is configured and reported independently** of the LLM
  provider (`embedding_provider` / `embedding_endpoint` in settings; surfaced as
  `embedding_provider|endpoint|model|state|detail` on `/health` and `/status`). States are
  `available`, `model_missing`, `unreachable`, `not_configured`; no substitution or silent
  alignment of the two identities occurs.
- When the embedding provider cannot serve the configured model, the retrieval tier reports
  a degraded state (`retrieval_state="unavailable"` with a reason) instead of an apparently
  successful empty result. Authoritative Tiers 1–2 and evidence gating are unaffected.

Lifecycle contract:

- The backend composition root (`ApplicationContainer`) exposes `initialize()` / `shutdown()` symmetry. `shutdown()` releases memory-engine handles (LanceDB vector engine, Kùzu graph engine) and is invoked from both the FastAPI lifespan and the MCP stdio shutdown path.
- Terminal interfaces restore the terminal (cursor, alternate screen, raw mode) on every exit path, including Ctrl+C, EOF, and uncaught errors.

---

# Verification & Test Coverage

The system is validated through 415 automated unit, integration, security, and benchmark tests:

```bash
# Full test suite (415 passed)
cd backend && uv run pytest tests/ -q

# MCP and Security regression suite
cd backend && uv run pytest tests/test_workspace_authorization.py tests/test_dataset_identity_isolation.py tests/test_mcp_concurrency_lifecycle.py tests/test_mcp_stdio_shutdown.py tests/test_mcp_logging_integrity.py tests/test_mcp_provider_recovery.py tests/test_mcp_adapter.py -v

# AST deterministic resolution tests
cd backend && uv run pytest tests/test_ast_integrity.py -v

# Golden benchmark evaluation
cd backend && uv run pytest tests/evaluation/ -v

# Frontend typecheck & build
npm run build
```

