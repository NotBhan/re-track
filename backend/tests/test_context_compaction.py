"""Deterministic tests for budget-aware context compaction.

These tests pin the replacement of tail truncation with explicit, evidence-aware
packing:

- budget accounting (task, prompt overhead, output reservation, evidence)
- multi-budget packing (2K / 4K / 8K / 16K) with intentional evidence selection
- priority: high-authority evidence outlives low-authority evidence
- no arbitrary tail loss (critical evidence at the end of an artifact survives)
- provenance preservation at every reduction level
- mandatory evidence handling and impossible-budget behaviour
- deterministic repeatability and input-order independence
- category independence and hard-negative (no evidence) behaviour
"""

from pathlib import Path
import tempfile
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.container import ApplicationContainer
from app.application.domain.arbitration import ArbitratedCandidate, AuthorityTier
from app.application.dto import AgentContextRequest, AgentContextResponse
from app.application.ports.llm_provider import LLMProviderPort
from app.application.use_cases.context import (
    _SYNTH_SYSTEM_PROMPT,
    ContextUseCases,
    build_synthesis_user_prompt,
)
from app.models.provider import ProviderType
from app.services.context_compactor import (
    LEVEL_NAMES,
    LEVEL_REFERENCE,
    ContextCompactor,
    EvidenceGroup,
    EvidenceItem,
    EvidenceRenderer,
    derive_task_terms,
)
from app.services.intent_parser import IntentParserService
from app.services.source_search_service import SourceSearchService
from app.services.token_budget import (
    MIN_EVIDENCE_BUDGET_TOKENS,
    estimate_tokens,
    plan_context_budget,
)
from app.services.workspace_authorization_service import WorkspaceAuthorizationService

TASK = "How does enforce_context_budget enforce the requested context budget?"
SYMBOLS = ["enforce_context_budget"]


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def candidate(
    cid: str,
    tier: AuthorityTier,
    content: str,
    *,
    kind: Optional[str] = None,
    relevance: float = 0.9,
    confidence: float = 0.9,
    specificity: float = 0.8,
    symbol: Optional[str] = None,
    file: str = "",
    line_start: Optional[int] = None,
    line_end: Optional[int] = None,
) -> ArbitratedCandidate:
    """Build an arbitration candidate exactly as the arbitrator would emit it."""
    return ArbitratedCandidate(
        id=cid,
        tier=tier,
        content=content,
        source_file=file,
        source_symbol=symbol,
        relationship_kind=kind,
        relevance=relevance,
        confidence=confidence,
        specificity=specificity,
        line_start=line_start,
        line_end=line_end,
        token_estimate=max(1, len(content) // 4),
    )


def source_candidate(
    cid: str = "src-0",
    path: str = "backend/app/services/engine.py",
    start: int = 1,
    body_lines: Optional[list[str]] = None,
    relevance: float = 0.8,
) -> ArbitratedCandidate:
    """A Tier-1 filesystem-verified source snippet in the real extractor format."""
    lines = body_lines if body_lines is not None else [f"value_{i} = compute({i})" for i in range(120)]
    end = start + len(lines) - 1
    content = f"### `{path}` (Lines {start}-{end})\n```\n" + "\n".join(lines) + "\n```"
    return candidate(
        cid,
        AuthorityTier.TIER_1_SOURCE,
        content,
        file=path,
        relevance=relevance,
        line_start=start,
        line_end=end,
    )


def memory_candidate(cid: str, text: str, relevance: float = 0.6) -> ArbitratedCandidate:
    return candidate(cid, AuthorityTier.TIER_4_COGNEE, text, relevance=relevance)


def big_file_with_critical_function() -> tuple[ArbitratedCandidate, str, str]:
    """A large file whose only task-relevant function sits at the very end."""
    filler = [f"    unrelated_step_{i} = helper_{i}(payload)" for i in range(400)]
    critical = "def enforce_context_budget(plan, evidence):\n    return plan.fit(evidence)"
    body = filler + critical.splitlines()
    cand = source_candidate(path="backend/app/services/engine.py", start=1, body_lines=body, relevance=1.0)
    return cand, cand.content, "enforce_context_budget"


def broad_evidence_set(count: int = 16, tokens_per_snippet: int = 120) -> list[ArbitratedCandidate]:
    """Many moderately relevant source artifacts, enough to exercise every budget."""
    candidates: list[ArbitratedCandidate] = []
    for index in range(count):
        lines = [f"payload_{index}_{j} = transform_{index}({j})" for j in range(tokens_per_snippet)]
        candidates.append(
            source_candidate(
                cid=f"src-{index}",
                path=f"backend/app/services/module_{index}.py",
                start=index * 10 + 1,
                body_lines=lines,
                relevance=max(0.3, 0.95 - index * 0.03),
            )
        )
    return candidates


def compact(
    candidates: list[ArbitratedCandidate],
    budget: int,
    *,
    task: str = TASK,
    symbols: Optional[list[str]] = None,
    terms: Optional[list[str]] = None,
    model_reserved: bool = False,
    overhead_text: str = "system instructions " * 20,
    relevant_files: Optional[list[str]] = None,
    missing_evidence: Optional[list[str]] = None,
    title: str = "budget enforcement",
    compactor: Optional[ContextCompactor] = None,
):
    """Run one deterministic compaction pass."""
    plan = plan_context_budget(
        requested_tokens=budget,
        task_prompt=task,
        fixed_overhead_text=overhead_text,
        model_reserved=model_reserved,
    )
    return (compactor or ContextCompactor()).compact(
        candidates=candidates,
        plan=plan,
        task_prompt=task,
        title=title,
        task_terms=terms if terms is not None else derive_task_terms(task, symbols or []),
        task_symbols=symbols if symbols is not None else SYMBOLS,
        relevant_files=relevant_files or [],
        missing_evidence=missing_evidence or [],
    )


# ---------------------------------------------------------------------------
# Phase 2 — budget accounting
# ---------------------------------------------------------------------------


class TestBudgetAccounting:
    def test_estimator_matches_project_char4_heuristic(self):
        assert estimate_tokens("") == 0
        assert estimate_tokens("   ") == 0
        assert estimate_tokens("abcd") == 1
        assert estimate_tokens("x" * 400) == 100

    def test_budget_plan_accounts_for_every_component(self):
        plan = plan_context_budget(4096, "Fix the bug", fixed_overhead_text="sys " * 50, model_reserved=True)
        assert plan.requested_tokens == 4096
        assert plan.task_prompt_tokens == estimate_tokens("Fix the bug")
        assert plan.fixed_overhead_tokens == estimate_tokens("sys " * 50)
        assert plan.output_reservation_tokens > 0
        assert plan.accounted_tokens == (
            plan.task_prompt_tokens
            + plan.fixed_overhead_tokens
            + plan.output_reservation_tokens
            + plan.evidence_budget_tokens
        )
        assert plan.accounted_tokens <= plan.requested_tokens

    def test_budget_plan_without_model_reserves_no_output(self):
        plan = plan_context_budget(4096, "Fix the bug", fixed_overhead_text="sys", model_reserved=False)
        assert plan.output_reservation_tokens == 0
        assert plan.evidence_budget_tokens == 4096 - plan.task_prompt_tokens - plan.fixed_overhead_tokens

    def test_output_reservation_is_bounded_and_deterministic(self):
        small = plan_context_budget(2048, "t", model_reserved=True)
        large = plan_context_budget(32768, "t", model_reserved=True)
        assert 0 < small.output_reservation_tokens < 2048
        assert small.output_reservation_tokens <= large.output_reservation_tokens <= 4096

    def test_tiny_budget_floors_the_evidence_allowance(self):
        plan = plan_context_budget(
            256,
            "Explain the context engine " * 40,
            fixed_overhead_text="system instructions " * 40,
            model_reserved=True,
        )
        assert plan.evidence_budget_tokens == MIN_EVIDENCE_BUDGET_TOKENS
        assert "evidence_budget_floored" in plan.notes

    def test_task_prompt_is_counted_exactly_once(self):
        """The budget split is disjoint: the task prompt has exactly one owner.

        The synthesis scaffold embeds the task verbatim, so measuring the scaffold
        with the task included *and* reporting `task_prompt_tokens` counts the task
        twice. That silently shrinks the repository-evidence allowance by the size
        of the task prompt, which is exactly the evidence the budget should buy.
        """
        task = "How does enforce_context_budget enforce the requested context budget?"
        scaffold_args = dict(
            task_prompt=task,
            task_summary="Understand budget enforcement",
            category="explanation",
            target_entities=["context engine"],
            symbols=["enforce_context_budget"],
            evidence_text="",
        )

        measured_scaffold = build_synthesis_user_prompt(**scaffold_args, include_task=False)
        assert task not in measured_scaffold, "the fixed-overhead scaffold must exclude the task"
        assert task in build_synthesis_user_prompt(**scaffold_args), "the sent prompt must carry the task"

        plan = plan_context_budget(
            requested_tokens=2048,
            task_prompt=task,
            fixed_overhead_text=_SYNTH_SYSTEM_PROMPT + measured_scaffold,
            model_reserved=True,
        )
        assert plan.accounted_tokens == plan.requested_tokens
        assert plan.evidence_budget_tokens == (
            plan.requested_tokens
            - plan.task_prompt_tokens
            - plan.fixed_overhead_tokens
            - plan.output_reservation_tokens
        )

        # Counting the task inside the overhead as well would steal evidence budget.
        inflated = plan_context_budget(
            requested_tokens=2048,
            task_prompt=task,
            fixed_overhead_text=_SYNTH_SYSTEM_PROMPT + build_synthesis_user_prompt(**scaffold_args),
            model_reserved=True,
        )
        assert inflated.fixed_overhead_tokens > plan.fixed_overhead_tokens
        assert inflated.evidence_budget_tokens < plan.evidence_budget_tokens


# ---------------------------------------------------------------------------
# Phase 9 — multiple budgets
# ---------------------------------------------------------------------------


class TestMultipleBudgets:
    @pytest.mark.parametrize("budget", [2048, 4096, 8192, 16384])
    def test_final_context_is_within_the_requested_budget(self, budget):
        result = compact(broad_evidence_set(), budget)
        assert result.report.final_tokens <= budget
        assert result.report.budget_satisfied is True
        assert result.report.degraded is False
        assert result.report.requested_tokens == budget

    @pytest.mark.parametrize("budget", [2048, 4096, 8192, 16384])
    def test_task_prompt_remains_present(self, budget):
        result = compact(broad_evidence_set(), budget)
        assert TASK in result.deterministic_markdown

    def test_larger_budget_retains_at_least_as_much_evidence(self):
        growth = []
        for budget in (2048, 4096, 8192, 16384):
            report = compact(broad_evidence_set(), budget).report
            growth.append(
                (
                    report.evidence_tokens,
                    report.candidates_after,
                    report.mandatory_evidence_tokens,
                )
            )
        for earlier, later in zip(growth, growth[1:]):
            assert later[0] >= earlier[0]  # more evidence text
            assert later[1] >= earlier[1]  # never fewer artifacts
            assert later[2] >= earlier[2]  # mandatory evidence never shrinks
        assert growth[0][0] < growth[-1][0], "a larger budget must buy more evidence"

    def test_evidence_selection_changes_intentionally_with_budget(self):
        tight = compact(broad_evidence_set(), 2048)
        roomy = compact(broad_evidence_set(), 16384)
        tight_levels = {entry.id: entry.level for entry in tight.report.retained}
        roomy_levels = {entry.id: entry.level for entry in roomy.report.retained}
        assert set(tight_levels) <= set(roomy_levels)
        for group_id, level in tight_levels.items():
            assert roomy_levels[group_id] <= level, "a larger budget never reduces evidence further"
        assert sum(tight_levels.values()) > sum(roomy_levels.values())

    @pytest.mark.parametrize("budget", [1024, 2048, 4096])
    def test_low_authority_evidence_yields_before_source_truth(self, budget):
        source = source_candidate(relevance=0.7)
        memories = [
            memory_candidate(f"mem-{i}", "Semantic memory: " + "derived note about budgets. " * 8)
            for i in range(10)
        ]
        result = compact([source] + memories, budget, model_reserved=True)
        retained_ids = {entry.id for entry in result.report.retained}
        assert "group:src-0" in retained_ids
        assert result.report.retained[0].kind == "source_snippet" or any(
            entry.kind == "source_snippet" for entry in result.report.retained
        )
        if result.report.omitted:
            assert all(entry.kind == "semantic_memory" for entry in result.report.omitted)
            assert all(entry.reason == "budget_exhausted_after_max_reduction" for entry in result.report.omitted)
        assert "engine.py" in result.evidence_markdown


# ---------------------------------------------------------------------------
# Phase 4/5 — packing, reduction ladder, no tail truncation
# ---------------------------------------------------------------------------


class TestPackingAndReduction:
    def test_no_tail_truncation_when_critical_evidence_is_last(self):
        critical_candidate, full_content, critical_symbol = big_file_with_critical_function()
        for budget in (1024, 2048):
            result = compact([critical_candidate], budget)
            body = result.evidence_markdown
            # The task-relevant function lives at the very end of a 400-line file.
            # Tail truncation would lose it; reduction must keep it.
            assert critical_symbol in body
            assert "Lines" in body
            # ... and the output must not simply be a prefix of the original text.
            assert not full_content.startswith(body.strip()[len("# Task"):].strip())
            assert "elided" in body or "signatures" in body

    def test_reducing_budget_does_not_remove_the_last_section(self):
        source = source_candidate(relevance=0.95)
        trailer = memory_candidate("mem-trailer", "Trailing derived note. " * 40)
        roomy = compact([source, trailer], 4096)
        tight = compact([source, trailer], 700)
        assert "Semantic Memory" in roomy.evidence_markdown  # last section at 4K
        assert "Relevant Code Snippets" in tight.evidence_markdown  # source section survives
        # The last-ranked section yields first, and its removal is recorded.
        assert "Relevant Code Snippets" in roomy.evidence_markdown
        if "Semantic Memory" not in tight.evidence_markdown:
            assert any(entry.kind == "semantic_memory" for entry in tight.report.omitted)
        # The evidence text must never simply be the tail of the roomy package.
        assert tight.evidence_markdown != roomy.evidence_markdown[-len(tight.evidence_markdown):]

    def test_reduction_levels_are_used_progressively(self):
        critical_candidate, _, _ = big_file_with_critical_function()
        levels = []
        for budget in (400, 800, 1600, 3200, 8000):
            report = compact([critical_candidate], budget).report
            levels.append(report.retained[0].level)
        assert levels == sorted(levels, reverse=True), "more budget must not mean more reduction"
        assert levels[0] > 0, "a 400-token package cannot contain a 400-line file in full"
        assert levels[-1] == 0, "a large budget must restore the full source"

    def test_provenance_is_preserved_at_every_level(self):
        filler = [f"    step_{i} = helper_{i}(payload)" for i in range(300)]
        critical = ["def enforce_context_budget(plan, evidence):", "    return plan.fit(evidence)"]
        cand = source_candidate(path="backend/app/services/engine.py", start=42, body_lines=filler + critical)
        levels = set()
        for budget in (400, 800, 1600, 3200, 8000, 32000):
            result = compact([cand], budget)
            entry = result.report.retained[0]
            levels.add(entry.level)
            assert "engine.py" in result.evidence_markdown
            assert "Lines" in result.evidence_markdown
            assert "enforce_context_budget" in result.evidence_markdown
        assert levels == {0, 2}, "the allocator must use the minimum reduction the budget allows"

    def test_every_level_of_the_ladder_is_well_formed(self):
        """Each reduction level is valid on its own: provenance, content, elision."""
        filler = [f"    step_{i} = helper_{i}(payload)" for i in range(200)]
        critical = ["def enforce_context_budget(plan, evidence):", "    return plan.fit(evidence)"]
        item = source_candidate(path="backend/app/services/engine.py", start=7, body_lines=filler + critical)
        group = EvidenceGroup(
            id="group:s",
            kind="source",
            items=[EvidenceItem.from_candidate(item)],
        )
        renderer = EvidenceRenderer(["enforce_context_budget", "budget"])
        previous_tokens = None
        for level in range(0, LEVEL_REFERENCE + 1):
            rendered = renderer.render(group, level, window_budget=400)
            assert "engine.py" in rendered, f"level {level} lost its file provenance"
            assert "Lines" in rendered, f"level {level} lost its line provenance"
            assert "```" in rendered or "omitted" in rendered.lower()
            tokens = estimate_tokens(rendered)
            if previous_tokens is not None:
                assert tokens <= previous_tokens * 2 + 64, "a deeper level must not explode in size"
            previous_tokens = tokens

    def test_reference_level_is_a_last_resort_and_keeps_provenance(self):
        """When nothing else fits, the package carries a reference, never a fragment."""
        filler = [f"    step_{i} = helper_{i}(payload)" for i in range(3000)]
        cand = source_candidate(path="backend/app/services/huge.py", start=100, body_lines=filler)
        result = compact([cand], 200, model_reserved=True)
        entry = result.report.retained[0]
        assert entry.level == LEVEL_REFERENCE
        assert LEVEL_NAMES[entry.level] == "evidence_reference"
        assert "huge.py" in result.evidence_markdown
        assert "Lines" in result.evidence_markdown
        assert "omitted" in result.evidence_markdown.lower()
        # The impossible-budget state is explicit, never a silent short package.
        assert result.report.degraded is True
        assert result.report.degradation_reason == "fixed_prompt_overhead_exceeds_budget"

    def test_oversized_artifact_does_not_evict_smaller_relevant_ones(self):
        huge = source_candidate(cid="src-huge", path="a_huge.py", body_lines=[f"    x_{i} = {i}" for i in range(4000)])
        small = source_candidate(cid="src-small", path="b_small.py", body_lines=["def enforce_context_budget():", "    return True"], relevance=0.95)
        result = compact([huge, small], 2048, symbols=SYMBOLS)
        paths = [entry.source_file for entry in result.report.retained]
        assert "b_small.py" in paths
        assert result.report.final_tokens <= 2048


# ---------------------------------------------------------------------------
# Phase 3/6 — evidence priority and coherence
# ---------------------------------------------------------------------------


class TestEvidencePriority:
    def test_mandatory_ast_relationship_survives_a_tight_budget(self):
        source = source_candidate(relevance=0.7)
        edge = candidate(
            "edge-0",
            AuthorityTier.TIER_2_MANIFEST_AST,
            "Call Edge: context_use_case -> enforce_context_budget",
            kind="call_graph",
        )
        memories = [
            memory_candidate(f"mem-{i}", "Semantic memory: " + "ranking note. " * 20) for i in range(8)
        ]
        result = compact([edge] + memories + [source], 700, model_reserved=True)
        assert result.report.mandatory_evidence_fit is True
        assert "enforce_context_budget" in result.evidence_markdown
        assert "context_use_case" in result.evidence_markdown

    def test_high_priority_evidence_late_in_the_candidate_list_still_wins(self):
        memories = [
            memory_candidate(f"mem-{i}", "Semantic memory: " + "derived ranking note. " * 20) for i in range(10)
        ]
        edge = candidate(
            "edge-0",
            AuthorityTier.TIER_2_MANIFEST_AST,
            "Symbol: enforce_context_budget",
            kind="symbol",
            symbol="enforce_context_budget",
            relevance=1.0,
        )
        source = source_candidate(cid="src-last", path="late_source.py", relevance=0.6)
        # Highest-authority evidence deliberately arrives last in the input list.
        result = compact(memories + [edge, source], 700, model_reserved=True)
        retained_files = [entry.source_file for entry in result.report.retained]
        assert "late_source.py" in retained_files
        assert any(entry.tier == "TIER_2_MANIFEST_AST" for entry in result.report.retained)
        assert all(entry.tier == "TIER_4_COGNEE" for entry in result.report.omitted) or not result.report.omitted

    def test_semantic_memory_never_displaces_deterministic_evidence(self):
        source = source_candidate(relevance=0.5)
        memories = [memory_candidate(f"mem-{i}", "Semantic only note. " * 30, relevance=1.0) for i in range(6)]
        result = compact([source] + memories, 600, model_reserved=True)
        retained_tiers = [entry.tier for entry in result.report.retained]
        if "TIER_4_COGNEE" in retained_tiers:
            assert "TIER_1_SOURCE" in retained_tiers
        assert "engine.py" in result.evidence_markdown

    def test_relationship_coherence_keeps_connected_evidence_together(self):
        source = source_candidate(path="backend/app/services/engine.py", relevance=0.9)
        symbol = candidate(
            "sym-0",
            AuthorityTier.TIER_2_MANIFEST_AST,
            "Symbol: enforce_context_budget",
            kind="symbol",
            symbol="enforce_context_budget",
            relevance=1.0,
        )
        edge = candidate(
            "edge-0",
            AuthorityTier.TIER_2_MANIFEST_AST,
            "Call Edge: enforce_context_budget -> plan_fit",
            kind="call_graph",
        )
        result = compact([source, symbol, edge], 1200, model_reserved=True)
        body = result.evidence_markdown
        assert "enforce_context_budget" in body and "plan_fit" in body
        ids = [entry.id for entry in result.report.retained]
        structural_groups = [group_id for group_id in ids if "ast" in group_id]
        assert structural_groups, "task-linked structural evidence must remain grouped"


# ---------------------------------------------------------------------------
# Phase 7/8 — telemetry and impossible budgets
# ---------------------------------------------------------------------------


class TestTelemetryAndImpossibleBudgets:
    def test_report_exposes_budget_and_loss_telemetry(self):
        report = compact([source_candidate()], 2048, model_reserved=True).report.to_dict()
        for key in (
            "requested_tokens",
            "fixed_overhead_tokens",
            "task_prompt_tokens",
            "output_reservation_tokens",
            "evidence_budget_tokens",
            "pre_compaction_tokens",
            "evidence_tokens",
            "final_tokens",
            "candidates_before",
            "candidates_after",
            "retained",
            "omitted",
            "reduced",
            "top_evidence",
            "mandatory_evidence_tokens",
            "mandatory_evidence_fit",
            "budget_satisfied",
            "degraded",
            "evidence_reduction",
        ):
            assert key in report
        assert report["final_tokens"] <= report["requested_tokens"]

    def test_omitted_evidence_records_reason_and_identity(self):
        memories = [memory_candidate(f"mem-{i}", "Repeated derived note. " * 30) for i in range(12)]
        result = compact(memories, 400, model_reserved=True)
        assert result.report.omitted
        for entry in result.report.omitted:
            assert entry.reason
            assert entry.tier
            assert entry.tokens > 0

    def test_impossible_budget_is_degraded_and_never_truncates_the_task(self):
        huge_task = "Explain the context engine budget behaviour " * 60
        result = compact([source_candidate()], 300, task=huge_task, model_reserved=True)
        assert result.report.budget_satisfied is False
        assert result.report.degraded is True
        assert result.report.degradation_reason in (
            "fixed_prompt_overhead_exceeds_budget",
            "mandatory_evidence_exceeds_budget",
        )
        # The developer's task is reproduced verbatim — never silently truncated.
        assert huge_task.strip() in result.deterministic_markdown
        assert result.report.final_tokens > 300

    def test_mandatory_evidence_over_allowance_is_reported(self):
        mandatory = source_candidate(cid="src-mandatory", path="must_keep.py", relevance=1.0,
                                     body_lines=[f"    enforce_context_budget_{i} = {i}" for i in range(500)])
        result = compact([mandatory], 400, model_reserved=True)
        entry = result.report.retained[0]
        assert entry.mandatory is True
        assert result.report.unplaced_mandatory == []
        assert "must_keep.py" in result.evidence_markdown
        if result.report.mandatory_evidence_tokens > result.report.evidence_budget_tokens:
            assert result.report.mandatory_evidence_fit is False
            assert "mandatory_evidence_exceeds_allowance" in result.report.notes

    def test_missing_evidence_is_recorded_but_never_fabricated(self):
        result = compact(
            [source_candidate()],
            2048,
            missing_evidence=["payment webhook signature verification"],
        )
        assert result.report.missing_evidence == ["payment webhook signature verification"]
        assert "payment webhook" not in result.evidence_markdown

    def test_zero_candidates_produces_a_budgeted_task_only_package(self):
        result = compact([], 2048)
        assert TASK in result.deterministic_markdown
        assert result.evidence_markdown == ""
        assert result.report.final_tokens <= 2048
        assert result.report.candidates_before == 0
        assert result.report.budget_satisfied is True

    def test_file_index_is_bounded_and_reported(self):
        files = [f"backend/app/services/module_{i}.py" for i in range(20)]
        result = compact([source_candidate()], 2048, relevant_files=files)
        assert result.deterministic_markdown.count("module_") == 12
        assert "file_index_capped:8" in result.report.notes

    def test_derived_recall_is_lowest_tier_and_dropped_first(self):
        """A recall document is packed separately and yields before source truth."""
        from app.application.use_cases.context import build_derived_recall_candidate

        package = MagicMock()
        package.markdown = (
            "# Task\n\nhow does the engine work\n\n---\n\n"
            "# Repository Context\n\n**Purpose**: tests\n\n---\n\n"
            "# Implementation Notes\n\n- " + "derived recall detail. " * 60
        )
        recall = build_derived_recall_candidate(package)
        assert len(recall) == 1
        assert recall[0].relationship_kind == "recall_package"
        assert "# Task" not in recall[0].content  # the task preamble is not duplicated
        assert "derived recall detail" in recall[0].content

        source = source_candidate(relevance=0.8)
        roomy = compact([source] + recall, 8192)
        assert "Derived Recall Context" in roomy.evidence_markdown
        tight = compact([source] + recall, 700, model_reserved=True)
        assert "Relevant Code Snippets" in tight.evidence_markdown
        assert tight.report.final_tokens <= 700
        if "Derived Recall Context" not in tight.evidence_markdown:
            assert any(entry.kind == "derived_recall" for entry in tight.report.omitted)

    def test_observed_synthesis_is_never_truncated_evidence_yields_instead(self):
        """A verbose answer re-packs the evidence; the answer itself is untouched."""
        source = source_candidate(body_lines=[f"    value_{i} = compute({i})" for i in range(200)])
        plan = plan_context_budget(2048, TASK, fixed_overhead_text="system instructions " * 20, model_reserved=True)
        compactor = ContextCompactor()

        def pack(override=None):
            return compactor.compact(
                candidates=[source],
                plan=plan,
                task_prompt=TASK,
                title="budget enforcement",
                task_terms=derive_task_terms(TASK, SYMBOLS),
                task_symbols=SYMBOLS,
                output_reservation_override=override,
            )

        planned = pack()
        # The model answered with far more than the reservation: the evidence is
        # re-packed smaller so the delivered package still fits.
        re_packed = pack(override=800)
        assert re_packed.report.final_tokens <= 2048
        assert re_packed.report.evidence_tokens < planned.report.evidence_tokens
        assert re_packed.report.output_reservation_tokens == 800
        assert "re_packed_for_observed_synthesis" in re_packed.report.notes
        assert "engine.py" in re_packed.evidence_markdown
        assert re_packed.report.mandatory_evidence_fit is True


# ---------------------------------------------------------------------------
# Phase 12 — determinism and category independence
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_repeated_compaction_is_byte_identical(self):
        candidates = broad_evidence_set()
        first = compact(candidates, 2048)
        second = compact(candidates, 2048)
        assert first.deterministic_markdown == second.deterministic_markdown
        assert first.report.to_dict() == second.report.to_dict()

    def test_input_order_does_not_change_the_result(self):
        candidates = broad_evidence_set()
        shuffled = list(reversed(candidates))
        assert compact(candidates, 2048).deterministic_markdown == compact(shuffled, 2048).deterministic_markdown

    def test_category_membership_does_not_gate_packing(self):
        exotic = candidate(
            "exotic-0",
            AuthorityTier.TIER_2_MANIFEST_AST,
            "Symbol: enforce_context_budget",
            kind="unknown_future_relationship",
            symbol="enforce_context_budget",
            relevance=1.0,
        )
        known = candidate(
            "known-0",
            AuthorityTier.TIER_2_MANIFEST_AST,
            "Symbol: enforce_context_budget",
            kind="symbol",
            symbol="enforce_context_budget",
            relevance=1.0,
        )
        exotic_result = compact([exotic], 1024)
        known_result = compact([known], 1024)
        assert exotic_result.report.retained
        assert "enforce_context_budget" in exotic_result.evidence_markdown
        assert exotic_result.report.retained[0].tokens_after == known_result.report.retained[0].tokens_after


# ---------------------------------------------------------------------------
# End-to-end wiring through the agent context use case
# ---------------------------------------------------------------------------


class RecordingSynthesisLLM(LLMProviderPort):
    """Records synthesis prompts and returns task-specific markdown."""

    def __init__(self, symbols: list[str], file_hint: str) -> None:
        self.provider_type = ProviderType.LM_STUDIO
        self.default_model = "recording-model"
        self.prompts: list[str] = []
        self.synthesis_prompts: list[str] = []
        self.max_tokens_seen: list[int] = []
        self._symbols = symbols
        self._file_hint = file_hint

    async def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> str:
        self.prompts.append(prompt)
        self.max_tokens_seen.append(max_tokens)
        if "JSON" in prompt or (system_prompt and "JSON" in system_prompt):
            symbols = ", ".join(f'"{s}"' for s in self._symbols)
            return (
                '{"task_summary": "budget enforcement", "category": "general", '
                f'"extracted_symbols": [{symbols}], "relevant_file_hints": ["{self._file_hint}"], '
                '"is_vague": false, "actions": ["explain"], "target_entities": ["context budget"]}'
            )
        self.synthesis_prompts.append(prompt)
        first_line = prompt.splitlines()[1] if "\n" in prompt else prompt
        return f"### Synthesis\nAnswering: {first_line[:60]}\n1. Inspect enforce_context_budget"

    async def check_health(self) -> Any:
        health = MagicMock()
        health.is_reachable = True
        health.active_model = self.default_model
        health.loaded_models = []
        health.quantization_warning = None
        return health

    async def list_models(self) -> list[Any]:
        return []

    async def discover_models(self, *args: Any, **kwargs: Any) -> Any:
        discovered = MagicMock()
        discovered.is_reachable = True
        discovered.models = []
        return discovered


def build_use_case(tmp_dir: str, repo_files: dict[str, str], llm: RecordingSynthesisLLM) -> ContextUseCases:
    """Compose the real use case with mocked memory but real source search/AST."""
    repo_path = Path(tmp_dir) / "repo"
    repo_path.mkdir(parents=True, exist_ok=True)
    for name, content in repo_files.items():
        target = repo_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)

    container = ApplicationContainer.create()
    container.llm_provider = llm
    container.intent_parser = IntentParserService(llm)
    container.cognee_service = MagicMock()
    container.indexing_service = MagicMock()
    paths = [repo_path / name for name in repo_files]
    container.indexing_service.discover_files.return_value = paths
    container.indexing_service.filter_files.return_value = paths
    container.source_search = SourceSearchService()

    context_service = MagicMock()
    package = MagicMock()
    package.markdown = "# Untracked deterministic package"
    package.sections = []
    package.references = []
    context_service.generate_context_package = AsyncMock(return_value=package)
    container.context_service = context_service
    container.workspace_auth = WorkspaceAuthorizationService(workspace_roots=[Path(tmp_dir)])
    return container.get_context_use_cases()


ENGINE_SOURCE = (
    "class ContextEngine:\n"
    + "".join(f"    def helper_{i}(self):\n        return {i}\n" for i in range(60))
    + "    def enforce_context_budget(self, plan, evidence):\n"
    "        return plan.fit(evidence)\n"
)


@pytest.mark.asyncio
@pytest.mark.parametrize("budget", [2048, 8192])
async def test_agent_context_respects_budget_and_reports_compaction(budget):
    """End-to-end: the delivered package fits the request and is task-specific."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        llm = RecordingSynthesisLLM(symbols=["enforce_context_budget"], file_hint="engine.py")
        use_case = build_use_case(tmp_dir, {"engine.py": ENGINE_SOURCE}, llm)
        request = AgentContextRequest(
            task_prompt="How does enforce_context_budget enforce the requested context budget?",
            repository_path=str(Path(tmp_dir) / "repo"),
            dataset_name="repo",
            max_tokens=budget,
        )
        response = await use_case.get_agent_context(request)

        assert isinstance(response, AgentContextResponse)
        assert response.success is True
        compaction = response.compaction
        assert compaction is not None
        assert compaction["requested_tokens"] == budget
        assert compaction["final_tokens"] <= budget
        assert compaction["budget_satisfied"] is True
        assert response.estimated_tokens == compaction["final_tokens"]
        assert compaction["task_prompt_tokens"] == estimate_tokens(request.task_prompt)
        # The task and its evidence remain present in the delivered context.
        assert request.task_prompt in response.context_markdown
        assert "engine.py" in response.context_markdown
        # The synthesis prompt is task-specific and carries the packed evidence.
        synthesis_prompt = llm.synthesis_prompts[-1]
        assert request.task_prompt in synthesis_prompt
        assert "enforce_context_budget" in synthesis_prompt
        # The generation budget is the budget's output reservation, never the
        # input context budget.
        assert llm.max_tokens_seen[-1] == compaction["planned_output_reservation_tokens"]
        assert compaction["planned_output_reservation_tokens"] > 0


@pytest.mark.asyncio
async def test_larger_budget_never_delivers_less_evidence_end_to_end():
    """Same repository, same task, two budgets: both fit and evidence never shrinks."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        files = {
            f"module_{i}.py": (
                f"def gather_context_budget_evidence_{i}(payload):\n"
                f'    """Enforce the requested context budget for module {i}."""\n'
                f"    return enforce_context_budget(payload)\n"
            )
            for i in range(6)
        }
        files["engine.py"] = ENGINE_SOURCE
        task = "How does enforce_context_budget enforce the requested context budget?"

        async def run(budget: int) -> AgentContextResponse:
            llm = RecordingSynthesisLLM(symbols=["enforce_context_budget"], file_hint="engine.py")
            return await build_use_case(tmp_dir, files, llm).get_agent_context(
                AgentContextRequest(
                    task_prompt=task,
                    repository_path=str(Path(tmp_dir) / "repo"),
                    dataset_name="repo",
                    max_tokens=budget,
                )
            )

        tight = await run(2048)
        roomy = await run(16384)

        assert tight.abstained is False
        assert tight.compaction["final_tokens"] <= 2048
        assert roomy.compaction["final_tokens"] <= 16384
        assert roomy.compaction["evidence_tokens"] >= tight.compaction["evidence_tokens"]
        assert roomy.compaction["evidence_budget_tokens"] > tight.compaction["evidence_budget_tokens"]
        # Critical evidence survives the tight budget, and nothing was dropped by
        # position: the tight package only removes what the budget cannot hold.
        assert "engine.py" in tight.context_markdown
        assert "enforce_context_budget" in tight.context_markdown
        assert tight.compaction["mandatory_evidence_fit"] is True
        assert task in tight.context_markdown


@pytest.mark.asyncio
async def test_unclassified_task_category_still_compacts_task_specific_evidence():
    with tempfile.TemporaryDirectory() as tmp_dir:
        llm = RecordingSynthesisLLM(symbols=["BpeTokenizer", "encode"], file_hint="tokenizer.py")
        use_case = build_use_case(
            tmp_dir,
            {"tokenizer.py": "class BpeTokenizer:\n    def encode(self, text):\n        return text.split()\n"},
            llm,
        )
        request = AgentContextRequest(
            task_prompt="Tune the BpeTokenizer vocabulary merge rules",
            repository_path=str(Path(tmp_dir) / "repo"),
            dataset_name="repo",
            max_tokens=2048,
        )
        response = await use_case.get_agent_context(request)
        assert response.success is True
        assert response.intent_category == "general"
        assert response.compaction["final_tokens"] <= 2048
        assert "tokenizer.py" in response.context_markdown
        assert request.task_prompt in response.context_markdown


class TruncatedReasoningLLM(RecordingSynthesisLLM):
    """A reasoning model cut off mid-``<think>`` by its generation reservation."""

    async def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> str:
        if "JSON" in prompt or (system_prompt and "JSON" in system_prompt):
            return await super().generate_completion(prompt, system_prompt, model, temperature, max_tokens)
        self.prompts.append(prompt)
        self.max_tokens_seen.append(max_tokens)
        self.synthesis_prompts.append(prompt)
        # No closing tag: the output budget ran out inside the reasoning block.
        return "<think>\nOkay, let's tackle this. The developer asks how the context engine fits "


@pytest.mark.asyncio
async def test_truncated_reasoning_is_never_delivered_as_the_answer():
    """A generation cap that cuts a reasoning model mid-trace must not leak.

    At a tight budget the output reservation is small enough that a reasoning
    model exhausts it inside its ``<think>`` block, so no closing tag is ever
    emitted and the complete-block regex cannot match. The delivered package must
    fall back to the deterministic compacted evidence instead of presenting raw
    truncated reasoning as the answer.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        llm = TruncatedReasoningLLM(symbols=["enforce_context_budget"], file_hint="engine.py")
        use_case = build_use_case(tmp_dir, {"engine.py": ENGINE_SOURCE}, llm)
        request = AgentContextRequest(
            task_prompt="How does enforce_context_budget enforce the requested context budget?",
            repository_path=str(Path(tmp_dir) / "repo"),
            dataset_name="repo",
            max_tokens=2048,
        )
        response = await use_case.get_agent_context(request)

        assert isinstance(response, AgentContextResponse)
        assert response.success is True
        assert "<think>" not in response.context_markdown
        assert "[THINKING]" not in response.context_markdown
        assert "Okay, let's tackle this" not in response.context_markdown
        # The budget contract still holds and the evidence is still delivered.
        assert response.compaction["final_tokens"] <= 2048
        assert response.compaction["budget_satisfied"] is True
        assert request.task_prompt in response.context_markdown
        assert "engine.py" in response.context_markdown
        assert "enforce_context_budget" in response.context_markdown
