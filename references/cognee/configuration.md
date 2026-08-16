# Cognee Configuration

## Purpose

Before any memory operations can be performed, Cognee must be configured with:

- LLM Provider
- Embedding Provider
- Vector Database
- Graph Database
- Storage Paths

RE:Track uses a fully local configuration built around Ollama and Cognee's default local databases.

---

# RE:Track Default Stack

| Component | Provider |
|----------|----------|
| LLM | Ollama |
| Embedding Model | Ollama |
| Vector Database | LanceDB |
| Graph Database | Kuzu |
| Relational Database | SQLite |

This configuration requires no external cloud services.

---

# Environment Variables

Typical `.env`

```env
# ------------------------
# LLM
# ------------------------

LLM_PROVIDER=ollama
LLM_MODEL=phi3:mini

LLM_ENDPOINT=http://localhost:11434/v1

LLM_API_KEY=ollama

# ------------------------
# Embeddings
# ------------------------

EMBEDDING_PROVIDER=ollama

EMBEDDING_MODEL=nomic-embed-text:latest

EMBEDDING_ENDPOINT=http://localhost:11434/api/embed

EMBEDDING_API_KEY=ollama

EMBEDDING_DIMENSIONS=768

# ------------------------
# HuggingFace Tokenizer (required by OllamaEmbeddingEngine)
# ------------------------

HUGGINGFACE_TOKENIZER=nomic-ai/nomic-embed-text-v1

# ------------------------
# Databases
# ------------------------

VECTOR_DB_PROVIDER=lancedb

GRAPH_DB_PROVIDER=kuzu

RELATIONAL_DB_PROVIDER=sqlite

# ------------------------
# Playground settings
# ------------------------

ENABLE_BACKEND_ACCESS_CONTROL=false
CACHING=false
COGNEE_SKIP_CONNECTION_TEST=true

# ------------------------
# Storage
# ------------------------

DATA_ROOT_DIRECTORY=.cognee_data

SYSTEM_ROOT_DIRECTORY=.cognee_system
```

---

# Runtime Configuration

Cognee also exposes configuration setters.

Example:

```python
import cognee

cognee.config.set_llm_provider("ollama")
cognee.config.set_vector_db_provider("lancedb")
cognee.config.set_graph_db_provider("kuzu")
```

Environment variables remain the preferred configuration mechanism for RE:Track.

---

# Verify Configuration

```python
import cognee

print(cognee.config)
```

or

```python
import os

print(os.environ["LLM_PROVIDER"])
```

---

# Example Initialization

```python
import asyncio
import cognee

async def initialize():

    await cognee.remember(
        data="Initialization successful.",
        dataset_name="andes_workspace"
    )

asyncio.run(initialize())
```

If no configuration errors occur, Cognee is correctly initialized.

---

# RE:Track Startup

Every RE:Track workspace should perform:

```
Load .env
        │
        ▼
Configure Providers
        │
        ▼
Initialize Cognee
        │
        ▼
Verify Models
        │
        ▼
Open Dataset
        │
        ▼
Ready
```

---

# Ollama Requirements

Required models:

```bash
ollama pull phi3:mini
ollama pull nomic-embed-text:latest
```

Verify:

```bash
ollama list
```

---

# Verify Ollama

```bash
curl http://localhost:11434/api/tags
```

or

```bash
ollama ps
```

---

# Recommended Project Structure

```
backend/

    config.py

    cognee_client.py

.env

.cognee_data/

.cognee_system/
```

---

# Best Practices

- Use `.env` for all configuration.
- One configuration per RE:Track installation.
- Keep databases local by default.
- Do not hardcode API keys.
- Verify Ollama before starting RE:Track.
- Keep embedding and LLM providers consistent.

---

# Common Problems

## Ollama not running

```
Connection refused
```

Start:

```bash
ollama serve
```

---

## Model missing

```
Model not found
```

Pull:

```bash
ollama pull phi3:mini
```

---

## Embedding model missing

```
Embedding initialization failed
```

Pull:

```bash
ollama pull nomic-embed-text:latest
```

---

## Wrong Provider

Verify:

```python
print(cognee.config)
```

---

## HuggingFace Tokenizer Error

```
None is not a valid model identifier
```

Set the tokenizer environment variable:

```bash
export HUGGINGFACE_TOKENIZER=nomic-ai/nomic-embed-text-v1
```

This is required even when using Ollama for embeddings — the tokenizer is used for token counting.

---

## Thinking Model Failures

```
instructor.exceptions.InstructorRetryException
```

Thinking-mode models (e.g., qwen3.5:4b) exhaust max_tokens on reasoning before producing structured output. Use phi3:mini instead.

---

## Slow Session Analysis

```
recall() takes 60-90 seconds
```

Disable session memory:

```bash
export CACHING=false
```

---

# RE:Track Notes

RE:Track is designed to operate completely offline.

The recommended deployment consists of:

- Local Ollama
- Local LanceDB
- Local Kuzu
- Local SQLite

This minimizes latency, removes cloud dependencies, and aligns with the project's goal of improving local AI development through persistent memory.

---

# Recommended Model

**phi3:mini** is the current recommended local model for Cognee integration.

- Compatible with Cognee's instructor-based structured output
- No thinking mode (avoids max_tokens exhaustion during reasoning)
- Successfully validated across remember(), recall(), improve(), forget()

Avoid thinking-mode models (e.g., qwen3.5:4b) — they cause structured output failures in Cognee's entity extraction pipeline.

---

# Related APIs

- remember()
- recall()
- improve()
- forget()

---

# Related Source Files

```
cognee/api/v1/config/
cognee/base_config.py
cognee/infrastructure/
```

