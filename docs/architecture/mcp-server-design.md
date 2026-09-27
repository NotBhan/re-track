# MCP Server — Current Design, Contracts & Phase 8 Reconciliation

## Executive Summary

RE:Track exposes repository memory, deterministic AST call graphs, architectural
summaries, and evidence-grounded context packages to external AI coding agents through
the Model Context Protocol (MCP) over **stdio**.

The server is an **Inbound (Driving) Adapter** under `backend/app/mcp/` built on the
official MCP Python SDK (`mcp >= 2.0.0`, `mcp.server.MCPServer`). It delegates every
operation to Application Use Cases; it never touches databases, vector/graph engines,
provider internals, or the filesystem directly.

This document replaces the Phase 8A design draft. Where the draft and the current
implementation diverged, the current implementation is authoritative; a correction
list is kept at the end for traceability.

---

## 1. Architecture

```
External AI Coding Agent (Claude Code, Cursor, …)
                     │
                     ▼ (stdio / JSON-RPC)
       ┌───────────────────────────────┐
       │     backend/app/mcp/          │  <-- Inbound Driving Adapter
       │  server.py / tools.py         │      (MCPServer, tool schemas)
       └──────────────┬────────────────┘
                      │ (DTOs)
                      ▼
       ┌───────────────────────────────┐
       │  backend/app/application/     │  <-- Application layer
       │    ├── use_cases/             │      (ContextUseCases,
       │    ├── domain/                │       RepositoryUseCases,
       │    └── container.py           │       IndexingUseCases)
       └──────────────┬────────────────┘
                      │ (capability ports)
                      ▼
       ┌───────────────────────────────┐
       │   backend/app/services/       │  <-- Outbound driven adapters
       │  (SummaryGen, SourceSearch,   │
       │   WorkspaceAuth, Cognee, …)   │
       └───────────────────────────────┘
```

Boundary invariants enforced by tests:

- `app/mcp/**` imports only the application container, DTOs/domain models, and the MCP
  SDK — no Cognee, LanceDB, Kùzu, SQLAlchemy, or concrete service imports.
- No tool reads provider singletons, FastAPI request state, or interface-layer state.
- Every tool result is built from a use-case DTO; nothing is synthesized in the adapter.

## 2. Tool Surface (5 tools)

| Tool | Application use case | Deterministic? | Filesystem access | LLM inference |
| :--- | :--- | :--- | :--- | :--- |
| `get_agent_context` | `ContextUseCases.get_agent_context` | Evidence retrieval is deterministic; synthesis, when configured, is model-backed | Reads repo source (contained) | Only when an interactive provider is configured and evidence passes the gate |
| `get_repository_summary` | `RepositoryUseCases.get_repository_summary` | Yes | Live filesystem/AST scan | No |
| `get_ast_call_graph` | `RepositoryUseCases.get_ast_call_graph` | Yes | Live filesystem/AST scan | No |
| `search_repository_code` | `ContextUseCases.search_repository_code` | Yes | Reads repo source (contained) | No |
| `list_indexed_repositories` | `RepositoryUseCases.list_repositories` | Yes | Reads the persisted registry | No |

Argument caps applied in the adapter: `max_tokens` ∈ [100, 32000], `max_nodes` ∈ [1, 500],
`limit` ∈ [1, 50]. `dataset_name` is a logical alias: the effective memory namespace is
always `{sanitized_alias_or_dirname}_{sha256(canonical_path)[:10]}`.

### 2.1 Response contract

Every tool returns one JSON object with an authoritative `success` field. Failures add
`error` (stable category: `ValidationError`, `AuthorizationError`, `BusyError`,
`TimeoutError`, `CogneeServiceError`, `InternalError`, …) and a sanitized `message`.
No stack traces, secrets, or partial data are returned on failure.

`get_agent_context` additionally reports evidence and inference truthfully:

- `evidence_state` ∈ `sufficient | partial | insufficient | none`
- `evidence_files`, `evidence_symbols`, `evidence_relationships`, `observed_evidence`,
  `missing_evidence`
- `abstained` + `abstention_reason` + `model_claims_allowed=false` when evidence is
  insufficient; the markdown is then an abstention package, not a synthesized answer
- `model_invoked`, `provider_identity`, `model_name`, `inference_status`,
  `fallback_used`, `fallback_reason`, `inference_time_ms`
- `compaction` — requested budget, evidence allowance, pre/post token counts, and which
  evidence was reduced or omitted

### 2.2 Truth hierarchy

1. Filesystem source truth
2. Manifest + deterministic AST/CST
3. LanceDB/Kùzu derived data
4. Cognee semantic memory
5. LLM synthesis

MCP never lets a lower tier override a higher one: semantic/vector recall enters the
arbitration as lower-authority candidates, and model synthesis runs only on
evidence that passed the gate. When retrieval tiers are unavailable, the response
reports reduced evidence instead of filling gaps.

## 3. Request Flow (`get_agent_context`)

```
MCP tool → validate + authorize path → ContextUseCases.get_agent_context
  → acquire bounded concurrency slot
  → resolve canonical path, derive collision-proof dataset name
  → cache lookup (repo + manifest fingerprint + task + budget)
  → intent (provider-backed, or deterministic heuristics; failure degrades honestly)
  → repo discovery/filter → summary + AST call graph
  → structure (CGC in-process when available)
  → retrieval: source snippets (Tier 1) + AST (Tier 2) + LanceDB/Kùzu (Tier 3)
               + Cognee semantic memory (Tier 4) → RetrievalArbitrator
  → EvidenceService gate → abstain when insufficient
  → budget-aware compaction (prompt overhead + output reservation reserved first)
  → optional grounded synthesis; evidence is re-packed around the answer
  → sanitize + measure against budget → AgentContextResponse
  → release slot (success, failure, timeout, or cancellation)
```

## 4. Lifecycle & Runtime

### 4.1 Startup
- Entry points: `retrack-mcp`, `retrack mcp`, `python -m app.mcp`,
  `python backend/mcp_server.py`.
- `run_mcp_stdio()` configures stderr logging, then initializes the
  `ApplicationContainer` **before** the stdio transport opens, so service-backed tools
  (`get_agent_context`) reach the real pipeline. This initialization step regressed
  silently at commit `6363b79` and was restored; `test_mcp_production_contract.py`
  guards it.
- Initialization imports the memory engine (measured ~4.5 s in this environment),
  so the first handshake can take several seconds.
- A failed initialization is not fatal: the server starts, deterministic tools keep
  working, and `get_agent_context` returns a structured error rather than fabricated
  context.
- `sys.stdout` carries protocol frames only. During initialization even third-party
  stdout output is redirected to stderr.

### 4.2 Serving
- All tool handlers are `async`.
- Read-only tools execute concurrently under the event loop with bounded offload
  threads for CPU/IO work (`retrack-offload`, 2 workers).
- Context generation is serialized by the process-scoped `BoundedConcurrencyGuard`.

### 4.3 Shutdown
- `stdin` EOF: the stdio transport ends, then `ApplicationContainer.shutdown()`
  releases memory-engine handles (LanceDB/Kùzu), shuts down the offload executor, and
  purges environment variables the app applied.
- `SIGINT`: handled gracefully (exit code 0).
- `SIGTERM`: OS default termination.
- No zombie processes, orphaned threads, or leaked descriptors across repeated
  start/stop cycles.

## 5. Security Boundary

1. **Workspace authorization** (before any sensitive filesystem operation):
   - Authorized = registered in the metadata store OR under a
     `RETRACK_WORKSPACE_ROOTS` root (`:`-separated on POSIX, `;` on Windows).
   - Paths are canonicalized with `Path.resolve()`; `..` traversal and symlinks that
     escape an authorized root are rejected.
   - Root filesystems (`/`, `C:\`) and sensitive directories (`/etc`, `/proc`,
     `/sys`, `/dev`, `/run`, `/boot`, `/root`, `/var`, `~/.ssh`, `~/.gnupg`) are
     rejected.
   - Inspection happens before existence/dir checks at the tool boundary and again
     inside the use cases (defense in depth).
   - If the authorization port is unavailable the tools fail closed.
2. **Source containment**: file discovery prunes external symlinks and ignored
   directories; search and snippet extraction re-verify containment at read time, so a
   file swapped for an escaping symlink after discovery cannot leak content.
3. **Dataset isolation**: retrieval namespaces are derived from the canonical path
   hash (see §2), matching the indexing derivation, so repositories with identical
   basenames cannot read each other's memory.
4. **Caps**: token budgets, node counts, and result limits are clamped to bound
   payload size.

## 6. Concurrency

`BoundedConcurrencyGuard` (`max_concurrent=1`, `max_queue=5`, `timeout=30.0 s`) is
owned by the composition root and shared by every `ContextUseCases` instance.

- Waiting requests queue up to 5; overflow returns retryable `BusyError`.
- Waiting longer than 30 s returns `TimeoutError`.
- There is no suspension point between a successful slot acquisition and the success
  return, so cancellation (queued or in-flight, e.g. client disconnect) can never
  strand the slot; the in-flight caller releases it in its own `finally`.
- Read-only tools do not consume the context slot.

## 7. Testing & Verification

| Area | Test file(s) |
| :--- | :--- |
| Tool registration/schema, boundary purity, JSON-RPC over memory streams | `tests/test_mcp_adapter.py` |
| Authorization boundary, truthfulness, real stdio protocol/resources, initialized context regression | `tests/test_mcp_production_contract.py` |
| Guard semantics (queue, timeout, cancellation) | `tests/test_mcp_concurrency_hardening.py`, `tests/test_mcp_concurrency_lifecycle.py` |
| Exception isolation and sanitization | `tests/test_mcp_exception_isolation.py` |
| stdout framing integrity (real subprocess) | `tests/test_mcp_logging_integrity.py` |
| Provider failure and same-process recovery | `tests/test_mcp_provider_recovery.py` |
| EOF/SIGINT/SIGTERM lifecycle (real subprocess) | `tests/test_mcp_stdio_shutdown.py`, `tests/test_phase_8d_lifecycle.py` |
| Official-client interoperability, entry points, reconnect cycles | `tests/test_phase_8d_deployment.py`, `tests/test_phase_8d_interoperability.py`, `tests/test_phase_8e_mcp_interoperability.py`, `tests/test_phase_8e_clean_deployment.py` |
| Packaging/entry-point integrity | `tests/test_packaging_validation.py` |
| Workspace authorization service, dataset identity | `tests/test_workspace_authorization.py`, `tests/test_dataset_identity_isolation.py` |

```bash
cd backend && uv run pytest tests/test_mcp_adapter.py tests/test_mcp_production_contract.py \
  tests/test_mcp_concurrency_hardening.py tests/test_mcp_concurrency_lifecycle.py \
  tests/test_mcp_exception_isolation.py tests/test_mcp_logging_integrity.py \
  tests/test_mcp_provider_recovery.py tests/test_mcp_stdio_shutdown.py -q
```

Current measurements (this environment, via `test_mcp_production_contract.py`):

- Deterministic tool round-trip over real stdio: p50 ≈ 3.5 ms, p95 ≈ 3.8 ms
- Container initialization: ≈ 4.5 s (memory-engine import dominates)
- `get_agent_context` on a 2-file repository with an unreachable provider: ≈ 12 s
  (honest abstention/fallback path)

## 8. ADR-015: MCP Server Inbound Driving Adapter

- **Status**: Accepted / implemented (Phase 8A), reconciled with the current
  application contracts.
- **Decision**: Implement MCP as a pure inbound adapter under `backend/app/mcp/`
  consuming `ApplicationContainer` use cases. Prohibit direct infrastructure access
  and subprocess spawning from the adapter.
- **Consequences**: full protocol compatibility with standard MCP clients; no
  duplicated retrieval/context logic; adds the `mcp` dependency.

## 9. Phase 8A Draft Corrections (traceability)

The following draft claims were stale and have been corrected in this document and/or
the implementation:

- “FastMCP” — the installed official SDK is `mcp 2.0.0`, whose server class is
  `MCPServer`; the dependency floor was raised from `mcp>=1.0.0` to `mcp>=2.0.0`.
- “stdio/SSE” — only stdio is wired.
- Container initialization was documented but missing from the code (regression at
  `6363b79`); it was restored.
- “SIGINT/SIGTERM handlers are registered” — precise behavior is documented in §4.3.
- “`C:\Windows` blocked” — the actual guard is canonical-path containment plus the
  forbidden-directory set in §5.
- Errors surfaced as “JSON-RPC error responses” — tool failures are structured result
  payloads (`success:false`); only protocol-level rejections (unknown tool, invalid
  argument type) surface as MCP `isError` results.
- `get_repository_summary` is backed by `RepositoryUseCases.get_repository_summary`,
  not `IndexingUseCases`.
- Latency figures in the draft were historical estimates; current measurements are in
  §7 and are reproduced by the test suite.
