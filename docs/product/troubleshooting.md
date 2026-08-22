# RE:Track Troubleshooting & Diagnostic Guide

**Document Type**: Diagnostic & Troubleshooting Reference  
**Version**: 0.1.0 (Phase 9C Release Baseline)  

---

## 1. Quick Diagnostic Workflow

When encountering unexpected behavior, follow this 3-step diagnostic procedure:

```bash
# 1. Check live system health and component status
retrack health

# 2. Inspect the latest structured logs
tail -n 50 ~/.retrack/logs/app.jsonl | jq

# 3. Export a complete, redacted diagnostic bundle for analysis
retrack diagnostics --output /tmp/retrack-diagnostics.json
```

---

## 2. Common Operational Scenarios

### Scenario A: Local LLM Provider (Ollama / LM Studio) is Offline
- **Symptom**: `retrack health` reports `Overall Health: degraded` and `Ollama Provider: unreachable`.
- **Behavior**:
  - Deterministic AST call graph (`get_ast_call_graph`), architectural summaries (`get_repository_summary`), and code search (`search_repository_code`) remain **100% operational** (< 5ms latency).
  - Context synthesis (`get_agent_context`) automatically falls back to deterministic AST snippets without crashing.
- **Resolution**:
  - Start Ollama (`ollama serve`) or LM Studio on `localhost:11434`.
  - RE:Track automatically detects provider recovery in ~20ms without needing an MCP server restart.

---

### Scenario B: Storage Directory Unwritable (`Health: unavailable`)
- **Symptom**: `retrack health` reports `Overall Health: unavailable` and `Canonical Storage (~/.retrack/): unwritable`.
- **Cause**: User lacks write permissions to `~/.retrack/` or filesystem is mounted read-only / disk full.
- **Resolution**:
  1. Fix directory ownership and permissions:
     ```bash
     chmod -R u+rwX ~/.retrack/
     ```
  2. Check available disk space:
     ```bash
     df -h ~/.retrack/
     ```

---

### Scenario C: Path Authorization Error (`UnauthorizedPathError`)
- **Symptom**: MCP tool returns error: `"Path '/path/to/repo' is not within authorized workspace roots"`.
- **Cause**: Security sandbox prevents AI coding agents from accessing arbitrary filesystem paths outside designated project folders.
- **Resolution**:
  1. Add the parent directory to `RETRACK_WORKSPACE_ROOTS` environment variable:
     ```bash
     export RETRACK_WORKSPACE_ROOTS="/home/user/projects,/tmp/repos"
     ```
  2. Or register the repository in RE:Track:
     ```bash
     retrack index /path/to/repo --dataset my-repo
     ```

---

### Scenario D: MCP Stdio Protocol Desynchronization
- **Symptom**: IDE agent (Cursor / Claude) reports `JSON-RPC parse error` or `Invalid header`.
- **Cause**: Standard output (`stdout`) was polluted by raw print statements or third-party library logging.
- **Guarantee**:
  - RE:Track routes all diagnostic logs to `stderr` exclusively (`setup_logging(stream=sys.stderr)`).
  - `stdout` is reserved 100% for FastMCP JSON-RPC communication.
- **Diagnostic Verification**:
  Run MCP standalone in terminal to inspect stderr output:
  ```bash
  retrack-mcp 2> debug.log
  ```

---

### Scenario E: Corrupted Cache or Metadata State
- **Symptom**: File changes are not reflected in context packages, or AST parsing errors occur.
- **Resolution**:
  1. Purge cached fingerprints:
     ```bash
     retrack reset --cache
     ```
  2. If metadata is corrupted, reset application state (automatic backup will be saved):
     ```bash
     retrack reset --state --confirm
     ```
  3. Re-initialize:
     ```bash
     retrack init
     ```

---

## 3. Interpreting Structured Logs

All runtime events are recorded in structured JSONL format at `~/.retrack/logs/app.jsonl`.

### Useful Inspection Commands

```bash
# Filter errors and warnings
grep -E '"level": "(ERROR|WARNING)"' ~/.retrack/logs/app.jsonl | jq

# Monitor live log stream
tail -f ~/.retrack/logs/app.jsonl | jq

# Search for specific operation duration
grep '"operation": "get_agent_context"' ~/.retrack/logs/app.jsonl | jq '{duration_ms, token_estimate}'
```

### Privacy Guarantee
Logs and diagnostic bundles undergo automatic secret redaction (`_SENSITIVE_PATTERNS`) and strictly omit source code files, function bodies, and task prompts.
