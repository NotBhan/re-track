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
6. **Token Budget Enforcement**: Context Packages enforce hard prompt token limits using line-boundary compression.

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

