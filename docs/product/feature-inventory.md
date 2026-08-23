# RE:Track Canonical Feature Inventory

**Document Type**: Canonical Product Feature Inventory  
**Version**: 1.0 (Phase 9A Release Baseline)  
**Status**: Authoritative & Evidence-Backed  

---

## 1. Overview & Verification Methodology

This document establishes the verified inventory of all features and technical capabilities implemented in RE:Track as of Phase 9A. Every entry is directly grounded in source code, configuration files, and passing automated test suites in the repository.

### Maturity Classifications:
- **Production**: Fully implemented, backed by dedicated integration or lifecycle tests, verified against failure modes, and ready for end-user / AI-agent workflows.
- **Production with Limitations**: Fully implemented and tested, but constrained by explicit environmental, language, or hardware bounds (e.g., heuristic parsing for non-Python languages, single-concurrency serialization).
- **Internal**: Architectural, security, reliability, or storage mechanisms that power user features but are not directly exposed as standalone user-facing tools.
- **Experimental**: Implemented exploratory features not yet hardened for mission-critical workflows.
- **Planned**: Documented roadmap capabilities for future development phases.
- **Deferred**: Explicitly excluded or postponed capabilities.
- **Deprecated / Removed**: Former implementations intentionally removed or replaced.

---

## 2. Feature Inventory Master Table

| ID | Feature Name | Category | User / Internal | Status | Exact Implementation Location | Verification Evidence | Known Limitations |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **FEAT-001** | FastMCP Stdio Server | MCP / AI Agent Integration | User-facing | Production | `backend/app/mcp/server.py`, `backend/mcp_server.py`, `backend/app/mcp/__main__.py` | `tests/test_phase_8e_mcp_interoperability.py`, `tests/test_phase_8d_interoperability.py` | Stdio transport only; network SSE/HTTP not implemented. |
| **FEAT-002** | Agent Context Synthesis (`get_agent_context`) | Context Engine | User-facing | Production | `backend/app/mcp/tools.py`, `backend/app/application/use_cases/context.py` | `tests/test_mcp_tools.py`, `tests/test_phase_8e_long_duration_soak.py` | Requires indexed repo; falls back gracefully to local summary if Cognee dataset is missing or LLM offline. |
| **FEAT-003** | Repository Architecture Summary (`get_repository_summary`) | Repository Intelligence | User-facing | Production | `backend/app/mcp/tools.py`, `backend/app/services/repository_summary.py` | `tests/test_mcp_tools.py`, `tests/test_phase_8e_environment_failures.py` | Static summary generated on first scan; cached in memory and manifest. |
| **FEAT-004** | Deterministic AST Call Graph (`get_ast_call_graph`) | AST & Code Intelligence | User-facing | Production | `backend/app/mcp/tools.py`, `backend/app/services/repository_summary.py` | `tests/test_ast_integrity.py`, `tests/test_phase_8e_long_duration_soak.py` | Clamped to max 500 nodes; deep dynamic reflection / `getattr` in Python untracked. |
| **FEAT-005** | Ranked Source Search (`search_repository_code`) | Context Engine | User-facing | Production | `backend/app/mcp/tools.py`, `backend/app/services/source_search_service.py` | `tests/test_mcp_tools.py`, `tests/test_phase_8e_resource_stability.py` | Clamped to max 50 results; uses TF-IDF/symbol lexical ranking. |
| **FEAT-006** | Indexed Repository Discovery (`list_indexed_repositories`) | Repository Intelligence | User-facing | Production | `backend/app/mcp/tools.py`, `backend/app/services/repository_metadata_store.py` | `tests/test_mcp_tools.py`, `tests/test_phase_8d_interoperability.py` | Discovers registered repositories in metadata store only. |
| **FEAT-007** | Workspace Authorization Sandboxing | Security & Trust | Internal | Production | `backend/app/services/workspace_authorization_service.py` | `tests/test_phase_8b_security_hardening.py`, `tests/test_phase_8e_environment_failures.py` | Access prohibited outside registered repo paths and `_workspace_roots`. |
| **FEAT-008** | Symlink Escape & Path Containment | Security & Trust | Internal | Production | `backend/app/services/workspace_authorization_service.py` | `tests/test_phase_8b_security_hardening.py` | Symlinks pointing outside workspace root pruned during file discovery. |
| **FEAT-009** | Collision-Proof Dataset Hashing | Storage & Data | Internal | Production | `backend/app/utils/dataset_naming.py` (`derive_dataset_name`) | `tests/test_phase_8b_security_hardening.py`, `tests/test_phase_8e_long_duration_soak.py` | Appends 10-char SHA-256 hash to folder basename for multi-workspace disambiguation. |
| **FEAT-010** | Process-Scoped Concurrency Guard | Reliability & Operations | Internal | Production | `backend/app/application/use_cases/context.py` (`BoundedConcurrencyGuard`) | `tests/test_phase_8c_lifecycle.py`, `tests/test_phase_8e_long_duration_soak.py` | Serialized (`max_concurrent=1`, `max_queue=5..10`); excess requests fail fast with `BusyError`. |
| **FEAT-011** | Stdio Stream & Logging Isolation | Reliability & Operations | Internal | Production | `backend/app/core/logging_config.py`, `backend/app/mcp/server.py` | `tests/test_phase_8c_lifecycle.py`, `tests/test_phase_8e_mcp_interoperability.py` | `stdout` strictly reserved for JSON-RPC; diagnostic logs routed to `stderr`. |
| **FEAT-012** | Subprocess Provider Failure & Auto-Recovery | Reliability & Operations | Internal | Production | `backend/app/services/llm_provider_service.py` | `tests/test_phase_8e_provider_lifecycle.py` (5/5 live OS subprocess cycles) | Recovers in ~20ms on socket reconnection without restarting the MCP server. |
| **FEAT-013** | Context Studio Workbench | Frontend / UX | User-facing | Production | `src/pages/ContextStudio.tsx`, `src/components/context-builder/` | `npm run build`, `src/pages/ContextStudio.tsx` | Character-heuristic token estimate (4 chars/token); live split-pane markdown. |
| **FEAT-014** | Force-Directed SVG Knowledge Explorer | Frontend / UX | User-facing | Production | `src/pages/KnowledgeExplorer.tsx`, `src/components/repositories/CallGraphView.tsx` | `npm run build`, `src/components/repositories/CallGraphView.tsx` | Spring physics graph view with symbol kind filters and caller/callee drawer. |
| **FEAT-015** | Repository Management & Scanning | Frontend / UX | User-facing | Production | `src/pages/Repositories.tsx`, `src/components/repositories/RepositoryCard.tsx` | `npm run build`, `tests/test_repositories_endpoints.py` | Scans languages, frameworks, components; provides quick context modal. |
| **FEAT-016** | Context Package Persistence | Context Engine | User-facing | Production | `backend/app/services/context_package_repository.py`, `src/pages/ContextPackages.tsx` | `tests/test_context_package_service.py`, `tests/test_packages_endpoints.py` | Canonical storage at `~/.retrack/context_packages.json` (legacy fallback: `~/.andes/`). |
| **FEAT-017** | Memory & Graph Topology Inspector | Memory & Knowledge | User-facing | Production | `src/pages/Memory.tsx`, `backend/app/api/routers/memory.py` | `tests/test_memory_endpoints.py` | Authoritative Kùzu triple and LanceDB vector stats from backend truth boundary. |
| **FEAT-018** | Benchmark Suite & Scorecard Dashboard | Benchmarking & Evaluation | User-facing | Production | `src/pages/Benchmarks.tsx`, `backend/app/services/benchmark_service.py` | `tests/test_benchmarks_endpoints.py`, `tests/test_phase_7e_evaluation.py` | Measures Precision@K, Recall@K, token baseline, and compression ratios. |
| **FEAT-019** | Settings & Provider Hot-Reloading | Provider Management | User-facing | Production | `src/pages/Settings.tsx`, `backend/app/api/routers/settings.py` | `tests/test_settings_endpoints.py` | Hot-reloads Ollama, LM Studio, and OpenAI-compatible endpoints dynamically. |
| **FEAT-020** | Headless Developer CLI (`retrack`) | CLI / Headless | User-facing | Production | `backend/app/cli/main.py` | `tests/test_cli.py` | Commands: `health`, `status`, `index`, `context`, `forget`, `mcp`. |
| **FEAT-021** | Python Native AST Extraction | AST & Code Intelligence | Internal | Production | `backend/app/services/repository_summary.py` | `tests/test_ast_integrity.py` | Deep symbol parsing, import resolution, alias handling, parameter shadowing. |
| **FEAT-022** | TypeScript / JS / JSX AST Extraction | AST & Code Intelligence | Internal | Production with Limitations | `backend/app/services/repository_summary.py` | `tests/test_ast_integrity.py` | Uses regex/heuristic extraction; deep macro/metaprogramming untracked. |
| **FEAT-023** | Context Cache & Invalidation Engine | Caching & Performance | Internal | Production | `backend/app/services/context_cache.py` | `tests/test_phase_8e_resource_stability.py` | Fingerprints query & file mtimes; evicts on source file modification. |
| **FEAT-024** | Hybrid Semantic-Graph Memory (Cognee) | Memory & Knowledge | Internal | Production with Limitations | `backend/app/services/cognee_service.py` | `tests/test_cognee_service.py` | Requires external local LLM for cognify/embedding; offline fallback provided. |
| **FEAT-025** | Pure Deterministic Evaluation Engine | Benchmarking & Evaluation | Internal | Production | `backend/tests/evaluation/evaluator.py` | `tests/test_evaluation_engine.py` | Functional precision/recall/coverage metrics against `golden_tasks.json`. |
| **FEAT-026** | Incremental / Diff-Aware Indexing Engine | Indexing & AST Intelligence | Internal | Production | `backend/app/services/manifest_service.py`, `backend/app/services/indexing_service.py`, `backend/app/services/repository_summary.py` | `tests/test_incremental_ast_updates.py`, `tests/test_incremental_manifest.py`, `tests/test_incremental_performance.py` | Schema 2.0 / Parser 1.0.0; supports NOOP (0 AST parses), INCREMENTAL, and FULL modes with crash-safe atomic manifest commit. |
| **FEAT-027** | Fine-Grained Provenance Context Cache Invalidation | Caching & Performance | Internal | Production | `backend/app/services/context_cache.py`, `backend/app/application/use_cases/context.py` | `tests/test_incremental_cache_invalidation.py` | Tracks referenced files and symbols; selectively invalidates impacted cache packages while preserving unrelated entries. |

---

## 3. Deep Feature Specifications

### FEAT-001: FastMCP Stdio Server Transport
- **User-Facing / Internal**: User-facing (AI Agent Integration)
- **Status**: Production
- **Implementation**: [`backend/app/mcp/server.py`](file:///home/chandrabhan/Documents/Personal%20Projects/re-track/backend/app/mcp/server.py), [`backend/mcp_server.py`](file:///home/chandrabhan/Documents/Personal%20Projects/re-track/backend/mcp_server.py), [`backend/app/mcp/__main__.py`](file:///home/chandrabhan/Documents/Personal%20Projects/re-track/backend/app/mcp/__main__.py)
- **How It Works**: Initializes the Hexagonal `ApplicationContainer` and launches a FastMCP stdio server listening for standard JSON-RPC protocol frames on `stdin`/`stdout`. Handles clean shutdown on `stdin` EOF, `SIGINT`, and `SIGTERM`.
- **Inputs**: JSON-RPC request frames via `sys.stdin`.
- **Outputs**: JSON-RPC response frames via `sys.stdout`.
- **Dependencies**: `mcp` SDK, `asyncio`, `ApplicationContainer`.
- **Verification Evidence**: `tests/test_phase_8e_mcp_interoperability.py` (20 consecutive real `ClientSession` cycles), `tests/test_phase_8d_lifecycle.py`.
- **Known Limitations**: Stdio transport only. Network-based HTTP/SSE transport is deferred until future multi-machine requirements arise.
- **Maturity**: Production.

### FEAT-002: Agent Context Synthesis Tool (`get_agent_context`)
- **User-Facing / Internal**: User-facing
- **Status**: Production
- **Implementation**: [`backend/app/mcp/tools.py`](file:///home/chandrabhan/Documents/Personal%20Projects/re-track/backend/app/mcp/tools.py), [`backend/app/application/use_cases/context.py`](file:///home/chandrabhan/Documents/Personal%20Projects/re-track/backend/app/application/use_cases/context.py)
- **How It Works**: Validates workspace authorization, parses task intent, resolves symbols against the AST call graph, extracts relevant code snippets, integrates semantic memory from Cognee (if available), applies adaptive token budgeting, and returns structured metadata with a Markdown context package.
- **Inputs**: `task_prompt` (str), `repository_path` (str), `max_tokens` (int, default: 8000), `dataset_name` (optional str), `include_structural_graph` (bool, default: True).
- **Outputs**: `AgentContextResponse` JSON object with `context_markdown`, `extracted_symbols`, `callers`, `callees`, `related_files`, `estimated_tokens`, and `total_time_ms`.
- **Dependencies**: `ContextUseCases`, `WorkspaceAuthorizationPort`, `BoundedConcurrencyGuard`, `RepositorySummaryGenerator`, `CogneeService`.
- **Verification Evidence**: `tests/test_mcp_tools.py`, `tests/test_phase_8e_long_duration_soak.py` (3,000 soak ops).
- **Known Limitations**: Requires indexed codebase or falls back to local AST summary if Cognee dataset is absent.
- **Maturity**: Production.

### FEAT-007: Workspace Authorization Sandboxing
- **User-Facing / Internal**: Internal (Security & Trust)
- **Status**: Production
- **Implementation**: [`backend/app/services/workspace_authorization_service.py`](file:///home/chandrabhan/Documents/Personal%20Projects/re-track/backend/app/services/workspace_authorization_service.py), [`backend/app/application/ports/workspace_authorization_port.py`](file:///home/chandrabhan/Documents/Personal%20Projects/re-track/backend/app/application/ports/workspace_authorization_port.py)
- **How It Works**: Inspects requested paths against authorized workspace roots and registered repository records in `RepositoryMetadataStore`. Rejects unauthorized paths before any file scanning or AST parsing begins.
- **Inputs**: Target repository / file path (`str` or `Path`).
- **Outputs**: `tuple[bool, Optional[str]]` indicating authorization status and reason.
- **Dependencies**: `RepositoryMetadataStore`.
- **Verification Evidence**: `tests/test_phase_8b_security_hardening.py`, `tests/test_phase_8e_environment_failures.py`.
- **Known Limitations**: Authorization is process-local; multi-user tenant ACLs are not supported.
- **Maturity**: Production.

### FEAT-010: Process-Scoped Shared Concurrency Guard
- **User-Facing / Internal**: Internal (Reliability)
- **Status**: Production
- **Implementation**: [`backend/app/application/use_cases/context.py`](file:///home/chandrabhan/Documents/Personal%20Projects/re-track/backend/app/application/use_cases/context.py) (`BoundedConcurrencyGuard`), [`backend/app/application/container.py`](file:///home/chandrabhan/Documents/Personal%20Projects/re-track/backend/app/application/container.py)
- **How It Works**: Lifecycle-scoped semaphore and queue that serializes heavy context synthesis operations (`max_concurrent=1`). Queues up to `max_queue` requests (default 5, soak 10). Rejects excess requests with `BusyError`.
- **Inputs**: Async execution callable.
- **Outputs**: Serialized execution result or fast `BusyError` rejection.
- **Dependencies**: `asyncio.Semaphore`, `asyncio.Queue`.
- **Verification Evidence**: `tests/test_phase_8c_lifecycle.py`, `tests/test_phase_8e_long_duration_soak.py`.
- **Known Limitations**: Single-concurrency serialization is intentional for 8GB RAM host environments; parallel multi-worker context synthesis is not supported.
- **Maturity**: Production.

### FEAT-016: Dual-Path Storage Contract
- **User-Facing / Internal**: Internal (Storage Compatibility)
- **Status**: Production
- **Implementation**: [`backend/app/services/repository_metadata_store.py`](file:///home/chandrabhan/Documents/Personal%20Projects/re-track/backend/app/services/repository_metadata_store.py), [`backend/app/services/context_package_repository.py`](file:///home/chandrabhan/Documents/Personal%20Projects/re-track/backend/app/services/context_package_repository.py), [`backend/app/config/settings.py`](file:///home/chandrabhan/Documents/Personal%20Projects/re-track/backend/app/config/settings.py)
- **How It Works**: All new write operations persist strictly to `~/.retrack/`. If `~/.retrack/` does not contain a requested record, the adapter falls back to reading legacy data from `~/.andes/`. Legacy files are never modified.
- **Inputs**: File read/write requests.
- **Outputs**: Loaded or persisted JSON records.
- **Dependencies**: `LocalFileSystemAdapter`, `Path`.
- **Verification Evidence**: `tests/test_storage_compatibility.py` (all tests passing).
- **Known Limitations**: Migration from `.andes` to `.retrack` is lazy on-demand rather than a bulk one-time migration script.
- **Maturity**: Production.
