# Workspace Model

## Purpose

The Workspace Model defines how RE:Track (RefinedEngine Track) represents software projects and maps them to Cognee's memory model.

A workspace is the primary organizational unit within RE:Track. Each workspace corresponds to exactly one software project and one Cognee dataset.

The workspace model provides clear isolation between projects while allowing multiple repositories to be managed independently.

---

# Core Concepts

```
Workspace

    │

    ▼

Repository

    │

    ▼

Cognee Dataset

    │

    ▼

Knowledge Graph

    │

    ▼

Context Packages
```

---

# Entity Model

```
Workspace

├── Repository
├── Dataset
├── Sessions
├── Settings
├── Memory
└── Context Packages
```

---

# Workspace

A Workspace represents a software project managed by RE:Track.

A workspace owns:

- Repository location
- Cognee dataset
- Active sessions
- Project settings
- Generated Context Packages

A workspace should never contain multiple unrelated projects.

---

# Repository

A repository is the source of truth.

It contains:

- Source code
- Documentation
- Configuration
- Assets

The repository is indexed into Cognee using the IndexingService.

---

# Dataset

Every workspace maps to exactly one Cognee dataset.

```
Workspace

↓

Dataset
```

Example:

```
Workspace

LAIOS

↓

Dataset

retrack_laios
```

Datasets isolate project memory and prevent cross-project contamination.

---

# Sessions

Sessions represent temporary working memory.

```
Workspace

↓

Session

↓

remember(session)

↓

recall(session)
```

Sessions are scoped to the active developer task.

Examples:

- Bug Fix
- Feature
- Refactor
- Documentation

---

# Context Packages

Context Packages are generated per task.

```
Workspace

↓

Task

↓

Context Package
```

Packages are transient artifacts generated from permanent memory.

---

# Workspace Lifecycle

```
Create Workspace

        │

        ▼

Select Repository

        │

        ▼

Create Dataset

        │

        ▼

Index Repository

        │

        ▼

Memory Ready

        │

        ▼

Developer Works

        │

        ▼

Generate Context Packages

        │

        ▼

Improve Memory

        │

        ▼

Workspace Updated
```

---

# Repository Synchronization

When files change:

```
Repository

↓

File Change

↓

IndexingService

↓

remember()

↓

Updated Memory
```

Deleted files:

```
Deleted File

↓

forget()

↓

Memory Updated
```

---

# Workspace State

Each workspace maintains:

```
Workspace

├── Name
├── Repository Path
├── Dataset Name
├── Created Date
├── Last Indexed
├── Last Recall
├── Active Sessions
├── Memory Statistics
└── Settings
```

---

# Workspace Settings

Possible settings include:

- Automatic indexing
- File watcher
- Ignore patterns
- Chunk size
- Preferred LLM
- Context size
- Retrieval depth

These settings apply only to the current workspace.

---

# Multi-Workspace Support

RE:Track supports multiple independent workspaces.

```
RE:Track
├── Workspace: Project A (Dataset: project_a)
├── Workspace: Project B (Dataset: project_b)
└── Workspace: Project C (Dataset: project_c)
```

Each workspace has isolated memory.

---

# Design Principles

The workspace model follows these principles:

- One repository per workspace.
- One dataset per workspace.
- Sessions belong to workspaces.
- Memory is isolated.
- Context Packages are generated on demand.

---

# Future Extensions

Potential future enhancements include:

- Multiple repositories per workspace.
- Shared datasets.
- Team workspaces.
- Remote repositories.
- Workspace templates.
- Workspace snapshots.

These are outside the MVP scope.

---

# Success Criteria

A developer should be able to:

1. Create a workspace.
2. Select a repository.
3. Index the project.
4. Start a session.
5. Generate Context Packages.
6. Continue development without manually rebuilding context.

---

# Guiding Principle

A Workspace represents a single software project.

Everything associated with that project—repository, memory, sessions, and Context Packages—should remain isolated and self-contained.

