# serve()

## Purpose

`serve()` exposes a running Cognee instance as a service that other applications, agents, or clients can communicate with.

Rather than embedding Cognee directly into every application, a single Cognee service can manage memory while multiple clients connect to it.

For RE:Track, this is a future scalability feature rather than an MVP requirement.

---

# Concept

```
            Cognee Server
          ┌────────────────┐
          │                │
          │ Knowledge Graph│
          │ Vector Store   │
          │ Session Memory │
          │                │
          └───────┬────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
    ▼             ▼             ▼

RE:Track   Claude Code    Other Agents
```

---

# Why serve() Exists

Without a server:

```
Every application

↓

Own Cognee Instance

↓

Own Memory
```

With a server:

```
Multiple Applications

↓

One Cognee Server

↓

Shared Memory
```

---

# Typical Responsibilities

A Cognee server may provide:

- remember()
- recall()
- improve()
- forget()
- dataset management
- session management
- memory querying

through a network interface.

---

# RE:Track Today

Current MVP architecture:

```
Tauri

↓

Python Backend

↓

Cognee

↓

Local Storage
```

Everything runs on one machine.

---

# Future Architecture

```
Tauri

↓

RE:Track Backend

↓

Cognee Server

↓

Knowledge Graph
```

This allows:

- multiple IDEs
- multiple coding agents
- shared project memory
- remote access

---

# Example Concept

Illustrative example only.

```python
import cognee

# Start Cognee service
await cognee.serve()
```

Refer to the installed Cognee version for the exact API.

---

# Possible Client Flow

```
Developer

↓

RE:Track

↓

HTTP / MCP / SDK

↓

Cognee Server

↓

Memory
```

---

# Potential RE:Track Features

A future version could support:

- shared team memory
- remote indexing
- background memory service
- multiple concurrent agents
- organization-wide knowledge

without changing the desktop application.

---

# When To Use

Recommended:

- multiple clients
- team environments
- background services
- persistent memory daemon

Not recommended for the initial hackathon MVP.

---

# MVP Recommendation

Keep Cognee embedded locally.

```
Tauri

↓

Python

↓

Cognee

↓

SQLite

↓

LanceDB

↓

Kuzu
```

This minimizes complexity and avoids networking concerns.

---

# Future Roadmap

Possible future deployment:

```
Laptop

↓

Cognee Server

↓

Projects

↓

Claude Code

↓

Codex

↓

RE:Track

↓

OpenHands

↓

Local Agents
```

One memory backend.

Many clients.

---

# Best Practices

- Keep the server stateless where possible.
- Authenticate clients if exposed beyond localhost.
- Keep datasets isolated.
- Limit concurrent heavy ingestion jobs.
- Monitor memory growth.

---

# Common Pitfalls

- Sharing unrelated datasets.
- Running multiple Cognee servers for the same storage.
- Allowing unlimited background ingestion.
- Exposing the server publicly without authentication.

---

# RE:Track Design Notes

The initial version of RE:Track should not depend on `serve()`.

Instead, embed Cognee directly into the local backend.

If RE:Track later evolves into a platform supporting multiple IDEs, editors, or autonomous coding agents, `serve()` becomes the natural evolution point, allowing one centralized memory layer to support many independent clients.

---

# Related APIs

- remember()
- recall()
- improve()
- forget()

---

# Related Concepts

- Datasets
- Sessions
- Agent Memory Decorator

---

# Related Documentation

https://docs.cognee.ai/core-concepts/main-operations/serve

