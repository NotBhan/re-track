"""Single token-accounting model for RE:Track context budgets.

RE:Track estimates tokens with one deterministic heuristic — 4 characters per
token — which is the model already used by `PackageMetadata.estimated_tokens`,
`BudgetManager`, `RetrievalArbitrator` and the benchmark runner
(`tokenizer_name="character-4b-heuristic"`). It is defined here once so that
budget planning, packing decisions, prompt accounting and telemetry can never
drift apart or introduce a second, incompatible estimator.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

#: Characters per estimated token (the project-wide heuristic).
CHARS_PER_TOKEN = 4

#: Output-token reservation policy for the synthesis request. The reservation is
#: derived from the requested budget so a request can never claim a budget is
#: context when part of it is actually spent on generated output.
RESERVATION_RATIO = 0.25
RESERVATION_FLOOR_TOKENS = 256
RESERVATION_CAP_TOKENS = 4096

#: Smallest usable repository-evidence allowance. When the task prompt and the
#: fixed scaffolding leave less than this, the budget is reported as exceeded
#: instead of silently packing nothing.
MIN_EVIDENCE_BUDGET_TOKENS = 64


def estimate_tokens(text: str) -> int:
    """Estimate the token count of `text` under the project-wide char-4 heuristic.

    Empty or whitespace-only text costs zero tokens. Non-empty text always costs
    at least one token so that packing cannot treat content as free.
    """
    if not text or not text.strip():
        return 0
    return max(1, len(text) // CHARS_PER_TOKEN)


def estimate_tokens_of(texts: "list[str] | tuple[str, ...]") -> int:
    """Estimate the token count of several rendered fragments."""
    return sum(estimate_tokens(t) for t in texts)


def reserve_output_tokens(requested_tokens: int) -> int:
    """Deterministic generation reservation for a requested context budget."""
    if requested_tokens <= 0:
        return 0
    ratio_based = int(requested_tokens * RESERVATION_RATIO)
    bounded = max(RESERVATION_FLOOR_TOKENS, min(ratio_based, RESERVATION_CAP_TOKENS))
    return min(bounded, requested_tokens)


@dataclass(frozen=True)
class ContextBudgetPlan:
    """Explicit split of a requested context budget.

    The requested budget is the maximum estimated size of everything the caller
    receives and everything the model request contains as input — never only the
    repository slice. Every consumer of the budget is itemised:

    - ``task_prompt_tokens``: the developer's task, reproduced verbatim at the
      top of the delivered package and inside the synthesis prompt.
    - ``fixed_overhead_tokens``: system instructions plus the static synthesis
      scaffolding (intent header, output-format instructions, package headings).
    - ``output_reservation_tokens``: generation reservation when a synthesis
      model is invoked; zero for the deterministic path.
    - ``evidence_budget_tokens``: the remainder — all that may be spent on
      repository evidence.
    """

    requested_tokens: int
    task_prompt_tokens: int
    fixed_overhead_tokens: int
    output_reservation_tokens: int
    evidence_budget_tokens: int
    model_reserved: bool = False
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def accounted_tokens(self) -> int:
        """Sum of every explicitly reserved component."""
        return (
            self.task_prompt_tokens
            + self.fixed_overhead_tokens
            + self.output_reservation_tokens
            + self.evidence_budget_tokens
        )

    @property
    def evidence_floor_applied(self) -> bool:
        """True when the evidence allowance had to be floored to stay usable."""
        return self.evidence_budget_tokens >= MIN_EVIDENCE_BUDGET_TOKENS and self.accounted_tokens > self.requested_tokens

    def to_dict(self) -> dict[str, Any]:
        """Serialize the budget plan for telemetry."""
        return {
            "requested_tokens": self.requested_tokens,
            "task_prompt_tokens": self.task_prompt_tokens,
            "fixed_overhead_tokens": self.fixed_overhead_tokens,
            "output_reservation_tokens": self.output_reservation_tokens,
            "evidence_budget_tokens": self.evidence_budget_tokens,
            "model_reserved": self.model_reserved,
            "accounted_tokens": self.accounted_tokens,
            "notes": list(self.notes),
        }


def plan_context_budget(
    requested_tokens: int,
    task_prompt: str,
    fixed_overhead_text: str = "",
    model_reserved: bool = False,
    extra_fixed_tokens: int = 0,
) -> ContextBudgetPlan:
    """Split a requested context budget into task, overhead, output and evidence.

    The evidence allowance is the remainder. When the remainder would be smaller
    than :data:`MIN_EVIDENCE_BUDGET_TOKENS` it is floored to that value and the
    plan is reported as over-committed rather than quietly degrading to an empty
    evidence pack.
    """
    requested = max(0, int(requested_tokens))
    task_tokens = estimate_tokens(task_prompt)
    overhead_tokens = estimate_tokens(fixed_overhead_text) + max(0, int(extra_fixed_tokens))
    reservation = reserve_output_tokens(requested) if model_reserved else 0

    available = requested - task_tokens - overhead_tokens - reservation
    notes: list[str] = []
    if available < MIN_EVIDENCE_BUDGET_TOKENS:
        notes.append("evidence_budget_floored")
        available = MIN_EVIDENCE_BUDGET_TOKENS

    return ContextBudgetPlan(
        requested_tokens=requested,
        task_prompt_tokens=task_tokens,
        fixed_overhead_tokens=overhead_tokens,
        output_reservation_tokens=reservation,
        evidence_budget_tokens=available,
        model_reserved=model_reserved,
        notes=tuple(notes),
    )
