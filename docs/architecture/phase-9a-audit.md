# Phase 9A — Product Truth, Capability Contract & Release Baseline Audit

**Date**: 2026-08-22  
**Auditor**: Product Architect, Principal Engineer & Release Owner  
**Target Scope**: RE:Track Core Engine, MCP Server, Frontend Dashboard, Storage Subsystem, Test Suites, and Release Metadata  
**Milestone Verdict**: **Phase 9A COMPLETE**

---

## 1. Executive Summary

Phase 9A establishes the single authoritative product capability contract and release readiness baseline for RE:Track. Following the completion of the Phase 8E production readiness gate, this audit reconciles all legacy claims, enforces precision in technical documentation, eliminates unsupported marketing generalizations, and defines the explicit execution plan for Phase 9 (Productization) and Phase 10 (Intelligence Evolution).

---

## 2. Claim vs. Evidence Reconciliation Table

| Historical Claim | Concrete Repository Evidence | Confidence Level | Truth Reconciliation / Correction Applied |
| :--- | :--- | :--- | :--- |
| *"RE:Track provides 24/7 unattended reliability"* | Verified across 3,000 soak operations (`tests/test_phase_8e_long_duration_soak.py`) and 500 churn cycles (`tests/test_phase_8e_resource_stability.py`). | **High (Empirically Bounded)** | **Corrected**: Claim is bounded to verified soak limits (3,000 ops, flat RSS slope, 0 leaked FDs/threads). Unconditional 24/7 claims are prohibited. |
| *"Sub-millisecond latency across all operations"* | Deterministic AST/Search cache hits measure 0.5ms–3.0ms; cold AST extraction measures 30ms–100ms; context synthesis with live Cognee recall measures 150ms–450ms. | **High** | **Corrected**: Explicitly separated cold vs. warm latency and deterministic tools vs. external LLM-dependent context synthesis. |
| *"Universal multi-language AST extraction"* | Python AST extraction uses native Python `ast` module (`RepositorySummaryGenerator._extract_python_symbols`); TypeScript/JS uses regex/heuristic parsing. | **High** | **Corrected**: Marked Python AST as Full-Fidelity Production, and TS/JS/JSX as Production with Limitations. Tree-sitter WASM planned for Phase 10B. |
| *"~/.andes/ is the canonical storage directory"* | `app/config/settings.py` and all repositories define `~/.retrack/` as canonical writable storage and `~/.andes/` as read-only legacy compatibility fallback. | **High** | **Corrected**: Updated all documentation and docstrings to reflect `~/.retrack/` as canonical and `~/.andes/` as legacy fallback. |
| *"Frontend compilation proves production readiness"* | Frontend compiles cleanly with `npm run build` (0 TypeScript errors), but lacks automated E2E component interaction tests. | **Moderate** | **Corrected**: Frontend classified as Production for manual workflows, but flagged with P1 gap (E2E testing) scheduled for Phase 9E. |

---

## 3. User-Facing Features vs. Internal Mechanisms Classification

| Component | Nature | Primary Role | User / Agent Exposure |
| :--- | :--- | :--- | :--- |
| **`get_agent_context`** | Product Feature | High-precision Markdown context synthesis | Standard MCP Tool |
| **`get_repository_summary`** | Product Feature | High-level architectural and tech stack discovery | Standard MCP Tool |
| **`get_ast_call_graph`** | Product Feature | Deterministic caller/callee directed graph query | Standard MCP Tool |
| **`search_repository_code`** | Product Feature | Symbol, function, and keyword code search | Standard MCP Tool |
| **`list_indexed_repositories`** | Product Feature | Registered repository discovery | Standard MCP Tool |
| **Context Studio** | Product Feature | Visual prompt crafting and context preview workbench | Desktop UI (`/studio`) |
| **Knowledge Explorer** | Product Feature | Interactive force-directed SVG topology visualization | Desktop UI (`/knowledge/:id`) |
| **Repositories Dashboard** | Product Feature | Local repository registration, file scan, quick context | Desktop UI (`/`) |
| **CLI Commands (`retrack`)** | Product Feature | Headless indexing, status, context generation, MCP server | Terminal Executable |
| **`BoundedConcurrencyGuard`** | Internal Safeguard | Shared process-scoped queueing to prevent OOM | Internal Operational Component |
| **`WorkspaceAuthorizationService`**| Internal Safeguard | Path sandboxing and symlink escape pruning | Internal Security Boundary |
| **`derive_dataset_name`** | Internal Safeguard | Collision-proof SHA-256 dataset isolation | Internal Utility |
| **`ContextCacheEngine`** | Internal Engine | Fingerprint hashing and mtime cache invalidation | Internal Performance Component |
| **`JsonRepositoryMetadataStore`**| Internal Storage | Dual-path canonical/legacy JSON persistence | Internal Storage Component |
| **`LocalHardwareTelemetryAdapter`**| Internal Telemetry | System CPU, RAM, and VRAM monitoring | Internal Port Adapter |

---

## 4. Current Capability vs. Release Blocker vs. Roadmap Phase

| Current Capability | Production Blocker / Gap | Proposed Roadmap Phase |
| :--- | :--- | :--- |
| Standalone git repo running via `uv run` | Missing standard PyPI / wheel package and 1-line installer | **Phase 9B** (Packaging & Installation) |
| Manual folder setup for `~/.retrack/` | Missing first-run bootstrap wizard and data reset CLI | **Phase 9B** (Bootstrap & Reset) |
| Terminal-based stderr logging | Missing structured log file rotation and in-app diagnostics | **Phase 9C** (Observability & Diagnostics) |
| Local developer pytest/build execution | Missing multi-platform GitHub Actions CI matrix | **Phase 9D** (CI Automation & Releases) |
| TypeScript build validation | Missing automated component E2E / visual regression tests | **Phase 9E** (Frontend UX Hardening) |
| Full-repository re-scan on file edits | Scalability bottleneck on >10,000 file repositories | **Phase 10A** (Incremental Git Indexing) |
| Heuristic TS/JS/JSX AST parsing | Missing cross-file type resolution in complex React/Node apps | **Phase 10B** (Tree-sitter WASM AST) |

---

## 5. Phase 9A Completion Sign-Off

All required audit goals for Phase 9A have been achieved:
1. Canonical feature inventory created at [`docs/product/feature-inventory.md`](file:///home/chandrabhan/Documents/Personal%20Projects/re-track/docs/product/feature-inventory.md).
2. Authoritative capability matrix created at [`docs/product/capability-matrix.md`](file:///home/chandrabhan/Documents/Personal%20Projects/re-track/docs/product/capability-matrix.md).
3. Release readiness assessment created at [`docs/product/release-readiness.md`](file:///home/chandrabhan/Documents/Personal%20Projects/re-track/docs/product/release-readiness.md).
4. Dual-path storage contract references verified and reconciled across code and documentation.
5. Latency, AST depth, and provider-dependency claims accurately qualified.

Phase 9A is hereby certified **COMPLETE**.
