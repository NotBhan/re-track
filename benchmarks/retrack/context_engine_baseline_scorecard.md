# RE:Track Context Engine — Phase 7 Baseline Evaluation Report

**Total Tasks**: 20 | **Passed**: 11 (55.0%) | **Failed**: 9

## 1. Aggregate Metric Summary

| Metric | Measured Score | Target Threshold | Status |
| :--- | :--- | :--- | :--- |
| **Precision@K** | `0.194` | `>= 0.400` | ⚠️ ATTENTION |
| **Recall@K** | `0.439` | `>= 0.500` | ⚠️ ATTENTION |
| **Critical Evidence Coverage** | `0.550` | `>= 0.600` | ⚠️ ATTENTION |
| **Noise Ratio** | `0.006` | `<= 0.200` | ✅ PASS |
| **Compression Ratio** | `16.35x` | `>= 5.0x` | ✅ PASS |
| **Average Retrieval Latency** | `916.5 ms` | `<= 500 ms` | ⚠️ PASS |

## 2. Category Performance Breakdown

| Category | Total Tasks | Pass Rate | Mean P@K | Mean R@K | Mean Critical Coverage | Mean Noise |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **architecture** | 5 | 40.0% | `0.167` | `0.290` | `0.417` | `0.000` |
| **bug_localization** | 5 | 80.0% | `0.175` | `0.600` | `0.533` | `0.000` |
| **feature_addition** | 5 | 60.0% | `0.125` | `0.500` | `0.733` | `0.025` |
| **refactoring** | 5 | 40.0% | `0.308` | `0.367` | `0.517` | `0.000` |

## 3. Individual Task Evaluation Results

| Task ID | Category | Verdict | P@K | R@K | Crit Cov | Noise | Tokens | Latency | Missing Critical |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `TASK-ARCH-01` | architecture | **FAIL** | `0.12` | `0.20` | `0.00` | `0.00` | 1406 | 954ms | backend/app/application/container.py, backend/app/server.py, ApplicationContainer, create |
| `TASK-ARCH-02` | architecture | **FAIL** | `0.00` | `0.00` | `0.00` | `0.00` | 1808 | 739ms | backend/app/services/repository_metadata_store.py, backend/app/services/repository_manager.py, RepositoryMetadataStore, RepositoryManager |
| `TASK-ARCH-03` | architecture | **PASS** | `0.38` | `0.75` | `1.00` | `0.00` | 1367 | 2203ms | None |
| `TASK-ARCH-04` | architecture | **PASS** | `0.33` | `0.50` | `0.75` | `0.00` | 1700 | 2690ms | all_routers |
| `TASK-ARCH-05` | architecture | **FAIL** | `0.00` | `0.00` | `0.33` | `0.00` | 1823 | 816ms | backend/app/services/indexing_service.py, backend/app/services/context_service.py, backend/app/services/package_builder.py, PackageBuilder |
| `TASK-BUG-01` | bug_localization | **PASS** | `0.25` | `1.00` | `0.50` | `0.00` | 1445 | 997ms | RepositoryManager |
| `TASK-BUG-02` | bug_localization | **PASS** | `0.25` | `0.67` | `0.75` | `0.00` | 1610 | 745ms | ContextCache |
| `TASK-BUG-03` | bug_localization | **PASS** | `0.12` | `0.50` | `0.67` | `0.00` | 1448 | 722ms | apply |
| `TASK-BUG-04` | bug_localization | **PASS** | `0.12` | `0.50` | `0.50` | `0.00` | 1785 | 3063ms | context_gen_lock |
| `TASK-BUG-05` | bug_localization | **FAIL** | `0.12` | `0.33` | `0.25` | `0.00` | 1621 | 736ms | backend/app/services/llm_provider_service.py, backend/app/services/context_service.py, check_health |
| `TASK-FEAT-01` | feature_addition | **FAIL** | `0.00` | `0.00` | `0.50` | `0.00` | 1993 | 2560ms | backend/app/application/ports/__init__.py, backend/app/application/container.py |
| `TASK-FEAT-02` | feature_addition | **PASS** | `0.12` | `1.00` | `1.00` | `0.00` | 1504 | 734ms | None |
| `TASK-FEAT-03` | feature_addition | **PASS** | `0.12` | `0.50` | `1.00` | `0.12` | 1583 | 733ms | None |
| `TASK-FEAT-04` | feature_addition | **PASS** | `0.12` | `0.50` | `0.67` | `0.00` | 1578 | 951ms | parse_intent_heuristics |
| `TASK-FEAT-05` | feature_addition | **FAIL** | `0.25` | `0.50` | `0.50` | `0.00` | 1719 | 752ms | backend/app/api/routers/packages.py, PackageUseCases |
| `TASK-REFAC-01` | refactoring | **PASS** | `0.17` | `0.33` | `0.50` | `0.00` | 1795 | 3215ms | create, get_container |
| `TASK-REFAC-02` | refactoring | **FAIL** | `0.25` | `0.50` | `0.75` | `0.00` | 1418 | 2926ms | backend/app/application/dto/__init__.py |
| `TASK-REFAC-03` | refactoring | **FAIL** | `0.12` | `0.33` | `0.25` | `0.00` | 1436 | 2996ms | backend/app/services/repository_summary.py, CallNode, CallEdge |
| `TASK-REFAC-04` | refactoring | **FAIL** | `0.00` | `0.00` | `0.33` | `0.00` | 2056 | 2784ms | backend/app/services/package_builder.py, build |
| `TASK-REFAC-05` | refactoring | **PASS** | `1.00` | `0.67` | `0.75` | `0.00` | 765 | 2315ms | HardwareTelemetryAdapter |