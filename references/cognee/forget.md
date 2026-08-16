# forget()

## Purpose

`forget()` removes information from Cognee's memory.

It allows applications to selectively delete knowledge from datasets, remove outdated information, or completely clear project memory.

For RE:Track, `forget()` keeps the knowledge graph synchronized with the actual project by removing deleted files, obsolete documentation, or deprecated architectural decisions.

---

## Source

Implementation:

```
cognee/api/v1/forget/forget.py
```

Verified against repository source.

---

## Signature

```python
async def forget(
    dataset: str | None = None,
    dataset_id: UUID | None = None,
    data_id: UUID | None = None,
    **kwargs
) -> None
```

**Note**: Verified against Cognee v1.2.2. The parameter is `dataset` (not `dataset_name`) and `data_id` (not `document_id`).

---

# Forget Pipeline

```
Forget Request
        │
        ▼
forget()
        │
        ├── Locate Dataset
        │
        ├── Resolve Documents
        │
        ├── Remove Vector Entries
        │
        ├── Remove Graph Nodes
        │
        ├── Remove Relationships
        │
        └── Cleanup Metadata
```

---

# What forget() Does

Typical operations include:

- deleting datasets
- removing documents
- removing graph nodes
- removing embeddings
- removing relationships
- cleaning metadata
- synchronizing storage

---

# Important Parameters

## dataset

Deletes knowledge associated with a dataset.

Example:

```python
dataset="andes_workspace"
```

---

## dataset_id

Deletes a dataset by UUID.

---

## data_id

Deletes a specific remembered data item by UUID.

Useful when only one file changes.

---

# Example 1 — Delete Dataset

```python
import asyncio
import cognee

async def main():
    await cognee.forget(
        dataset="andes_workspace"
    )

asyncio.run(main())
```

---

# Example 2 — Delete a Document

```python
await cognee.forget(
    data_id="<uuid-of-architecture.md>"
)
```

---

# Example 3 — Re-index a File

```python
await cognee.forget(
    data_id="<uuid-of-auth.py>"
)

await cognee.remember(
    data="./src/auth.py",
    dataset_name="andes_workspace"
)
```

---

# Example 4 — Refresh Documentation

```python
await cognee.forget(
    data_id="<uuid-of-api.md>"
)

await cognee.remember(
    data="./docs/api.md",
    dataset_name="andes_workspace"
)
```

---

# RE:Track Usage

`forget()` should be called when:

- a file is deleted
- documentation is removed
- a repository is disconnected
- a project is archived
- obsolete architectural decisions are discarded
- the user manually clears memory

It should **not** be used for normal file modifications if incremental updates are supported.

---

# Recommended Workflow

```
File Deleted
        │
        ▼
forget()
        │
        ▼
Memory Updated
```

For modified files:

```
Modified File
        │
        ▼
forget()
        │
        ▼
remember()
        │
        ▼
improve()
```

---

# Best Practices

- Delete only affected documents when possible.
- Reserve dataset deletion for project removal.
- Re-index updated files after forgetting them.
- Keep memory synchronized with the repository.

---

# Common Pitfalls

- Forgetting an entire dataset unintentionally.
- Forgetting without re-indexing updated content.
- Leaving stale memories after large refactors.
- Using dataset deletion when only a single document changed.

---

# RE:Track Integration

Suggested triggers:

- File deleted
- Project removed
- Repository reset
- Manual "Clear Memory"
- Branch reset (optional future feature)

The backend should determine the smallest deletion scope possible to avoid unnecessary re-indexing.

---

# Related APIs

- remember()
- recall()
- improve()
- serve()

---

# Related Source Files

```
cognee/api/v1/forget/
cognee/modules/data/
cognee/modules/storage/
```

---

# RE:Track Notes

Unlike traditional vector stores, Cognee maintains multiple interconnected storage layers. Forgetting data should be treated as a synchronization operation rather than simply deleting embeddings.

Whenever possible, RE:Track should perform targeted forgetting followed by selective re-ingestion instead of rebuilding the entire knowledge graph.

