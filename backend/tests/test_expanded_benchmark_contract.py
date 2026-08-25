"""Contract and integrity tests for Phase 10C expanded retrieval benchmark.

Verifies:
1. Frozen baseline assets from Phase 7/9D remain 100% byte-for-byte immutable.
2. Expanded benchmark corpus and golden tasks schema integrity (36 tasks, 12 categories, 6 repos).
3. Ground truth path existence: all expected and critical files genuinely exist in their fixture repositories.
4. Ground truth symbol existence: all expected and critical symbols exist in source files.
5. Strict domain neutrality guard (zero prohibited commercial/payment/auth words).
"""

import hashlib
import json
from pathlib import Path
import re
import pytest

from app.evaluation.expanded_benchmark import ExpandedBenchmarkEvaluator


# Exact SHA-256 hashes of immutable frozen baseline files
FROZEN_BASELINE_HASHES = {
    "benchmarks/retrack/golden_tasks.json": "3ca041be5adb31d0483b27893593be9c62449264add54807723556dcbf292a91",
    "backend/tests/test_benchmark_baseline_contract.py": "ae6fe23b90a275020860e30d5431b22fde0b38358a9e70d566be550b515eccac",
}

PROHIBITED_TERMS_PATTERN = re.compile(
    r"\b(payment|billing|checkout|subscription|wallet|invoice|customer|account|login|password|monetization)\b",
    re.IGNORECASE,
)

EXPECTED_CATEGORIES = {
    "python_layered_architecture",
    "typescript_structural",
    "javascript_structural",
    "barrel_reexport",
    "path_alias",
    "cross_package_monorepo",
    "polyglot_cross_language",
    "calls_relationship",
    "inherits_implements",
    "type_reference",
    "jsx_render",
    "noise_discrimination",
}

EXPECTED_REPOSITORIES = {
    "py_backend",
    "ts_react",
    "ts_barrel",
    "polyglot",
    "ts_alias",
    "monorepo",
}


def test_frozen_baseline_immutability():
    """Ensure Phase 7 baseline assets remain bitwise identical and uncorrupted."""
    root = Path(__file__).parent.parent.parent
    for rel_path, expected_hash in FROZEN_BASELINE_HASHES.items():
        target = root / rel_path
        assert target.exists(), f"Frozen file missing: {rel_path}"
        computed_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        assert computed_hash == expected_hash, (
            f"FROZEN ASSET MODIFIED: {rel_path}\n"
            f"Expected SHA-256: {expected_hash}\n"
            f"Actual SHA-256:   {computed_hash}"
        )

    scorecard = root / "benchmarks" / "retrack" / "context_engine_baseline_scorecard.md"
    assert scorecard.exists(), "Phase 7 baseline scorecard must exist"
    scorecard_text = scorecard.read_text(encoding="utf-8")
    assert "Phase 7 Baseline Evaluation Report" in scorecard_text
    assert "TASK-ARCH-01" in scorecard_text
    assert "TASK-REFAC-05" in scorecard_text


def test_expanded_golden_tasks_schema():
    """Verify golden tasks count, distribution across 12 categories, and valid repo mappings."""
    root = Path(__file__).parent.parent.parent
    golden_path = root / "benchmarks" / "expanded" / "golden_tasks.json"
    assert golden_path.exists(), "Expanded golden tasks file missing"

    tasks = ExpandedBenchmarkEvaluator.load_golden_tasks(golden_path)
    assert len(tasks) == 36, f"Expected exactly 36 tasks, found {len(tasks)}"

    task_ids = set()
    category_counts: dict[str, int] = {}
    repo_counts: dict[str, int] = {}

    for task in tasks:
        assert task.id not in task_ids, f"Duplicate task ID: {task.id}"
        task_ids.add(task.id)

        assert task.category in EXPECTED_CATEGORIES, f"Unexpected category: {task.category}"
        category_counts[task.category] = category_counts.get(task.category, 0) + 1

        assert task.repository_id in EXPECTED_REPOSITORIES, f"Unexpected repository: {task.repository_id}"
        repo_counts[task.repository_id] = repo_counts.get(task.repository_id, 0) + 1

        assert len(task.expected_files) >= 1
        assert len(task.critical_files) >= 1
        assert set(task.critical_files).issubset(set(task.expected_files))
        assert len(task.expected_symbols) >= 1
        assert len(task.critical_symbols) >= 1
        assert set(task.critical_symbols).issubset(set(task.expected_symbols))

    assert len(category_counts) == 12
    for cat, count in category_counts.items():
        assert count == 3, f"Category {cat} has {count} tasks, expected 3"

    assert len(repo_counts) == 6


def test_ground_truth_existence_in_corpus():
    """Verify every golden task references files and symbols that genuinely exist in its assigned repository."""
    root = Path(__file__).parent.parent.parent
    corpus_dir = root / "benchmarks" / "corpus"
    golden_path = root / "benchmarks" / "expanded" / "golden_tasks.json"

    tasks = ExpandedBenchmarkEvaluator.load_golden_tasks(golden_path)

    for task in tasks:
        repo_path = corpus_dir / task.repository_id
        assert repo_path.exists(), f"Repository fixture missing: {task.repository_id}"

        # Check expected files exist
        for exp_file in task.expected_files:
            target_path = repo_path / exp_file
            assert target_path.exists(), f"Task {task.id} expected file missing: {exp_file} in {task.repository_id}"

        # Check critical files exist
        for crit_file in task.critical_files:
            target_path = repo_path / crit_file
            assert target_path.exists(), f"Task {task.id} critical file missing: {crit_file} in {task.repository_id}"

        # Check irrelevant/noise files exist
        for noise_file in task.disallowed_noise:
            target_path = repo_path / noise_file
            assert target_path.exists(), f"Task {task.id} noise file missing: {noise_file} in {task.repository_id}"

        # Check expected symbols exist across expected files
        combined_content = ""
        for exp_file in task.expected_files:
            target_path = repo_path / exp_file
            combined_content += target_path.read_text(encoding="utf-8", errors="ignore") + "\n"

        for sym in task.expected_symbols:
            assert sym in combined_content, (
                f"Task {task.id} expected symbol '{sym}' not found in expected files: {task.expected_files}"
            )


def test_domain_neutrality_guard():
    """Verify benchmark corpus and golden tasks contain zero prohibited commercial/billing terms."""
    root = Path(__file__).parent.parent.parent
    corpus_dir = root / "benchmarks" / "corpus"
    golden_path = root / "benchmarks" / "expanded" / "golden_tasks.json"

    # 1. Check golden tasks
    golden_content = golden_path.read_text(encoding="utf-8")
    matches = PROHIBITED_TERMS_PATTERN.findall(golden_content)
    assert not matches, f"Prohibited domain terms found in golden_tasks.json: {set(matches)}"

    # 2. Check corpus code files
    for file_path in corpus_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix in (".py", ".ts", ".tsx", ".js", ".cjs", ".json", ".md"):
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            file_matches = PROHIBITED_TERMS_PATTERN.findall(content)
            assert not file_matches, f"Prohibited domain terms in {file_path.relative_to(corpus_dir)}: {set(file_matches)}"
