# RE:Track Backend Architecture

## Overview

The RE:Track backend is a Python 3.12 service layer communicating with the desktop application via Tauri IPC and external agents via REST.

```text
┌───────────────────────────────────────────────────────────────┐
│                      RE:Track Desktop UI                      │
├───────────────────────────────────────────────────────────────┤
│                     React + Vite + Tauri                      │
└──────────────────────────────┬────────────────────────────────┘
                               │
                           Tauri IPC
                               │
                               ▼
┌───────────────────────────────────────────────────────────────┐
│                      Python Backend (3.12)                    │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  IndexingService                                              │
│      • File Discovery & .gitignore Parsing                    │
│      • SHA256 Manifest Fingerprinting                         │
│                                                               │
│  RepositorySummaryGenerator                                   │
│      • Framework & Directory Mapping                          │
│      • 2-Pass Deterministic AST Call Graph Resolver           │
│                                                               │
│  IntentParserService                                          │
│      • Task Intent Classification & Symbol Extraction         │
│                                                               │
│  CogneeService                                                │
│      • remember() / recall() / improve() / forget()           │
│                                                               │
│  ContextService & PackageBuilder                              │
│      • Discrete Latency Breakdown                             │
│      • Dedup → Rank → Compress → Categorize → Render          │
│                                                               │
│  BudgetManager                                                │
│      • Line-Boundary Token Compression                        │
│                                                               │
│  BenchmarkEngine                                              │
│      • Exact Source Baseline Tokenization                     │
│      • Immutable Run Metadata & Hardware Telemetry            │
│                                                               │
└──────────────────────────────┬────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────┐
│                         Storage Layer                         │
├───────────────────────────────────────────────────────────────┤
│  • LanceDB (Vector Embeddings)                                │
│  • Kùzu (Knowledge Graph Entities & Relationships)            │
│  • SQLite (Relational Store & Metadata)                       │
└───────────────────────────────────────────────────────────────┘
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

### 3. Latency Decomposition
Context generation instruments discrete execution timings:
- `retrieval_time_ms`: Memory query from vector/graph stores
- `ranking_time_ms`: Pipeline multi-factor scoring
- `synthesis_time_ms`: Markdown rendering and budget enforcement
- `total_time_ms`: End-to-end execution latency

---

## API Endpoints

- `GET /health` — Hardware & memory telemetry (CPU, RAM %, detected GPU, execution device)
- `GET /status` — Backend system and model configuration
- `POST /index` — Trigger repository indexing
- `POST /context` — Synthesize Context Package for prompt
- `POST /api/v1/context` — Agent Context API
- `POST /forget` — Dataset deletion
- `POST /benchmarks` — Run deterministic benchmark evaluation