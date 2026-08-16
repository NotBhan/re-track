# Sessions

## Purpose

Sessions provide temporary, short-lived memory within Cognee.

Unlike datasets, which store permanent project knowledge, sessions capture the current working context of a user or agent. Session memory can later be promoted into permanent memory through Cognee's improvement pipeline.

For RE:Track, sessions represent the developer's active coding session.

---

# Concept

```
Permanent Memory

        ▲
        │
 improve()
        │
        │

Session Memory

        ▲
        │
 remember(session_id=...)
        │

Developer
```

---

# Permanent vs Session Memory

| Permanent Memory | Session Memory |
|------------------|---------------|
| Long-term | Temporary |
| Shared across sessions | Active session only |
| Stored in dataset | Identified by session_id |
| Repository knowledge | Current work |
| Architecture | Current task |
| Documentation | Recent edits |

---

# Why Sessions Matter

Without sessions:

```
Developer

↓

remember()

↓

Permanent Graph
```

Every small thought becomes permanent.

With sessions:

```
Developer

↓

Session Memory

↓

Coding

↓

Improve

↓

Permanent Memory
```

Only useful knowledge survives.

---

# session_id

Both `remember()` and `recall()` support:

```python
session_id="editor-session-001"
```

This identifies temporary memory belonging to a specific coding session.

---

# Example 1 — Store Session Memory

```python
import asyncio
import cognee

async def main():

    await cognee.remember(
        data="Refactoring authentication middleware.",
        dataset_name="re_track",
        session_id="editor-session-001"
    )

asyncio.run(main())
```

---

# Example 2 — Recall Session Memory

```python
results = await cognee.recall(
    query_text="What am I currently working on?",
    session_id="editor-session-001"
)
```

---

# Example 3 — Session + Dataset

```python
results = await cognee.recall(
    query_text="Explain the authentication flow.",
    datasets=["re_track"],
    session_id="editor-session-001"
)
```

This allows Cognee to combine:

- long-term project memory
- active working memory

---

# Session Lifecycle

```
Open Repository

        │

        ▼

Create Session

        │

        ▼

remember(session)

        │

        ▼

Coding

        │

        ▼

recall(session)

        │

        ▼

improve()

        │

        ▼

Permanent Memory

        │

        ▼

Close Session
```

---

# RE:Track Mapping

Recommended mapping:

| RE:Track | Cognee |
|--------------|---------|
| Repository | Dataset |
| Workspace | Dataset |
| Coding Session | Session |
| Chat Thread | Session |
| Task | Session |
| Project Memory | Dataset |

---

# Session Naming

Use stable unique identifiers.

Example:

```
editor-session-001

editor-session-2026-06-30

task-implement-auth

chat-42
```

---

# Typical Workflow

```
User Opens Project

↓

Dataset Loaded

↓

Session Created

↓

Developer Works

↓

remember(session)

↓

Agent Needs Context

↓

recall(session)

↓

Task Completed

↓

improve()

↓

Session Closed
```

---

# RE:Track Usage

Sessions should be created when:

- a repository is opened
- a coding task begins
- an AI conversation starts
- a new feature is implemented

Sessions should end when:

- the task completes
- the repository closes
- the user explicitly ends the session

---

# Best Practices

- Create one session per active coding task.
- Keep session memory temporary.
- Allow improve() to promote valuable knowledge.
- Reuse datasets across sessions.
- Generate unique session identifiers.

---

# Common Pitfalls

- Treating sessions as permanent storage.
- Forgetting to provide session_id.
- Creating extremely long-lived sessions.
- Mixing multiple tasks into one session.

---

# RE:Track Design Notes

Sessions eliminate the need for RE:Track to implement its own temporary memory system.

Instead:

- Cognee manages temporary session memory.
- Cognee promotes useful information through `improve()`.
- RE:Track focuses on orchestration, Context Package generation, and developer experience.

This significantly simplifies the architecture while leveraging Cognee's native capabilities.

---

# Related APIs

- remember()
- recall()
- improve()
- forget()

---

# Related Concepts

- Datasets
- Ontologies
- Global Context Index

---

# Related Source

```
cognee/api/v1/remember/
cognee/api/v1/recall/
```

