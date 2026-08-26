# Product Guide: Grounded Context Generation & Zero-Hallucination Evidence Gating

## Overview

In coding-assistant workflows, Large Language Models and reasoning models (such as DeepSeek-R1 or Qwen-2.5) tend to produce speculative explanations or hallucinated architectures when a developer requests a feature that is not yet implemented in a project.

RE:Track solves this with **Deterministic Evidence Gating**:
1. Before invoking any inference model, RE:Track deterministically searches the indexed codebase for AST symbols, source code implementations, and call relationships matching the task.
2. If the requested subsystem is not present in the repository, RE:Track **abstains** from speculative synthesis.
3. Instead of generating a speculative think block or hallucinated API, RE:Track returns an **Abstention Package** indicating what structure was found, what is missing, and actionable guidance for implementing the feature from scratch.

---

## User Interface Indicators

### Context Studio Badges

| Badge | Meaning | Action Taken |
|---|---|---|
| 🟢 **Model Synthesized** | Sufficient repository evidence found. Model synthesized grounded context. | Full verified context provided. |
| 🟡 **Partial Evidence** | Some components found, but key dependencies are absent. | Bounded synthesis provided with explicit missing-evidence list. |
| 🟠 **Insufficient Repository Evidence** | Requested subsystem absent in repository. | Deterministic abstention package rendered; model inference skipped. |
| 🟡 **Deterministic Fallback** | Provider unreachable or disabled. | Deterministic AST symbol and call graph context returned. |

---

## Example: Django Authentication Negative Case

### Scenario
A developer asks RE:Track:
> *"Implement an API endpoint requiring JWT authentication and user permissions."*

The repository is a minimal Django app containing `manage.py`, `models.py`, and `views.py`, but **no authentication middleware, models, or endpoints**.

### Output Rendered by RE:Track
```markdown
# Task Intent
**Requested Objective**: Implement JWT authenticated API endpoint
**Intent Category**: `feature`

---

# Observed Repository Evidence
- Framework detected: Django (architectural structure).
- Indexed repository files: 4 files analyzed.

---

# Missing Evidence
- **Absent**: authentication (no existing symbols, middleware, models, or endpoints found)

---

# Insufficient Repository Evidence Notice
> **Status**: `ABSTAINED` (insufficient)
> **Reason**: No repository evidence was found for: authentication (no existing symbols, middleware, models, or endpoints found).

**Suggested Next Action**: Treat authentication as a new subsystem to build from scratch rather than modifying an existing implementation.
```

---

## Technical Invariants
- **Prompt intent is never evidence**: Mentioning "Stripe" or "JWT" in a prompt does not create Stripe or JWT evidence.
- **Model reasoning traces are never exposed**: `<think>` and `[THINKING]` tags are stripped automatically.
- **MCP Consumers**: Coding agents connected via MCP (`get_agent_context`) receive `abstained: true` and `missing_evidence: [...]` in the response payload.
