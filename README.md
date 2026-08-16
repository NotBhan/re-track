# RE:Track — AI Context Hub

<div align="center">

**Local-first AI memory & context engine for software repositories.**  
*Extracts AST call graphs, semantic memories, and directory structure into token-budgeted Context Packages for any coding agent.*

[![TypeScript](https://img.shields.io/badge/Frontend-React%20%7C%20Vite%20%7C%20Tauri-blue?style=flat-square)](https://tauri.app/)
[![Python](https://img.shields.io/badge/Backend-Python%203.12%20%7C%20Cognee-green?style=flat-square)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-Apache%202.0-orange?style=flat-square)](LICENSE)

</div>

---

## What it does

**RE:Track** solves repository-scale context limits for AI coding agents (Claude Code, Cursor, Aider, LM Studio, Ollama). Instead of dumping entire directory trees, RE:Track:

1. **Indexes** a repository, respecting `.gitignore` patterns dynamically.
2. **Extracts** a Depth-2.5 structural map: root folders → subfolders → AST-level symbol outlines.
3. **Builds** a real call graph by walking Python AST (`ast.Call`, `ast.ClassDef`) and React/TS import chains.
4. **Generates** deterministic, token-budgeted Markdown Context Packages on demand.
5. **Visualizes** the extracted call graph as an interactive force-directed SVG (drag, zoom, pan).

---

## Key Features

| Feature | Status |
|---------|--------|
| Depth-2.5 Repository Map (root → subfolder → AST symbols) | ✅ |
| Real call graph extraction (Python AST `ast.Call` + React/TS imports) | ✅ |
| Interactive force-directed graph (drag, zoom, pan, legend) | ✅ |
| `.gitignore`-aware file filtering | ✅ |
| React/Vite/Next/Vue/Svelte component detection | ✅ |
| Repository dropdown for fast switching | ✅ |
| Token-budgeted Context Package generation | ✅ |
| Multi-model support (Ollama, LM Studio, OpenAI-compatible) | ✅ |
| Live hardware telemetry (RAM, CPU, GPU VRAM) | ✅ |
| Vercel Geist aesthetic — monochrome dark, hairline borders | ✅ |
| 284+ backend unit tests | ✅ |

---

## Depth-2.5 Defined

| Depth | What is scanned |
|-------|----------------|
| Root (1.0) | Top-level directory layout + framework fingerprinting |
| Subfolders (2.0) | Per-folder responsibility mapping |
| AST overview (2.5) | Class names, function signatures, exported React components per file |
| Call graph | Full `ast.Call` traversal — implemented via `_build_call_graph` |

---

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                     Desktop UI (React + Tauri)                 │
│                                                                │
│  Dashboard                                                     │
│    ├─ Prompt Workbench   → synthesized Context Package         │
│    └─ Repository AST Map                                       │
│         ├─ Directory List  — filterable subfolder/symbol list  │
│         └─ Call Graph      — interactive force-directed SVG    │
│                                                                │
│  Memory · Benchmarks · Settings                                │
└───────────────────────────┬────────────────────────────────────┘
                            │  Tauri IPC (local, no network)
┌───────────────────────────▼────────────────────────────────────┐
│                      Python Backend                            │
│                                                                │
│  IndexingService          ← .gitignore-aware file discovery    │
│  RepositorySummaryGenerator                                    │
│    ├─ _build_repo_map     ← directory structure grouping       │
│    ├─ _extract_components ← Python AST + React regex           │
│    └─ _build_call_graph   ← ast.Call traversal + TS imports    │
│  ContextService           ← semantic memory retrieval          │
│  PackageBuilder           ← dedup → rank → compress → render   │
│  BudgetManager            ← token budget enforcement           │
│  CogneeService            ← Cognee vector + graph memory       │
│                                                                │
└───────────────────────────┬────────────────────────────────────┘
                            │
               LanceDB · KuzuDB · SQLite
```

---

## Call Graph Extraction

Extracted during indexing and persisted in the repo metadata store.

**Python** (`backend/app/services/repository_summary.py` — `_build_call_graph`):
- `ast.ClassDef` → class nodes + `inherits` edges from base classes
- `ast.FunctionDef` / `ast.AsyncFunctionDef` → function/method nodes
- `ast.Call` inside each function body → directed `calls` edges to callee

**React / TypeScript**:
- `export function/const/class Name` → component nodes
- `import ... from './relative'` → `imports` edges
- `<ComponentName` JSX usage → `renders` edges

Cap: 80 nodes / 200 edges. Migrations and `__pycache__` excluded automatically.

**Frontend** (`src/components/repositories/CallGraphView.tsx`):
- Pure React + SVG, no external graph library
- Spring-force simulation (repulsion + link springs + centering + damping at 60 fps)
- Node shapes: square=class, diamond=component, circle=function/method
- Edge styles: solid=calls, dashed=imports, thick=inherits, dotted=renders
- Drag nodes, scroll-to-zoom, click-drag to pan, node tooltip on hover

---

## Getting Started

### Prerequisites

- **Node.js** `v20+` & `npm`
- **Python** `3.11+` (managed via `uv` or `venv`)
- **Rust** `cargo` (Tauri desktop wrapper)
- **Ollama** or **LM Studio** (optional — for semantic memory)

### Installation

```bash
# 1. Clone
git clone https://github.com/NotBhan/andes-context.git
cd re-track

# 2. Backend
cd backend
uv venv .venv --python 3.12
source .venv/bin/activate
pip install -r requirements.txt
cd ..

# 3. Frontend
npm install

# 4. Launch dev mode
npm run tauri dev
```

---

## Agent Context API

External agents can pull structured context via HTTP:

```bash
POST http://localhost:8000/api/v1/context
Content-Type: application/json

{
  "task_prompt": "How are Django models related to views in this project?",
  "repository_path": "/path/to/repo",
  "max_tokens": 8000,
  "include_structural_graph": true
}
```

Response: `context_markdown`, `intent_category`, `callers`, `callees`, `related_files`, `estimated_tokens`.

---

## Development

```bash
# Backend tests
cd backend && pytest tests/ -q          # 284+ tests

# Frontend build check
npm run build

# TypeScript type check
npx tsc --noEmit
```

---

## Contributing

1. Fork. Create feature branch: `git checkout -b feat/my-change`
2. Commit: `git commit -m "feat: describe change"`
3. Test: `cd backend && pytest tests/ -q && cd .. && npm run build`
4. Open a Pull Request.

---

## License

Apache-2.0. See `LICENSE`.
