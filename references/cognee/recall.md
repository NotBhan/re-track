# recall()

## Purpose

`recall()` retrieves information from Cognee's memory system. Depending on the supplied parameters, Cognee automatically searches session memory, the permanent knowledge graph, vector memory, or a hybrid combination.

For RE:Track, `recall()` is responsible for constructing the Context Package supplied to the coding LLM.

---

## Source

Implementation:

```
cognee/api/v1/recall/recall.py
```

Verified against repository source.

---

## Signature

```python
async def recall(
    query_text: str,
    query_type: SearchType | None = None,
    *,
    datasets: list[str] | None = None,
    dataset_ids: list[UUID] | None = None,
    top_k: int = 15,
    auto_route: bool = True,
    scope: str | list[str] | None = None,
    system_prompt: str | None = None,
    system_prompt_path: str = "answer_simple_question.txt",
    node_name: list[str] | None = None,
    node_name_filter_operator: str = "OR",
    only_context: bool = False,
    session_id: str | None = None,
    context_profile: str = "qa",
    wide_search_top_k: int | None = 100,
    triplet_distance_penalty: float | None = 6.5,
    feedback_influence: float = ...,
    verbose: bool = False,
    retriever_specific_config: dict | None = None,
    neighborhood_depth: int | None = None,
    neighborhood_seed_top_k: int | None = None,
    include_references: bool = False,
    user: object | None = None,
    llm_config: LLMConfig | None = None,
    embedding_config: EmbeddingConfig | None = None,
) -> list[RecallResponse]
```

---

# Retrieval Pipeline

```
User Request
        │
        ▼
recall()
        │
        ├── Session Memory
        │
        ├── Vector Search
        │
        ├── Graph Traversal
        │
        └── Hybrid Ranking
        │
        ▼
Relevant Context
        │
        ▼
Context Package
        │
        ▼
Coding LLM
```

---

# Important Parameters

## query_text

Natural language request.

Example:

```python
query_text="Where is authentication initialized?"
```

---

## datasets

Restricts retrieval to one or more datasets.

Example:

```python
datasets=["andes_workspace"]
```

---

## session_id

Searches the active coding session.

Useful while a developer is currently modifying code.

---

## top_k

Maximum number of retrieved results.

```python
top_k=20
```

---

## context_profile

Controls the retrieval profile.

Examples include:

- qa
- architecture
- implementation
- debugging

(Profile availability depends on the configured Cognee installation.)

---

## include_references

Includes references to the original stored memory items.

Recommended when building Context Packages.

---

# Example 1 — Basic Retrieval

```python
import asyncio
import cognee

async def main():
    results = await cognee.recall(
        query_text="Where is authentication implemented?",
        datasets=["andes_workspace"]
    )

    for result in results:
        print(result)

asyncio.run(main())
```

---

# Example 2 — Session Retrieval

```python
import asyncio
import cognee

async def main():
    results = await cognee.recall(
        query_text="What files am I currently editing?",
        session_id="editor-session-001"
    )

    print(results)

asyncio.run(main())
```

---

# Example 3 — Retrieve More Results

```python
results = await cognee.recall(
    query_text="Explain the authentication architecture",
    datasets=["andes_workspace"],
    top_k=25
)
```

---

# Example 4 — Include References

```python
results = await cognee.recall(
    query_text="How does JWT authentication work?",
    datasets=["andes_workspace"],
    include_references=True
)
```

---

# Example 5 — Context Package Generation

```python
import asyncio
import cognee

async def build_context(task: str):
    memory = await cognee.recall(
        query_text=task,
        datasets=["andes_workspace"],
        include_references=True,
        top_k=15
    )

    context_package = {
        "task": task,
        "memory": memory
    }

    return context_package

asyncio.run(
    build_context(
        "Implement OAuth login"
    )
)
```

---

# RE:Track Usage

`recall()` should be used whenever:

- A coding task begins.
- The developer asks a project question.
- The agent needs architectural decisions.
- Existing implementations must be located.
- Documentation must be retrieved.
- Previous conversations are required.
- A Context Package is generated.

The retrieved memories should be processed into a concise Context Package before being sent to the coding model.

---

# Best Practices

- Always specify the active dataset.
- Use session memory during active development.
- Keep `top_k` reasonably small.
- Include references whenever possible.
- Retrieve only the information needed for the current task.

---

# Common Pitfalls

- Searching every dataset.
- Retrieving excessive context.
- Ignoring session memory.
- Passing raw retrieval output directly to the LLM without formatting.

---

# Related APIs

- remember()
- improve()
- forget()
- serve()

---

# Related Source Files

```
cognee/api/v1/recall/
cognee/modules/retrieval/
cognee/modules/search/
```

---

# RE:Track Notes

For RE:Track, `recall()` is the primary mechanism for building a Context Package.

The package should contain:

- Relevant implementation files
- Architectural decisions
- Coding conventions
- Previous developer decisions
- Related documentation
- Referenced source locations

The Context Package should remain compact so that local LLMs with limited context windows receive only the information necessary for the current task.

