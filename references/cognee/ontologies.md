# Ontologies

## Purpose

An ontology defines the types of entities and relationships that Cognee should extract from ingested data.

Instead of treating documents as generic text, an ontology gives semantic meaning to the extracted knowledge.

For RE:Track, ontologies enable Cognee to understand software engineering concepts rather than simply indexing source code.

---

# Concept

```
Repository

        │

        ▼

remember()

        │

        ▼

Ontology

        │

        ▼

Entity Extraction

        │

        ▼

Knowledge Graph
```

---

# Why Ontologies Matter

Without an ontology:

```
README.md

↓

Entity

↓

Authentication
```

With an ontology:

```
README.md

↓

Feature

↓

Authentication

↓

Uses

↓

JWT

↓

Depends On

↓

Database
```

The resulting graph is significantly richer.

---

# RE:Track Ontology

Potential entity types:

```
Repository

Module

Package

Class

Function

API

Feature

Bug

Architecture Decision

Coding Convention

TODO

Configuration

Environment Variable

Dependency

Database

External Service

Documentation

Test

Issue

Pull Request
```

---

# Possible Relationships

```
USES

DEPENDS_ON

IMPLEMENTS

CALLS

RETURNS

IMPORTS

EXTENDS

INHERITS

CONFIGURES

FIXES

INTRODUCES

REFERENCES

DOCUMENTS

BELONGS_TO

REPLACES

DEPRECATES
```

---

# Example Software Graph

```
Feature

Authentication

        │

        IMPLEMENTS

        │

        ▼

JWT Service

        │

        DEPENDS_ON

        │

        ▼

Database

        │

        USED_BY

        │

        ▼

User API
```

---

# Example — Custom Prompt

```python
await cognee.remember(

    data="./src",

    dataset_name="re_track",

    custom_prompt="""
Extract:

- Features
- Modules
- APIs
- Architecture Decisions
- Coding Conventions
- TODOs
- Bugs
- Dependencies
- Relationships
"""
)
```

---

# Example — Documentation Import

```python
await cognee.remember(

    data="./docs",

    dataset_name="re_track",

    custom_prompt="""
Focus on:

- Architecture
- System Design
- Interfaces
- Design Decisions
- Constraints
"""
)
```

---

# Example — Source Code Import

```python
await cognee.remember(

    data="./src",

    dataset_name="re_track",

    custom_prompt="""
Identify:

- Classes
- Functions
- Imports
- APIs
- Dependencies
- Services
"""
)
```

---

# RE:Track Workflow

```
Repository

↓

remember()

↓

Ontology

↓

Entity Extraction

↓

Knowledge Graph

↓

recall()

↓

Context Package
```

---

# Best Practices

- Keep entity types stable.
- Prefer meaningful engineering concepts.
- Avoid excessive ontology complexity.
- Reuse entity definitions across projects.
- Expand incrementally.

---

# Common Pitfalls

- Too many entity types.
- Ambiguous relationships.
- Generic entities with no engineering meaning.
- Treating every identifier as an entity.

---

# Future RE:Track Ontology

Possible future entity categories:

```
Architecture

Feature

Implementation

Testing

Deployment

Performance

Security

Documentation

Configuration

Developer Workflow
```

These higher-level concepts could produce significantly more useful Context Packages.

---

# RE:Track Design Notes

The ontology is one of the primary ways RE:Track can improve retrieval quality.

Instead of retrieving arbitrary chunks of text, Cognee can retrieve structured engineering knowledge such as:

- Architectural decisions
- API contracts
- Feature ownership
- Dependencies
- Design rationale
- Coding conventions

This allows smaller language models to receive more precise and relevant context.

---

# Related APIs

- remember()
- recall()
- improve()

---

# Related Concepts

- Datasets
- Sessions
- Node Sets
- Global Context Index

---

# Related Source

```
cognee/core-concepts/further-concepts/ontologies
```

