# Purpose

Owns all project documentation for RE:Track (RefinedEngine Track).

This directory defines the project's vision, architecture, memory model, implementation plan, repository knowledge model, and development contracts.

Documentation is the authoritative description of the project. Implementation must remain synchronized with documentation.

---

# Ownership

Owns:

- Vision (`vision.md`)
- Problem Statement (`problem_statement.md`)
- Scope (`scope.md`)
- Architecture (`architecture.md`) — includes call graph service, CallGraphExtractor, updated package structure
- Implementation Plan (`implementation_plan.md`) — milestones 1-6, current status
- Repository Knowledge Model (`repository_knowledge_model.md`)
- Memory Model (`memory_model.md`)
- Cognee Integration (`cognee_integration.md`)
- Development Plan (`development_plan.md`)
- Demo Plan (`demo_plan.md`)

---

# Local Contracts

Documentation describes stable project behavior and contracts.

Do not duplicate implementation details — reference file paths instead.

Documentation must be updated whenever:
- A new service is added
- A new data model is introduced
- A new UI feature is shipped
- A design constraint is removed (e.g., "graph visualization excluded" was removed when CallGraphView shipped)

---

# Work Guidance

Keep documents concise.

Prefer modifying existing documents over creating new ones.

Delete stale constraints immediately rather than marking them as deferred.

---

# Verification

Verify documentation remains synchronized with implementation after every milestone.

---

# Child DOX Index

No child DOX documents exist under docs/. All files are direct children.
