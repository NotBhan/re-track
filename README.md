# RE:Track — AI Context Hub

<div align="center">

**Local-first AI memory & context engine for software repositories.**  
*Deterministic AST call graphs, multi-layer semantic memory, and token-budgeted Context Packages for any AI coding agent.*

[![TypeScript](https://img.shields.io/badge/Frontend-React%20%7C%20Vite%20%7C%20Tauri-blue?style=flat-square)](https://tauri.app/)
[![Python](https://img.shields.io/badge/Backend-Python%203.12%20%7C%20Cognee-green?style=flat-square)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/Tests-294%20passed-brightgreen?style=flat-square)](https://pytest.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-orange?style=flat-square)](LICENSE)

</div>

---

## Overview

**RE:Track** eliminates repository-scale context window exhaustion for modern AI coding agents (Claude Code, Cursor, Aider, Windsurf, Copilot, LM Studio, Ollama).

Instead of dumping raw multi-thousand-token files into an LLM prompt, RE:Track creates compact, authoritative **Context Packages**:

1. **Deterministic AST Call Graph**: Statically resolves call hierarchies, class inheritance, import aliases, and React/JSX rendering paths using a strict 2-pass AST walker.
2. **Multi-Layer Memory Model**: Separates raw ingested source files, LanceDB vector semantic embeddings, and Kùzu knowledge graph entities into independent, verifiable storage tiers.
3. **Intent-Guided Retrieval**: Combines task intent parsing, symbol extraction, and Cognee hybrid memory recall into a 2-stage progressive synthesis pipeline.
4. **Token Budget Enforcement**: Employs line-boundary compression and priority-tier trimming to reduce codebase prompt footprints by **85–95%**.
5. **Truth Boundary Guarantee**: Zero synthetic data, zero inferred graph edges, and zero demo metric fallbacks. The UI reflects exact backend reality across 5 explicit graph states.

---

## Core Capabilities

| Capability | Specification |
|---|---|
| **Deterministic AST Topology** | 2-pass symbol table & import alias resolution (`ast.Call`, `ast.ClassDef`, TS/JSX). Guarantees `edge.source/target ∈ node.ids`. |
| **Interactive Graph Explorer** | Spring-force SVG layout with connected path highlighting, zoom/pan controls, and Symbol Inspector drawer. |
| **5 Explicit Graph States** | `not_analyzed`, `analyzing`, `analyzed` (>0 edges), `zero_edges` (isolated symbols), and `failed`. |
| **Multi-Tier Memory Topology** | Independent layers for Ingested Source Files, LanceDB Vector Embeddings (`Active`), and Knowledge Graph Entities. |
| **Context Studio** | Split Prompt Workbench with preset suggestions, live token counter, discrete latency decomposition, and evidence provenance. |
| **Reproducible Benchmarks** | Evaluates prompt savings against exact codebase token baselines with immutable execution metadata (Git SHA, device, cache state). |
| **Hardware & RAM Telemetry** | Differentiates detected GPU presence (AMD/NVIDIA) from active execution device (`CPU`/`GPU`) with high-pressure memory alerts. |
| **Local-First & Offline** | 100% local execution via Tauri IPC, local Ollama/LM Studio LLMs, and local LanceDB/SQLite databases. |

---

## System Architecture

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                      RE:Track Desktop UI (React + Tauri)                │
│                                                                         │
│  Context Studio                                                         │
│    ├─ Prompt Workbench        → suggested prompts, live token limits    │
│    ├─ Evidence Provenance     → extracted symbols, callers, callees     │
│    └─ Markdown Reveal         → token-budgeted Context Package artifact │
│                                                                         │
│  Knowledge Explorer                                                     │
│    ├─ AST Call Graph View     → force-directed SVG + Symbol Inspector   │
│    ├─ Directory & Module Map  → framework-aware file hierarchy          │
│    └─ Key Components          → detected classes, services, entrypoints │
│                                                                         │
│  Memory Layers · Reproducible Benchmarks · Settings                     │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │  Tauri IPC (local commands)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      Python Backend (3.12 + FastAPI)                    │
│                                                                         │
│  IndexingService               ← .gitignore-aware delta file discovery  │
│  RepositorySummaryGenerator                                             │
│    ├─ _build_repo_map          ← framework layout grouping              │
│    ├─ _extract_components      ← Python AST + React regex export scan   │
│    └─ _build_call_graph        ← 2-pass deterministic AST resolver     │
│  IntentParserService           ← task intent + symbol extraction        │
│  ContextService                ← hybrid vector + graph memory retrieval │
│  PackageBuilder                ← dedup → rank → compress → render       │
│  BudgetManager                 ← token budget enforcement at boundaries │
│  BenchmarkEngine               ← baseline tokenization & timing breakdown│
│  CogneeService                 ← Cognee memory lifecycle wrapper        │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                 LanceDB (Vector) · Kùzu (Graph) · SQLite (Relational)
```

---

## AST Call Graph Resolution Invariants

RE:Track adheres to a strict static-certainty principle: **Truthful Data > Connected Graph Completeness**.

1. **Resolution Pipeline**:
   $$\text{AST Parse} \longrightarrow \text{Module Symbol Table} \longrightarrow \text{Import/Alias Table} \longrightarrow \text{Qualified Name Resolution} \longrightarrow \text{Internal Symbol Check} \longrightarrow \text{CallEdge}$$
2. **Backend Invariant**:
   Every edge strictly satisfies:
   $$\forall e \in \text{Edges},\quad e.\text{source} \in \text{Nodes} \;\land\; e.\text{target} \in \text{Nodes}$$
3. **Ambiguity Handling**: Parameter shadows, variable overrides, dynamic callables, and unresolved cross-module symbols produce **0 internal edges** rather than speculative guesses.
4. **TypeScript & React**: Resolves path aliases (`@/*`, `~/*`), relative imports, and `<Component />` JSX rendering edges.

---

## Getting Started

### Prerequisites

- **Node.js** `v20+` & `npm`
- **Python** `3.11+` (managed via `uv` or `venv`)
- **Rust** & `cargo` (for Tauri desktop runtime)
- **Ollama** or **LM Studio** (local LLM backend, e.g., `phi-4-mini-reasoning`, `qwen2.5-coder`)

### Quick Setup

```bash
# 1. Clone the repository
git clone https://github.com/NotBhan/re-track.git
cd re-track

# 2. Setup Python backend environment
cd backend
uv venv .venv --python 3.12
source .venv/bin/activate
pip install -r requirements.txt
cd ..

# 3. Install frontend dependencies
npm install

# 4. Launch in Tauri desktop development mode
npm run tauri dev
```

---

## Agent Context API

External AI coding tools, autonomous agents, and MCP servers can request token-optimized Context Packages via HTTP:

### Request

```bash
POST http://localhost:8000/api/v1/context
Content-Type: application/json

{
  "task_prompt": "Explain how the BudgetManager enforces token limits across sections",
  "repository_path": "/home/user/projects/my-repo",
  "max_tokens": 8000,
  "include_structural_graph": true
}
```

### Response Schema

```json
{
  "success": true,
  "task_summary": "Explain how the BudgetManager enforces token limits across sections",
  "intent_category": "Architecture Inquiry",
  "extracted_symbols": ["BudgetManager", "compress_section", "enforce_budget"],
  "callers": ["PackageBuilder.build_package"],
  "callees": ["BudgetManager._compress_at_boundary"],
  "related_files": [
    "backend/app/services/budget_manager.py",
    "backend/app/services/package_builder.py"
  ],
  "estimated_tokens": 1280,
  "generation_time_ms": 142,
  "retrieval_time_ms": 56,
  "ranking_time_ms": 18,
  "synthesis_time_ms": 68,
  "total_time_ms": 142,
  "context_markdown": "# Task Context: BudgetManager Token Enforcement\n\n..."
}
```

---

## Benchmark & Telemetry Methodology

RE:Track calculates compression and token efficiency deterministically against the target repository:

- **Baseline Tokens**: Sum of tokens from all eligible source code files (`.py`, `.ts`, `.tsx`, `.js`, `.go`, `.rs`, `.md`), excluding `.git`, `node_modules`, `dist`, `.venv`, and build artifacts, tokenized with the exact same tokenizer (`character-4b-heuristic`).
- **Formulas**:
  $$\text{Compression Ratio} = \frac{\text{Baseline Tokens}}{\text{Context Package Tokens}}$$
  $$\text{Token Savings \%} = \frac{\text{Baseline Tokens} - \text{Context Package Tokens}}{\text{Baseline Tokens}} \times 100$$
- **Immutable Run Metadata**: Each benchmark run records Git Commit SHA, tokenizer name, cache state (`warm`/`cold`), active LLM model, detected GPU, and execution device (`CPU`/`GPU`).

---

## Verification & Test Suite

```bash
# Run all backend unit tests (294 tests)
cd backend
source .venv/bin/activate
pytest tests/ -q

# Run deterministic AST integrity tests
pytest tests/test_ast_integrity.py -v

# Frontend TypeScript check & production build
cd ..
npm run build
```

---

## License

Apache 2.0. See [LICENSE](LICENSE) for details.
