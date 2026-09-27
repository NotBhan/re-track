# RE:Track MCP Server Configuration & Usage Guide

## Overview

RE:Track exposes its repository memory, deterministic AST call graphs, architectural
summaries, and evidence-grounded context packages to external AI coding agents through
the standard **Model Context Protocol (MCP)** over `stdio`.

The server is implemented on the official MCP Python SDK (`mcp >= 2.0.0`,
`mcp.server.MCPServer`) as an inbound adapter: every tool delegates to RE:Track
application use cases. No tool reaches into Cognee/LanceDB/Kùzu, provider internals,
or the filesystem directly.

---

## 1. Running the MCP Server

The RE:Track MCP server can be launched using any of the following standard mechanisms:

### Using the Dedicated Console Script (Recommended after `pip install retrack-ai`):
```bash
retrack-mcp
```

### Using the RE:Track CLI:
```bash
retrack mcp
```

### Running the Python Module directly:
```bash
python -m app.mcp
```

### Running the Launcher Script:
```bash
python backend/mcp_server.py
```

### Running with `uv`:
```bash
cd backend && uv run python -m app.mcp
```

At startup the server initializes the application container (settings, provider
clients, memory/indexing/context services) before opening the stdio transport, so
`get_agent_context` can reach the full context pipeline. Initialization imports the
memory engine, which takes several seconds on the first run of a machine. If
initialization fails, the server still starts: deterministic tools continue to work
and `get_agent_context` reports the failure honestly instead of fabricating context.

---

## 2. Configuring External AI Coding Clients

### Claude Desktop / Claude Code (Standard Package Install)
```json
{
  "mcpServers": {
    "retrack": {
      "command": "retrack-mcp",
      "args": [],
      "env": {
        "RETRACK_WORKSPACE_ROOTS": "/path/to/your/projects"
      }
    }
  }
}
```

### Claude Desktop / Claude Code (Developer UV Run)
Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "retrack": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/re-track/backend",
        "python",
        "-m",
        "app.mcp"
      ]
    }
  }
}
```

### Cursor
Add to your project's `.cursor/mcp.json` or Cursor Settings -> Features -> MCP:

```json
{
  "mcpServers": {
    "retrack": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/re-track/backend",
        "python",
        "-m",
        "app.mcp"
      ]
    }
  }
}
```

---

## 3. Available MCP Tools

Every tool returns a single JSON object. `success` is the authoritative outcome field.
Failures carry `error` (stable category) and `message` (human-readable, sanitized);
there is no partial or fabricated data on failure.

| Tool Name | Arguments | Description |
| :--- | :--- | :--- |
| `get_agent_context` | `task_prompt` (str, required)<br>`repository_path` (str, required)<br>`max_tokens` (int, default: 8000, clamped 100–32000)<br>`dataset_name` (str, optional, logical alias)<br>`include_structural_graph` (bool, default: true) | Synthesizes a token-budgeted, evidence-grounded Context Package: source evidence, AST symbols, caller/callee relationships, provenance, evidence state, inference/fallback telemetry, and compaction accounting. May abstain when repository evidence is insufficient. |
| `get_repository_summary` | `repository_path` (str, required) | Live structural summary of an authorized repository: purpose, tech stack, frameworks, architecture pattern/layers, key components, entry points, public APIs, coding conventions, file count, call-graph status. |
| `get_ast_call_graph` | `repository_path` (str, required)<br>`file_filter` (str, optional)<br>`max_nodes` (int, default: 150, clamped 1–500) | Deterministic AST call graph: real nodes (`id`, `label`, `file`, `kind`, `line`) and caller→callee edges. `call_graph_status` distinguishes `analyzed` / `zero_edges` / `not_analyzed` / `failed`. |
| `search_repository_code` | `repository_path` (str, required)<br>`query` (str, required)<br>`limit` (int, default: 10, clamped 1–50) | Ranked source search returning repository-relative paths with matched symbols and bounded snippets. Reads are confined to the repository root. |
| `list_indexed_repositories` | *None* | Repositories registered with this RE:Track installation: id, name, local path, branch, commit, status, languages, frameworks, file count, size, indexing timestamp, summary, architecture, components, call-graph state. |

### Reading `get_agent_context` results

The context tool reports what the pipeline actually established:

- `evidence_state`: `sufficient` | `partial` | `insufficient` | `none`
- `evidence_files`, `evidence_symbols`, `evidence_relationships`: verified provenance
- `missing_evidence`: explicit gaps; `observed_evidence`: observed repository facts
- `abstained` + `abstention_reason`: the pipeline refused to synthesize a confident
  answer because evidence was insufficient; `model_claims_allowed` is `false` and the
  returned markdown is an abstention package
- `model_invoked`, `provider_identity`, `model_name`, `inference_status`,
  `fallback_used`, `fallback_reason`, `inference_time_ms`: synthesis telemetry. When
  the configured provider is unavailable the request falls back to deterministic
  assembly (or abstains) and says so — it never presents fallback text as model output
- `compaction`: requested budget, evidence allowance, pre/post token counts and which
  evidence was reduced or omitted

Semantic memory, vector recall, and model synthesis never override source/AST
evidence. When semantic/procedural memory is unavailable the response reports reduced
evidence rather than inventing content.

---

## 4. Security Model & Trust Boundary

RE:Track implements strict defense-in-depth isolation between external MCP clients and
the host filesystem/memory:

### 1. Workspace Authorization
- External clients are restricted to **authorized repositories** only.
- A path is authorized if:
  1. It is explicitly registered in RE:Track's metadata store (indexed/imported via
     GUI, TUI, CLI, or API), OR
  2. It resides within a configured workspace root directory specified via the
     `RETRACK_WORKSPACE_ROOTS` environment variable (delimited by `:` on
     Linux/macOS or `;` on Windows).
- Root filesystem directories (`/`, `C:\`), sensitive system directories (`/etc`,
  `/proc`, `/sys`, `/dev`, `/run`, `/boot`, `/root`, `/var`), and credential stores
  (`~/.ssh`, `~/.gnupg`) are rejected.
- Paths are canonicalized (`Path.resolve()`) before the containment check, so
  symlinks that escape an authorized root and `..` traversal are rejected.
- The containment check is re-applied at file-read time, so a file swapped for an
  escaping symlink after discovery cannot leak content.
- If the workspace-authorization port is unavailable, tools fail closed.

### 2. Dataset Identity & Memory Isolation
- Context memory is partitioned using deterministic, collision-proof dataset
  identifiers: `{sanitized_name}_{sha256(canonical_path)[:10]}`.
- Indexing and MCP retrieval derive this identifier identically, so a repository
  always reads the memory produced for its own canonical path.
- A `dataset_name` alias is a *logical* label only: it is sanitized and still bound
  to the canonical path hash, so it cannot redirect retrieval to another
  repository's memory.
- Distinct repositories sharing identical directory basenames (e.g.
  `/client_a/service` and `/client_b/service`) are physically isolated.

### 3. Bounded Concurrency & Process-Scoped Queueing
- The context engine uses a process-scoped bounded concurrency queue
  (`max_concurrent=1`, `max_queue=5`, `timeout=30.0s`) owned by the composition root
  `ApplicationContainer` and shared by every `ContextUseCases` instance.
- All `get_agent_context` calls share the same execution slot.
- Requests arriving when the queue is saturated receive a retryable `BusyError`;
  requests that wait longer than 30s receive `TimeoutError`.
- A slot is always released on success, failure, cancellation, or client
  disconnect — including cancellation while queued.
- Read-only tools (`get_repository_summary`, `get_ast_call_graph`,
  `search_repository_code`, `list_indexed_repositories`) execute concurrently and do
  not consume the context slot.

### 4. Exception Isolation & Error Boundaries
- Tool handlers catch unexpected internal exceptions at the adapter boundary, log
  diagnostic details to stderr, and return structured, sanitized error responses
  without stack traces, secrets, or database connection strings.
- Protocol-level rejections (unknown tool name, invalid argument type) surface as
  MCP `isError` results; malformed JSON-RPC input is ignored without corrupting the
  stdout stream, and the process remains usable.

---

## 5. Operational Lifecycle & Reliability

### 1. Stdio Framing & Stderr-Only Logging
- All application and diagnostic logging (including Cognee, structlog, LiteLLM, and
  server startup diagnostics) writes strictly to `sys.stderr`.
- `sys.stdout` is reserved exclusively for clean, uncorrupted JSON-RPC protocol
  frames; even third-party output during container initialization is redirected to
  stderr before the transport opens.

### 2. Shutdown & Signals
- `stdin` EOF (client disconnect) terminates the server cleanly: the container
  `shutdown()` runs and releases memory-engine handles (LanceDB/Kùzu) before exit.
- `SIGINT` is handled gracefully (exit code 0). `SIGTERM` terminates the process
  through the OS default disposition.
- Repeated start/stop cycles leave no zombie processes, threads, or file
  descriptors.

### 3. Provider Behavior
- Interactive inference, embeddings, and semantic-memory extraction have
  independent provider identities; the MCP server never substitutes one for another.
- Deterministic tools do not depend on LLM inference and keep working during a
  complete provider outage.
- A provider restarted while the MCP server is running is picked up by subsequent
  requests without restarting the server.
- Provider failures are reported through `inference_status`/`fallback_reason`, never
  hidden.

---

## 6. Verifying the MCP Server

```bash
# MCP adapter, schemas, exception isolation, concurrency, provider recovery
cd backend && uv run pytest tests/test_mcp_adapter.py tests/test_mcp_concurrency_hardening.py \
  tests/test_mcp_concurrency_lifecycle.py tests/test_mcp_exception_isolation.py \
  tests/test_mcp_provider_recovery.py -q

# Production-contract suite: authorization boundary, truthfulness, real stdio
# protocol/resources, and the initialized get_agent_context regression
cd backend && uv run pytest tests/test_mcp_production_contract.py -q

# stdout framing, process lifecycle, official-client interop over real subprocesses
cd backend && uv run pytest tests/test_mcp_logging_integrity.py tests/test_mcp_stdio_shutdown.py \
  tests/test_phase_8d_deployment.py tests/test_phase_8d_interoperability.py \
  tests/test_phase_8d_lifecycle.py tests/test_phase_8e_clean_deployment.py \
  tests/test_phase_8e_mcp_interoperability.py -q

# Workspace authorization and dataset identity
cd backend && uv run pytest tests/test_workspace_authorization.py tests/test_dataset_identity_isolation.py -q
```

## 7. Limitations

- Transport is **stdio only**; SSE/streamable-HTTP are not wired up.
- Paths that do not exist are reported as `ValidationError` before authorization is
  evaluated, so a client can distinguish "missing" from "unauthorized" for arbitrary
  paths (existence oracle). This is inherent to the shared authorization service and
  accepted for usability; it does not grant access.
- `get_repository_summary` performs live filesystem/AST analysis per call; there is
  no branch/commit metadata in the summary (use `list_indexed_repositories` for the
  registered branch/commit).
- `max_tokens` is a planning budget; the delivered package is measured against it,
  but exact token counts depend on the estimator.
