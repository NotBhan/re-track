# Semantic Memory Quality & Retrieval Capabilities

## Overview

RE:Track's Semantic Memory engine integrates local Cognee vector and graph storage to provide long-lived, high-level understanding of codebase architecture.

Semantic memories compress complex multi-file relationships into concise architectural concepts, enabling developer agents to quickly grasp high-level system flows while maintaining strict grounding in authoritative source code.

---

## Core Capabilities

### 1. Weak-Lexical Semantic Bridge
When a developer asks conceptual questions that don't match exact identifier names (e.g., *"Where is background job execution handled?"*), semantic memory matches the conceptual description and retrieves the relevant classes (`JobScheduler`, `TaskQueue`, `WorkerPool`).

### 2. Multi-Hop Cross-File Discovery
In event-driven or layered architectures, calls span across multiple decoupled files. Semantic memory links publishers to handlers and mailers in a single cohesive retrieval candidate.

### 3. Context Compression
Instead of saturating context windows with 15 raw source files, semantic memory provides a verified architectural summary, reducing context token costs by over 50% for high-level tasks.

---

## Safety & Authority Principles

1. **Ground Truth Authority**: Only files and deterministic AST definitions in Manifest 2.0 represent ground truth.
2. **Deterministic Abstention**: If a requested feature does not exist in the code, semantic memory cannot manufacture it. The system transparently reports code absence.
3. **Instant Invalidation**: Editing or deleting source files immediately invalidates related semantic memories on subsequent index operations.
4. **Zero-Overhead Exact Search**: Precision for direct symbol searches (`def create_order`) is preserved without degradation from semantic abstractions.

---

## Evaluation Benchmark Summary

| Metric | Target | Measured Result | Status |
| :--- | :--- | :--- | :--- |
| **Recall@K** | `>= 0.70` | `0.889` | ✅ EXCEEDS |
| **Precision@K** | `>= 0.75` | `0.833` | ✅ PASS |
| **Critical Evidence Coverage** | `>= 0.90` | `1.000` | ✅ PASS |
| **Relationship Coverage** | `>= 0.80` | `1.000` | ✅ PASS |
| **Noise Ratio** | `<= 0.20` | `0.000` | ✅ PASS |
| **Regression Rate** | `0.0%` | `0.0%` | ✅ PASS |
