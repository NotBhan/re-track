# RE:Track Context Engine — Phase 7 Baseline Evaluation Report

**Total Tasks**: 20 | **Passed**: 9 (45.0%) | **Failed**: 11

## 1. Aggregate Metric Summary

| Metric | Measured Score | Target Threshold | Status |
| :--- | :--- | :--- | :--- |
| **Precision@K** | `0.144` | `>= 0.400` | ⚠️ ATTENTION |
| **Recall@K** | `0.469` | `>= 0.500` | ⚠️ ATTENTION |
| **Critical Evidence Coverage** | `0.521` | `>= 0.600` | ⚠️ ATTENTION |
| **Noise Ratio** | `0.010` | `<= 0.200` | ✅ PASS |
| **Compression Ratio** | `14.04x` | `>= 5.0x` | ✅ PASS |
| **Average Retrieval Latency** | `1317.2 ms` | `<= 500 ms` | ⚠️ PASS |

## 2. Category Performance Breakdown

| Category | Total Tasks | Pass Rate | Mean P@K | Mean R@K | Mean Critical Coverage | Mean Noise |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **architecture** | 5 | 40.0% | `0.200` | `0.410` | `0.517` | `0.000` |
| **bug_localization** | 5 | 40.0% | `0.120` | `0.500` | `0.317` | `0.020` |
| **feature_addition** | 5 | 60.0% | `0.120` | `0.600` | `0.733` | `0.020` |
| **refactoring** | 5 | 40.0% | `0.137` | `0.367` | `0.517` | `0.000` |

## 3. Individual Task Evaluation Results

| Task ID | Category | Verdict | P@K | R@K | Crit Cov | Noise | Tokens | Latency | Missing Critical |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `TASK-ARCH-01` | architecture | **FAIL** | `0.30` | `0.60` | `0.00` | `0.00` | 1679 | 733ms | backend/app/application/container.py, backend/app/server.py, ApplicationContainer, create |
| `TASK-ARCH-02` | architecture | **FAIL** | `0.10` | `0.20` | `0.50` | `0.00` | 2029 | 991ms | backend/app/services/repository_metadata_store.py, backend/app/services/repository_manager.py |
| `TASK-ARCH-03` | architecture | **PASS** | `0.30` | `0.75` | `1.00` | `0.00` | 1598 | 3275ms | None |
| `TASK-ARCH-04` | architecture | **PASS** | `0.30` | `0.50` | `0.75` | `0.00` | 1931 | 3107ms | all_routers |
| `TASK-ARCH-05` | architecture | **FAIL** | `0.00` | `0.00` | `0.33` | `0.00` | 2055 | 822ms | backend/app/services/indexing_service.py, backend/app/services/context_service.py, backend/app/services/package_builder.py, PackageBuilder |
| `TASK-BUG-01` | bug_localization | **FAIL** | `0.10` | `0.50` | `0.00` | `0.00` | 1741 | 522ms | backend/app/services/repository_manager.py, RepositoryManager |
| `TASK-BUG-02` | bug_localization | **PASS** | `0.20` | `0.67` | `0.75` | `0.00` | 1808 | 820ms | ContextCache |
| `TASK-BUG-03` | bug_localization | **FAIL** | `0.10` | `0.50` | `0.33` | `0.10` | 1679 | 569ms | BudgetManager, apply |
| `TASK-BUG-04` | bug_localization | **PASS** | `0.10` | `0.50` | `0.50` | `0.00` | 2002 | 3505ms | context_gen_lock |
| `TASK-BUG-05` | bug_localization | **FAIL** | `0.10` | `0.33` | `0.00` | `0.00` | 1917 | 585ms | backend/app/services/llm_provider_service.py, backend/app/services/context_service.py, LLMProviderService, check_health |
| `TASK-FEAT-01` | feature_addition | **FAIL** | `0.00` | `0.00` | `0.50` | `0.00` | 2243 | 2897ms | backend/app/application/ports/__init__.py, backend/app/application/container.py |
| `TASK-FEAT-02` | feature_addition | **PASS** | `0.10` | `1.00` | `1.00` | `0.00` | 1737 | 569ms | None |
| `TASK-FEAT-03` | feature_addition | **PASS** | `0.10` | `0.50` | `1.00` | `0.10` | 1814 | 802ms | None |
| `TASK-FEAT-04` | feature_addition | **PASS** | `0.20` | `1.00` | `0.67` | `0.00` | 1730 | 546ms | parse_intent_heuristics |
| `TASK-FEAT-05` | feature_addition | **FAIL** | `0.20` | `0.50` | `0.50` | `0.00` | 1950 | 644ms | backend/app/api/routers/packages.py, PackageUseCases |
| `TASK-REFAC-01` | refactoring | **PASS** | `0.10` | `0.33` | `0.50` | `0.00` | 1973 | 3545ms | create, get_container |
| `TASK-REFAC-02` | refactoring | **FAIL** | `0.20` | `0.50` | `0.75` | `0.00` | 1647 | 3678ms | backend/app/application/dto/__init__.py |
| `TASK-REFAC-03` | refactoring | **FAIL** | `0.10` | `0.33` | `0.25` | `0.00` | 1721 | 3635ms | backend/app/services/repository_summary.py, CallNode, CallEdge |
| `TASK-REFAC-04` | refactoring | **FAIL** | `0.00` | `0.00` | `0.33` | `0.00` | 2471 | 3255ms | backend/app/services/package_builder.py, build |
| `TASK-REFAC-05` | refactoring | **PASS** | `0.29` | `0.67` | `0.75` | `0.00` | 997 | 2548ms | HardwareTelemetryAdapter |