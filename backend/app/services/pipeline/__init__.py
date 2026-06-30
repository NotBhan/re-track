"""Pipeline stages for Context Package generation.

Each stage is independent and composable:
- Deduplicator: removes duplicate memories
- Ranker: scores and sorts by relevance
- Compressor: merges redundant entries
- Categorizer: classifies into section types
- ReferenceResolver: formats traceable citations
"""
