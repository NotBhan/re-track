# remember()

## Purpose

`remember()` is Cognee's primary ingestion API. It stores new information into memory by processing text, files, documents, or structured data into Cognee's persistent knowledge system.

Depending on whether a `session_id` is supplied, `remember()` stores information either in permanent memory or in temporary session memory.

For RE:Track, `remember()` is responsible for indexing repositories, documentation, developer notes, and project knowledge.

---

## Source

Implementation:

```
cognee/api/v1/remember/remember.py
```

Verified against repository source.

---

## Signature

```python
async def remember(
    data: Union[
        BinaryIO,
        list[BinaryIO],
        str,
        list[str],
        DataItem,
        list[DataItem],
        MemoryEntry,
        MemorySource,
    ],
    dataset_name: str = "main_dataset",
    *,
    session_id: Optional[str] = None,
    chunk_size: Optional[int] = None,
    chunker: Optional[Any] = None,
    custom_prompt: Optional[str] = None,
    run_in_background: bool = False,
    self_improvement: bool = True,
    session_ids: Optional[List[str]] = None,
    **kwargs
) -> RememberResult
```

---

# Memory Pipeline

```
Input
    │
    ▼
remember()
    │
    ├── session_id provided?
    │
    ├── YES
    │      │
    │      ▼
    │  Session Memory
    │      │
    │      ▼
    │ improve()
    │ (optional background sync)
    │      │
    │      ▼
    │ Permanent Knowledge Graph
    │
    └── NO
           │
           ▼
         add()
           │
           ▼
       cognify()
           │
           ▼
 Permanent Knowledge Graph
```

---

# What remember() Does

Internally, `remember()` coordinates Cognee's ingestion pipeline.

Typical stages include:

1. Input validation
2. Loader selection
3. Document parsing
4. Chunk generation
5. Entity extraction
6. Relationship extraction
7. Embedding generation
8. Vector indexing
9. Graph indexing
10. Session synchronization (optional)

---

# Important Parameters

## data

The content to ingest.

Examples include:

- plain text
- markdown
- PDFs
- source code
- images
- binary streams
- file paths

Example:

```python
data="JWT authentication uses RSA keys."
```

or

```python
data=["./README.md", "./docs/architecture.md"]
```

---

## dataset_name

Logical memory namespace.

Every RE:Track workspace should use its own dataset.

Example:

```python
dataset_name="andes_workspace"
```

---

## session_id

Stores information in temporary session memory.

Useful while a developer is actively coding.

---

## self_improvement

When enabled, Cognee automatically promotes useful session knowledge into permanent memory.

Default:

```python
True
```

---

## chunk_size

Overrides automatic chunk sizing.

Useful when ingesting large repositories.

---

## chunker

Custom chunking implementation.

Advanced usage.

---

## custom_prompt

Allows custom extraction instructions.

Example ideas for RE:Track:

- Extract architectural decisions
- Extract coding conventions
- Extract TODO items
- Extract API contracts
- Extract design rationale

---

## run_in_background

Starts ingestion asynchronously.

Useful when indexing an entire repository.

---

# Example 1 — Remember Text

```python
import asyncio
import cognee

async def main():
    await cognee.remember(
        data="Authentication uses JWT.",
        dataset_name="andes_workspace"
    )

asyncio.run(main())
```

---

# Example 2 — Remember Multiple Files

```python
import asyncio
import cognee

async def main():
    await cognee.remember(
        data=[
            "./README.md",
            "./docs/architecture.md",
            "./src/auth.py"
        ],
        dataset_name="andes_workspace"
    )

asyncio.run(main())
```

---

# Example 3 — Repository Indexing

```python
import asyncio
from pathlib import Path
import cognee

async def main():
    files = [
        str(path)
        for path in Path("./src").rglob("*")
        if path.is_file()
    ]

    await cognee.remember(
        data=files,
        dataset_name="andes_workspace"
    )

asyncio.run(main())
```

---

# Example 4 — Session Memory

```python
import asyncio
import cognee

async def main():
    await cognee.remember(
        data="Currently refactoring authentication.",
        dataset_name="andes_workspace",
        session_id="editor-session-001",
        self_improvement=True
    )

asyncio.run(main())
```

---

# Example 5 — Background Repository Import

```python
await cognee.remember(
    data=["./"],
    dataset_name="andes_workspace",
    run_in_background=True
)
```

---

# Example 6 — Custom Extraction Prompt

```python
await cognee.remember(
    data="./docs",
    dataset_name="andes_workspace",
    custom_prompt="""
Extract:

- Architectural decisions
- API contracts
- Coding conventions
- Design patterns
- Feature descriptions
- Known limitations
"""
)
```

---

# RE:Track Usage

`remember()` should be called when:

- A repository is imported.
- Documentation changes.
- Source files change.
- Developer notes are created.
- Meeting notes are added.
- A coding session begins.
- New architectural decisions are recorded.

During active development, RE:Track should prefer using `session_id` to store transient knowledge before allowing Cognee's self-improvement pipeline to synchronize important information into permanent memory.

---

# Best Practices

- Create one dataset per workspace.
- Batch file changes instead of indexing every save.
- Use session memory during development.
- Allow `self_improvement=True`.
- Use custom prompts to extract software-engineering concepts.
- Run repository imports in the background.

---

# Common Pitfalls

- Mixing multiple repositories into one dataset.
- Re-indexing unchanged files.
- Calling `remember()` on every keystroke.
- Ignoring session memory.
- Using excessively small chunk sizes.

---

# Related APIs

- recall()
- improve()
- forget()
- serve()

---

# Related Source Files

```
cognee/api/v1/remember/
cognee/tasks/
cognee/modules/
```

---

# RE:Track Notes

Within RE:Track, `remember()` is responsible for building the project's long-term memory.

Typical ingestion targets include:

- Source code
- Documentation
- Architecture documents
- ADRs
- API specifications
- Developer notes
- TODO lists
- Bug reports
- Design discussions

Rather than storing every file indiscriminately, RE:Track should ingest meaningful project artifacts and maintain a clean dataset for efficient retrieval by `recall()`.

