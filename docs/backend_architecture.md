# RE:Track Backend Architecture (Hexagonal / Ports & Adapters)

## Overview

The RE:Track backend is a Python 3.12 service layer structured as a Hexagonal (Ports and Adapters) system. It supports multiple inbound driving interfaces: Tauri desktop IPC, FastAPI modular REST routers, headless CLI, and Model Context Protocol (MCP) over stdio.

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                INBOUND / DRIVING ADAPTERS                              │
├──────────────────────────────┬──────────────────────────────┬──────────────────────────┤
│    FastAPI Modular Routers   │         Headless CLI         │   MCP Server (stdio)     │
│   (Desktop UI / Tauri IPC)   │      (Terminal / CI/CD)      │ (External Coding Agents) │
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
└──────────────┬──────────────┬──────────────┬──────────────┬───────────────┬────────────┘
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

## Service Contracts & Invariants

### 1. AST Call Graph Resolver
- **Static Invariant**: Every `CallEdge.source` and `CallEdge.target` must exist in `node_ids`.
- **Ambiguity Policy**: Unresolved cross-module calls or shadowed variables generate zero internal edges.
- **5 Graph States**: `not_analyzed`, `analyzing`, `analyzed` (>0 edges), `zero_edges`, `failed`.

### 2. Multi-Layer Memory Storage
- **Ingested Source Files Layer**: Real file counts and dataset summaries.
- **Vector / Semantic Index Layer**: LanceDB embedding index status (`Ready / Active`).
- **Knowledge Graph Entities Layer**: Explicit `knowledge_graph_status` (`not_extracted`, `extracting`, `extracted`, `failed`).
- **Dataset Identity Isolation**: Deterministic dataset names (`{sanitized_name}_{path_sha256_10hex}`) prevent cross-repository memory collision.

### 3. Latency Decomposition & Budgeting
Context generation instruments discrete execution timings:
- `retrieval_time_ms`: Memory query from vector/graph stores
- `ranking_time_ms`: Pipeline multi-factor scoring
- `synthesis_time_ms`: Markdown rendering and budget enforcement
- `total_time_ms`: End-to-end execution latency

---

## Modular REST Routers (`backend/app/api/routers/`)

- **System Router (`system.py`)**: `GET /health`, `GET /status`, `GET /dashboard/stats`, `POST /provider/update`
- **Repositories Router (`repositories.py`)**: `GET /repos`, `POST /repos`, `POST /repos/{repo_id}/scan`, `GET /repos/{repo_id}/progress`, `DELETE /repos/{repo_id}`, `GET /repos/{repo_id}/prompts`, `GET /repositories`
- **Context Router (`context.py`)**: `POST /index`, `POST /context`, `POST /api/v1/context`
- **Memory Router (`memory.py`)**: `GET /datasets`, `GET /datasets/{dataset_id}/items`, `POST /forget`, `GET /memory/stats`, `GET /memory/graph`, `GET /memory/vectors`, `POST /memory/cognify`
- **Packages Router (`packages.py`)**: `GET /packages`, `POST /packages`, `GET /packages/{package_id}`, `DELETE /packages/{package_id}`, `POST /packages/{package_id}/append`
- **Benchmarks Router (`benchmarks.py`)**: `POST /benchmarks/run`
- **Settings Router (`settings.py`)**: `GET /settings`, `POST /settings`, `POST /settings/cognee`

---

## MCP Server Interface (`backend/app/mcp/`)

Exposes 5 standardized tools over stdio transport:
- `get_agent_context`: Token-budgeted context package with AST call graph and symbol definitions.
- `get_repository_summary`: Tech stack, architectural layers, key components, and entry points.
- `get_ast_call_graph`: Deterministic AST caller/callee directed graph with path filtering.
- `search_repository_code`: High-speed symbol and keyword search across repository source files.
- `list_indexed_repositories`: Lists registered repositories with metadata and indexing status.

**Operational Hardening**:
- Process-scoped shared `BoundedConcurrencyGuard` (`max_concurrent=1`, `max_queue=5`, `timeout=30.0s`).
- Logging writes strictly to `sys.stderr`, preserving `sys.stdout` exclusively for clean JSON-RPC frames.
- Prompt stdio EOF, SIGINT, and SIGTERM termination (< 0.15s).
- Deterministic tools operate independently of LLM provider availability; context synthesis automatically recovers in the same running process when the provider is restored.