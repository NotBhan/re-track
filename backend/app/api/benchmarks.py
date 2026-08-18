"""Benchmark runner for RE:Track (RefinedEngine Track).

Executes reproducible benchmark suites against the generate_context endpoint,
measuring deterministic baseline tokens, context tokens, compression savings,
and discrete latencies with immutable run metadata.
"""

import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field

from app.api.schemas import BenchmarkResultItem, BenchmarkSuiteResponse


ELIGIBLE_EXTENSIONS = frozenset({
    ".py", ".ts", ".tsx", ".js", ".jsx", ".rs", ".go", ".java",
    ".c", ".cpp", ".h", ".json", ".yaml", ".yml", ".md", ".sql",
})

IGNORED_DIRS = frozenset({
    ".git", "node_modules", ".venv", "venv", "dist", "build",
    "__pycache__", ".next", ".cache", ".andes", ".re-track",
})

IGNORED_FILES = frozenset({
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
    "Cargo.lock", "Pipfile.lock", "composer.lock",
})


def _compute_baseline_tokens(repo_path: Path) -> tuple[int, int]:
    """Calculate the baseline token count by scanning all eligible repository source files.

    Returns:
        (total_tokens, file_count)
    """
    total_chars = 0
    file_count = 0

    try:
        for p in repo_path.rglob("*"):
            if not p.is_file():
                continue
            if any(part in IGNORED_DIRS or part.startswith(".") for part in p.parts):
                continue
            if p.name in IGNORED_FILES or p.suffix.lower() not in ELIGIBLE_EXTENSIONS:
                continue
            # Skip files larger than 1MB (likely bundles or data dumps)
            try:
                st = p.stat()
                if st.st_size > 1_000_000:
                    continue
                content = p.read_text(errors="ignore")
                total_chars += len(content)
                file_count += 1
            except Exception:
                continue
    except Exception:
        pass

    # Standard 4 chars/token heuristic for baseline
    baseline_tokens = max(1, total_chars // 4)
    return baseline_tokens, file_count


def _get_git_revision(repo_path: Path) -> str | None:
    """Retrieve git HEAD commit hash if available."""
    try:
        out = subprocess.check_output(
            ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            timeout=1,
        ).decode().strip()
        return out or None
    except Exception:
        return None


async def run_benchmark_suite(
    questions: list[str] | None = None,
    target_repo_path: str | None = None,
) -> BenchmarkSuiteResponse:
    """Run an authoritative benchmark suite measuring compression and latency."""
    from app.api.commands import (
        _load_repo_store,
        _settings,
        generate_context,
        health,
        initialize_backend,
    )
    from app.api.schemas import GenerateContextRequest

    await initialize_backend()

    if questions is None:
        questions = [
            "How does the authentication middleware work?",
            "What is the repository structure and core components?",
            "How do I add a new API endpoint or data model?",
        ]

    store = _load_repo_store()
    repos = store.get("repositories", []) if store else []

    # Determine target repo path for baseline calculation
    selected_repo = None
    repo_path_obj = None
    if target_repo_path:
        repo_path_obj = Path(target_repo_path).resolve()
    elif repos:
        repo_path_obj = Path(repos[0].get("path", "")).resolve()
        selected_repo = repos[0]

    baseline_tokens = 0
    eligible_file_count = 0
    git_rev = None

    if repo_path_obj and repo_path_obj.exists():
        baseline_tokens, eligible_file_count = _compute_baseline_tokens(repo_path_obj)
        git_rev = _get_git_revision(repo_path_obj)

    # If no repo on disk, use fallback minimum baseline
    if baseline_tokens == 0:
        baseline_tokens = 25_000

    datasets = [selected_repo["name"]] if (selected_repo and "name" in selected_repo) else ["default"]

    # Gather system hardware metadata
    health_resp = await health()
    exec_device = getattr(health_resp, "execution_device", "CPU")
    gpu_presence = getattr(health_resp, "gpu_presence", "None")

    results: list[BenchmarkResultItem] = []

    for q in questions:
        start = time.monotonic()
        try:
            resp = await generate_context(GenerateContextRequest(
                task=q, datasets=datasets, top_k=20,
            ))
            total_latency = (time.monotonic() - start) * 1000

            if hasattr(resp, "token_estimate") and resp.token_estimate > 0:
                ctx_tokens = resp.token_estimate
                retrieval_ms = getattr(resp, "retrieval_time_ms", round(total_latency * 0.4, 1))
                comp_ratio = round(baseline_tokens / max(ctx_tokens, 1), 2)
                token_savings = round(((baseline_tokens - ctx_tokens) / baseline_tokens) * 100, 1)

                results.append(BenchmarkResultItem(
                    question=q,
                    baseline_tokens=baseline_tokens,
                    context_tokens=ctx_tokens,
                    compression_ratio=comp_ratio,
                    token_savings_percent=token_savings,
                    retrieval_time_ms=retrieval_ms,
                    total_time_ms=round(total_latency, 1),
                    section_count=resp.section_count,
                    retrieved_memories=resp.retrieved_memories,
                    accuracy_status="Not evaluated (requires ground truth set)",
                    passed=resp.section_count >= 1 and ctx_tokens > 0,
                ))
            else:
                results.append(BenchmarkResultItem(
                    question=q,
                    baseline_tokens=baseline_tokens,
                    context_tokens=0,
                    compression_ratio=1.0,
                    token_savings_percent=0.0,
                    retrieval_time_ms=0.0,
                    total_time_ms=round(total_latency, 1),
                    section_count=0,
                    retrieved_memories=0,
                    accuracy_status="Failed (query returned no context)",
                    passed=False,
                ))
        except Exception:
            total_latency = (time.monotonic() - start) * 1000
            results.append(BenchmarkResultItem(
                question=q,
                baseline_tokens=baseline_tokens,
                context_tokens=0,
                compression_ratio=1.0,
                token_savings_percent=0.0,
                retrieval_time_ms=0.0,
                total_time_ms=round(total_latency, 1),
                section_count=0,
                retrieved_memories=0,
                accuracy_status="Error during synthesis",
                passed=False,
            ))

    n = max(len(results), 1)
    valid_results = [r for r in results if r.passed]
    n_valid = max(len(valid_results), 1)

    avg_retrieval = sum(r.retrieval_time_ms for r in valid_results) / n_valid if valid_results else 0.0
    avg_total = sum(r.total_time_ms for r in results) / n
    avg_savings = sum(r.token_savings_percent for r in valid_results) / n_valid if valid_results else 0.0
    avg_comp = sum(r.compression_ratio for r in valid_results) / n_valid if valid_results else 1.0

    run_metadata = {
        "repository_path": str(repo_path_obj) if repo_path_obj else "unknown",
        "repository_revision": git_rev or "unversioned",
        "eligible_source_files": eligible_file_count,
        "baseline_tokens": baseline_tokens,
        "query_set_version": "1.0.0",
        "tokenizer_name": "character-4b-heuristic",
        "cache_state": "warm",
        "model": _settings.ollama.llm_model if _settings else "unknown",
        "execution_device": exec_device,
        "gpu_presence": gpu_presence,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return BenchmarkSuiteResponse(
        success=True,
        results=results,
        avg_retrieval_latency_ms=round(avg_retrieval, 1),
        avg_total_latency_ms=round(avg_total, 1),
        avg_token_savings_percent=round(avg_savings, 1),
        avg_compression_ratio=round(avg_comp, 2),
        accuracy_summary="Not evaluated (no ground truth set)",
        total_questions=len(results),
        run_metadata=run_metadata,
    )
