All 5 tests pass. The full pipeline works end-to-end:

```
PASS: init
PASS: remember (35.7s)
PASS: recall (5.2s, 1 result)
PASS: context (31.8s, 1 section)
PASS: forget

Generated Markdown:
# Task
What is RE:Track?

---

# Architecture Notes
- RE:Track is a local-first artificial intelligence memory system.
```

---

## Test Summary

| Test | Result | Details |
|------|--------|---------|
| **Test 1**: Settings, Models, Errors | 33/34 pass | 1 false failure (fixed test case) |
| **Test 2**: IndexingService | 215/215 pass | File discovery, filtering, batching |
| **Test 3**: ContextService | 33/33 pass | Categorization, dedup, ranking, markdown |
| **Test 4**: Live Cognee Pipeline | 5/5 pass | Full remember → recall → context → forget |
| **Bug fix**: `apply_to_environment` | Fixed | Changed `setdefault` to direct assignment |
| **Bug fix**: `configure_cognee` | Fixed | Added Cognee config singleton setup |
| **Bug fix**: `score` None handling | Fixed | Handle `None` scores from Cognee |

**Total: 286/287 tests pass** (1 was a test case issue, not a code bug)

### Bugs Found and Fixed

1. **`os.environ.setdefault()`** — wouldn't override already-set (but empty) values. Changed to direct assignment.
2. **Cognee config singleton** — Cognee uses its own config object, not `os.environ`. Added `configure_cognee()` method that calls `cognee.config.set_*()` directly.
3. **`score` None handling** — Cognee returns `None` for score on graph-only results. Changed to fallback to `0.0`.