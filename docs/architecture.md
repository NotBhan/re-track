# RE:Track Architecture

## Overview

RE:Track (RefinedEngine Track) is a local-first desktop application that provides persistent memory and deterministic context synthesis for AI-assisted software development.

The system separates user interaction, business logic, deterministic code topology analysis, memory orchestration, and persistent storage into independent layers.

Rather than directly exposing memory backends to the frontend, all interactions occur through backend services responsible for indexing repositories, extracting AST relationships, managing sessions, retrieving memory, and generating token-budgeted Context Packages.

---

# High-Level Architecture

```text
┌───────────────────────────────────────────────────────────────┐
│                      RE:Track Desktop UI                      │
├───────────────────────────────────────────────────────────────┤
│                     React + Vite + Tauri                      │
│                                                               │
│  • Context Studio (Prompt Workbench, Provenance, Package)     │
│  • Knowledge Explorer (5-State AST Topology & Call Graph)     │
│  • Repositories (Catalog & Indexing Telemetry)                │
│  • Memory (Multi-Tier Storage Inspector)                      │
│  • Benchmarks (Deterministic Baseline Evaluation)             │
│  • Settings (Provider Configuration & Telemetry)              │
└──────────────────────────────┬────────────────────────────────┘
                               │
                           Tauri IPC
                               │
                               ▼
┌───────────────────────────────────────────────────────────────┐
│                      Python Backend (3.12)                    │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  IndexingService           ✅ .gitignore-aware file discovery  │
│  ManifestService           ✅ SHA256 file fingerprinting       │
│  RepositorySummaryGenerator✅ 2-pass deterministic AST resolver│
│  IntentParserService       ✅ Task intent & symbol extractor   │
│  CogneeService             ✅ Cognee memory lifecycle wrapper  │
│  ContextService            ✅ Discrete latency instrumentation │
│  PackageBuilder            ✅ Dedup → Rank → Compress → Render │
│  BudgetManager             ✅ Line-boundary token compression  │
│  BenchmarkEngine           ✅ Source baseline token evaluator  │
│  LLMProviderService        ✅ Multi-provider health manager    │
│                                                               │
└──────────────────────────────┬────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────┐
│                         Storage Layer                         │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  • Ingested Source Files   → Local Filesystem & Manifest      │
│  • Vector Semantic Index   → LanceDB (Embeddings)             │
│  • Knowledge Graph Store   → Kùzu (Entities & Relationships)  │
│  • Relational Metadata     → SQLite                           │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

---

# Architectural Principles

The architecture follows five primary principles:

1. **Truth Boundary Authority**: The backend is the sole authority for repository analysis, graph identity, memory statistics, benchmark measurements, and hardware telemetry. The frontend never synthesizes fallback data or masks unknown states with fake zeroes.
2. **Deterministic Static Certainty**: AST and call graph analysis prioritize static certainty over graph completeness. Unresolved or dynamic symbols produce no internal edge.
3. **Local-First Execution**: All indexing, AST parsing, vector storage, and inference run locally on the developer's machine without external data transmission.
4. **Explicit Memory Layering**: Ingested raw files, vector embeddings, and knowledge graph entities are separated into independent, inspectable storage tiers.
5. **Token Budget Enforcement**: Context Packages enforce hard prompt token limits using line-boundary compression.

---

# Layer Responsibilities

## Frontend

Responsible for:
- User interaction and prompt authoring
- 5-state AST call graph rendering with force-directed physics
- Connected path highlighting and Symbol Inspector drawer
- Progressive markdown rendering for generated Context Packages
- Multi-tier memory inspection and deterministic benchmark triggers
- Hardware telemetry presentation (GPU presence vs active device, RAM pressure)

The frontend never communicates with Cognee or SQLite directly.

---

## Backend Services

### 1. RepositorySummaryGenerator (`backend/app/services/repository_summary.py`)
- Traverses codebase files respecting `.gitignore` patterns dynamically.
- Implements a 2-pass deterministic AST resolver:
  - Pass 1: Registers module symbol tables, class definitions, function signatures, exported components, and import alias tables (`import X as Y`, `from A import B as C`, `@/` and `~/` path aliases).
  - Pass 2: Resolves qualified names and function calls (`ast.Call`), class inheritance (`ast.ClassDef.bases`), and JSX renders (`<Component />`).
- **Graph Integrity Invariant**: Every `CallEdge.source` and `CallEdge.target` strictly resolves to an existing `CallNode.id`. Ambiguous symbols produce zero edges.
- Emits 5 explicit states: `"not_analyzed"`, `"analyzing"`, `"analyzed"`, `"zero_edges"`, `"failed"`.

### 2. CogneeService (`backend/app/services/cognee_service.py`)
- Encapsulates Cognee memory lifecycle: `remember()`, `recall()`, `improve()`, `forget()`.
- Configures internal provider settings for LanceDB, Kùzu, and SQLite.

### 3. ContextService & PackageBuilder (`backend/app/services/context_service.py`, `package_builder.py`)
- Coordinates retrieval from vector and graph stores.
- Instruments discrete latency timings: `retrieval_time_ms`, `ranking_time_ms`, `synthesis_time_ms`, `total_time_ms`.
- Pipeline stages:
  - **Deduplicator**: removes duplicate memories via normalized text comparison.
  - **Ranker**: scores entries by semantic relevance, confidence, and type weights.
  - **Compressor**: compresses redundant facts while preserving actionable code entities.
  - **Categorizer**: groups facts into structured Markdown sections.
  - **ReferenceResolver**: generates traceable source citations.

### 4. BudgetManager (`backend/app/services/budget_manager.py`)
- Enforces user-configured token budgets (e.g. 4,000 or 8,000 tokens).
- Trims low-priority sections and compresses high-priority sections cleanly at line boundaries.

### 5. BenchmarkEngine (`backend/app/api/benchmarks.py`)
- Calculates deterministic baseline tokens across all eligible repository source files using the `character-4b-heuristic` tokenizer.
- Computes `compression_ratio` and `token_savings_percent`.
- Records immutable run metadata: repository path, Git commit SHA, eligible source file count, active model, execution device (`CPU`/`GPU`), and evaluation timestamp.

---

# Verification & Test Coverage

The system is validated through 294 automated unit tests:

```bash
# Full test suite
cd backend && pytest tests/ -q

# AST deterministic resolution tests
cd backend && pytest tests/test_ast_integrity.py -v

# Frontend typecheck & build
npm run build
```
