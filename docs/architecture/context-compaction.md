# Context Compaction & Budget Contract

Authoritative reference for how a requested context budget (`max_tokens`) is
accounted for and how repository evidence is packed to fit it.

Applies to the agent-context path (`POST /api/v1/context`,
`ContextUseCases.get_agent_context`) and to the MCP `get_agent_context` tool.

---

## 1. Why this exists

The previous budget mechanism was an allocation of *position*:

- `BudgetManager` removed low/medium package sections, then cut the remaining
  high-priority sections to their **first 50 %** — a tail truncation.
- `RetrievalArbitrator` evicted candidates whose token estimate did not fit and
  force-admitted the first Tier-1 candidate even when it alone exceeded the
  budget; oversized candidates were never reduced.
- The synthesis prompt capped evidence by list position
  (`relevant_snippets[:6]`, `matched_file_rels[:10]`, `tier3_memories[:4]`).
- The delivered markdown was assembled with **no budget at all**.

Measured consequence on a real repository (before this change):

| Requested | Delivered (estimated) | Effect |
| :--- | :--- | :--- |
| 2048 | 2512 tokens | 22 % over budget |
| 8192 | 2669 tokens | 67 % under budget — the budget bought nothing |

Compaction now decides **what the budget buys**, in authority order, and always
records what it removed.

---

## 2. Budget contract

`max_tokens` is the maximum estimated size of everything the caller receives and
everything the model request contains as input. It is split explicitly:

```text
requested_tokens
├── task_prompt_tokens        developer task, verbatim (never reduced)
├── fixed_overhead_tokens     system instructions + synthesis scaffolding
├── output_reservation_tokens generation allowance (0 when no model is invoked)
└── evidence_budget_tokens    everything the budget may spend on repository evidence
```

Rules:

1. The evidence allowance is the **remainder**, never the headline number.
2. The generation cap sent to the provider is the reservation
   (`clamp(requested/4, 256, 4096)`), never the input context budget.
3. After synthesis the evidence is **re-packed** around the answer the model
   actually produced, so a verbose answer shrinks the evidence instead of
   pushing the package over budget. The answer itself is never truncated.
4. If the task prompt plus fixed scaffolding alone exceed the requested budget,
   the plan reports an over-committed state (`evidence_budget_floored`,
   `degradation_reason=fixed_prompt_overhead_exceeds_budget`) instead of
   silently shrinking the task.
5. A budget under `MIN_EVIDENCE_BUDGET_TOKENS` (64) floors the evidence
   allowance and is reported, never hidden.
6. The four components are **disjoint**. The synthesis scaffold embeds the task
   verbatim, so the fixed overhead is measured with `include_task=False` and the
   task is owned solely by `task_prompt_tokens`. Measuring the scaffold with the
   task included would count it twice and shrink the evidence allowance by the
   size of the task prompt — exactly the evidence the budget exists to buy.
7. The estimator floors each fragment independently, so the itemised sum can
   differ from the assembled request by a few tokens. The residual is bounded by
   the number of measured fragments and is far below the estimator's own error
   (limitation 2); the contract is audited with the single char-4 estimator, not
   a second tokenizer.

### Token accounting

One estimator, defined once in `app/services/token_budget.py`:

```python
estimate_tokens(text) = 0 if text is blank else max(1, len(text) // 4)
```

This is the project-wide char-4 heuristic already used by
`PackageMetadata.estimated_tokens`, `BudgetManager` and the benchmark runner
(`tokenizer_name="character-4b-heuristic"`). No second estimator is introduced.

---

## 3. Evidence priority

Candidates carry the existing arbitration signals — no new scoring system.

- **Order:** `(authority tier, relevance, confidence, specificity, id)` — the
  exact lexicographic key produced by `RetrievalArbitrator`, with a stable
  string tie-break so packing is byte-for-byte reproducible.
- **Truth hierarchy:** source truth > deterministic AST > derived retrieval >
  semantic memory. A lower tier can never displace a higher tier.
- **Mandatory evidence** (never dropped, never reduced below the reference level
  by choice):
  - the highest-ranked Tier-1 source artifact for the task (always at least one),
  - Tier-1 artifacts matching an extracted task symbol or a task-referenced file,
  - Tier-2 AST symbols/definitions matching a task symbol exactly,
  - Tier-2 call relationships touching a selected task symbol (the "connecting
    evidence" between the task's symbols and the source artifacts).
- **Coherence (Phase 6):** supporting evidence is attached to the highest-ranked
  source artifact it explains (same file, symbol mentioned in the body), so a
  snippet, its symbols and its call edges are packed as one group. Mandatory
  structural evidence forms its own group so it can never be dropped together
  with a non-mandatory artifact.
- **Hard negatives are untouched:** abstention still happens in
  `EvidenceService` *before* packing. The compactor never invents evidence and
  never turns an abstention into a package.

---

## 4. Algorithm

`ContextCompactor.compact()` runs three deterministic passes over
`EvidenceGroup`s (coherent evidence units):

1. **Allocate** — every group receives an equal fair share of what remains, and
   is rendered at the *least reduced* level that fits its share. The
   highest-ranked artifact cannot consume the whole budget and starve the
   evidence that explains it.
2. **Correct** — if the measured document still exceeds the target, the
   *lowest-ranked* group is reduced one level; when it is already at the last
   level it is dropped (with a reason). High-authority evidence is the last to
   be reduced and the last to be dropped.
3. **Grow** — any unallocated budget is spent restoring fidelity, highest-ranked
   evidence first. This is what makes a larger budget buy *more* evidence rather
   than the same evidence. Relevant-region entries grow in place.

Sources are packed before relationships, which are packed before derived memory
and derived recall, mirroring the truth hierarchy in the rendered document.

---

## 5. Reduction ladder

| Level | Name | Behaviour |
| :--- | :--- | :--- |
| 0 | `full` | Complete task-relevant evidence. |
| 1 | `normalized` | Redundant whitespace, repeated lines and metadata prefixes removed. |
| 2 | `relevant_region` | Single contiguous window around the task terms, **grown to the allowance** so no budget is wasted; elided line count is stated. |
| 3 | `symbol_body` | The enclosing definition block (indentation/brace aware) containing the match. |
| 4 | `signatures_and_control_flow` | Signatures, declarations and control flow; pure body lines elided with an explicit marker. |
| 5 | `evidence_reference` | Provenance only: path, line range, symbols found, and an explicit "source omitted to satisfy the context budget" notice. |

Provenance (file path + line range) is preserved at **every** level. Removed
line ranges are marked with `# [...] N lines elided by budget` — a reduced block
can never be mistaken for complete source. Structural facts (single-line symbols,
call edges) compact in place, keeping the relationship intact. Derived recall
blocks reduce head-first and end as an explicit reference.

No LLM is invoked to compress. Summarisation is limited to the deterministic
reduction above.

### Reasoning traces

A reasoning model can exhaust its generation reservation *inside* a `<think>`
block. The closing tag is then never emitted, so the complete-block regex cannot
match and the raw trace would be delivered as though it were the answer — which
is what happens at a tight budget, where the reservation is smallest. Both the
synthesis step and `EvidenceService.sanitize_and_validate_grounded_response`
therefore also drop an **unclosed** reasoning block (splitting on the opening
tag), matching the deterministic convention already established by
`semantic_memory_generator`. If sanitisation leaves no usable synthesis, the
package falls back to the deterministic compacted evidence instead of shipping
truncated reasoning.

---

## 6. Impossible budgets

When mandatory evidence cannot fit even at level 5:

- mandatory evidence is still packed (never silently dropped);
- `mandatory_evidence_fit=false` and
  `notes=["mandatory_evidence_exceeds_allowance"]` are reported;
- non-mandatory evidence is dropped first, each with
  `reason="budget_exhausted_after_max_reduction"`;
- if the package still exceeds the request, `degraded=true` with an explicit
  `degradation_reason` (`fixed_prompt_overhead_exceeds_budget`,
  `mandatory_evidence_exceeds_budget`, or
  `final_package_exceeds_requested_budget` when a provider ignored its
  generation cap) and `budget_satisfied=false`.

---

## 7. Telemetry

Returned as `AgentContextResponse.compaction` and logged as
`context_compaction_completed`.

| Field | Meaning |
| :--- | :--- |
| `requested_tokens` | The requested budget. |
| `task_prompt_tokens` / `fixed_overhead_tokens` / `output_reservation_tokens` / `planned_output_reservation_tokens` / `evidence_budget_tokens` | The budget split. |
| `pre_compaction_tokens` | Size of all evidence before packing. |
| `evidence_tokens` / `final_tokens` | Delivered evidence and delivered package (measured). |
| `candidates_before` / `candidates_after` | Artifacts considered vs retained. |
| `retained[]` | id, tier, kind, level, level name, tokens before/after, provenance, mandatory flag. |
| `reduced[]` | Retained artifacts whose level is > 0. |
| `omitted[]` | id, tier, kind, tokens, reason, provenance, mandatory flag. |
| `levels_used` | Per-group reduction level (the packing decisions). |
| `top_evidence[]` | Highest-priority evidence retained. |
| `mandatory_evidence_tokens` / `mandatory_evidence_fit` / `unplaced_mandatory` | Mandatory-evidence accounting. |
| `budget_satisfied` / `degraded` / `degradation_reason` | Whether the request was met, and why not. |
| `evidence_reduction` | Measured fraction of the pre-compaction evidence text removed (0.0 = nothing removed). |
| `notes` | Plan notes (`evidence_budget_floored`, `file_index_capped:N`, `re_packed_for_observed_synthesis`). |

No fabricated percentages: every number is measured from the delivered text.

---

## 8. Determinism

- Sorting uses `(tier, relevance, confidence, specificity, id)` with explicit
  string tie-breaks; no randomness, sampling, clock or dict-order dependence.
- The same repository state, task, retrieval result and budget produce byte
  identical output, independent of input candidate order.
- Intent category is never an input to packing — an unknown category packs
  exactly like a known one.

---

## 9. Known limitations

1. **Evidence is bounded by retrieval.** `SourceSearchService` extracts at most
   5 snippets of ~29 lines and `_extract_ast_call_context` caps symbols/edges, so
   above roughly 2.5 K tokens a larger budget cannot buy more evidence — the
   package is evidence-limited, not budget-limited (`evidence_reduction = 0.0`
   makes this explicit). Widening retrieval is a separate change.
2. **Estimator, not provider tokenizer.** Char-4 can differ from the provider's
   tokenizer by a few percent; the contract is measured with RE:Track's single
   estimator, and a provider that ignores its generation cap is reported as
   degraded rather than masked.
3. **`PackageBuilder`/`BudgetManager`** still serve the deterministic
   `generate_context` package path; the agent path no longer depends on them.
4. **Recall-package content** is available only in the deterministic fallback
   (it duplicates arbitration evidence otherwise), where it is packed as the
   lowest authority tier and dropped first.
