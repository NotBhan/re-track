# Cognee Integration

## Purpose

Defines how RE:Track (RefinedEngine Track) integrates with Cognee as its persistent memory layer.

This document reflects verified behavior from Cognee v1.2.2 validation via the playground.

---

## Memory Operations

| Operation | Purpose | Verified |
|-----------|---------|----------|
| `remember()` | Ingest data into persistent memory | Yes |
| `recall()` | Retrieve context for coding tasks | Yes |
| `improve()` | Enrich and refine existing memory | Yes |
| `forget()` | Remove outdated or deleted data | Yes |

---

## Verified API Parameters

### remember()

```python
await cognee.remember(data="...", dataset_name="workspace")
```

- `dataset_name` — logical memory namespace, one per workspace
- Each call triggers full pipeline: classification → chunking → extraction → indexing

### recall()

```python
results = await cognee.recall(query_text="...", datasets=["workspace"], top_k=15)
```

- `query_text` — natural language query
- `datasets` — list of dataset name strings (NOT `dataset_name`)
- Returns `RecallResponse` objects with `.kind`, `.text`, `.score`, `.dataset_name`

### improve()

```python
await cognee.improve()
```

- No `dataset_name` parameter in v1.2.2
- Operates on all available datasets
- Run after bulk ingestion, not after every file change

### forget()

```python
await cognee.forget(dataset="workspace")
```

- Uses `dataset` (str), NOT `dataset_name`
- Also accepts `dataset_id` (UUID) or `data_id` (UUID)
- Cascade deletion across vectors, graph, and metadata

---

## Local Stack

| Component | Provider | Model/DB |
|-----------|----------|----------|
| LLM | Ollama | phi3:mini |
| Embeddings | Ollama | nomic-embed-text:latest |
| Vector DB | LanceDB | local file |
| Graph DB | Kuzu | local file |
| Relational DB | SQLite | local file |

---

## Required Environment Variables

| Variable | Value | Reason |
|----------|-------|--------|
| `LLM_PROVIDER` | ollama | Local inference |
| `LLM_MODEL` | phi3:mini | Compatible with structured output |
| `EMBEDDING_MODEL` | nomic-embed-text:latest | 768-dim embeddings |
| `VECTOR_DB_PROVIDER` | lancedb | Local vector storage |
| `GRAPH_DB_PROVIDER` | kuzu | Local graph storage |
| `HUGGINGFACE_TOKENIZER` | nomic-ai/nomic-embed-text-v1 | Token counting for embedding engine |
| `COGNEE_SKIP_CONNECTION_TEST` | true | Skip startup connection tests |
| `ENABLE_BACKEND_ACCESS_CONTROL` | false | Single-user local mode |
| `CACHING` | false | Disable session memory overhead |

See `references/cognee/verified_notes.md` for full details on why each variable exists.

---

## Integration Workflow

### Repository Indexing

```
Files discovered
      │
      ▼
remember(dataset_name=workspace)
      │ (batched, background)
      ▼
improve()
      │ (once after bulk ingestion)
      ▼
Indexed workspace
```

### Context Package Generation

```
Developer request
      │
      ▼
recall(query_text=task, datasets=[workspace])
      │
      ▼
RecallResponse objects
      │
      ▼
Format as Context Package
      │
      ▼
Send to coding LLM
```

### File Update

```
File modified
      │
      ▼
forget(dataset=workspace)
      │
      ▼
remember(data=file, dataset_name=workspace)
```

---

## Limitations

- `remember()` processes one item at a time (~30s per item with phi3:mini)
- `recall()` has ~60-90s latency due to session turn analysis (even with `CACHING=false`)
- `improve()` operates on all datasets (no single-dataset scoping in v1.2.2)
- Thinking-mode models (qwen3.5:4b) cause structured output failures
- HuggingFace tokenizer dependency is required for embedding operations
- `transformers` Python package must be installed

See `references/cognee/verified_notes.md` for complete limitation details.

---

## Recommended Model

**phi3:mini** is the current recommended local model for Cognee integration.

- Compatible with Cognee's instructor-based structured output
- No thinking mode conflicts
- Successfully validated across all memory operations
- See `references/cognee/verified_notes.md` for comparison with qwen3.5:4b

---

## References

- `references/cognee/verified_notes.md` — authoritative implementation reference
- `references/cognee/sdk_reference.md` — SDK signatures and flows
- `references/cognee/configuration.md` — configuration and environment setup
- `references/cognee/remember.md` — remember() details
- `references/cognee/recall.md` — recall() details
- `references/cognee/improve.md` — improve() details
- `references/cognee/forget.md` — forget() details
- `backend/playground/` — validation scripts
