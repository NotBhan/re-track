# RE:Track Development Plan & Execution Status

This document tracks the phased development milestones and operational roadmap for RE:Track.

---

## 1. Roadmap & Phase Execution

### Phase 1: Local Knowledge Base & Onboarding UX (Completed)

- [x] LanceDB & Kuzu graph database integration through Cognee.
- [x] Repository indexing pipeline with `.gitignore` and `.agentignore` adherence.
- [x] Provider reachability banner (`ProviderAlertBanner.tsx`) with auto-detection & retry for Ollama and LM Studio.
- [x] Empty state onboarding card with ambient visual tokens and core feature highlights.
- [x] Modal-based Quick Context Synthesizer (`QuickContextModal.tsx`) with 1-click execution from repo cards.

### Phase 2: AST Call Graph & Knowledge Explorer (Completed)

- [x] Multi-language AST extraction in Python (`repository_summary.py`) supporting ClassDef, FunctionDef, Calls, and React JSX renders.
- [x] Force-directed interactive SVG graph view (`CallGraphView.tsx`) with spring physics, node kind filters, and live search.
- [x] Interactive node inspector drawer showing symbol file lines, callers, and callees.
- [x] 3-Tab Knowledge Explorer (`KnowledgeExplorer.tsx`) with AST topology, directory hierarchy, and ranked key components.

### Phase 3: Core Context Loop & Prompt Studio (Completed)

- [x] Two-column responsive Prompt Workbench (`Dashboard.tsx`) with preset templates and `Ctrl+Enter` shortcut.
- [x] 6-stage animated synthesis pipeline progress feedback.
- [x] Intent parsing & hallucination guardrails display card.
- [x] Dynamic token budget manager with reduction gauge (~92% token savings).
- [x] One-click save to versioned context package library and markdown export.

### Phase 4: Context Packages Library & Comparison (Completed)

- [x] Persistent JSON store (`~/.retrack/context_packages.json`) for generated packages.
- [x] Search filtering and codebase dropdown filter (`ContextPackages.tsx`).
- [x] Side-by-side context package comparison/diff modal.
- [x] Markdown accordion preview and clipboard copy (`PackageCard.tsx`).

### Phase 5: Telemetry, Benchmarks & Provider Management (Completed)

- [x] Automated benchmark suite measuring latency (< 200ms), token savings (~90%), and accuracy.
- [x] Visual Token Budget comparison bar chart (Raw Repo vs RE:Track Context).
- [x] Settings tab for dynamic LLM provider configuration and hot-reloading (`OllamaSettings.tsx`).

### Phase 6: Hexagonal Architecture & Composition Root (Completed)

- [x] Architectural separation into Inbound Driving Adapters, Application Use Cases, Outbound Ports, and Driven Infrastructure Adapters.
- [x] Centralized composition root (`ApplicationContainer`) with container lifecycle management (`get_container()`, `reset_container()`).
- [x] Modular FastAPI route architecture (`app/api/routers/`) separating system, repository, context, memory, packages, benchmarks, and settings.
- [x] Canonical storage migration with backward-compatible legacy storage adapters.

### Phase 7: Empirical Benchmarks & Retrieval Validation (Completed)

- [x] Canonical golden task dataset (`benchmarks/retrack/golden_tasks.json`, 20 tasks across 4 categories).
- [x] Pure deterministic evaluation engine (`tests/evaluation/evaluator.py`) measuring Precision@K, Recall@K, Critical Evidence Coverage, and Noise Ratio.
- [x] Phase 7E controlled retrieval experiments (proven AST indexing, intent priors, fingerprint caching; CGC subprocess prohibited on hot path).

### Phase 8A: MCP Server Inbound Driving Adapter (Completed)

- [x] FastMCP stdio server (`backend/app/mcp/`) exposing 5 standardized tools: `get_agent_context`, `get_repository_summary`, `get_ast_call_graph`, `search_repository_code`, `list_indexed_repositories`.
- [x] Pure Hexagonal boundary wiring directly to `ApplicationContainer` use cases without database or Cognee coupling.
- [x] In-process AST and search execution avoiding subprocess bottlenecks.

### Phase 8B: MCP Production Hardening & Trust Boundary Enforcement (Completed)

- [x] Workspace authorization boundary (`WorkspaceAuthorizationPort` & `WorkspaceAuthorizationService`) restricting access to registered repos and `RETRACK_WORKSPACE_ROOTS`.
- [x] Path containment and symlink escape pruning.
- [x] Deterministic collision-proof dataset identity isolation (`derive_dataset_name`).
- [x] Bounded context concurrency guard (`max_concurrent=1`, `max_queue=5`, `timeout=30.0s`) with retryable `BusyError`.
- [x] MCP exception isolation boundary returning sanitized structured error responses.

### Phase 8C: MCP Operational Lifecycle & Reliability Validation (Completed)

- [x] Process-scoped shared concurrency guard lifecycle on `ApplicationContainer`.
- [x] Stderr-only logging separation (`setup_logging(stream=sys.stderr)`) preserving clean JSON-RPC stdout frames.
- [x] Clean stdio EOF, SIGINT, SIGTERM, and cancellation termination semantics (< 0.15s).
- [x] Verified LLM provider failure resilience and automatic same-process recovery without server restart.

### Phase 8D: Production Readiness & Soak Validation (Completed)

- [x] 520-iteration prolonged soak validation measuring bounded RSS growth (< 25MB delta), zero leaked FDs (28 baseline/final), and zero leaked threads.
- [x] Failure recovery matrix with 5 isolated fault injection scenarios (LLM down/up cycles, active worker crashes, cancellation slot preservation, auth violations, malformed inputs).
- [x] Official MCP `ClientSession` stdio interoperability with 5 consecutive reconnect cycles.
- [x] Subprocess signal handling verification for SIGINT, SIGTERM, and EOF without zombie leaks.
- [x] Dual entry point (`python mcp_server.py` and `python -m app.mcp`) and 7-turn realistic AI coding agent workload.

### Phase 8E: Final Production Readiness Gate (Completed)

- [x] Prolonged 3,000-operation multi-repository soak test with continuous mutation, 100-request telemetry profiling, 0 FD leaks, 0 thread leaks, and sub-3ms P99 latency.
- [x] Real OS subprocess provider lifecycle with 5 live SIGKILL crash/restart cycles against TCP socket server (avg failure detect 38.42ms, avg recovery 20.41ms, zero container rebuild).
- [x] 13-point host environment failure matrix (deleted/recreated repos, broken symlinks, syntax errors, binary blobs, corrupted manifests, unauthorized paths).
- [x] 20-cycle real MCP `ClientSession` stdio reconnect interoperability test suite.
- [x] 500-iteration cache & resource churn stability validation (+0.91MB RSS delta, zero leaks).
- [x] Standalone and module deployment reproducibility verification.
- [x] Comprehensive production readiness audit report (`docs/architecture/phase-8e-audit.md`) and definitive `PRODUCTION GRADE` certification.

### Phase 9: Productization & Release Engineering (COMPLETED & FROZEN)

- [x] **Phase 9A: Product Truth & Capability Contract Cleanup (Completed)**
  - Canonical feature inventory (`docs/product/feature-inventory.md`).
  - User-facing capability matrix (`docs/product/capability-matrix.md`).
  - Release readiness audit and prioritized gap analysis (`docs/product/release-readiness.md`).
  - Phase 9A audit sign-off (`docs/architecture/phase-9a-audit.md`).
- [x] **Phase 9B: Installation, Packaging & Update Workflow (Completed)**
  - Standard PEP 517/621 distribution build (`pyproject.toml`, `retrack_ai-0.1.0-py3-none-any.whl`).
  - First-run bootstrap service & CLI initialization command (`retrack init`).
  - Scoped state reset (`retrack reset`) and legacy migration (`retrack migrate`) with automated pre-reset backups.
  - Verification in clean virtual environment outside repository.
  - Phase 9B audit sign-off (`docs/architecture/phase-9b-audit.md`).
- [x] **Phase 9C: Observability, Diagnostics & Supportability (FROZEN)**
  - Structured persistent JSONL logging (`~/.retrack/logs/app.jsonl`) with `SafeRotatingFileHandler` size-based rotation and bounded retention.
  - In-flight secret redaction regex engine redacting API keys (`sk-...`), bearer tokens, passwords, and DB/HTTP connection strings.
  - FastMCP stdio safety: `sys.stdout` 100% reserved for JSON-RPC, human diagnostics exclusively on `sys.stderr`.
  - In-application operational health state machine (`healthy`, `degraded`, `unavailable`, `not_configured`) and concurrency queue inspection.
  - Redacted diagnostic bundle generation and atomic export (`retrack diagnostics`, `POST /diagnostics/export`).
  - Interactive Desktop Settings Diagnostics UI for real-time monitoring and log stream inspection.
  - 32 dedicated Phase 9C unit and adversarial audit tests passing across 6 test suites.
  - Phase 9C final security and architecture audit sign-off (`docs/architecture/phase-9c-final-audit.md`) and user guide (`docs/product/observability.md`).
- [x] **Phase 9D: CI Regression & Release Automation (FROZEN)**
  - Multi-platform GitHub Actions CI matrix (Ubuntu, macOS, Windows) supporting Python 3.11, 3.12, and 3.13 (`.github/workflows/ci.yml`).
  - Deterministic golden retrieval benchmark regression gate (`BenchmarkRegressionGate`, `app.evaluation.benchmark_gate`) preventing precision/recall regressions beyond mathematically established tolerances.
  - Single-source version authority (`backend/app/__init__.py`) with hatchling dynamic build derivation and mechanical version drift enforcement (`test_version_authority.py`).
  - Artifact-first package validation and clean-install outside repository (`test_packaging_validation.py`) verifying CLI and FastMCP stdio framing cleanliness.
  - Automated gate-protected release workflow (`.github/workflows/release.yml`) with SHA-256 checksum generation and supply-chain hardening.
  - 21 dedicated Phase 9D tests passing across 3 new test files (`test_version_authority.py`, `test_benchmark_baseline_contract.py`, `test_packaging_validation.py`).
  - Phase 9D audit sign-off (`docs/architecture/phase-9d-audit.md`, `docs/architecture/phase-9d-hosted-validation.md`), CI guide (`docs/product/ci-and-release.md`), and release runbook (`docs/product/release-process.md`).
- [x] **Phase 9E: Frontend Behavioral Verification & UX Hardening (FROZEN)**
  - Automated component interaction and integration user workflow tests covering 10 Critical User Journeys (A through J).
  - 100% passing automated test suite with 50 tests across 12 test files (`src/test/journeys/`).
  - Strict Truth Boundary guarantees preventing synthetic metrics or fake data invention.
  - Edge-case error state, rapid double-click prevention, and offline degraded state hardening.
  - Phase 9E final audit and verification closure sign-off (`docs/architecture/phase-9e-audit.md`).
- [x] **Phase 9E.1: Real Runtime Frontend Smoke Validation (FROZEN)**
  - Full evidence classification for the 12 test files / 50 tests Vitest foundation.
  - 9/9 Playwright real browser smoke tests passing in Chromium against built frontend (`dist/`).
  - Live Python FastAPI backend integration (`http://127.0.0.1:8765`) verifying repository scan, AST extraction, context synthesis, and diagnostics export.
  - Quantitatively measured provider failure (15ms UI error display) and recovery retry (102ms synthesis).
  - Rust Tauri bridge `cargo check` verified with 0 errors.
  - Phase 9E.1 runtime validation architecture document (`docs/architecture/phase-9e-runtime-validation.md`).

### Phase 10: Retrieval & Intelligence Evolution (Planned)

- [ ] **Phase 10A: Incremental / Diff-Aware Indexing** (Git diff change detection and selective file re-indexing).
- [ ] **Phase 10B: Improved TS/JS/JSX Structural Analysis** (Tree-sitter native WASM bindings for cross-file type resolution).
- [ ] **Phase 10C: Expanded Retrieval Benchmarking** (Multi-repository complex cross-package golden tasks).
- [ ] **Phase 10D: Adaptive Query-Aware Retrieval** (Task-type-specific token allocation profiles).
- [ ] **Phase 10E: Agent Workflow Optimization** (Multi-turn conversational context caching).

### Deferred Capabilities (Postponed Until Specific Demand)

- **HTTP / Streamable MCP Transport**: Postponed (local stdio remains the primary standard for Claude and Cursor).
- **Remote Git Repository Ingestion**: Postponed (local-first workstation scope prioritized).
- **Cloud Multi-Tenancy**: Excluded by design (privacy-first local execution).
- **Distributed Task Workers (Celery/Redis)**: Excluded by design (8GB RAM single-node target).

---

## 2. Quality & Verification Metrics

- **Backend Pytest Suite:** Passing unit/integration/soak tests across 39 test files (`backend/tests/`).
- **Frontend Vitest Suite:** 50 passing behavioral tests across 12 test suites (`src/test/journeys/`).
- **AST Integrity:** 100% passing multi-language AST syntax and symbol resolution tests (`tests/test_ast_integrity.py`).
- **Frontend Build & Types:** 100% clean TypeScript compile and Vite production build (`npm run build`).
- **Design System:** Vercel Geist aesthetic with dark mode canvas (`#000000`), micro-animations (`motion/react`), and high-contrast typography.
- **Protocol Compliance:** 100% clean JSON-RPC framing on stdio; 0 unhandled exception leaks across MCP tools.
- **Production Status:** **PRODUCTION GRADE** certified.
