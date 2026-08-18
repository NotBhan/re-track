# Repository Knowledge Model

## Purpose

This document defines how RE:Track (RefinedEngine Track) represents software repositories as reusable knowledge.

The goal is to move beyond simple code indexing and retrieval toward a structured representation of software engineering knowledge that is portable, token-efficient, and model-agnostic.

---

## Implementation Status

| Knowledge Domain | Status | Description |
|---|---|---|
| Code Knowledge (classes, functions, methods) | ✅ Implemented | Extracted via Python `ast.ClassDef`, `ast.FunctionDef`, and TS export regex |
| Structural Knowledge (folder hierarchy, modules) | ✅ Implemented | `_build_repo_map` with dynamic `.gitignore` filtering |
| AST Call Graph | ✅ Implemented | 2-pass deterministic symbol & import alias resolver (`calls`, `imports`, `inherits`, `renders`) |
| Graph Integrity Invariant | ✅ Implemented | Strict validation: `edge.source, edge.target ∈ node_ids` |
| 5-State Graph Lifecycle | ✅ Implemented | `not_analyzed`, `analyzing`, `analyzed`, `zero_edges`, `failed` |
| Multi-Tier Memory Model | ✅ Implemented | Ingested files, LanceDB vector index, Kùzu graph entities |
| Architectural Heuristics | ✅ Implemented | `_infer_architecture` framework & pattern detection |
| Documentation Knowledge (README) | ✅ Implemented | README purpose & tech stack extraction |

---

# Motivation

Current AI coding workflows repeatedly perform repository understanding during inference.

This results in:

- Repeated retrieval
- Excessive token usage
- Noisy context
- Redundant reasoning
- Dependency on repository documentation quality

RE:Track separates repository understanding from task execution.

Repository understanding becomes an offline process while task execution becomes lightweight knowledge retrieval.

---

# Vision

Transform a software repository into structured knowledge that can later be consumed by:

- Humans
- AI assistants
- IDEs
- MCP servers
- Research pipelines
- Fine-tuning datasets

The extracted knowledge should be reusable without requiring repeated repository analysis.

---

# Repository Knowledge

Repository knowledge consists of multiple knowledge domains rather than only source code.

## Code Knowledge

- Files
- Classes
- Interfaces
- Functions
- Methods
- Enums
- Constants
- Public APIs

---

## Structural Knowledge

- Folder hierarchy
- Package layout
- Module boundaries
- Imports
- Exports
- Dependency graph
- Call graph

---

## Architectural Knowledge

Extracted from documentation when available or inferred from code.

Examples:

- MVC
- Clean Architecture
- Hexagonal Architecture
- Event Driven
- CQRS
- Microservices
- Repository Pattern
- Strategy Pattern

---

## Configuration Knowledge

- Environment variables
- Build configuration
- Dependency versions
- Runtime configuration
- Deployment configuration

---

## Documentation Knowledge

- README
- ADRs (Architecture Decision Records)
- Markdown documentation
- Inline comments
- Code examples

---

## Domain Knowledge

Business concepts represented inside the repository.

Examples:

- Order
- Invoice
- Customer
- Session
- Workspace
- Tenant

---

## Relationship Knowledge

Relationships between software artifacts.

Examples:

- Function A calls Function B
- Class X implements Interface Y
- Service A depends on Repository B
- API Route uses Middleware C

---

# Knowledge Extraction Pipeline

Currently implemented pipeline:

```
Repository
  ↓
IndexingService — .gitignore-aware file discovery
  ↓
RepositorySummaryGenerator
  ├─ _build_repo_map        → DirectoryEntry[] (structural map)
  ├─ _extract_components    → ComponentInfo[] (AST symbols)
  └─ _build_call_graph      → CallNode[], CallEdge[] (call graph)
  ↓
RepositorySummary (persisted to repo metadata store)
  ↓
Frontend (Dashboard)
  ├─ Directory List tab     → filterable symbol/folder list
  └─ Call Graph tab         → interactive force-directed SVG
```

Future pipeline (planned):

```
Knowledge Distillation → Repository Knowledge Base → Portable Knowledge Representation
```

# Knowledge Distillation

Knowledge Distillation converts raw repository information into reusable software knowledge.

Goals:

- Remove redundancy
- Preserve relationships
- Preserve architecture
- Preserve semantics
- Reduce token count

---

# Repository Outputs

A repository may produce multiple output formats.

## Human Bundle

**Target**

Developers

**Format**

Markdown

**Purpose**

Readable project documentation.

---

## AI Bundle

**Target**

Language Models

**Purpose**

Token-efficient repository representation.

Characteristics:

- Deterministic
- Structured
- Compact
- Low redundancy
- Explicit relationships

This format should avoid natural language whenever possible.

---

## Research Dataset

**Target**

Machine Learning

**Purpose**

Structured software engineering datasets.

Potential outputs:

- Knowledge graphs
- Call graphs
- Dependency graphs
- Architecture datasets
- API datasets

---

# Feature Bundles

Knowledge should be partitionable.

Rather than producing one monolithic repository representation, RE:Track should support feature-oriented bundles.

Examples:

- Authentication
- Payments
- Database
- API
- CLI
- Frontend
- Deployment
- Logging
- Observability
- Configuration
- User Management

Task-specific context generation should load only the relevant feature bundles.

---

# Documentation Independence

The system should not depend on repository documentation.

If documentation exists:

- Parse it
- Link it
- Rank it

If documentation does not exist:

Infer knowledge from:

- AST
- Imports
- Call Graph
- Dependency Graph
- Naming conventions
- Directory structure
- Symbol relationships

Architecture inference should function even for undocumented repositories.

---

# Task-aware Context Generation

Knowledge extraction and task-aware retrieval are separate stages.

Repository

↓

Knowledge Base

↓

User Task

↓

Task Analysis

↓

Knowledge Selection

↓

Knowledge Synthesis

↓

AI Context

The knowledge base remains persistent.

The generated context is ephemeral and task-specific.

---

# Future Research

## Repository Knowledge Language

Investigate a compact intermediate representation optimized for language models.

Goals:

- Lower token usage
- Deterministic parsing
- Explicit relationships
- Model independence

---

## Automatic Architecture Inference

Infer:

- Layers
- Services
- Boundaries
- Design patterns
- Workflows

without requiring documentation.

---

## Knowledge Compression

Research question:

How much repository information can be removed while maintaining downstream task performance?

---

## Knowledge Quality

Evaluate:

- Completeness
- Correctness
- Token efficiency
- Retrieval accuracy
- Downstream usefulness

---

# Long-term Vision

RE:Track should become a general-purpose software knowledge engine.

Repository

↓

Knowledge Extraction

↓

Repository Knowledge Base

↓

Knowledge Distillation

↓

Portable Knowledge Representation

↓

Task-aware Context Generation

↓

Any AI Model

↓

Any IDE

↓

Any Research Pipeline

↓

Offline Usage

The repository should be analyzed once and reused many times.
