## §1 Task identity
- task_id: T21
- short summary: Fix code quality issues in list_datasets endpoint — move SDK calls to CogneeService, fix N+1 pattern, make optional fields nullable

## §2 Subagent intent
Fix three code quality issues found in Task 1.1 (list_datasets endpoint): (1) AGENTS.md contract violation — direct `cognee_sdk.datasets.*` calls in commands.py must go through CogneeService, (2) N+1 query pattern from `list_data(ds.id)` inside a loop, (3) hardcoded `size_bytes=0` and `source_path=""` placeholders should be optional in the schema so the frontend can distinguish unknown from zero.

## §3 Files and code sections
- `backend/app/services/cognee_service.py`: Added `list_datasets()` async method that wraps `cognee.datasets.list_datasets()` and `cognee.datasets.list_data()`, returning a list of dicts with id, name, created_at, and file_count. Follows existing CogneeService pattern (tries SDK call, catches exceptions, raises CogneeServiceError).
- `backend/app/api/commands.py`: Removed `import cognee as cognee_sdk` and all direct SDK calls from `list_datasets()` command. Now delegates to `_cognee_service.list_datasets()` and maps the returned dicts into `DatasetInfo` objects.
- `backend/app/api/schemas.py`: Changed `DatasetInfo.size_bytes` from `int = 0` to `Optional[int] = None` and `DatasetInfo.source_path` from `str = ""` to `Optional[str] = None`.

## §4 Verbatim commands
```bash
cd "/home/chandrabhan/Documents/Personal Project/Cognee Hackathon/andes-context-mimocode/backend" && python3.13 -c "from app.services.cognee_service import CogneeService; print('OK')"
```
```bash
npx tsc --noEmit
```

## §5 Outcome and discoveries
- Outcome (success): All three issues fixed. Python import verified. TypeScript compilation passed. Committed as `12e2049`.
- Discoveries that may matter for other tasks: Cognee 1.x SDK has no batch endpoint for `list_data` — the N+1 pattern is unavoidable at the SDK level but is now encapsulated within CogneeService. The `list_datasets()` method is a read-only query that fits naturally alongside the existing remember/recall/improve/forget methods without expanding CogneeService's responsibilities.
