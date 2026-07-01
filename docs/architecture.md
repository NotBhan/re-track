# AndesContext Architecture

## Overview

AndesContext is a local-first desktop application that provides persistent memory for AI-assisted software development.

The system separates user interaction, business logic, memory orchestration, and persistent storage into independent layers.

Rather than directly exposing Cognee to the frontend, all interactions occur through backend services responsible for indexing repositories, managing sessions, retrieving memory, and generating Context Packages.

---

# High-Level Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                      AndesContext                             │
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
│  WorkspaceService          (planned)                          │
│  IndexingService           ✅ implemented                     │
│  CogneeService             ✅ implemented                     │
│  ContextService            ✅ implemented                     │
│  SessionService            (planned)                          │
│                                                               │
└──────────────────────────────┬────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────┐
│                           Cognee                              │
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
           LanceDB                         Kuzu Graph
                │
                ▼
             SQLite
```

---

# Architectural Principles

The architecture follows four principles:

1. Separation of concerns.
2. Local-first execution.
3. Explicit memory lifecycle.
4. AI-provider independence.

Each service has a single responsibility and communicates through well-defined interfaces.

---

# Layer Responsibilities

## Frontend

Responsible for:

- User interaction
- Project management
- Displaying memory
- Displaying Context Packages
- Settings

The frontend never communicates with Cognee directly.

---

## Backend

Responsible for:

- Repository indexing
- Memory orchestration
- Context generation
- Session management
- IPC endpoints
- Error handling

The backend exposes a stable interface to the frontend while hiding Cognee implementation details.

---

## Cognee

Cognee provides the persistent memory layer.

Its responsibilities include:

- remembering information
- retrieving information
- improving stored knowledge
- forgetting obsolete knowledge

Cognee is treated as infrastructure rather than business logic.

---

# Service Responsibilities

## CogneeService ✅

Thin wrapper around Cognee APIs.

Responsibilities:

- initialize providers (Ollama, LanceDB, Kuzu, SQLite)
- configure Cognee's internal config singleton
- remember
- recall
- improve
- forget

No business logic exists here. All Cognee interactions go through this service.

Implementation: `backend/app/services/cognee_service.py`

---

## IndexingService ✅

Repository indexing pipeline.

Responsibilities:

- discover repository files
- apply ignore rules (`.git/`, `node_modules/`, etc.)
- filter supported file types (`.py`, `.ts`, `.md`, etc.)
- batch ingestion into Cognee
- report indexing progress

Implementation: `backend/app/services/indexing_service.py`

---

## ContextService ✅

Orchestrates memory retrieval and delegates to PackageBuilder.

Responsibilities:

- retrieve memories via CogneeService (with timing)
- delegate package assembly to PackageBuilder
- pass RepositorySummary to PackageBuilder

This service is the entry point for Context Package generation.

Implementation: `backend/app/services/context_service.py`

---

## PackageBuilder ✅

Assembles Context Packages from pipeline output.

Responsibilities:

- orchestrate retrieval pipeline (dedup → rank → compress → categorize)
- build sections from categorized results
- apply budget enforcement
- resolve references
- render Markdown
- generate package metadata

Implementation: `backend/app/services/package_builder.py`

---

## BudgetManager ✅

Enforces soft-target token budgets on sections.

Responsibilities:

- prioritize sections by importance (Critical/High/Medium/Low)
- remove low-priority sections when over budget
- compress high-priority sections at line boundaries
- track compression ratio

Implementation: `backend/app/services/budget_manager.py`

---

## MarkdownRenderer ✅

Renders structured package data as Markdown.

Responsibilities:

- render Task, Objective, Repository Context, Sections, References
- skip empty sections
- render Repository Summary when available

Implementation: `backend/app/services/renderer.py`

---

## RepositorySummaryGenerator ✅

Generates stable project knowledge from indexed files.

Responsibilities:

- extract technology stack from file extensions
- build repository directory map
- infer architecture from structure
- extract key components
- infer project purpose from README

Implementation: `backend/app/services/repository_summary.py`

---

## Pipeline Stages ✅

Independent, composable retrieval processing stages.

- **Deduplicator**: removes duplicate memories via normalized text
- **Ranker**: multi-factor scoring (semantic × confidence × type weight)
- **Compressor**: merges redundant entries, preserves executable facts
- **Categorizer**: rule-based classification into section types
- **ReferenceResolver**: formats traceable citations with provenance

Implementation: `backend/app/services/pipeline/`

---

## WorkspaceService (planned)

Manages repositories.

Responsibilities:

- create workspace
- open workspace
- close workspace
- map repositories to datasets

---

## SessionService (planned)

Manages active development sessions.

Responsibilities:

- create session
- close session
- working memory
- session metadata

---

# Data Flow

Repository

↓

IndexingService

↓

CogneeService.remember()

↓

Persistent Memory (LanceDB + Kuzu + SQLite)

↓

Developer Request

↓

ContextService.generate_context_package()

↓

CogneeService.recall() (timed)

↓

PackageBuilder.build()

↓

Dedup → Rank → Compress → Categorize → Budget → References → Render

↓

Context Package (Markdown + metadata + references)

↓

Coding LLM

---

# Backend Package Structure

```
backend/app/
    __init__.py
    config/
        __init__.py
        settings.py          # Centralized env loading, provider config, validation
    core/
        __init__.py
        logging.py           # Structured logging setup
    models/
        __init__.py
        errors.py            # Exception hierarchy
        responses.py         # Data models (ContextPackage, RepositorySummary, PackageMetadata, etc.)
    services/
        __init__.py
        cognee_service.py    # Thin Cognee wrapper
        indexing_service.py  # Repository indexing pipeline
        context_service.py   # Entry point for Context Package generation
        package_builder.py   # Pipeline orchestrator
        budget_manager.py    # Token budget enforcement
        renderer.py          # Markdown rendering
        repository_summary.py # Repository Summary generator
        stats_logger.py      # Package statistics logging
        pipeline/
            __init__.py
            dedup.py         # Deduplication stage
            ranking.py       # Multi-factor ranking stage
            compression.py   # Semantic compression stage
            categorization.py # Rule-based categorization stage
            references.py    # Reference resolution stage
    api/
        __init__.py          # ✅ implemented — API command exports
        commands.py          # ✅ implemented — Async commands (health, index, context, forget)
        schemas.py           # ✅ implemented — Pydantic request/response models
    utils/
        __init__.py
```

---

# Configuration

All configuration flows through `backend/app/config/settings.py`.

Settings are loaded from environment variables with `.env` support.

Cognee's internal config is set via `cognee.config.set_*()` methods — Cognee does not read from `os.environ` directly.

Key environment variables:

| Variable | Value | Purpose |
|----------|-------|---------|
| `LLM_MODEL` | phi3:mini | Structured output compatible |
| `EMBEDDING_MODEL` | nomic-embed-text:latest | 768-dim embeddings |
| `HUGGINGFACE_TOKENIZER` | nomic-ai/nomic-embed-text-v1 | Required by embedding engine |
| `CACHING` | false | Disable session memory overhead |
| `COGNEE_SKIP_CONNECTION_TEST` | true | Skip startup latency |

---

# Design Constraints

The MVP intentionally excludes:

- Multi-user collaboration
- Cloud synchronization
- Distributed memory
- Plugin architecture
- Autonomous coding agents
- Graph visualization

These features may be explored after the hackathon but are outside the initial scope.

---

# Technology Stack

Frontend

- React
- TypeScript
- Vite
- Tauri

Backend

- Python 3.13
- Pydantic (settings, models)

Memory

- Cognee 1.2.2

Storage

- LanceDB (vectors)
- Kuzu (graph)
- SQLite (metadata)

Models

- Ollama
- phi3:mini (LLM)
- nomic-embed-text:latest (embeddings)

---

# Guiding Principle

AndesContext is not an AI coding assistant.

It is a persistent memory layer that enables AI coding assistants to understand software projects with significantly less context.

Every architectural decision should support this objective.
