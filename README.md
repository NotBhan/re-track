# RE:Track (AI Context Hub)

<div align="center">

**High-performance, local-first AI memory & context engine for coding agents.**  
*Transform repository architecture, AST graphs, and semantic memory into structured, token-budgeted Context Packages.*

[![TypeScript](https://img.shields.io/badge/Frontend-React%20%7C%20Vite%20%7C%20Tauri-blue?style=flat-square)](https://tauri.app/)
[![Python](https://img.shields.io/badge/Backend-FastAPI%20%7C%20Cognee%20%7C%20CGC-green?style=flat-square)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-Apache%202.0-orange?style=flat-square)](LICENSE)

</div>

---

## Overview

**RE:Track** is a desktop application and local context engine designed to solve repository-scale context limits for modern AI coding assistants (Claude Code, Cursor, Windsurf, Aider, LM Studio, Ollama).

Instead of dumping massive unorganized files or making coding agents blindly traverse directories, **RE:Track** intercepts tasks, retrieves semantic memories from Cognee, traverses structural AST call graphs via CodeGraphContext (CGC), and deterministically packages actionable Markdown context with precise token budgeting.

---

## Key Features

- **Context Studio Deck**: Real-time prompt interceptor with live token budget allocations (8k default, customizable up to 128k).
- **Depth-2.5 Repository Map**: High-level structural folder hierarchies and AST symbol outlines.
- **Local-First & Multi-Model**: Native support for **LM Studio**, **Ollama**, and **OpenAI-compatible** local endpoints (e.g. `phi-4-mini`, `qwen2.5-coder`).
- **Live Hardware Telemetry**: Real-time host RAM, CPU load, and GPU VRAM monitoring.
- **Deterministic Delivery**: Structured Markdown context packages ready to copy, export, or pipe into coding agents and LLM harnesses.
- **Memory Graph Browser**: Manage semantic vector embeddings and entity relationships stored in Cognee.
- **Telemetry Benchmarks**: Measure latency, token throughput, and retrieval accuracy across local model quants.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Desktop UI (React + Tauri)                │
│  Context Studio │ Repository Map │ Memory Graph │ Settings  │
└──────────────────────────────┬──────────────────────────────┘
                               │ Local HTTP / Tauri IPC
┌──────────────────────────────▼──────────────────────────────┐
│                    Python Backend (FastAPI)                 │
├──────────────────────────────┬──────────────────────────────┤
│       Intent Parser          │      Structural Graph (CGC)  │
│  - Task extraction           │  - Symbol callers/callees    │
│  - Query classification      │  - AST dependency paths      │
├──────────────────────────────┼──────────────────────────────┤
│       Cognee Engine          │      Package Builder         │
│  - Vector search             │  - Deduplication & Ranking   │
│  - Semantic memory recall    │  - Token Budget Enforcement  │
└──────────────────────────────┴──────────────────────────────┘
```

---

## Getting Started

### Prerequisites

- **Node.js**: `v20+` & `npm`
- **Python**: `3.11+` or `3.12+` (managed via `uv` or `venv`)
- **Rust Toolchain**: `cargo` (for building the Tauri desktop wrapper)
- **Local LLM Runner (Optional)**: [LM Studio](https://lmstudio.ai/) or [Ollama](https://ollama.com/)

### Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/NotBhan/andes-context.git
   cd re-track
   ```

2. **Set up the Python backend:**

   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   cd ..
   ```

3. **Install frontend dependencies:**

   ```bash
   npm install
   ```

4. **Launch in development mode:**

   ```bash
   npm run tauri dev
   ```

---

## API & Agent Interception

External agents and harnesses can pull context directly via HTTP:

```bash
POST http://localhost:8000/api/v1/context
Content-Type: application/json

{
  "task_prompt": "Find how LLM providers are configured in settings",
  "repository_path": "/path/to/repo",
  "max_tokens": 8000,
  "include_structural_graph": true
}
```

**Response:**

```json
{
  "success": true,
  "intent_category": "explanation",
  "estimated_tokens": 1420,
  "context_markdown": "# Task\n...\n## Relevant Files\n...\n## Architecture\n...",
  "generation_time_ms": 285
}
```

---

## Contributing

Contributions are warmly welcome! Whether fixing bugs, improving the AST parsing pipelines, adding local model connectors, or enhancing the desktop UI:

1. Fork the repository.
2. Create a feature branch: `git checkout -b feat/my-improvement`.
3. Commit your changes: `git commit -m "Add feature"`.
4. Run tests:

   ```bash
   npm run build
   pytest backend/tests
   ```

5. Open a Pull Request.

---

## License

Distributed under the **Apache-2.0 License**. See `LICENSE` for more information.
