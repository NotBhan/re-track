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

---

## 2. Quality & Verification Metrics

- **Backend Pytest Suite:** 428 passing unit/integration/soak tests across 33 test files (`backend/tests/`).
- **AST Integrity:** 100% passing multi-language AST syntax and symbol resolution tests (`tests/test_ast_integrity.py`).
- **Frontend Build & Types:** 100% clean TypeScript compile and Vite production build (`npm run build`).
- **Design System:** Vercel Geist aesthetic with dark mode canvas (`#000000`), micro-animations (`motion/react`), and high-contrast typography.
- **Protocol Compliance:** 100% clean JSON-RPC framing on stdio; 0 unhandled exception leaks across MCP tools.


