# improve()

## Purpose

`improve()` enriches existing memory.

Unlike `remember()`, which stores new information, `improve()` analyzes previously stored knowledge and refines it by generating higher-quality relationships, summaries, and semantic organization.

For RE:Track, `improve()` is responsible for continuously improving project memory without requiring the repository to be re-indexed.

---

## Source

Implementation:

```
cognee/api/v1/improve/improve.py
```

Verified against repository source.

---

## Signature

```python
async def improve(
    dataset: str | None = None,
    **kwargs
) -> ImproveResult
```

**Note**: Verified against Cognee v1.2.2. The parameter is `dataset` (not `dataset_name`).

---

# Improvement Pipeline

```
Existing Memory
        │
        ▼
improve()
        │
        ├── Analyze Graph
        │
        ├── Find Relationships
        │
        ├── Merge Similar Concepts
        │
        ├── Generate Better Summaries
        │
        ├── Update Knowledge Graph
        │
        └── Refresh Retrieval Quality
```

---

# What improve() Does

Typical improvement tasks include:

- enriching relationships
- refining semantic links
- generating higher-level summaries
- improving retrieval quality
- promoting session memory into permanent memory
- removing redundant information

The exact operations depend on the configured Cognee pipeline.

---

# Important Parameters

## dataset

Improves a single dataset.

Example:

```python
dataset="andes_workspace"
```

If omitted, Cognee improves all available datasets.

---

# Example 1 — Improve Workspace Memory

```python
import asyncio
import cognee

async def main():
    await cognee.improve(
        dataset="andes_workspace"
    )

asyncio.run(main())
```

---

# Example 2 — Improve After Repository Import

```python
await cognee.remember(
    data=["./src"],
    dataset_name="andes_workspace"
)

await cognee.improve(
    dataset="andes_workspace"
)
```

---

# Example 3 — Improve Session Memory

```python
await cognee.remember(
    data="Authentication service is being refactored.",
    dataset_name="andes_workspace",
    session_id="editor-session"
)

await cognee.improve(
    dataset="andes_workspace"
)
```

---

# Example 4 — Background Improvement

```python
import asyncio

asyncio.create_task(
    cognee.improve(
        dataset="andes_workspace"
    )
)
```

Useful after indexing large repositories.

---

# RE:Track Usage

`improve()` should be called:

- after repository indexing
- after large documentation imports
- after multiple file updates
- when a coding session ends
- periodically during idle time

It should **not** be executed after every individual file change.

---

# Recommended Workflow

```
Repository Import
        │
        ▼
remember()
        │
        ▼
Developer Works
        │
        ▼
Session Memory
        │
        ▼
improve()
        │
        ▼
Better Permanent Memory
```

---

# Best Practices

- Batch improvements.
- Run during idle periods.
- Improve after significant changes.
- Allow session knowledge to mature before promotion.
- Avoid repeatedly improving unchanged datasets.

---

# Common Pitfalls

- Running improve() after every save.
- Improving incomplete datasets.
- Running multiple improvement jobs simultaneously.
- Expecting immediate changes after every execution.

---

# RE:Track Integration

RE:Track should schedule `improve()` automatically.

Suggested triggers:

- Repository import completed
- Session ended
- Idle for several minutes
- Manual "Optimize Memory" button
- Overnight maintenance

This allows memory quality to improve continuously without interrupting development.

---

# Related APIs

- remember()
- recall()
- forget()
- serve()

---

# Related Source Files

```
cognee/api/v1/improve/
cognee/tasks/memify/
cognee/modules/
```

---

# RE:Track Notes

`improve()` is what makes RE:Track's memory evolve.

Rather than repeatedly ingesting the same information, RE:Track should periodically refine existing knowledge so future `recall()` operations produce cleaner, more relevant Context Packages.

This operation is computationally heavier than `remember()` or `recall()` and is best treated as a background maintenance task.

