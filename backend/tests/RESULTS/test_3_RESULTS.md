# Test 3 — Full Pipeline & CLI Testing

**Date**: 2026-06-30

---

## Automated Tests (pytest)

**47/47 pass** — schemas, commands, CLI all green.

- 35 API tests (schemas + commands + serialization)
- 12 CLI tests (health, status, index, context, forget)

---

## Live Cognee Integration

| Script | Result | Notes |
|--------|--------|-------|
| `setup.py` | PASS | Cognee initialized with phi3:mini + nomic-embed-text |
| `remember_demo.py` | PARTIAL | Data ingested (graph nodes created). Timed out during self-improvement step (phi3:mini structured output retries) |
| `recall_demo.py` | PASS | All 4 queries returned relevant results |
| `improve_demo.py` | SKIPPED | Depends on successful remember() |
| `forget_demo.py` | PASS | Dataset deleted, recall confirmed empty after |

---

## CLI Commands

| Command | Result | Output |
|---------|--------|--------|
| `health` | PASS | Status: ok, Ollama reachable, Cognee initialized |
| `status` | PASS | Full config table (models, DBs, storage paths) |
| `context -q "What is RE:Track?" -d andes_playground` | PASS | ~132 tokens, 1 section |
| `forget -d andes_playground` | PASS | Deleted in ~6s |
| `index /nonexistent` | PASS (error) | "Repository path does not exist" |
| `context -q "  "` | PASS (error) | "Query must not be empty" |
| `forget` (no args) | PASS (error) | "At least one of --dataset..." |

---

## Known Limitation

phi3:mini struggles with Cognee's structured output during the self-improvement step inside `remember()`, causing retries on SummarizedContent and KnowledgeGraph schemas. The core ingestion and recall pipeline works correctly regardless.
