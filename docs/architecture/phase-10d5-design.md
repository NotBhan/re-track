# Phase 10D.5 Architecture Design: End-to-End Retrieval Arbitration

## 1. Executive Summary

Phase 10D.5 establishes an authoritative **End-to-End Retrieval Arbitration Pipeline** in RE:Track. The pipeline combines source search, deterministic AST relationships, and validated derived memory into a single authority-first retrieval system before evidence gating and model synthesis.

---

## 2. Authority Hierarchy & Lexicographic Ranking

### 2.1 Four Authority Tiers

```
┌────────────────────────────────────────────────────────┐
│ Tier 1: filesystem_verified_source (Priority: 4)       │
│ Authoritative code snippets, exact file paths, lines   │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│ Tier 2: manifest_ast (Priority: 3)                     │
│ Deterministic AST call nodes, symbols, imports, edges   │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│ Tier 3: validated_lancedb_kuzu (Priority: 2)           │
│ Vector embeddings & graph projections with valid prov  │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│ Tier 4: validated_cognee (Priority: 1)                 │
│ Semantic memory dataset items with valid provenance    │
└────────────────────────────────────────────────────────┘
```

### 2.2 Lexicographic Sorting Contract

Every retrieval candidate is evaluated into an `ArbitratedCandidate` and assigned a comparison tuple:

$$\text{SortKey} = (\text{TierPriority}, \text{RelevanceScore}, \text{Confidence}, \text{Specificity})$$

Because `TierPriority` is the primary tuple key, any candidate in a higher authority tier unconditionally outranks candidates in lower tiers, regardless of semantic similarity scores.

---

## 3. Token Budget Reservation & Non-Eviction Guarantee

1. **Reserved Authoritative Allocation**:
   - The token budget is first allocated to Tier 1 (`filesystem_verified_source`) and Tier 2 (`manifest_ast`) candidates.
2. **Subordinate Fill**:
   - Lower tiers (Tier 3 and Tier 4) only fill remaining unallocated token capacity.
3. **Strict Non-Eviction**:
   - A candidate from Tier 3 or Tier 4 cannot displace, evict, or downrank any candidate from Tier 1 or Tier 2.

---

## 4. Evidence Gate & LLM Boundaries

- **Single Gate Authority**: `EvidenceService` remains the sole authority for evidence gating and synthesis authorization. `RetrievalArbitrator` feeds structured, ranked candidates to `EvidenceService` without making synthesis decisions.
- **LLM Isolation**: LLM synthesis output is not a source of truth and never re-enters the retrieval arbitration pipeline.
- **Prompt Vocabulary Isolation**: Keywords and tokens in user prompts are treated exclusively as query intent, never as observed repository symbols.
- **Path Existence Invariant**: File path existence alone without matched code content or symbol definitions is insufficient to satisfy an evidence gate.
