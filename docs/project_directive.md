# RE:Track Project Directive

## Purpose

This document defines the long-term direction of RE:Track (RefinedEngine Track).

Every architectural decision, implementation, and contribution must align with the principles described here.

If implementation details conflict with this document, this document takes precedence unless explicitly revised.

---

# Mission

Build the best local-first memory layer for AI-assisted software development.

RE:Track should dramatically reduce the amount of project context developers must manually provide to AI coding assistants.

The system should continuously accumulate project knowledge and transform it into compact, relevant Context Packages.

---

# Primary Objective

Produce high-quality Context Packages.

Everything else exists to improve the quality of those packages.

---

# Product Statement

RE:Track is **not**:

- A chat interface
- A coding agent
- An IDE replacement
- A simple search tool
- A prompt builder

RE:Track is a persistent software engineering memory system.

---

# Design Philosophy

## Memory First

Memory is the core feature.

Everything else supports memory.

---

## Local First

The application should function without cloud services.

Cloud providers should be optional.

---

## AI Agnostic

The application should work with:

- Ollama
- OpenAI
- Anthropic
- Gemini
- OpenRouter
- future providers

No implementation should depend on a single LLM provider.

---

## Explainability

Users should understand why information appears inside a Context Package.

Whenever practical, references should be traceable back to:

- source files
- documentation
- architectural decisions
- developer notes

---

## Minimal Context

The system should send only the information required for the current task.

Larger prompts are not inherently better prompts.

---

# Architectural Rules

The frontend never communicates directly with Cognee.

All memory operations pass through backend services.

Business logic belongs inside backend services, not UI components.

Cognee should be wrapped by a dedicated service layer.

Repository indexing must remain independent from Context Package generation.

---

# Scope

## Included

- Repository indexing
- Persistent memory
- Context Package generation
- Workspace management
- Session memory
- Local execution

---

## Excluded (MVP)

- Autonomous coding agents
- Team collaboration
- Cloud synchronization
- Plugin ecosystem
- Graph visualization
- CI/CD integration
- Multi-user editing

These may be explored after the hackathon.

---

# Development Principles

Implement vertically.

Complete one feature before beginning another.

Avoid speculative abstractions.

Prefer simple solutions over flexible ones until flexibility is required.

Keep services focused on a single responsibility.

Avoid introducing infrastructure that is not immediately necessary.

---

# AI Development Rules

AI agents should:

- follow the DOX hierarchy
- respect AGENTS.md
- avoid redesigning architecture
- implement only the requested task
- avoid unrelated modifications
- ask for clarification instead of guessing

Agents should not introduce new architectural patterns without explicit approval.

---

# Success Criteria

The MVP succeeds if a developer can:

1. Import a repository.
2. Build project memory.
3. Ask a software engineering question.
4. Receive a useful Context Package.
5. Use that package with an AI coding assistant.

---

# Non-Goals

Success is **not** measured by:

- number of graph nodes
- database size
- number of indexed files
- UI complexity
- number of supported providers

Success is measured by whether the generated Context Package improves AI-assisted software development.

---

# Guiding Principle

Every feature should answer one question:

> Does this improve the quality, relevance, or efficiency of Context Package generation?

If the answer is no, the feature should be reconsidered or postponed.

