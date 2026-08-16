# Sync Failure Root Cause Analysis

## Summary

Frontend-triggered sync fails. Backend pytest passes. Three root causes found.

---

## Root Cause 1 — CRITICAL: No virtualenv; wrong Python picked by Tauri

**The #1 failure.** The backend has **no venv and no `requirements.txt`**.

`lib.rs:start_backend()` tries these in order:
```
python3.13 → python3 → python
```

- `python3.13`: **not found** on this system
- `python3`: resolves to `/usr/bin/python3` (Python 3.14 system install)
- System Python **has no `uvicorn`, `fastapi`, or `cognee`**

So Tauri spawns `python3 -m uvicorn app.server:app` using the bare system Python.
This fails immediately — `uvicorn` is not importable — so the backend process dies.

`wait_for_backend(30)` then polls `/health` for 30 seconds, gets no response, and **panics**:
```
Python backend did not become ready within 30 seconds
```

**Why do backend tests pass?** You run pytest from a shell where your PATH
activates the correct environment — likely the uv Python 3.12 at
`~/.local/share/uv/python/cpython-3.12.8-linux-x86_64-gnu/` — where all packages exist.

---

## Root Cause 2 — SECONDARY: `CARGO_MANIFEST_DIR` not set at runtime

In `lib.rs:start_backend()`:
```rust
let manifest_dir = std::env::var("CARGO_MANIFEST_DIR").unwrap_or_else(|_| {
    std::env::current_dir()...
```

`CARGO_MANIFEST_DIR` is only set during `cargo build`, **not** at runtime.
So the fallback `current_dir()` is used. When Tauri runs packaged,
`current_dir()` is the app bundle dir, not the project root.
This makes `backend_dir` resolve to a wrong path — `app.server:app` module not found.

---

## Root Cause 3 — MINOR: Piped stdio, pipes never drained

```rust
.stdout(Stdio::piped())
.stderr(Stdio::piped())
```

Piped stdio fills OS pipe buffers. Parent never reads them.
Backend crash logs are **completely invisible**.

---

## Fix Plan

### Fix 1 — Create project venv

```bash
cd backend/
uv venv .venv --python 3.12
uv pip install -r requirements.txt
```

First, generate `requirements.txt` from what pytest uses:
```bash
uv pip freeze > requirements.txt
```

### Fix 2 — Update `lib.rs` to use the venv Python

```rust
fn get_python_path(backend_dir: &std::path::Path) -> String {
    let venv_python = backend_dir.join(".venv/bin/python");
    if venv_python.exists() {
        return venv_python.to_string_lossy().to_string();
    }
    for cmd in &["python3.13", "python3", "python"] {
        if Command::new(cmd).arg("--version").output()
            .map(|o| o.status.success()).unwrap_or(false) {
            return cmd.to_string();
        }
    }
    "python3".to_string()
}
```

### Fix 3 — Fix backend_dir resolution

```rust
let backend_dir = std::env::current_exe()
    .ok()
    .and_then(|p| p.parent().map(|d| d.join("../backend")))
    .unwrap_or_else(|| std::path::PathBuf::from("backend"));
```

For `cargo tauri dev`, use a build-time constant via `build.rs`.

### Fix 4 — Log backend output to file

```rust
let log_path = std::env::temp_dir().join("retrack-backend.log");
let log_file = std::fs::File::create(&log_path).ok();
command.stdout(log_file.map(Stdio::from).unwrap_or(Stdio::null()));
command.stderr(Stdio::null());
```

---

## Verification

1. `cd backend && .venv/bin/uvicorn app.server:app --port 8765` — confirm backend starts
2. `curl http://127.0.0.1:8765/health` — confirm OK
3. Apply lib.rs fixes
4. `cargo tauri dev` — backend should spawn and become ready


Good refinements. One critical point changed — need to clarify.

**Question 10:**

Earlier confirmed: agent calls RE:Track → gets Context Package → agent calls LLM itself.

Now you said "forward requests with context to the LLM."

Clear — RE:Track optimizes **input context only**, never touches LLM output. Middleware confirmed.

**Question 11:**

---

## Complete Understanding Lock

**Revised full picture:**

**RE:Track role:** Context middleware. Receives agent's task prompt → returns optimized Context Package. Never touches LLM output.

```
Agent sends: { task_prompt, repo_path }
                     ↓
          RE:Track Backend API
                     ↓
         ┌─────── Index Check ──────────┐
         │  timestamp vs repo mtime      │
         │  changed files? → partial     │
         │  re-index only those          │
         └───────────────────────────────┘
                     ↓
         ┌────── Intent Parsing ─────────┐
         │  phi4:mini (prefer Q6+, warn) │
         │  • symbol extraction           │
         │  • intent classification       │
         │  • file relevance scoring      │
         │  structured prompts only       │
         │  (anti-hallucination guards)   │
         └───────────────────────────────┘
                     ↓
         ┌────── Context Retrieval ──────┐
         │  CGC graph → structural hits  │
         │  Cognee recall → semantic hits│
         │  merged, ranked               │
         └───────────────────────────────┘
                     ↓
         ┌───── Context Compression ─────┐
         │  only if prompt is vague      │
         │  phi4:mini summarizes chunks  │
         │  avoid hardware bottleneck    │
         └───────────────────────────────┘
                     ↓
          Context Package (Markdown)
                     ↓
Agent feeds: { task_prompt + Context Package } → LLM (any provider)
```

**Key decisions captured:**

| Decision | Value |
|---|---|
| Model selection | Use currently loaded model; prefer phi4:mini any variant; warn if Q6+ not found |
| Model download | Never download without explicit user permission |
| Storage priority | Context DB (LanceDB + Kuzu + CGC) takes VRAM/RAM priority over model |
| Cold start skip | Timestamp check; partial re-index on changed files only |
| Intent parsing | Symbol extraction + intent classification + file relevance scoring |
| Compression trigger | Only when prompt is too vague; avoids unnecessary model load |
| API format | OpenAI-compatible (works with Ollama, LM Studio, cloud, anything) |
| LLM output | RE:Track never processes or modifies it |

**Non-goals (confirmed):**
- No model download automation
- No LLM output processing
- No cloud sync
- No bundled inference server

**Assumptions:**
- Agent already knows the repo path and sends it with every request
- "Currently loaded model" = detected via provider's running model API
- Partial re-index tracks file hashes/mtimes in a local manifest
- CGC index staleness tracked separately from Cognee index

**Open questions before design:**
1. Should RE:Track expose a **single enriched `/context` endpoint**, or multiple (one for package-only, one for intent-parsed)? 
2. What API does the agent use to connect — custom REST, or should RE:Track mimic an OpenAI-compatible `/v1/context` path so agents need minimal config?

> Does this accurately reflect your intent? Confirm and we move to design approaches.