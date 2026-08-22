# RE:Track Release Contract Freeze

**Document Type**: Canonical Product Release Contract  
**Version**: 0.1.0  
**Phase**: Phase 9B Release Baseline  
**Auditor**: Principal Release Engineer & Python Packaging Architect  

---

## 1. Executive Summary

This document freezes the technical release contract for RE:Track. Every statement, file path, environment variable, entrypoint, and lifecycle invariant is directly derived from and verified against the repository codebase.

---

## 2. Product Identity & Metadata

- **Canonical Product Name**: RE:Track (RefinedEngine Track)
- **Authoritative Version**: `0.1.0` (sourced from `app.__version__` in `backend/app/__init__.py`)
- **Package Distribution Name**: `retrack-ai`
- **Supported Python Runtimes**: `>=3.11, <3.14` (Verified on Python 3.12.8)
- **Supported Host Operating Systems**: Linux (x86_64, aarch64), macOS (Apple Silicon, Intel), Windows 11 (x64)

---

## 3. Canonical Executable Names & Entry Points

| Executable / Invocation | Implementation Target | Transport / Protocol | Logging Target | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **`retrack`** | `app.cli.main:app` | Native Console (Typer / Rich) | `sys.stdout` (formatted text) | Primary developer CLI (init, status, health, index, context, reset, migrate). |
| **`retrack-mcp`** | `app.mcp.server:main` | Standard I/O (JSON-RPC) | `sys.stderr` exclusively | Dedicated FastMCP server entrypoint for IDE agent configuration. |
| **`python -m app.mcp`** | `app.mcp.__main__` | Standard I/O (JSON-RPC) | `sys.stderr` exclusively | Python module execution syntax for MCP stdio clients. |
| **`python mcp_server.py`** | `backend/mcp_server.py` | Standard I/O (JSON-RPC) | `sys.stderr` exclusively | Standalone backward-compatible script entrypoint in repository root. |

---

## 4. Configuration Sources & Precedence

Configuration is evaluated with deterministic precedence (highest priority first):
1. **Runtime Arguments**: Passed explicitly via CLI flags or MCP tool parameters.
2. **Environment Variables**:
   - `RETRACK_WORKSPACE_ROOTS`: Comma-separated absolute paths authorized for scanning (e.g. `/home/user/projects,/tmp/repos`).
   - `OLLAMA_HOST` / `OLLAMA_PORT`: Hostname and port for local LLM provider (default: `localhost:11434`).
   - `LLM_MODEL`: Target completion model name (default: `phi3:mini`).
   - `EMBEDDING_MODEL`: Target vector embedding model (default: `nomic-embed-text:latest`).
   - `LOG_LEVEL`: Diagnostic log severity (default: `INFO`).
3. **Persisted User Settings**: Canonical JSON file at `~/.retrack/settings.json`.
4. **Hardcoded Defaults**: Sourced from `app/config/settings.py`.

---

## 5. Storage Contract: Canonical vs. Legacy

```
┌────────────────────────────────────────────────────────────────────────┐
│                        STORAGE DIRECTORY CONTRACT                      │
├────────────────────────────────┬───────────────────────────────────────┤
│ CANONICAL STORAGE (~/.retrack) │ LEGACY FALLBACK (~/.andes)            │
│ • ~/.retrack/settings.json     │ • Read-Only compatibility fallback    │
│ • ~/.retrack/repositories.json │ • Never modified implicitly           │
│ • ~/.retrack/context_packages/ │ • Migrated explicitly via CLI         │
│ • ~/.retrack/manifests/        │ • Discovered on read misses           │
│ • ~/.retrack/cache/            │                                       │
│ • ~/.retrack/backups/          │                                       │
└────────────────────────────────┴───────────────────────────────────────┘
```

- **Canonical Path (`~/.retrack/`)**:
  - All write operations (registering repos, saving context packages, updating settings, storing manifests, caching AST fingerprints) persist strictly under `~/.retrack/`.
- **Legacy Path (`~/.andes/`)**:
  - Strictly read-only fallback. If a requested repository, setting, or package is not found in `~/.retrack/`, the loader queries `~/.andes/`. Legacy files are never altered or deleted during normal runtime.

---

## 6. Provider Reachability & Fallback Contract

- **Ollama / LM Studio Online**: Full semantic vector search, knowledge graph triples extraction, and LLM-assisted context synthesis.
- **Provider Offline / Unreachable**:
  - Deterministic AST call graph extraction (`get_ast_call_graph`) remains **100% operational** (< 5ms latency).
  - High-level architectural summaries (`get_repository_summary`) remain **100% operational**.
  - Ranked code search (`search_repository_code`) remains **100% operational**.
  - Context synthesis (`get_agent_context`) falls back gracefully to deterministic local AST snippets and summaries without crashing.
  - Subprocess crash recovery auto-reconnects in ~20ms upon provider restart without requiring an MCP server restart.

---

## 7. Lifecycle & Reset Safety Guarantees

1. **Idempotent Initialization (`retrack init`)**:
   - Safely creates `~/.retrack/` directory tree and default config if missing.
   - If directories already exist, existing user data is preserved untouched.
2. **Explicit Reset Operations (`retrack reset`)**:
   - `retrack reset --cache`: Purges cached AST fingerprints and temporary context snippets.
   - `retrack reset --state --confirm`: Purges registered repository metadata and saved packages.
   - `retrack reset --all --confirm`: Full reset of `~/.retrack/` state.
   - **Critical Invariant**: Application reset operations **NEVER** modify or delete user source repositories under any circumstances.
3. **Explicit Migration (`retrack migrate`)**:
   - Discovers legacy records in `~/.andes/`, previews changes with `--dry-run`, and copies records into `~/.retrack/` with automatic pre-migration backup in `~/.retrack/backups/`.
