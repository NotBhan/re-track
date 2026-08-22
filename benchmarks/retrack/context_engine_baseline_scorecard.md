# RE:Track Context Engine — Phase 7 Baseline Evaluation Report

**Total Tasks**: 20 | **Passed**: 9 (45.0%) | **Failed**: 11

## 1. Aggregate Metric Summary

| Metric | Measured Score | Target Threshold | Status |
| :--- | :--- | :--- | :--- |
| **Precision@K** | `0.141` | `>= 0.400` | ⚠️ ATTENTION |
| **Recall@K** | `0.434` | `>= 0.500` | ⚠️ ATTENTION |
| **Critical Evidence Coverage** | `0.496` | `>= 0.600` | ⚠️ ATTENTION |
| **Noise Ratio** | `0.010` | `<= 0.200` | ✅ PASS |
| **Compression Ratio** | `14.02x` | `>= 5.0x` | ✅ PASS |
| **Average Retrieval Latency** | `854.6 ms` | `<= 500 ms` | ⚠️ PASS |

## 2. Category Performance Breakdown

| Category | Total Tasks | Pass Rate | Mean P@K | Mean R@K | Mean Critical Coverage | Mean Noise |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **architecture** | 5 | 40.0% | `0.180` | `0.370` | `0.417` | `0.000` |
| **bug_localization** | 5 | 40.0% | `0.120` | `0.500` | `0.317` | `0.020` |
| **feature_addition** | 5 | 60.0% | `0.100` | `0.500` | `0.733` | `0.020` |
| **refactoring** | 5 | 40.0% | `0.162` | `0.367` | `0.517` | `0.000` |

## 3. Individual Task Evaluation Results

| Task ID | Category | Verdict | P@K | R@K | Crit Cov | Noise | Tokens | Latency | Missing Critical |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `TASK-ARCH-01` | architecture | **FAIL** | `0.20` | `0.40` | `0.00` | `0.00` | 1642 | 402ms | backend/app/application/container.py, backend/app/server.py, ApplicationContainer, create |
| `TASK-ARCH-02` | architecture | **FAIL** | `0.10` | `0.20` | `0.00` | `0.00` | 2042 | 565ms | backend/app/services/repository_metadata_store.py, backend/app/services/repository_manager.py, RepositoryMetadataStore, RepositoryManager |
| `TASK-ARCH-03` | architecture | **PASS** | `0.30` | `0.75` | `1.00` | `0.00` | 1601 | 2143ms | None |
| `TASK-ARCH-04` | architecture | **PASS** | `0.30` | `0.50` | `0.75` | `0.00` | 1934 | 1764ms | all_routers |
| `TASK-ARCH-05` | architecture | **FAIL** | `0.00` | `0.00` | `0.33` | `0.00` | 2058 | 403ms | backend/app/services/indexing_service.py, backend/app/services/context_service.py, backend/app/services/package_builder.py, PackageBuilder |
| `TASK-BUG-01` | bug_localization | **FAIL** | `0.10` | `0.50` | `0.00` | `0.00` | 1703 | 513ms | backend/app/services/repository_manager.py, RepositoryManager |
| `TASK-BUG-02` | bug_localization | **PASS** | `0.20` | `0.67` | `0.75` | `0.00` | 1812 | 324ms | ContextCache |
| `TASK-BUG-03` | bug_localization | **FAIL** | `0.10` | `0.50` | `0.33` | `0.10` | 1682 | 315ms | BudgetManager, apply |
| `TASK-BUG-04` | bug_localization | **PASS** | `0.10` | `0.50` | `0.50` | `0.00` | 2019 | 2325ms | context_gen_lock |
| `TASK-BUG-05` | bug_localization | **FAIL** | `0.10` | `0.33` | `0.00` | `0.00` | 1920 | 350ms | backend/app/services/llm_provider_service.py, backend/app/services/context_service.py, LLMProviderService, check_health |
| `TASK-FEAT-01` | feature_addition | **FAIL** | `0.00` | `0.00` | `0.50` | `0.00` | 2228 | 1856ms | backend/app/application/ports/__init__.py, backend/app/application/container.py |
| `TASK-FEAT-02` | feature_addition | **PASS** | `0.10` | `1.00` | `1.00` | `0.00` | 1740 | 559ms | None |
| `TASK-FEAT-03` | feature_addition | **PASS** | `0.10` | `0.50` | `1.00` | `0.10` | 1817 | 348ms | None |
| `TASK-FEAT-04` | feature_addition | **PASS** | `0.10` | `0.50` | `0.67` | `0.00` | 1860 | 329ms | parse_intent_heuristics |
| `TASK-FEAT-05` | feature_addition | **FAIL** | `0.20` | `0.50` | `0.50` | `0.00` | 1954 | 409ms | backend/app/api/routers/packages.py, PackageUseCases |
| `TASK-REFAC-01` | refactoring | **PASS** | `0.11` | `0.33` | `0.50` | `0.00` | 1976 | 2492ms | create, get_container |
| `TASK-REFAC-02` | refactoring | **FAIL** | `0.20` | `0.50` | `0.75` | `0.00` | 1650 | 2365ms | backend/app/application/dto/__init__.py |
| `TASK-REFAC-03` | refactoring | **FAIL** | `0.10` | `0.33` | `0.25` | `0.00` | 1671 | 2279ms | backend/app/services/repository_summary.py, CallNode, CallEdge |
| `TASK-REFAC-04` | refactoring | **FAIL** | `0.00` | `0.00` | `0.33` | `0.00` | 2474 | 1824ms | backend/app/services/package_builder.py, build |
| `TASK-REFAC-05` | refactoring | **PASS** | `0.40` | `0.67` | `0.75` | `0.00` | 1000 | 1998ms | HardwareTelemetryAdapter |