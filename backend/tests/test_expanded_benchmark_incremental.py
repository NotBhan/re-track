"""Tests for RE:Track incremental mutation scenarios across repositories.

Verifies that all 7 mutation scenarios execute deterministically in temporary environments
and properly leverage AST reuse and delta manifests.
"""

from pathlib import Path
import pytest

from app.evaluation.expanded_benchmark import IncrementalMutationEvaluator


def test_incremental_mutation_scenarios():
    corpus_dir = Path(__file__).parent.parent.parent / "benchmarks" / "corpus"
    results = IncrementalMutationEvaluator.run_all_scenarios(corpus_dir)

    assert len(results) == 7

    scenario_map = {r.scenario_name: r for r in results}

    # 1. Cold initial index: all files parsed, 0 reused
    cold = scenario_map["cold_initial_index"]
    assert cold.passed
    assert cold.files_parsed > 0
    assert cold.files_reused == 0

    # 2. Warm noop reindex: 0 files parsed, all reused
    warm = scenario_map["warm_noop_reindex"]
    assert warm.passed
    assert warm.files_parsed == 0
    assert warm.files_reused > 0

    # 3. Single file modification: exactly 1 file parsed, rest reused
    mod = scenario_map["single_file_modification"]
    assert mod.passed
    assert mod.files_parsed == 1
    assert mod.files_reused > 0

    # 4. Single file addition: exactly 1 file parsed, existing reused
    add = scenario_map["single_file_addition"]
    assert add.passed
    assert add.files_parsed == 1
    assert add.files_reused > 0

    # 5. Single file deletion: 0 files parsed, remaining reused
    delete = scenario_map["single_file_deletion"]
    assert delete.passed
    assert delete.files_parsed == 0
    assert delete.files_reused > 0

    # 6. Rename without edit: detected rename, fast reuse
    rename = scenario_map["rename_without_edit"]
    assert rename.passed

    # 7. Dependency relink: single dependent parsed, rest reused
    relink = scenario_map["dependency_relink"]
    assert relink.passed
    assert relink.files_parsed == 1
    assert relink.files_reused >= 4
