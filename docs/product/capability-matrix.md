# RE:Track Product Capability Matrix

**Document Type**: Authoritative Product Capability Contract  
**Version**: 1.0 (Phase 9A Release Baseline)  
**Maturity Scope**: Local Workstation Developer & AI Agent Workloads  

---

## 1. Executive Capability Summary

RE:Track provides a local-first code intelligence and context synthesis platform. This matrix outlines the exact capabilities available to human developers and external AI coding agents, distinguishing between production-grade features, capabilities with operational constraints, internal mechanisms, and planned/deferred roadmap items.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        RE:TRACK CAPABILITY MATRIX                      │
├────────────────────────────────┬───────────────────────────────────────┤
│ EXTERNAL AI AGENTS (MCP STDIO) │ HUMAN DEVELOPERS (DESKTOP UI & CLI)   │
│ • Token-Budgeted Context       │ • Interactive Context Studio          │
│ • Deterministic AST Call Graph │ • Force-Directed Knowledge Explorer   │
│ • Architectural Summary        │ • Repository Scan & Management        │
│ • Ranked Code Search           │ • Kùzu Graph & LanceDB Vector Viewer  │
│ • Repository Discovery         │ • Precision/Recall Benchmark Runner   │
│ • Workspace Sandboxing         │ • Typer CLI Headless Automation       │
└────────────────────────────────┴───────────────────────────────────────┘
```

---

## 2. Capability Matrix by Functional Domain

| Domain | Capability | Maturity State | Target Persona | Latency & Performance Profile | Provider Dependency |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **MCP Integration** | FastMCP Stdio Transport | **Production** | AI Coding Agents (Claude, Cursor) | Sub-1ms frame processing | None (Native Stdio) |
| **MCP Integration** | Architectural Summary (`get_repository_summary`) | **Production** | AI Coding Agents | **Cold**: ~30-50ms<br>**Warm/Cached**: < 2ms | None (Deterministic AST) |
| **MCP Integration** | Deterministic AST Call Graph (`get_ast_call_graph`) | **Production** | AI Coding Agents | **Cold**: ~50-100ms<br>**Warm/Cached**: < 5ms | None (Native AST) |
| **MCP Integration** | Ranked Code Search (`search_repository_code`) | **Production** | AI Coding Agents | **Cold**: ~10-25ms<br>**Warm**: < 3ms | None (Local Lexical Search) |
| **MCP Integration** | Registered Repo List (`list_indexed_repositories`) | **Production** | AI Coding Agents | **Cold/Warm**: < 1ms | None (Local JSON Store) |
| **Context Synthesis** | Agent Context Synthesis (`get_agent_context`) | **Production** | AI Coding Agents | **Cold**: ~80-150ms<br>**Warm/Hit**: < 2ms | Local LLM for semantic recall; offline fallback enabled |
| **Context Synthesis** | Interactive Context Studio | **Production** | Human Developers | Real-time UI updates (60fps) | None for AST; LLM for semantic chunks |
| **Context Synthesis** | Token Budgeting (100–32,000 tokens) | **Production** | Human Developers & Agents | Sub-1ms budget pruning | None |
| **Code Intelligence** | Python AST Call Graph Extraction | **Production** | Internal Engine | Full-fidelity native AST (`ast` module) | None |
| **Code Intelligence** | TypeScript / JS / JSX Call Graph Extraction | **Production with Limitations** | Internal Engine | Heuristic regex/AST extraction | None |
| **Code Intelligence** | Force-Directed Graph Explorer | **Production** | Human Developers | Smooth 60fps spring-physics layout | None (SVG Canvas) |
| **Memory & Graph** | LanceDB Vector Indexing | **Production with Limitations** | Internal Engine | Sub-50ms vector query | **Required** (Ollama / LM Studio for embeddings) |
| **Memory & Graph** | Kùzu Graph Triples Indexing | **Production with Limitations** | Internal Engine | Sub-20ms graph traversal | **Required** (Ollama / LM Studio for entity extraction) |
| **Memory & Graph** | Memory Topology & Triple Inspector | **Production** | Human Developers | Direct read from Kùzu/LanceDB | None (Read-only truth boundary) |
| **Benchmarking** | Golden Task Evaluator (20 Tasks) | **Production** | Developers & CI | ~1-3s complete suite execution | None (Deterministic evaluator) |
| **Benchmarking** | Precision@K, Recall@K Scorecard | **Production** | Human Developers | Real-time scorecard rendering | None |
| **Administration** | Headless CLI Tooling (`retrack`) | **Production** | Developers & Scripts | Instant startup (< 200ms) | Provider-dependent for `index` |
| **Administration** | Provider Hot-Reloading | **Production** | Human Developers | Instant runtime switch (< 5ms) | Connects to active Ollama / LM Studio |

---

## 3. Detailed Performance Truth & Latency Characterization

To prevent misleading claims, RE:Track latency characteristics are categorized into discrete execution profiles:

### 1. Deterministic In-Process Tools (`get_repository_summary`, `get_ast_call_graph`, `search_repository_code`, `list_indexed_repositories`):
- **Cold Execution** (first scan after startup): 10ms – 100ms depending on repository size (up to 500 files).
- **Warm / Cached Execution** (fingerprint hit): 0.5ms – 3.0ms.
- **Provider Status Impact**: Zero impact. Latency remains identical even if Ollama/LM Studio is completely offline.

### 2. Context Synthesis Tool (`get_agent_context`):
- **Cache Hit**: 0.7ms – 1.5ms.
- **Cold Synthesis (with local AST fallback / LLM offline)**: 80ms – 180ms.
- **Cold Synthesis (with live Cognee Semantic Recall)**: 150ms – 450ms (dominated by local vector similarity and Ollama socket round-trip).

### 3. Server Startup & Initialization:
- **MCP Server Stdio Process Launch**: 2.5s – 6.0s (dominated by Python module imports, PyTorch/Cognee initialization, and local database connection pooling).

---

## 4. Final Maturity Matrix

| Category | Production | Production with Limitations | Internal-Only | Planned (Roadmap) | Deferred / Excluded |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **MCP / Agent Transport** | Stdio FastMCP Server, 5 Standard Tools | — | — | — | Network HTTP/SSE Transport |
| **Context Synthesis** | Token Budgeting, Section Selection, Context Studio | Local Summary Fallback when Cognee empty | Bounded Concurrency Guard (`max_concurrent=1`) | Dynamic Multi-Repo Context Union | Cloud-Hosted Multi-Tenant Synthesis |
| **Code Intelligence** | Python Native AST Symbol & Call Resolution | TypeScript/JS/JSX Heuristic AST Extraction | Context Cache Invalidation Engine | Tree-sitter Native WASM Bindings | Dynamic Runtime Execution Tracing |
| **Repository Management** | Local Repository Registration, File Scanning | — | Workspace Authorization Sandboxing | Git Diff-Aware Incremental Re-indexing | Remote Git Ingestion (`git clone` API) |
| **Memory & Storage** | Dataset Deletion (`forget`), Metadata Store | Cognee 1.5.0 Semantic Vector/Graph Ingestion | Dual-Path Storage (`.retrack` canonical, `.andes` fallback) | Chunk-Level Hash Change Detection | Distributed Database Clustering |
| **Reliability & Ops** | Subprocess Provider Reconnection, Signal Teardown | — | Stderr-Only Logging Separation | Automated Daemon Watchdog | Distributed Celery/Redis Task Queue |
| **Benchmarking** | 20-Task Golden Suite, Precision/Recall Evaluator | — | Token Baseline Scanner | Automated CI GitHub Action Benchmark Gate | — |
| **CLI & Desktop UX** | Typer CLI (`retrack`), React 19 Desktop Dashboard | — | Hardware Telemetry Port | Native Desktop System Tray Widget | Light/Dark Theme Customizer |

---

## 5. Explicit Limitations & Non-Goals

1. **Local-First Workstation Scope**: RE:Track is intentionally engineered for local single-developer workstations. It does not provide remote multi-user cloud hosting or SaaS authentication.
2. **Sequential Context Synthesis**: Concurrent requests are queued FIFO and executed sequentially (`max_concurrent=1`) to guarantee safety on 8GB RAM host environments.
3. **AST Depth Across Languages**: Python AST extraction uses full native syntax tree parsing; non-Python languages use robust regex/heuristic extraction.
4. **Provider-Dependent Semantic Features**: Semantic vector search requires a running local LLM. If the provider is offline, the deterministic engine functions without interruption, but semantic triples are bypassed.
