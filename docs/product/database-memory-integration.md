# Database & Memory Integration Guide (Phase 10D.4)

## 1. Overview

RE:Track utilizes a multi-tiered memory and storage architecture designed for speed, deterministic correctness, and grounded AI context generation.

Every piece of information stored in RE:Track has a strict origin:
1. **Source Code & Manifest**: The ultimate ground truth.
2. **Knowledge Graphs (Kùzu)**: Structural relationships between classes, functions, files, and modules.
3. **Vector Embeddings (LanceDB)**: Semantic search indexes over code chunks.
4. **Context Cache**: Sub-millisecond retrieval of grounded context packages.

---

## 2. Provenance Guarantee

When you query RE:Track for context:
- Every cited symbol or file path is validated against the active repository manifest.
- Stale memory from edited or deleted files is automatically pruned.
- If a database subsystem is unavailable (e.g. vector search is offline), deterministic AST code search continues to work seamlessly without hallucinating answers.

---

## 3. Storage Subsystems at a Glance

| Subsystem | Storage Technology | Purpose | Truth Boundary |
|---|---|---|---|
| **Manifest & AST** | JSON (`~/.retrack/manifests/`) | File checksums, symbol definitions, and AST call graphs. | **Authoritative** |
| **Vector Space** | LanceDB (`~/.retrack/lancedb/`) | Fast similarity search over code chunks. | **Derived** |
| **Graph Topology** | Kùzu (`~/.retrack/kuzu/`) | Property graph queries for structural dependencies. | **Derived** |
| **Context Cache** | In-Memory LRU Cache | Fast retrieval of validated context packages. | **Ephemeral** |

---

## 4. Troubleshooting Memory & Storage

- **"Dataset Staged / Not Cognified"**: Source files have been indexed into the manifest. Semantic embeddings and deep entity graphs can be generated on demand.
- **"Database Degraded"**: A storage component encountered an issue (e.g. disk write lock). Deterministic AST and file search remain fully operational.
