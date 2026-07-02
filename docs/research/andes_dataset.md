# AndesDataset

## Status

Future Research Scope

---

## Vision

AndesDataset extends AndesContext from a repository understanding system into an automated software knowledge dataset generation pipeline.

Instead of collecting raw source code, AndesDataset extracts structured, validated knowledge from repositories that can be used for machine learning, retrieval systems, benchmarking, and software engineering research.

The objective is to generate high-quality datasets describing software systems rather than merely storing source files.

---

## Motivation

Current code datasets primarily contain source code.

Large language models must infer architecture, relationships, design decisions, APIs, and dependencies directly from raw code.

AndesDataset shifts this effort offline by extracting explicit software knowledge before training or indexing.

---

## Goals

- Generate structured software knowledge datasets
- Produce architecture-aware training data
- Create reusable benchmark datasets
- Support supervised fine-tuning
- Support retrieval systems
- Enable software engineering research

---

## Potential Dataset Types

### Architecture Dataset

Repository architecture

Module relationships

Layer boundaries

Component interactions

---

### API Dataset

Public interfaces

Parameters

Return values

Exceptions

Usage examples

---

### Dependency Dataset

Internal dependencies

External packages

Import graph

Call graph

---

### Function Dataset

Function summaries

Responsibilities

Inputs

Outputs

Complexity

---

### Documentation Dataset

Documentation generation targets

Documentation quality evaluation

Documentation completeness

---

### Repository Evolution Dataset

Architecture evolution

Dependency evolution

Refactoring history

Breaking changes

---

### Design Pattern Dataset

Detected design patterns

Architectural styles

Common implementation strategies

---

## Research Questions

- Can software knowledge improve training compared to raw code?
- Which extracted representations are most useful?
- Can architecture-aware datasets improve reasoning?
- How much redundancy can be removed without losing information?

---

## Long-Term Vision

AndesDataset becomes a general-purpose software knowledge extraction pipeline capable of producing datasets suitable for training future software engineering language models.
