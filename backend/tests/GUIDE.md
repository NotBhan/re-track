# Manual Testing Guide — RE:Track Backend

## Prerequisites

Before testing, ensure these are running:

```bash
# 1. Ollama must be running
ollama serve

# 2. Required models must be pulled
ollama pull phi3:mini
ollama pull nomic-embed-text:latest
```

Verify Ollama is reachable:
```bash
curl http://localhost:11434/api/tags
```

---

## Part 1: Automated Tests (pytest)

### Step 1.1 — Run all tests

```bash
cd backend
python3.13 -m pytest tests/ -v
```

Expected: 47+ tests pass (35 API + 12 CLI).

### Step 1.2 — Run only API schema/command tests

```bash
python3.13 -m pytest tests/test_api.py -v
```

Tests covered:
- **Schema validation** — Pydantic models accept valid input, reject invalid
- **Command delegation** — API commands call services correctly (mocked)
- **Error handling** — ErrorResponse returned on failures
- **Serialization roundtrip** — JSON encode/decode preserves data

### Step 1.3 — Run only CLI tests

```bash
python3.13 -m pytest tests/test_cli.py -v
```

Tests covered:
- **health** — shows ok/degraded, handles errors
- **status** — displays full config table
- **index** — rejects missing paths, shows results
- **context** — rejects empty queries, renders markdown
- **forget** — requires identifier, shows success/error

### Step 1.4 — Run tests with coverage

```bash
python3.13 -m pytest tests/ -v --tb=short
```

---

## Part 2: Cognee Integration (Playground Scripts)

These scripts test the actual Cognee pipeline end-to-end. Run them **in order**.

### Step 2.1 — Bootstrap & initialize

```bash
cd backend/playground
python3.13 setup.py
```

Expected output:
```
  LLM provider:     ollama
  LLM model:        phi3:mini
  Embedding model:  nomic-embed-text:latest
  Vector DB:        lancedb
  Graph DB:         kuzu
  Relational DB:    sqlite
Cognee initialized successfully.
```

If this fails:
- Check `ollama serve` is running
- Verify models exist: `ollama list`
- Check disk space for database files

### Step 2.2 — Validate remember()

```bash
python3.13 remember_demo.py
```

Expected output:
```
[1/4] Initializing CogneeService...
[2/4] Storing 10 items into dataset 'andes_playground'...
  [1/10] RE:Track is a local-first AI memory system...
       -> OK (items_sent=1)
  ...
[3/4] Verifying data was stored (basic recall)...
  Recall returned 3 result(s)
[4/4] Summary
  Dataset:    andes_playground
  Items sent: 10
  Status:     remember() validation complete
```

What this validates:
- CogneeService.initialize() works
- cognee.remember() ingests data
- LanceDB, Kuzu, SQLite storage functional
- Ollama LLM + embeddings working

### Step 2.3 — Validate recall()

```bash
python3.13 recall_demo.py
```

Expected output:
```
[1/3] Initializing CogneeService...
[2/3] Running recall queries...

  Query 1: "What is RE:Track?"
  --------------------------------------------------
  Results: 3
    [1] RE:Track is a local-first AI memory system...
    [2] The system uses Cognee as its persistent memory layer...
    [3] Repository indexing builds long-term project memory...

  Query 2: "How does repository indexing work?"
  ...
```

What this validates:
- Vector search via LanceDB works
- Graph queries via Kuzu work
- Hybrid recall returns relevant results
- Multiple queries succeed

### Step 2.4 — Validate improve()

```bash
python3.13 improve_demo.py
```

Expected output:
```
[1/3] Initializing CogneeService...
[2/3] Running improve()...
  improve() completed in ~30s
[3/3] Verifying improvement with recall...
  Post-improve recall returned 3 result(s)
```

Note: `improve()` is computationally heavy. Expect 15-60 seconds.

What this validates:
- Knowledge graph enrichment works
- LLM-driven summarization functional
- Post-improve recall still works

### Step 2.5 — Validate forget()

```bash
python3.13 forget_demo.py
```

Expected output:
```
[1/4] Initializing CogneeService...
[2/4] Verifying data exists before forget()...
  Before forget: 3 result(s)
[3/4] Forgetting dataset 'andes_playground'...
  forget() completed successfully
[4/4] Verifying data was removed...
  After forget: 0 result(s)
  Dataset is empty — forget() worked completely
```

What this validates:
- cognee.forget() removes data
- Vectors, graph nodes, metadata deleted
- Recall returns empty after forget

---

## Part 3: CLI Manual Testing

### Step 3.1 — Test CLI help

```bash
cd backend
python3.13 retrack.py --help
```

Expected: Shows all 5 commands (health, status, index, context, forget).

### Step 3.2 — Test health command

```bash
python3.13 retrack.py health
```

Expected: Table showing status, Ollama reachable, Cognee initialized, version.

### Step 3.3 — Test status command

```bash
python3.13 retrack.py status
```

Expected: Table showing LLM model, embedding model, DB providers, storage paths.

### Step 3.4 — Test index command

```bash
# Index a real repository
python3.13 retrack.py index /path/to/your/project -d my-project

# Test error: nonexistent path
python3.13 retrack.py index /nonexistent -d test

# Test error: file instead of directory
python3.13 retrack.py index /etc/hostname -d test
```

Expected: Progress spinner, then results table with file counts.

### Step 3.5 — Test context command

```bash
# Generate context (requires indexed data)
python3.13 retrack.py context -q "How does authentication work?" -d my-project

# Test error: empty query
python3.13 retrack.py context -q "  " -d test
```

Expected: Green panel with stats, then rendered markdown.

### Step 3.6 — Test forget command

```bash
# Forget a dataset
python3.13 retrack.py forget -d old-data

# Test error: no identifier
python3.13 retrack.py forget
```

Expected: Success message or error panel.

---

## Part 4: Cross-Component Validation

### Step 4.1 — Full pipeline test

```bash
cd backend/playground

# 1. Setup
python3.13 setup.py

# 2. Store data
python3.13 remember_demo.py

# 3. Retrieve data
python3.13 recall_demo.py

# 4. Enrich data
python3.13 improve_demo.py

# 5. Clean up
python3.13 forget_demo.py
```

### Step 4.2 — CLI + Backend integration

```bash
cd backend

# 1. Check health via CLI
python3.13 retrack.py health

# 2. Index via CLI
python3.13 retrack.py index /path/to/project -d cli-test

# 3. Query via CLI
python3.13 retrack.py context -q "What is this project?" -d cli-test

# 4. Clean up via CLI
python3.13 retrack.py forget -d cli-test
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Connection refused` on Ollama | Run `ollama serve` |
| `model not found` | Run `ollama pull phi3:mini` |
| `HUGGINGFACE_TOKENIZER not set` | Set env: `export HUGGINGFACE_TOKENIZER=nomic-ai/nomic-embed-text-v1` |
| Database lock error | Kill other processes using the DB: `pkill -f cognee` |
| `improve()` hangs | Normal — can take 30-60s on first run |
| CLI shows `degraded` | Check Ollama is running and models are available |
| Tests fail with import errors | Run from `backend/` directory, ensure `app/` is on path |