# RE:Track — Architectural Baseline Manifest

> **Phase**: Phase 0 (Stabilization & Baseline Audit)  
> **Date**: 2026-08-20  
> **Purpose**: Formal record of environment, test results, build outputs, and verified behaviors for regression tracking.

---

## 1. System & Environment Baseline

| Property | Measured Value |
| :--- | :--- |
| **Git Commit Hash** | `ed4712ed6f7d8f5c2655fdd436e7bd9113e18117` |
| **Python Environment (venv)** | Python 3.12.8 (uv toolchain, Linux x86_64) |
| **Host System Python** | Python 3.14.7 |
| **Node.js Runtime** | v26.7.0 |
| **NPM Package Manager** | v10.8.2 |
| **Rust / Cargo** | rustc 1.84+ (cargo build active) |
| **Operating System** | Linux (Kernel 6.x, x86_64) |

---

## 2. Dependency Manifest

### Backend (Python)
- **FastAPI / Server**: `fastapi==0.115.6`, `uvicorn==0.34.0`, `pydantic>=2.10.0`, `pydantic-settings>=2.7.0`
- **Memory & Storage**: `cognee==0.1.30`, `lancedb>=0.17.0`, `kuzu>=0.7.0`, `sqlite3`
- **CLI & Formatting**: `typer==0.15.1`, `rich==13.9.4`
- **Inference & Networking**: `httpx>=0.28.0`, `psutil>=6.1.0`
- **Testing**: `pytest>=8.3.0`, `pytest-asyncio>=0.25.0`

### Frontend (React & Desktop)
- **Framework**: React 19 (`19.0.0`), React DOM 19
- **Build Tool**: Vite 7 (`7.3.6`), TypeScript 5.7
- **State Management**: Zustand 5 (`5.0.3`)
- **Desktop Runtime**: Tauri 2 (`@tauri-apps/api@^2.0.0`, `@tauri-apps/plugin-dialog@^2.0.0`)
- **UI & Styling**: TailwindCSS 4 (`@tailwindcss/vite@^4.0.0`), Lucide React (`0.475.0`), Framer Motion (`motion@^12.4.7`)

---

## 3. Build & Test Verification Baseline

### Backend Unit & Integration Tests
Command executed:
```bash
/home/chandrabhan/Documents/Personal\ Projects/re-track/backend/.venv/bin/pytest -q
```
**Results**:
- **Total Collected**: 297 tests
- **Passed**: 295 passed
- **Skipped**: 2 skipped (conftest integration skips without active live Ollama daemon)
- **Failed**: 0 failed
- **Execution Time**: 5.56 seconds
- **Warnings**: 15 warnings (11 Pydantic deprecation warnings originating inside the third-party `cognee` SDK package; 4 unawaited coroutine mock warnings in CLI/model unit tests)

### Frontend Production Build
Command executed:
```bash
npm run build
```
**Results**:
- **TypeScript Check (`tsc`)**: 0 errors
- **Vite Production Bundle**:
  - `dist/index.html`: 0.46 kB (gzip: 0.29 kB)
  - `dist/assets/index-Nq-kGcg9.css`: 81.61 kB (gzip: 14.32 kB)
  - `dist/assets/index-BhCa3Z88.js`: 1.25 kB (gzip: 0.47 kB)
  - `dist/assets/index-DbXXkvic.js`: 893.76 kB (gzip: 261.14 kB)
  - Transformed modules: 2,531
  - Total build duration: 3.10 seconds
  - Exit code: 0 (Success)

---

## 4. Runtime Configuration Baseline

```json
{
  "ollama": {
    "host": "localhost",
    "port": 11434,
    "llm_model": "phi3:mini",
    "embedding_model": "nomic-embed-text:latest",
    "embedding_dimensions": 768,
    "hf_tokenizer": "nomic-ai/nomic-embed-text-v1"
  },
  "storage": {
    "vector_db": "lancedb",
    "graph_db": "kuzu",
    "relational_db": "sqlite",
    "enable_kg_extraction": true,
    "auto_link_entities": false,
    "data_root": "backend/.cognee_data",
    "system_root": "backend/.cognee_system"
  },
  "service": {
    "enable_access_control": false,
    "caching": false,
    "skip_connection_test": true
  },
  "budget": {
    "default_interactive_target_tokens": 3000,
    "default_agent_middleware_target_tokens": 8000,
    "token_estimation_ratio": "1 token = 4 characters"
  }
}
```

---

## 5. Verified Behavior Matrix

| Domain Pipeline | Known Operational Behavior | Performance & Reliability Baseline |
| :--- | :--- | :--- |
| **Repository Indexing** | Scans filesystem using `discover_files` with `.gitignore` pruning; checks mtime hashes against `.andes/manifest.json`; generates AST outline via `RepositorySummaryGenerator`; ingests outline into Cognee via `add()`. | Fast cold-start ($< 200\text{ms}$ on 500 files); skips unchanged repositories completely (0 IO). |
| **Interactive Context Generation** | Validates non-empty prompt; executes `_cognee.recall()`; deduplicates by normalized text; ranks by composite score; compresses entries with $>35\%$ token overlap; categorizes by keywords; budgets to 3000 tokens; renders Markdown. | Produces structured GitHub Flavored Markdown with references and metadata in $< 100\text{ms}$ (excluding Ollama latency). |
| **Agent Context Middleware** | Checks `ContextCache` hit ($< 5\text{ms}$); parses intent via LLM/regex; generates repo summary; queries CGC structural graph; runs disk AST snippet match; merges Markdown with caller/callee trees; caches result. | Delivers comprehensive context package tailored for coding LLMs with quantization health check. |
| **Graph Generation** | Deterministically parses Python AST and TypeScript regex to construct `CallNode` and `CallEdge` arrays; inspects Kùzu graph engine when extracted. | 100% deterministic AST graph extraction; zero synthetic mock nodes created on frontend. |
| **Memory Operations** | Ingests data into LanceDB tables and Kùzu graph store via `cognify()`; queries vector rows and graph node counts; supports dataset-level `forget()`. | Authoritative vector counts and graph topology metrics surfaced directly from storage engines. |
| **Benchmark Execution** | Calculates total baseline tokens across repository source files; executes benchmark prompts; measures compression ratio and discrete latencies (retrieval vs synthesis). | Computes deterministic compression metrics and latency breakdowns. |
