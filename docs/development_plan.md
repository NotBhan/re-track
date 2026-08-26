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

### Phase 10: Retrieval & Intelligence Evolution

- [x] **Phase 10A: Incremental / Diff-Aware Indexing (COMPLETED & FROZEN)**
  - Three execution modes: `NOOP` (0 source AST parses on unchanged repo), `INCREMENTAL` (parses only added/modified files and reuses manifest AST for unchanged files), and `FULL` (deterministic rebuild on corruption, schema mismatch, or user request).
  - Manifest Schema 2.0 / Parser 1.0.0 with per-file cryptographic fingerprints, atomic persistence (`.tmp` + `os.fsync` + rename), and rename detection with conservative fallback.
  - Multi-tier change detection: Git-aware fast-path (`git status --porcelain=v1`) with authoritative filesystem fallback (mtime + size + SHA-256).
  - Fine-grained provenance-based `ContextCacheEngine` invalidation (`referenced_files`, `referenced_symbols`) selectively purging impacted context packages while preserving unaffected entries.
  - Strict Memory & Security truth boundary preservation: updates Cognee memory at the architectural outline level without unsupported per-file mutation claims; full workspace authorization and symlink containment.
  - 27 dedicated automated test cases passing across 7 test files (`test_incremental_manifest.py`, `test_incremental_ast_updates.py`, `test_incremental_cache_invalidation.py`, `test_incremental_failure_recovery.py`, `test_incremental_security.py`, `test_incremental_semantic_memory.py`, `test_incremental_performance.py`).
  - Empirical 23.6x speedup on unchanged repos (< 1ms) and 7.9x speedup on single-file modifications.
  - Authoritative Phase 10A audit documentation (`docs/architecture/phase-10a-audit.md`) and user guide (`docs/product/incremental-indexing.md`).
- [x] **Phase 10B: Improved TS/JS/JSX Structural Analysis (COMPLETED & FROZEN)**
  - Replaced regex heuristics with native Tree-sitter concrete syntax tree (CST) parser across TypeScript, TSX, and JavaScript dialects.
  - Full symbol extraction: top-level & async functions, arrow functions, classes, constructors, methods, interfaces, type aliases, enums, namespaces, and JSX component render usages.
  - Deterministic module resolution (`TSModuleResolver`): relative imports (`./`, `../`), comment-tolerant `tsconfig.json`/`jsconfig.json` `compilerOptions.baseUrl` + `compilerOptions.paths` wildcard mapping (`@/*` -> `src/*`), extension probing (`.ts`, `.tsx`, `.d.ts`, `.js`, `.jsx`, `/index.ts`), and external package classification.
  - Cross-file symbol and call graph linking (`TSCrossFileLinker`): resolves imported symbols, recursive re-export barrel chains (up to depth 5 with cycle protection), namespace calls (`API.fetchUser`), and JSX renders into canonical `CallNode` and `CallEdge` graphs.
  - Incremental Indexing integration: bumped `PARSER_VERSION = "2.0.0"` in Manifest Schema 2.0; automatic clean rebuild for parser 1.0.0 manifests and instant 0-parse AST reuse for unchanged TypeScript/JavaScript files.
  - 31 dedicated automated test cases passing across 8 test suites (`test_ts_js_parser.py`, `test_ts_js_import_resolution.py`, `test_ts_js_cross_file_graph.py`, `test_ts_js_incremental.py`, `test_ts_js_compatibility.py`, `test_ts_js_security.py`, `test_ts_js_performance.py`, `test_ast_integrity.py`).
  - Full regression validation: 566/566 backend pytest tests passing, `npm run build` passing with 0 errors, and 50/50 Vitest tests passing.
  - Authoritative Phase 10B audit documentation (`docs/architecture/phase-10b-audit.md`) and user guide (`docs/product/typescript-structural-analysis.md`).
- [x] **Phase 10C: Expanded Retrieval Benchmarking (COMPLETED & FROZEN)**
  - Multi-repository synthetic benchmark corpus across 6 neutral fixtures (`py_backend`, `ts_react`, `ts_barrel`, `polyglot`, `ts_alias`, `monorepo`) with strict domain neutrality guard (zero commercial/billing/auth terms).
  - 36 deterministic golden retrieval tasks across 12 distinct categories (3 tasks each) with exact ground-truth expected files, critical evidence, expected symbols, AST relationships, and noise negative assertions.
  - Multi-dimensional evaluator (`ExpandedBenchmarkEvaluator`, `app.evaluation.expanded_benchmark`) computing Precision@K (0.5977), Recall@K (0.9907), Critical Evidence Coverage (1.0000), Noise Ratio (0.1750), Relationship Coverage (0.9722), and Latency (2.99ms).
  - Comprehensive incremental mutation evaluator (`IncrementalMutationEvaluator`) validating 7 mutation scenarios against isolated temp copies (`cold_initial_index`, `warm_noop_reindex`, `single_file_modification`, `single_file_addition`, `single_file_deletion`, `rename_without_edit`, `dependency_relink`).
  - Strict immutability guarantee for Phase 7/9D frozen baseline assets verified via automated bitwise SHA-256 integrity tests.
  - 7 dedicated automated test cases passing across 4 new test suites (`test_expanded_benchmark.py`, `test_expanded_benchmark_contract.py`, `test_expanded_benchmark_incremental.py`, `test_expanded_benchmark_reproducibility.py`).
  - Deterministic evaluation artifacts generated: `benchmarks/expanded/benchmark_results.json` and `benchmarks/expanded/benchmark_scorecard.md`.
  - Authoritative Phase 10C audit documentation (`docs/architecture/phase-10c-audit.md`) and user guide (`docs/product/expanded-retrieval-benchmarking.md`).
- [x] **Phase 10D.1: Frontend ↔ Backend Integration, Provider Discovery, and Secure Configuration (COMPLETED & FROZEN)**
  - Authoritative provider detection eliminating port-based heuristics in frontend (`GET /provider/status` returning `ollama`, `lmstudio`, `openai_compatible`).
  - Non-mutating model discovery engine (`POST /provider/discover`, `discover_provider`) probing candidate endpoints without state side-effects; distinct truthful handling of `available`, `reachable_but_empty`, `unreachable`, `discovery_failed`, and `not_configured` states.
  - Atomic configuration persistence with POSIX security (`~/.retrack/settings.json` enforcing `0600` file / `0700` dir permissions; hot-reload synchronization with environment variables).
  - Secure secret handling: absolute elimination of plain secrets from `localStorage`, logs, and diagnostics; masked token telemetry (`api_key_masked`, `api_key_configured`).
  - Clean hexagonal architecture alignment: `SystemUseCases` adheres strictly to `LLMProviderPort` protocol without concrete service dependencies.
  - 100% test validation: 7 new dedicated tests in `test_provider_configuration.py`, 37 API tests, 18 architectural boundary tests, 51/51 Vitest frontend tests, and clean Vite/TypeScript production build.
  - Authoritative Phase 10D.1 audit documentation (`docs/architecture/phase-10d1-audit.md`) and user guide (`docs/product/provider-configuration.md`).
- [x] **Phase 10D.1.1: Runtime Engine State Reconciliation (COMPLETED & FROZEN)**
  - Unified authoritative runtime engine state contract (`engine_state`, `engine_reason`, `provider_identity`, `provider_reachable`, `provider_health_state`, `active_model`, `configured_model`, `cognee_state`, `cognee_reason`) across `GET /health` and `GET /status`.
  - Solved environment variable overwrite bug where default Ollama endpoints overrode persisted LM Studio settings on restart.
  - Fixed hardcoded Ollama connection validation in Cognee initialization via generalized `validate_provider()` and decoupled inference engine health from Cognee memory initialization.
  - Truth boundary guarantees: removed synthetic `"phi4-mini"` fallback; active model is populated only when authoritatively confirmed by backend.
  - Universal frontend runtime state alignment: updated `useHealthStore` with `Promise.allSettled` resilience; synchronized `TopBar`, `Sidebar`, `ProviderAlertBanner`, `Repositories`, and `Memory` to consume unified backend runtime state.
  - Authoritative Phase 10D.1.1 audit documentation (`docs/architecture/phase-10d1-runtime-reconciliation-audit.md`).
- [x] **Phase 10D.2: Context Generation Runtime Verification & Model Invocation (COMPLETED & FROZEN)**
  - Eliminates silent local heuristics fallback swallows in `IntentParserService`; emits structured observability events (`context_model_invocation_started`, `context_model_invocation_completed`, `context_model_invocation_failed`, `context_deterministic_fallback`).
  - Strict provider invocation: `LLMProviderService.generate_completion()` strictly targets configured OpenAI-compatible / LM Studio / Ollama `/v1/chat/completions` endpoints with configured model names and explicit error classifications.
  - Truthful telemetry contracts across `ParsedIntentRecord`, `AgentContextResponse`, `ContextResponse`, and MCP `get_agent_context_tool` (`model_invoked`, `provider_identity`, `model_name`, `inference_status`, `fallback_used`, `fallback_reason`, `inference_time_ms`).
  - Frontend truth alignment: `ContextStudio.tsx` and context-builder panels truthfully display `Model Synthesized` (green) only on completed provider invocations, and `Deterministic Fallback` (amber) with notice tooltip when local AST heuristics are used.
  - 10 new dedicated automated test cases across `test_context_model_invocation.py` and `test_context_model_contract.py`.
  - Authoritative Phase 10D.2 audit documentation (`docs/architecture/phase-10d2-context-generation-audit.md`) and product specification (`docs/product/context-generation.md`).
- [x] **Phase 10D.3: Grounded Context Generation, Evidence Gating & Abstention (COMPLETED & FROZEN)**
  - Authoritative **Deterministic Evidence Assessment & Gating Engine** (`EvidenceService`, `EvidenceRecord`, `EvidenceState`) enforcing multi-dimensional scoring (symbols: 0.35, code snippets: 0.30, files: 0.20, AST edges: 0.10, framework context: 0.05 background only).
  - Strict separation of **task intent** (prompt vocabulary) from **observed repository evidence** (deterministic indexed data).
  - Hard negative gate: when a requested subsystem (e.g. JWT authentication, billing, celery workers) has no supporting repository evidence, the engine bypasses model inference and returns a deterministic **Abstention Package** (`# Task Intent`, `# Observed Repository Evidence`, `# Missing Evidence`, `# Suggested Next Action`).
  - Strict abstention invariant: `abstained=true => model_invoked=false, model_claims_allowed=false`.
  - Post-generation grounding validation: automatic stripping of `<think>...</think>` and `[THINKING]` reasoning blocks; validation of referenced symbols and files against indexed repository.
  - Telemetry and DTO synchronization across REST API (`AgentContextResponse`, `ContextResponse`), FastMCP (`get_agent_context_tool`), and TypeScript interfaces (`src/lib/api.ts`).
  - Frontend truth alignment in `ContextStudio.tsx`, `ContextPipelineVisualization.tsx`, and `ContextPackageOutputPanel.tsx` with dedicated badges (`Insufficient Repository Evidence`, `Partial Evidence`, `Model Synthesized`) and structured missing-evidence callouts.
  - 13 new dedicated automated tests across `test_context_evidence_gate.py`, `test_context_grounding.py`, and `test_context_evidence_contract.py` verifying critical Django negative case and positive grounded cases.
  - Authoritative Phase 10D.3 audit documentation (`docs/architecture/phase-10d3-grounded-context-audit.md`) and user guide (`docs/product/grounded-context-generation.md`).
- [x] **Phase 10D.4: Database & Memory Integration — Truth Alignment (COMPLETED & FROZEN)**
  - Established strict **Truth Hierarchy & Authority Precedence**: Level 1 (Filesystem Source) > Level 2 (Manifest 2.0 + Deterministic AST) > Level 3 (Derived LanceDB / Kùzu Projections) > Level 4 (Cognee Semantic Memory) > Level 5 (LLM Synthesis).
  - Derived memory subordination: derived memory records may never create repository truth, invent missing nodes, or repair absent source evidence.
  - Implemented `MemoryProvenance` contract with SHA-256 fingerprint validation; stale provenance from edited/deleted files is pruned and excluded from `EvidenceService`.
  - Strict storage failure resilience: LanceDB, Kùzu, or Cognee unavailability gracefully degrades vector/semantic features while deterministic AST retrieval remains 100% operational.
  - 8 dedicated automated test cases in `test_memory_truth_alignment.py` verifying fresh provenance, stale invalidation, deletion pruning, cross-repo isolation, symbol absence, and storage outage resilience.
  - Authoritative Phase 10D.4 audit documentation (`docs/architecture/phase-10d4-audit.md`) and product guide (`docs/product/database-memory-integration.md`).
- [x] **Phase 10D.5: End-to-End Retrieval Arbitration (COMPLETED & FROZEN)**
  - Implemented authoritative **End-to-End Retrieval Arbitration Pipeline** (`RetrievalArbitrator`, `app.services.retrieval_arbitrator`) establishing authority-first evidence selection prior to `EvidenceService` gating and LLM synthesis.
  - Strict 4-tier lexicographic ordering: Tier 1 (`filesystem_verified_source`) > Tier 2 (`manifest_ast`) > Tier 3 (`validated_lancedb_kuzu`) > Tier 4 (`validated_cognee`).
  - Lexicographic sort key: `(TierPriority, Relevance, Confidence, Specificity)` ensuring that authoritative source and AST evidence unconditionally outrank semantic similarity.
  - Hard token budget guarantees: Authoritative Tier 1/2 evidence is reserved; subordinate Tier 3/4 candidates only fill residual budget and can never evict or displace higher-tier candidates.
  - 7 new adversarial test cases passing in `test_retrieval_arbitration.py` covering stale rejection, lexicographic tier precedence, path-only non-sufficiency, LLM output isolation, budget reservation, cross-repo rejection, and Django abstention contract.
  - Authoritative Phase 10D.5 audit documentation (`docs/architecture/phase-10d5-audit.md`), design spec (`docs/architecture/phase-10d5-design.md`), and user guide (`docs/product/retrieval-arbitration.md`).
- [ ] **Phase 10D: Adaptive Query-Aware Retrieval** (Task-type-specific token allocation profiles).
- [ ] **Phase 10E: Agent Workflow Optimization** (Multi-turn conversational context caching).


### Deferred Capabilities (Postponed Until Specific Demand)

- **HTTP / Streamable MCP Transport**: Postponed (local stdio remains the primary standard for Claude and Cursor).
- **Remote Git Repository Ingestion**: Postponed (local-first workstation scope prioritized).
- **Cloud Multi-Tenancy**: Excluded by design (privacy-first local execution).
- **Distributed Task Workers (Celery/Redis)**: Excluded by design (8GB RAM single-node target).

---

## 2. Quality & Verification Metrics

- **Backend Pytest Suite:** 593/593 passing unit/integration/soak tests across 40 test files (`backend/tests/`).
- **Frontend Vitest Suite:** 51/51 passing behavioral tests across 12 test suites (`src/test/journeys/`).
- **AST Integrity:** 100% passing multi-language AST syntax and symbol resolution tests (`tests/test_ast_integrity.py`).
- **Frontend Build & Types:** 100% clean TypeScript compile and Vite production build (`npm run build`).
- **Design System:** Vercel Geist aesthetic with dark mode canvas (`#000000`), micro-animations (`motion/react`), and high-contrast typography.
- **Protocol Compliance:** 100% clean JSON-RPC framing on stdio; 0 unhandled exception leaks across MCP tools.
- **Production Status:** **PRODUCTION GRADE** certified.
