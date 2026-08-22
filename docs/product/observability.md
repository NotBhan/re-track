# RE:Track Observability & Diagnostics Guide

RE:Track provides a comprehensive, local-first observability and diagnostics subsystem designed to give developers and system operators full visibility into system health, performance, and issues without compromising code privacy or security credentials.

---

## 1. Observability Principles & Guarantees

1. **Local-First & Privacy Preserving**: Zero telemetry or diagnostic information leaves your machine. All logging, health aggregation, and diagnostic generation execute entirely in-process.
2. **MCP Stdio Isolation**: Standard output (`stdout`) is strictly reserved for JSON-RPC MCP framing. All human-readable diagnostic messages are routed exclusively to standard error (`stderr`), and detailed structured logs are written to disk.
3. **Automatic Secret Redaction**: All API keys (e.g. OpenAI `sk-...`, Anthropic `sk-ant-...`), bearer tokens, authorization headers, passwords, and database connection strings are automatically sanitized and replaced with `[REDACTED]`.
4. **Source Code & Prompt Exclusion**: Diagnostic bundles intentionally exclude source code contents, function bodies, and task prompts.
5. **Bounded Resource Footprint**: Structured logs are subject to size-based rotation and strict retention limits to prevent unbounded disk consumption.

---

## 2. Structured Persistent Logging

### 2.1 File Location & Format
Structured logs are stored as JSON Lines (JSONL) at:
```
~/.retrack/logs/app.jsonl
```

### 2.2 Record Schema
Every log entry is formatted as a single JSON object per line:

```json
{
  "timestamp": "2026-08-22T12:30:45.123456+00:00",
  "level": "INFO",
  "logger": "app.application.use_cases.context",
  "message": "Synthesized agent context package",
  "process_id": 14220,
  "thread_name": "MainThread",
  "event": "context_synthesized",
  "component": "context_engine",
  "operation": "get_agent_context",
  "duration_ms": 45.2,
  "error_class": null
}
```

### 2.3 Log Rotation & Retention
Log rotation is managed automatically by `SafeRotatingFileHandler`:
- **Default Maximum File Size**: 10 MB per file (`max_bytes`).
- **Default Backup Count**: 5 backup files (`backup_count`).
- **Rotated File Names**: `app.jsonl.1`, `app.jsonl.2`, ..., `app.jsonl.5`.
- **Failure Resilience**: If the log directory is unwritable or permissions fail, logging gracefully falls back to `stderr` without crashing the application.

---

## 3. Operational Health Monitoring

RE:Track distinguishes between four distinct health states:

| Health State | Definition | System Capability |
| :--- | :--- | :--- |
| **`healthy`** | Inference provider reachable, Cognee initialized, storage writable | Full functionality (AST retrieval + hybrid LLM synthesis) |
| **`degraded`** | Storage writable and AST available, but LLM provider unreachable | Deterministic AST search and context packaging active; offline fallback |
| **`unavailable`** | Canonical storage directory (`~/.retrack/`) unwritable or disk full | Retrieval impaired; filesystem permissions require resolution |
| **`not_configured`** | Fresh environment where `retrack init` has not yet been executed | Run `retrack init` to initialize default configuration |

### 3.1 CLI Health Command
To inspect live operational status from the terminal:
```bash
retrack health
```

Example output:
```text
                    System Health & Operational Status                     
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Component                       ┃ Status / Metric                       ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Overall Health                  │ ok (healthy)                          │
│ Version                         │ 0.1.0                                 │
│ Ollama Provider                 │ reachable                             │
│ Active Model                    │ qwen2.5-coder:7b                      │
│ Memory Engine (Cognee)          │ initialized                           │
│ Canonical Storage (~/.retrack/) │ available                             │
│ Registered Repositories         │ 3                                     │
│ Saved Context Packages          │ 8                                     │
│ Cached AST Files                │ 142 files (512.4 KB)                  │
│ Concurrency Queue Depth         │ 0 / 5                                 │
│ Host RAM Usage                  │ 8.4 / 31.2 GB (26.9%)                 │
│ Host CPU Usage                  │ 4.2%                                  │
└─────────────────────────────────┴────────────────━━━━━━━━━━━━━━━━━━━━━━━┘
```

### 3.2 CLI Status Command
To view detailed configuration and storage pathways:
```bash
retrack status
```

---

## 4. Diagnostics Bundle & Export

When reporting issues or troubleshooting installation anomalies, you can generate a redacted diagnostic bundle.

### 4.1 Exporting via CLI
Generate an atomic diagnostic bundle file:
```bash
# Export to default ~/.retrack/diagnostics/
retrack diagnostics

# Export to a custom file
retrack diagnostics --output /tmp/retrack-diag.json

# Output raw JSON to stdout (pipeable to jq)
retrack diagnostics --json
```

### 4.2 Bundle Contents
A diagnostic bundle includes:
1. **Metadata**: Product name, version, Python version, platform/OS, hostname hash.
2. **Configuration**: Sanitized LLM provider endpoint, vector DB engine, graph DB engine, storage directories.
3. **Live Health & Telemetry**: Provider status, memory engine status, RAM/CPU stats, concurrency queue depth.
4. **Workspaces Summary**: List of registered repositories, file counts, and last indexing timestamps.
5. **Recent Logs**: The last 100 structured log entries from `app.jsonl` with full secret redaction.

---

## 5. Desktop UI Diagnostics & Logs

In the RE:Track Desktop application:
1. Navigate to **Settings** (`/settings`).
2. Select the **Diagnostics** tab.
3. View real-time component health badges, concurrency depth gauges, and cache utilization.
4. Search and filter recent structured log entries in real-time.
5. Click **Export Diagnostics Bundle** to save a diagnostic report to disk.
