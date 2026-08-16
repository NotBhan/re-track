# RE:Track Architecture

```text
┌───────────────────────────────────────────────────────────────┐
│                      RE:Track (RefinedEngine)                 │
├───────────────────────────────────────────────────────────────┤
│                     React + Tauri Frontend                    │
│                                                               │
│  • Projects                                                   │
│  • Context Builder                                            │
│  • Memory Viewer                                              │
│  • Sessions                                                   │
│  • Settings                                                   │
└──────────────────────────────┬────────────────────────────────┘
                               │
                          Tauri IPC
                               │
                               ▼
┌───────────────────────────────────────────────────────────────┐
│                      Python Backend                           │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  WorkspaceService                                             │
│      • Repository Management                                  │
│      • Dataset Lifecycle                                      │
│                                                               │
│  IndexingService                                              │
│      • Repository Import                                      │
│      • Incremental Indexing                                   │
│      • File Change Detection                                  │
│                                                               │
│  CogneeService                                                │
│      • initialize()                                           │
│      • remember()                                             │
│      • recall()                                               │
│      • improve()                                              │
│      • forget()                                               │
│                                                               │
│  ContextService                                               │
│      • Context Package Builder                                │
│      • Context Compression                                    │
│      • Memory Ranking                                         │
│                                                               │
│  SessionService                                               │
│      • Coding Sessions                                        │
│      • Working Memory                                         │
│      • Session Lifecycle                                      │
│                                                               │
└──────────────────────────────┬────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────┐
│                           Cognee                             │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  remember()                                                   │
│  recall()                                                     │
│  improve()                                                    │
│  forget()                                                     │
│                                                               │
└───────────────┬───────────────────────────────┬───────────────┘
                │                               │
                ▼                               ▼
         ┌──────────────┐               ┌──────────────┐
         │   LanceDB    │               │     Kuzu     │
         │ Vector Store │               │ Knowledge    │
         │              │               │ Graph        │
         └──────┬───────┘               └──────────────┘
                │
                ▼
         ┌──────────────┐
         │    SQLite    │
         │ Metadata &   │
         │ Relational   │
         │ Storage      │
         └──────────────┘
```

## Data Flow

```text
Developer

    │

    ▼

Tauri Frontend

    │

    ▼

Python Backend

    │

    ▼

ContextService

    │

    ▼

Cognee recall()

    │

    ▼

Context Package

    │

    ▼

Coding LLM

    │

    ▼

Generated Code

    │

    ▼

Cognee remember()

    │

    ▼

Session Memory

    │

    ▼

improve()

    │

    ▼

Permanent Knowledge Graph
```

## Repository Indexing Flow

```text
Open Repository

        │

        ▼

WorkspaceService

        │

        ▼

Create Dataset

        │

        ▼

IndexingService

        │

        ▼

remember()

        │

        ▼

Knowledge Graph

        │

        ▼

Ready for Retrieval
```

## Context Generation Flow

```text
User Request

        │

        ▼

ContextService

        │

        ▼

recall()

        │

        ▼

Relevant Memories

        │

        ▼

Ranking

        │

        ▼

Compression

        │

        ▼

Markdown Context Package

        │

        ▼

Coding LLM
```

## Core Responsibilities

| Layer | Responsibility |
|-------|----------------|
| Frontend | User interaction and workspace management |
| WorkspaceService | Repository and dataset lifecycle |
| IndexingService | Import and synchronize repositories |
| CogneeService | Thin wrapper around Cognee APIs |
| ContextService | Build optimized Context Packages |
| SessionService | Temporary coding-session memory |
| Cognee | Persistent memory lifecycle |
| LanceDB | Semantic vector retrieval |
| Kuzu | Knowledge graph relationships |
| SQLite | Metadata and internal storage |