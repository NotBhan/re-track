# Retrieval Arbitration & Evidence Ordering

## Overview

RE:Track's **Retrieval Arbitration Pipeline** is an authority-first decision engine that unites multi-modal retrieval mechanisms across filesystem source code, deterministic AST call graphs, vector embeddings, and semantic memory.

---

## Authority Ordering

Evidence is structured into four distinct tiers:

1. **Tier 1 — Filesystem Verified Source**:
   - Direct source code snippets, line ranges, and verified content extracted from the repository workspace.
   - Highest authority; represents ground truth code.

2. **Tier 2 — Manifest 2.0 AST**:
   - Tree-sitter parsed functions, classes, interfaces, React components, and deterministic call/import edges.
   - Structural authority; represents precise topological coupling.

3. **Tier 3 — Validated LanceDB & Kùzu Projections**:
   - Vector similarity embeddings and cached graph relationships validated against the active repository manifest.

4. **Tier 4 — Validated Cognee Semantic Memory**:
   - Semantic document memories validated against source file fingerprints.

---

## Lexicographic Ranking & Guarantees

- **Lexicographic Hierarchy**: Candidates are compared by `(TierPriority, Relevance, Confidence, Specificity)`. High semantic similarity in Tier 4 will **never** outrank code in Tier 1 or Tier 2.
- **Budget Reservation**: Token budgets are allocated to Tier 1 and Tier 2 first. Tier 3 and 4 only occupy residual capacity.
- **Stale Memory Isolation**: If a source file is edited or deleted, any derived memory record associated with the prior SHA-256 fingerprint is immediately pruned before ranking.
- **Abstention Gating**: If no concrete code or AST symbols exist for a requested feature, the system returns an authoritative Abstention Package, preventing model hallucination.
