# Datasets

## Purpose

Datasets are the primary logical boundary for memory in Cognee.

A dataset groups related information into an isolated namespace so that memory from one project does not interfere with another.

For RE:Track, every imported repository should correspond to its own dataset.

---

# Concept

```
Cognee

├── Dataset A
│       ├── README
│       ├── Source Code
│       ├── Documentation
│       └── Decisions
│
├── Dataset B
│       ├── Source Code
│       ├── Wiki
│       └── ADRs
│
└── Dataset C
```

Each dataset owns its own memory.

---

# Why Datasets Exist

Without datasets:

```
Project A

↓

Memory

↑

Project B
```

Knowledge from unrelated repositories can mix together.

With datasets:

```
Project A

↓

Dataset A

Project B

↓

Dataset B
```

Memory remains isolated.

---

# RE:Track Mapping

Recommended mapping:

| RE:Track | Cognee |
|--------------|---------|
| Workspace | Dataset |
| Repository | Dataset |
| Coding Session | Session |
| Context Package | Recall Result |
| Long-term Memory | Dataset Memory |

---

# Dataset Naming

Use stable identifiers.

Recommended:

```
andes_<repository_name>
```

Examples:

```
re_track

andes_laios

andes_trm

andes_company_portal
```

Avoid generic names such as:

```
default

test

workspace

project
```

---

# Example 1 — Store into Dataset

```python
import asyncio
import cognee

async def main():

    await cognee.remember(
        data="./README.md",
        dataset_name="re_track"
    )

asyncio.run(main())
```

---

# Example 2 — Query Dataset

```python
results = await cognee.recall(
    query_text="How does authentication work?",
    datasets=["re_track"]
)
```

---

# Example 3 — Improve Dataset

```python
await cognee.improve(
    dataset_name="re_track"
)
```

---

# Example 4 — Forget Dataset

```python
await cognee.forget(
    dataset_name="re_track"
)
```

---

# Typical RE:Track Workflow

```
Open Repository

        │

        ▼

Create Dataset

        │

        ▼

remember()

        │

        ▼

Coding

        │

        ▼

recall()

        │

        ▼

improve()

        │

        ▼

Long-term Project Memory
```

---

# Dataset Lifecycle

```
Repository Imported

↓

Dataset Created

↓

Files Indexed

↓

Memory Improved

↓

Developer Uses Project

↓

Repository Deleted

↓

Dataset Removed
```

---

# Best Practices

- One dataset per repository.
- Never mix unrelated repositories.
- Use stable names.
- Delete datasets when projects are removed.
- Improve datasets periodically.

---

# Common Pitfalls

- Using the default dataset for every project.
- Mixing multiple repositories into one dataset.
- Forgetting to specify the dataset during recall.
- Reusing dataset names for unrelated projects.

---

# RE:Track Design

Every workspace opened inside RE:Track should automatically map to a dedicated Cognee dataset.

Future features may include:

- multiple datasets per workspace
- dependency datasets
- shared organization datasets
- imported documentation datasets

However, the initial implementation should maintain a simple 1:1 relationship:

```
Repository

↓

Dataset
```

This minimizes complexity while providing complete isolation between projects.

---

# Related APIs

- remember()
- recall()
- improve()
- forget()

---

# Related Concepts

- Sessions
- Ontologies
- Node Sets
- Global Context Index

---

# Related Source

```
cognee/core-concepts/datasets
cognee/api/v1/
```

