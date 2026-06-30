# AndesContext Benchmark Questions

15 repository-specific questions covering architecture, implementation, and extension points.

---

## Architecture Understanding

**Q1**: How is the backend structured? What are the main layers and how do they communicate?
- Expected files: `backend/app/services/__init__.py`, `backend/app/api/commands.py`, `backend/app/cli/main.py`
- Expected symbols: `CogneeService`, `IndexingService`, `ContextService`

**Q2**: What is the data flow from repository indexing to Context Package generation?
- Expected files: `backend/app/services/indexing_service.py`, `backend/app/services/context_service.py`, `backend/app/services/cognee_service.py`
- Expected symbols: `index_repository`, `generate_context_package`, `remember`, `recall`

**Q3**: How does CogneeService initialize the local AI providers?
- Expected files: `backend/app/services/cognee_service.py`, `backend/app/config/settings.py`
- Expected symbols: `CogneeService.initialize`, `configure_cognee`

---

## File Location

**Q4**: Where should I add support for Rust files (.rs)?
- Expected files: `backend/app/services/indexing_service.py`
- Expected symbols: `SUPPORTED_EXTENSIONS`

**Q5**: Where is the CLI entry point and how are commands registered?
- Expected files: `backend/andescontext.py`, `backend/app/cli/main.py`
- Expected symbols: `app` (Typer instance)

**Q6**: Where are the Pydantic request/response schemas defined?
- Expected files: `backend/app/api/schemas.py`
- Expected symbols: `ContextRequest`, `ContextResponse`, `ErrorResponse`

---

## API Understanding

**Q7**: What API commands are available and what does each do?
- Expected files: `backend/app/api/commands.py`
- Expected symbols: `health`, `get_backend_status`, `index_repository`, `generate_context`, `forget_dataset`

**Q8**: How does the forget command work? What parameters does it accept?
- Expected files: `backend/app/api/commands.py`, `backend/app/api/schemas.py`
- Expected symbols: `forget_dataset`, `ForgetRequest`

---

## Convention Identification

**Q9**: What naming conventions does this project use?
- Expected files: `backend/app/services/context_service.py`, `backend/app/models/responses.py`
- Expected patterns: snake_case functions, PascalCase classes, UPPER_SNAKE constants

**Q10**: How are errors handled in the backend?
- Expected files: `backend/app/models/errors.py`, `backend/app/api/commands.py`
- Expected symbols: `CogneeServiceError`, `IndexingError`

---

## Extension Points

**Q11**: If I wanted to add a new pipeline stage (e.g., graph expansion), where would I hook in?
- Expected files: `backend/app/services/context_service.py`
- Expected symbols: `generate_context_package`

**Q12**: How would I add a new CLI command?
- Expected files: `backend/app/cli/main.py`, `backend/app/api/commands.py`, `backend/app/api/schemas.py`
- Expected pattern: Add command → add API function → add schema → register in CLI

---

## Implementation Details

**Q13**: How does ContextService categorize retrieved memories into sections?
- Expected files: `backend/app/services/context_service.py`
- Expected symbols: `_categorize`, `_classify_memory`, `SectionType`

**Q14**: How does the indexing pipeline handle large repositories?
- Expected files: `backend/app/services/indexing_service.py`
- Expected symbols: `batch_files`, `DEFAULT_BATCH_SIZE`, `IndexingProgress`

**Q15**: What environment variables are required for Cognee to work locally?
- Expected files: `backend/app/config/settings.py`, `docs/cognee_integration.md`
- Expected symbols: `HUGGINGFACE_TOKENIZER`, `COGNEE_SKIP_CONNECTION_TEST`, `LLM_MODEL`
