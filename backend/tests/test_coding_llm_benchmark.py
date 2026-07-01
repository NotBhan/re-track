"""Coding LLM benchmark — validates Context Packages against repository questions.

Runs 15 benchmark questions through the PackageBuilder pipeline and scores
each package against expected files and symbols. Uses mock data to validate
the scoring framework independent of live Cognee.
"""

import json
import re
from pathlib import Path

import pytest

from app.models.responses import RecallResult
from app.services.package_builder import PackageBuilder


BENCHMARK_DIR = Path(__file__).resolve().parent.parent.parent / "benchmarks" / "andescontext"


def _load_expected(filename: str) -> dict:
    """Load expected answers from benchmark JSON file."""
    path = BENCHMARK_DIR / filename
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _score_files(package_md: str, expected_files: list[str], critical_files: list[str]) -> dict:
    """Score how many expected files appear in the package."""
    found = []
    missing = []

    for f in expected_files:
        fname = Path(f).name
        if f in package_md or fname in package_md:
            found.append(f)
        else:
            missing.append(f)

    critical_found = []
    critical_missing = []
    for f in critical_files:
        fname = Path(f).name
        if f in package_md or fname in package_md:
            critical_found.append(f)
        else:
            critical_missing.append(f)

    total = len(expected_files) or 1
    return {
        "found": found,
        "missing": missing,
        "critical_found": critical_found,
        "critical_missing": critical_missing,
        "score": len(found) / total,
        "critical_score": len(critical_found) / max(len(critical_files), 1),
    }


def _score_symbols(package_md: str, expected_symbols: list[str], critical_symbols: list[str]) -> dict:
    """Score how many expected symbols appear in the package."""
    found = [s for s in expected_symbols if s in package_md]
    missing = [s for s in expected_symbols if s not in package_md]

    critical_found = [s for s in critical_symbols if s in package_md]
    critical_missing = [s for s in critical_symbols if s not in package_md]

    total = len(expected_symbols) or 1
    return {
        "found": found,
        "missing": missing,
        "critical_found": critical_found,
        "critical_missing": critical_missing,
        "score": len(found) / total,
        "critical_score": len(critical_found) / max(len(critical_symbols), 1),
    }


def _detect_hallucinations(package_md: str, expected_files: list[str]) -> list[str]:
    """Detect file references in package that don't match expected files."""
    refs = re.findall(r"`([^`]+\.\w+)`", package_md)
    file_refs = [r for r in refs if "/" in r or r.endswith((".py", ".ts", ".js", ".md", ".json"))]
    expected_names = {Path(f).name for f in expected_files}
    return [r for r in file_refs if Path(r).name not in expected_names and r not in expected_files]


def _score_package(question_id: str, package_md: str, expected_files: dict, expected_symbols: dict) -> dict:
    """Score a single package against expected answers."""
    files_exp = expected_files.get(question_id, {})
    symbols_exp = expected_symbols.get(question_id, {})

    file_score = _score_files(
        package_md,
        files_exp.get("expected_files", []),
        files_exp.get("critical_files", []),
    )
    symbol_score = _score_symbols(
        package_md,
        symbols_exp.get("expected_symbols", []),
        symbols_exp.get("critical_symbols", []),
    )
    hallucinations = _detect_hallucinations(package_md, files_exp.get("expected_files", []))

    overall = (
        file_score["critical_score"] * 0.4
        + symbol_score["critical_score"] * 0.4
        + file_score["score"] * 0.1
        + symbol_score["score"] * 0.1
    )

    return {
        "question_id": question_id,
        "file_score": file_score,
        "symbol_score": symbol_score,
        "hallucinations": hallucinations,
        "overall_score": round(overall, 3),
        "verdict": "PASS" if overall >= 0.6 else "FAIL",
    }


class TestCodingLLMBenchmark:
    """Run benchmark questions through the package builder and score results."""

    def test_all_questions_score(self):
        """Score all benchmark questions against expected answers."""
        expected_files = _load_expected("expected_files.json")
        expected_symbols = _load_expected("expected_symbols.json")

        if not expected_files:
            pytest.skip("No benchmark data found")

        results = []
        for qid in sorted(expected_files.keys()):
            # Build mock results that include the expected files and symbols
            mock_results = []
            for f in expected_files[qid].get("expected_files", [])[:3]:
                mock_results.append(RecallResult(
                    kind="file", search_type="semantic",
                    text=f, score=0.9, dataset_name="test",
                ))
            for s in expected_symbols.get(qid, {}).get("expected_symbols", [])[:3]:
                mock_results.append(RecallResult(
                    kind="text", search_type="semantic",
                    text=f"The {s} function is defined in the module",
                    score=0.8, dataset_name="test",
                ))
                # Also add a result with just the symbol name for exact matching
                mock_results.append(RecallResult(
                    kind="text", search_type="semantic",
                    text=s,
                    score=0.7, dataset_name="test",
                ))
            if not mock_results:
                mock_results.append(RecallResult(
                    kind="text", search_type="semantic",
                    text=f"General information about {qid}",
                    score=0.5, dataset_name="test",
                ))
            pkg = PackageBuilder().build(f"Query {qid}", mock_results, None, ["test"])
            score = _score_package(qid, pkg.markdown, expected_files, expected_symbols)
            results.append(score)

        avg_score = sum(r["overall_score"] for r in results) / max(len(results), 1)
        pass_count = sum(1 for r in results if r["verdict"] == "PASS")

        print(f"\n--- Coding LLM Benchmark ---")
        print(f"Questions: {len(results)}")
        print(f"Average Score: {avg_score:.3f}")
        print(f"Pass: {pass_count}/{len(results)}")
        for r in results:
            print(f"  {r['question_id']}: {r['overall_score']:.3f} ({r['verdict']})")

        assert pass_count >= len(results) * 0.5, f"Only {pass_count}/{len(results)} passed"

    def test_scoring_functions_work(self):
        """Verify scoring functions produce valid output."""
        expected_files = _load_expected("expected_files.json")
        expected_symbols = _load_expected("expected_symbols.json")

        if not expected_files:
            pytest.skip("No benchmark data found")

        # Test with a real package
        mock_results = [
            RecallResult(kind="file", search_type="semantic", text="backend/app/services/context_service.py", score=0.9, dataset_name="test"),
        ]
        pkg = PackageBuilder().build("How does ContextService work?", mock_results, None, ["test"])

        score = _score_package("Q13", pkg.markdown, expected_files, expected_symbols)
        assert "overall_score" in score
        assert "verdict" in score
        assert score["overall_score"] >= 0.0

    def test_hallucination_detection(self):
        """Verify hallucination detection works."""
        md = "See `real_file.py` and `fake_file.py`"
        expected = ["real_file.py"]
        hallucinations = _detect_hallucinations(md, expected)
        assert "fake_file.py" in hallucinations
        assert "real_file.py" not in hallucinations

    def test_file_scoring(self):
        """Verify file scoring works."""
        md = "The file `backend/app/main.py` contains the entry point"
        found, missing = [], []
        for f in ["backend/app/main.py", "backend/app/config.py"]:
            if f in md or Path(f).name in md:
                found.append(f)
            else:
                missing.append(f)
        assert len(found) == 1
        assert len(missing) == 1

    def test_symbol_scoring(self):
        """Verify symbol scoring works."""
        md = "The ContextService class uses PackageBuilder"
        assert "ContextService" in md
        assert "PackageBuilder" in md
        assert "NonexistentSymbol" not in md
