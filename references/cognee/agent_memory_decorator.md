# Agent Memory Decorator

## Purpose

The Agent Memory Decorator allows Cognee to automatically provide memory to an AI agent without requiring explicit `remember()` and `recall()` calls throughout application code.

Rather than manually retrieving memory before every request, the decorator intercepts agent execution and injects relevant context automatically.

For RE:Track, this concept can reduce boilerplate and provide seamless memory augmentation for future agent integrations.

---

# Concept

```
Developer Request

        │

        ▼

Agent

        │

        ▼

Memory Decorator

        │

        ▼

recall()

        │

        ▼

Relevant Memory

        │

        ▼

Prompt

        │

        ▼

LLM

        │

        ▼

Response
```

---

# Why It Exists

Without a decorator:

```
User Request

↓

recall()

↓

Build Prompt

↓

LLM

↓

remember()

↓

Return Response
```

Every interaction requires explicit orchestration.

With a decorator:

```
User Request

↓

Decorator

↓

Memory

↓

LLM

↓

Response
```

Memory integration becomes transparent.

---

# RE:Track Today

Current architecture:

```
Developer

↓

RE:Track Backend

↓

recall()

↓

Context Package

↓

Coding LLM

↓

remember()

↓

Response
```

Everything is explicitly controlled.

---

# Future RE:Track

Potential architecture:

```
Developer

↓

Agent

↓

Memory Decorator

↓

Cognee

↓

LLM

↓

Response
```

The decorator automatically enriches prompts.

---

# Possible Usage

Illustrative example:

```python
from cognee import agent_memory

@agent_memory
async def coding_agent(task: str):

    ...
```

(Actual API depends on the installed Cognee version. Verify against the current documentation.)

---

# Example Workflow

```
Developer asks:

"Implement OAuth."

↓

Decorator retrieves:

- Architecture
- Existing Auth
- Coding Standards
- API Contracts

↓

Prompt automatically enriched

↓

LLM writes code
```

---

# RE:Track Integration

The MVP should **not** depend on the Agent Memory Decorator.

Instead, RE:Track should continue to:

- control retrieval explicitly,
- build Context Packages,
- decide what information reaches the coding model.

This provides greater transparency and makes debugging easier during the hackathon.

---

# Advantages

- Less boilerplate
- Automatic retrieval
- Cleaner application code
- Easier multi-agent integration
- Consistent memory usage

---

# Limitations

- Less control over prompt construction
- Harder to debug retrieval decisions
- May retrieve unnecessary information
- Depends on Cognee's decorator implementation

---

# Recommendation for RE:Track

### MVP

Do **not** use the decorator.

Use explicit calls:

```
remember()

↓

recall()

↓

Context Package

↓

Coding Model

↓

remember()
```

### Future Versions

Evaluate replacing parts of the orchestration layer with the decorator after the Context Package generation pipeline is mature.

---

# Related APIs

- remember()
- recall()
- improve()
- forget()

---

# Related Concepts

- Sessions
- Datasets
- Ontologies
- Context Packages

---

# Related Documentation

```
https://docs.cognee.ai/core-concepts/further-concepts/agent-memory-decorator
```

---

# RE:Track Notes

Although Cognee supports automatic memory injection through decorators, RE:Track's primary value lies in generating deterministic, inspectable Context Packages.

Maintaining explicit control over retrieval ensures:

- predictable prompts,
- explainable context,
- reproducible AI behavior,
- compatibility with both local and cloud coding models.

The decorator should therefore be considered an optional future enhancement rather than a core dependency.

