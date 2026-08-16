# RE:Track Verified SDK Reference for Cognee

This document provides a verified, implementation-oriented SDK reference for integrating **Cognee** into the **RE:Track** AI coding agent. It is strictly derived from the `topoteretes/cognee` repository structure and abstracts away large code blocks in favor of targeted execution flows, signatures, and integration notes.

---

## 1. System Configuration

**Path:** `cognee/api/v1/config/config.py`, `cognee/base_config.py`

Before running memory operations, Cognee requires infrastructure configuration. It uses a singleton pattern for configuration management.

### Public API

```python
class Config:
    def set_llm_provider(self, provider: str): ...
    def set_vector_db_provider(self, provider: str): ...
    def set_graph_db_provider(self, provider: str): ...

```

### RE:Track Integration

RE:Track operates locally. It must explicitly set local providers before invoking `remember` or `recall`.

```python
import os
from cognee.api.v1.config.config import config

# RE:Track Local Init
os.environ["LLM_PROVIDER"] = "ollama"
os.environ["VECTOR_DB_PROVIDER"] = "lancedb" 
os.environ["GRAPH_DB_PROVIDER"] = "kuzu"

config.set_llm_provider("ollama")

```

---

## 2. `cognee.remember`

**Path:** `cognee/api/v1/remember/remember.py`
**Task Pipeline:** `cognee/tasks/memify/memify_default_tasks.py`

### Public Function Signature

```python
async def remember(
    data: Union[str, List[str], BaseModel, List[BaseModel], Any], 
    dataset_name: str = "default", 
    **kwargs
) -> PipelineRunInfo:

```

### Parameters

* `data`: The payload to ingest. Accepts raw text, lists of strings (file paths), or structured Pydantic objects.
* `dataset_name` (str, default `"default"`): The logical namespace to partition data within the graph and vector DBs.
* `kwargs`: Pipeline configuration overrides, such as specifying a custom ontology.

### Execution Flow & Implementation Summary

1. **Classification & Loading:** Routes data to appropriate loaders (e.g., `TextLoader`, `PdfLoader`) based on file signatures.
2. **Chunking:** Splits text into overlapping `DocumentChunk` objects (`cognee/tasks/chunks/`).
3. **Graph Extraction:** Uses the configured LLM (`LLMGateway`) combined with `litellm_instructor` to deterministically extract entities and `Triplet` structures.
4. **Storage:** Vectors are generated and pushed to LanceDB/PGVector (`index_data_points.py`). Graph edges are upserted into Kùzu/Neo4j (`index_graph_edges.py`).

### Reference Links

* **Tests:** `cognee/tests/unit/api/v1/test_public_memory_api.py`
* **Example:** `examples/demos/remember_recall_improve_example.py`

### RE:Track Integration

Call `remember` when the user adds files to the context window or when a workspace is indexed.

```python
# Map the IDE workspace to the dataset_name to prevent cross-contamination
run_status = await cognee.remember(["./src/app.py"], dataset_name="andes_workspace_123")

```

---

## 3. `cognee.recall`

**Path:** `cognee/api/v1/recall/recall.py`
**Retrievers:** `cognee/modules/retrieval/`

### Public Function Signature

```python
async def recall(
    query: str, 
    dataset_name: str = "default", 
    search_type: SearchType = SearchType.HYBRID, 
    **kwargs
) -> List[SearchResultItem]:

```

### Parameters

* `query` (str): The semantic or structural query from the user/agent.
* `dataset_name` (str): The namespace to constrain the search.
* `search_type` (Enum): The algorithm to use (`SearchType.VECTOR`, `SearchType.GRAPH`, `SearchType.HYBRID`, `SearchType.CHUNKS`).

### Execution Flow & Implementation Summary

1. **Decomposition:** The query is optionally decomposed into sub-queries for broader semantic coverage (`query_decomposition.py`).
2. **Entry Point Search:** `HYBRID` search executes a vector similarity search on `LanceDB` to find relevant starting chunks.
3. **Graph Traversal:** Extracts connected entities (Triplets) from the starting chunks using the Graph DB.
4. **Ranking & Formatting:** Aggregates facts, sorts by relevance, and returns `SearchResultItem` payloads.

### Reference Links

* **Search Types Enum:** `cognee/modules/search/types/SearchType.py`
* **Tests:** `cognee/tests/unit/api/v1/recall/test_recall_api.py`

### RE:Track Integration

Used during the context-gathering phase of prompt execution. Use `SearchType.HYBRID` to fetch both semantically related code and structurally connected dependencies.

```python
from cognee.modules.search.types.SearchType import SearchType

context = await cognee.recall(
    query="Where is the database initialized?", 
    dataset_name="andes_workspace_123",
    search_type=SearchType.HYBRID
)

```

---

## 4. `cognee.forget`

**Path:** `cognee/api/v1/forget/forget.py`
**Deletion Logic:** `cognee/modules/data/deletion/`

### Public Function Signature

```python
async def forget(
    dataset: str = None, 
    dataset_id: UUID = None,
    data_id: UUID = None,
    **kwargs
) -> None:

```

### Parameters

* `dataset` (Optional[str]): Deletes all knowledge associated with a specific workspace namespace.
* `dataset_id` (Optional[UUID]): Targets a dataset by UUID.
* `data_id` (Optional[UUID]): Targets a specific ingested data item by UUID for targeted forgetting.

### Execution Flow & Implementation Summary

1. **Resolution:** Queries the relational ledger to find the internal IDs of nodes, edges, and vectors tied to the `dataset_name` or `document_id`.
2. **Cascade Deletion:** Sequentially removes vectors from `LanceDB`, edges/nodes from `Kùzu`, and finally purges the relational records (`delete_data.py`).

### Reference Links

* **Implementation:** `cognee/modules/data/methods/delete_dataset.py`
* **Tests:** `cognee/tests/unit/api/v1/forget/test_forget_endpoint.py`

### RE:Track Integration

Essential for maintaining sync with the file system. When a file is deleted or heavily refactored in the IDE, RE:Track must call `forget` on the specific file/dataset before re-ingesting it via `remember`.

**Note**: Verified against Cognee v1.2.2. The parameter is `dataset` (not `dataset_name`) and `data_id` (not `document_id`).

---

## 5. `cognee.improve`

**Path:** `cognee/api/v1/improve/improve.py`
**Graph Improvement Logic:** `cognee/modules/truth_subspace/`

### Public Function Signature

```python
async def improve() -> None:

```

### Execution Flow & Implementation Summary

1. **Deduplication:** Scans the knowledge graph for redundant entity nodes (e.g., "User" vs "Users") and merges their relationships (canonicalization).
2. **Summarization:** Analyzes connected subgraphs to generate higher-level summary nodes, populating a `global_context_index`.
3. **Orphan Cleanup:** Removes disconnected graph nodes that no longer contribute to semantic meaning.

### Reference Links

* **Implementation Tasks:** `cognee/tasks/memify/global_context_index/summarize.py`
* **Tests:** `cognee/tests/unit/api/v1/improve/test_improve_agent_context.py`

### RE:Track Integration

This is a computationally expensive background task. RE:Track should schedule `improve()` to run asynchronously during idle time, specifically after a large bulk ingestion of an entire repository.