# RE:Track MCP Server Configuration & Usage Guide

## Overview

RE:Track exposes its repository memory, deterministic AST call graphs, architectural summaries, and high-precision context packages to external AI coding assistants through the standard **Model Context Protocol (MCP)** over `stdio`.

---

## 1. Running the MCP Server

The RE:Track MCP server can be launched using any of the following standard mechanisms:

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

---

## 2. Configuring External AI Coding Clients

### Claude Desktop / Claude Code
Add the following to your `claude_desktop_config.json` (located at `~/.config/Claude/claude_desktop_config.json` on Linux or `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

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

| Tool Name | Arguments | Description |
| :--- | :--- | :--- |
| `get_agent_context` | `task_prompt` (str, required)<br>`repository_path` (str, required)<br>`max_tokens` (int, default: 8000)<br>`dataset_name` (str, optional)<br>`include_structural_graph` (bool, default: true) | Synthesizes a high-precision, token-budgeted Markdown Context Package with AST caller/callee relationships, symbol definitions, and relevant source snippets. |
| `get_repository_summary` | `repository_path` (str, required) | Returns high-level architectural knowledge: tech stack, frameworks, architectural layers, key components, and entry points. |
| `get_ast_call_graph` | `repository_path` (str, required)<br>`file_filter` (str, optional)<br>`max_nodes` (int, default: 150) | Extracts the deterministic AST call graph (nodes and directed caller/callee edges) with optional file prefix filtering. |
| `search_repository_code` | `repository_path` (str, required)<br>`query` (str, required)<br>`limit` (int, default: 10) | Searches repository code for matching symbols, function definitions, classes, and keywords with relevance ranking. |
| `list_indexed_repositories` | *None* | Lists all registered repositories in RE:Track with their paths, status, languages, file counts, and metadata. |

---

---

## 4. Security Model & Trust Boundary (Phase 8B Hardening)

RE:Track implements strict defense-in-depth isolation between external MCP clients and the host filesystem/memory:

### 1. Workspace Authorization
- External MCP clients are restricted to accessing **authorized repositories** only.
- A path is authorized if:
  1. It is explicitly registered in RE:Track's metadata store (e.g. indexed via UI or CLI), OR
  2. It resides within a configured workspace root directory specified via the `RETRACK_WORKSPACE_ROOTS` environment variable (delimited by `:` on Linux/macOS or `;` on Windows).
- Root filesystem directories (`/`, `C:\`), system directories (`/etc`, `/proc`, `/sys`, `/dev`, `/root`, `/var`), and user credential stores (`~/.ssh`, `~/.gnupg`) are strictly prohibited.
- Symlinks traversing outside the authorized repository root are automatically detected and pruned during file discovery and indexing.

### 2. Dataset Identity & Memory Isolation
- Context memory is partitioned using deterministic, collision-proof dataset identifiers: `{sanitized_name}_{path_sha256_10hex}`.
- Distinct repositories sharing identical directory basenames (e.g., `/client_a/service` and `/client_b/service`) are physically isolated and cannot leak memory records across boundaries.

### 3. Bounded Concurrency & Process-Scoped Queueing
- The context engine uses a process-scoped bounded concurrency queue (`max_concurrent=1`, `max_queue=5`, `timeout=30.0s`) owned by the composition root `ApplicationContainer`.
- All MCP `get_agent_context` tool calls share the same execution queue.
- Concurrent requests within capacity queue gracefully rather than dropping immediately; requests arriving when the queue is saturated return a retryable `BusyError`.

### 4. Exception Isolation & Error Boundaries
- All MCP tool handlers catch unexpected internal exceptions at the transport boundary, log diagnostic details to standard error, and return structured, sanitized error responses (`ValidationError`, `AuthorizationError`, `ConnectionError`, `InternalError`) without leaking internal stack traces or database connection strings to the client.

---

## 5. Operational Lifecycle & Reliability (Phase 8C Hardening)

RE:Track's MCP runtime is hardened for long-running developer workstation operation:

### 1. Process-Scoped Shared Concurrency Guard
- `BoundedConcurrencyGuard` is instantiated as a singleton on `ApplicationContainer` and shared across all `ContextUseCases` factory calls.
- Guarantees strict single-worker concurrency (`max_concurrent=1`) with up to 5 queued requests across all simultaneous MCP client requests.

### 2. Stdio Framing & Stderr-Only Logging
- All application and diagnostic logging (including Cognee, structlog, LiteLLM, and server startup diagnostics) writes strictly to `sys.stderr`.
- `sys.stdout` is reserved exclusively for clean, uncorrupted JSON-RPC protocol frames.

### 3. Graceful Stdio EOF & Signal Shutdown
- The MCP server detects client disconnects (`stdin` reaching EOF) and terminates cleanly without hanging or leaving background zombie tasks.
- Clean shutdown handlers are registered for `SIGINT`, `SIGTERM`, and asyncio loop cancellation.

### 4. LLM Provider Failure & Same-Process Recovery
- **Deterministic Tools Immunity**: `get_repository_summary`, `get_ast_call_graph`, `search_repository_code`, and `list_indexed_repositories` do not depend on LLM inference and continue functioning normally (~1.3ms latency) even during complete LLM provider outages.
- **Automatic Same-Process Recovery**: When a failed or restarted LLM provider (Ollama / LM Studio) comes back online, subsequent `get_agent_context` requests in the same running MCP process immediately recover and succeed without requiring an MCP server restart.


