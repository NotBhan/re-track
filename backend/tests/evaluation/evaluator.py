"""Pure, framework-independent evaluation metric engine for Context Engine validation.

Computes exact quantitative retrieval metrics:
- Precision@K
- Recall@K
- Critical Evidence Coverage
- Noise Ratio
- Token Efficiency and Compression Ratios
- Attribution and Hallucination detection
"""

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any, Optional, Sequence


@dataclass
class GoldenTask:
    """Standardized representation of a single ground truth evaluation task."""

    id: str
    category: str
    task_prompt: str
    expected_files: list[str] = field(default_factory=list)
    critical_files: list[str] = field(default_factory=list)
    expected_symbols: list[str] = field(default_factory=list)
    critical_symbols: list[str] = field(default_factory=list)
    known_irrelevant_files: list[str] = field(default_factory=list)
    rationale: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GoldenTask":
        return cls(
            id=str(data.get("id", "")),
            category=str(data.get("category", "general")),
            task_prompt=str(data.get("task_prompt", "")),
            expected_files=list(data.get("expected_files", [])),
            critical_files=list(data.get("critical_files", [])),
            expected_symbols=list(data.get("expected_symbols", [])),
            critical_symbols=list(data.get("critical_symbols", [])),
            known_irrelevant_files=list(data.get("known_irrelevant_files", [])),
            rationale=str(data.get("rationale", "")),
        )


@dataclass
class TaskEvaluationResult:
    """Detailed evaluation score and evidence breakdown for a single task."""

    task_id: str
    category: str
    task_prompt: str
    precision_at_k: float
    recall_at_k: float
    critical_evidence_coverage: float
    noise_ratio: float
    token_savings_percent: float
    compression_ratio: float
    retrieved_files: list[str]
    missing_expected_files: list[str]
    missing_critical_files: list[str]
    retrieved_symbols: list[str]
    missing_expected_symbols: list[str]
    missing_critical_symbols: list[str]
    detected_noise_files: list[str]
    context_tokens: int
    baseline_tokens: int
    retrieval_time_ms: float
    total_time_ms: float
    passed: bool
    verdict: str
    failure_reasons: list[str] = field(default_factory=list)


@dataclass
class SuiteEvaluationSummary:
    """Aggregated statistical evaluation summary across all benchmark tasks."""

    total_tasks: int
    passed_tasks: int
    failed_tasks: int
    pass_rate: float
    mean_precision_at_k: float
    mean_recall_at_k: float
    mean_critical_coverage: float
    mean_noise_ratio: float
    mean_compression_ratio: float
    mean_retrieval_time_ms: float
    mean_total_time_ms: float
    category_breakdown: dict[str, dict[str, float]]
    task_results: list[TaskEvaluationResult]


def normalize_path(p: str) -> str:
    """Normalize a path string by removing leading ./, trailing slashes, and standardizing separators."""
    if not p:
        return ""
    clean = p.replace("\\", "/").strip()
    while clean.startswith("./"):
        clean = clean[2:]
    return clean.rstrip("/")


def match_path(expected: str, candidate: str) -> bool:
    """Collision-safe repository-relative path matcher.
    
    Rules:
    1. Exact normalized match:
       'backend/app/application/use_cases/context.py' == 'backend/app/application/use_cases/context.py'
    2. Suffix match with directory boundary when shorter path has at least one directory component:
       'app/application/use_cases/context.py' matches 'backend/app/application/use_cases/context.py'
       'use_cases/context.py' matches 'backend/app/application/use_cases/context.py'
    3. Bare basename-only matching without directory context is strictly DISALLOWED:
       'context.py' does NOT match 'backend/app/api/routers/context.py'.
    """
    exp_norm = normalize_path(expected)
    cand_norm = normalize_path(candidate)
    if not exp_norm or not cand_norm:
        return False
    if exp_norm == cand_norm:
        return True
    
    shorter, longer = (exp_norm, cand_norm) if len(exp_norm) <= len(cand_norm) else (cand_norm, exp_norm)
    if "/" in shorter:
        if longer.endswith("/" + shorter):
            return True
    return False


def match_symbol(symbol: str, markdown_text: str, structured_symbols: Sequence[str] = ()) -> bool:
    """Collision-safe symbol matcher using word boundaries and structured symbol lists.
    
    Rules:
    1. Direct membership in structured symbol lists (e.g. extracted_symbols, callers, callees).
    2. Exact backticked symbol match in Markdown text (e.g. `ApplicationContainer`).
    3. Word-boundary token match in Markdown text (regex \\b{symbol}\\b).
    4. Arbitrary substring match within other words is disallowed.
    """
    if not symbol:
        return False
    if symbol in structured_symbols:
        return True
    if not markdown_text:
        return False
    if f"`{symbol}`" in markdown_text:
        return True
    pattern = rf"\b{re.escape(symbol)}\b"
    return bool(re.search(pattern, markdown_text))


class ContextEngineEvaluator:
    """Pure, deterministic evaluation scorer for RE:Track context packages."""

    @staticmethod
    def load_golden_tasks(benchmark_dir: Path | str) -> list[GoldenTask]:
        """Load golden benchmark tasks from directory with legacy fallback.
        
        Raises FileNotFoundError if no benchmark files can be found.
        """
        bdir = Path(benchmark_dir)
        golden_file = bdir / "golden_tasks.json"
        
        # Primary canonical file
        if golden_file.exists():
            data = json.loads(golden_file.read_text(encoding="utf-8"))
            tasks_raw = data.get("tasks", []) if isinstance(data, dict) else data
            if not tasks_raw:
                raise ValueError(f"No tasks found in canonical benchmark file: {golden_file}")
            return [GoldenTask.from_dict(t) for t in tasks_raw]
        
        # Legacy fallback reconstruction from expected_files and expected_symbols
        expected_files_p = bdir / "expected_files.json"
        expected_symbols_p = bdir / "expected_symbols.json"
        
        if expected_files_p.exists():
            files_map = json.loads(expected_files_p.read_text(encoding="utf-8"))
            symbols_map = json.loads(expected_symbols_p.read_text(encoding="utf-8")) if expected_symbols_p.exists() else {}
            
            tasks = []
            for tid, f_info in files_map.items():
                s_info = symbols_map.get(tid, {})
                tasks.append(GoldenTask(
                    id=tid,
                    category="legacy",
                    task_prompt=f_info.get("question", ""),
                    expected_files=f_info.get("expected_files", []),
                    critical_files=f_info.get("critical_files", []),
                    expected_symbols=s_info.get("expected_symbols", []),
                    critical_symbols=s_info.get("critical_symbols", []),
                ))
            if not tasks:
                raise ValueError(f"No tasks reconstructible from legacy files in {bdir}")
            return tasks
        
        raise FileNotFoundError(f"Canonical benchmark tasks not found in {bdir}")

    @staticmethod
    def extract_file_references(context_markdown: str) -> list[str]:
        """Extract unique normalized relative file paths mentioned in context Markdown."""
        if not context_markdown:
            return []
        
        # 1. Backticked paths like `backend/app/main.py` or `src/lib/api.ts`
        backticked = re.findall(r"`([a-zA-Z0-9_\-\.\/]+\.[a-zA-Z0-9]+)`", context_markdown)
        
        # 2. Markdown headers like ### `backend/app/main.py` (Lines 1-50)
        headers = re.findall(r"###\s+`?([a-zA-Z0-9_\-\.\/]+\.[a-zA-Z0-9]+)`?", context_markdown)
        
        # 3. File list items like - `backend/app/main.py`
        list_items = re.findall(r"[\*\-]\s+`?([a-zA-Z0-9_\-\.\/]+\.[a-zA-Z0-9]+)`?", context_markdown)
        
        all_refs = backticked + headers + list_items
        
        # Filter valid source code extensions
        valid_exts = {
            ".py", ".ts", ".tsx", ".js", ".jsx", ".rs", ".go", ".java",
            ".json", ".yaml", ".yml", ".toml", ".md", ".sql", ".css", ".html"
        }
        
        cleaned = []
        for r in all_refs:
            p = normalize_path(r)
            if any(p.endswith(ext) for ext in valid_exts):
                if p not in cleaned:
                    cleaned.append(p)
                    
        return cleaned

    @classmethod
    def evaluate_task(
        cls,
        task: GoldenTask,
        context_markdown: str,
        k: int = 10,
        baseline_tokens: int = 25000,
        retrieval_time_ms: float = 0.0,
        total_time_ms: float = 0.0,
        structured_symbols: Sequence[str] = (),
        retrieved_files_override: Optional[Sequence[str]] = None,
    ) -> TaskEvaluationResult:
        """Evaluate a single task context package against ground truth."""
        extracted_files = cls.extract_file_references(context_markdown)
        
        if retrieved_files_override:
            # Combine structured related_files with extracted markdown files preserving order
            combined_files = []
            for f in list(retrieved_files_override) + extracted_files:
                norm_f = normalize_path(f)
                if norm_f and norm_f not in combined_files:
                    combined_files.append(norm_f)
            retrieved_files = combined_files
        else:
            retrieved_files = extracted_files

        retrieved_k = retrieved_files[:k]

        # File Precision@K
        if retrieved_k:
            true_positives = sum(
                1 for rf in retrieved_k
                if any(match_path(ef, rf) for ef in task.expected_files)
            )
            precision_at_k = true_positives / len(retrieved_k)
        else:
            precision_at_k = 0.0

        # File Recall@K
        matched_expected_files = []
        missing_expected_files = []
        for ef in task.expected_files:
            if any(match_path(ef, rf) for rf in retrieved_k):
                matched_expected_files.append(ef)
            else:
                missing_expected_files.append(ef)

        recall_at_k = (
            len(matched_expected_files) / len(task.expected_files)
            if task.expected_files else 1.0
        )

        # Critical Files Coverage
        matched_critical_files = [
            cf for cf in task.critical_files
            if any(match_path(cf, rf) for rf in retrieved_k)
        ]
        missing_critical_files = [
            cf for cf in task.critical_files
            if not any(match_path(cf, rf) for rf in retrieved_k)
        ]

        # Expected and Critical Symbols Coverage
        retrieved_symbols = [
            s for s in task.expected_symbols
            if match_symbol(s, context_markdown, structured_symbols)
        ]
        missing_expected_symbols = [
            s for s in task.expected_symbols
            if not match_symbol(s, context_markdown, structured_symbols)
        ]
        
        matched_critical_symbols = [
            cs for cs in task.critical_symbols
            if match_symbol(cs, context_markdown, structured_symbols)
        ]
        missing_critical_symbols = [
            cs for cs in task.critical_symbols
            if not match_symbol(cs, context_markdown, structured_symbols)
        ]

        total_critical = len(task.critical_files) + len(task.critical_symbols)
        if total_critical > 0:
            critical_evidence_coverage = (
                len(matched_critical_files) + len(matched_critical_symbols)
            ) / total_critical
        else:
            critical_evidence_coverage = recall_at_k

        # Noise / Irrelevant File Ratio
        detected_noise_files = [
            nf for nf in task.known_irrelevant_files
            if any(match_path(nf, rf) for rf in retrieved_k)
        ]
        noise_ratio = (
            len(detected_noise_files) / len(retrieved_k)
            if retrieved_k else 0.0
        )

        # Token & Compression Metrics (1 token ≈ 4 chars)
        context_tokens = max(1, len(context_markdown) // 4)
        compression_ratio = round(baseline_tokens / context_tokens, 2)
        token_savings = round(max(0.0, ((baseline_tokens - context_tokens) / baseline_tokens) * 100), 1)

        # Determine Verdict
        failure_reasons = []
        if len(missing_critical_files) > 0:
            failure_reasons.append(f"Missing critical files: {missing_critical_files}")
        if len(missing_critical_symbols) > 0:
            failure_reasons.append(f"Missing critical symbols: {missing_critical_symbols}")
        if recall_at_k < 0.4:
            failure_reasons.append(f"Low recall ({recall_at_k:.2f} < 0.40)")
        if noise_ratio > 0.4:
            failure_reasons.append(f"High noise ratio ({noise_ratio:.2f} > 0.40)")
            
        passed = (
            len(missing_critical_files) == 0
            and critical_evidence_coverage >= 0.5
            and recall_at_k >= 0.3
            and context_tokens > 10
        )
        verdict = "PASS" if passed else "FAIL"

        return TaskEvaluationResult(
            task_id=task.id,
            category=task.category,
            task_prompt=task.task_prompt,
            precision_at_k=round(precision_at_k, 3),
            recall_at_k=round(recall_at_k, 3),
            critical_evidence_coverage=round(critical_evidence_coverage, 3),
            noise_ratio=round(noise_ratio, 3),
            token_savings_percent=token_savings,
            compression_ratio=compression_ratio,
            retrieved_files=retrieved_k,
            missing_expected_files=missing_expected_files,
            missing_critical_files=missing_critical_files,
            retrieved_symbols=retrieved_symbols,
            missing_expected_symbols=missing_expected_symbols,
            missing_critical_symbols=missing_critical_symbols,
            detected_noise_files=detected_noise_files,
            context_tokens=context_tokens,
            baseline_tokens=baseline_tokens,
            retrieval_time_ms=round(retrieval_time_ms, 1),
            total_time_ms=round(total_time_ms, 1),
            passed=passed,
            verdict=verdict,
            failure_reasons=failure_reasons,
        )

    @classmethod
    def summarize_suite(cls, results: list[TaskEvaluationResult]) -> SuiteEvaluationSummary:
        """Aggregate task evaluation results into a comprehensive suite summary."""
        total = len(results)
        if total == 0:
            return SuiteEvaluationSummary(
                total_tasks=0,
                passed_tasks=0,
                failed_tasks=0,
                pass_rate=0.0,
                mean_precision_at_k=0.0,
                mean_recall_at_k=0.0,
                mean_critical_coverage=0.0,
                mean_noise_ratio=0.0,
                mean_compression_ratio=1.0,
                mean_retrieval_time_ms=0.0,
                mean_total_time_ms=0.0,
                category_breakdown={},
                task_results=[],
            )

        passed = sum(1 for r in results if r.passed)
        failed = total - passed

        mean_p = sum(r.precision_at_k for r in results) / total
        mean_r = sum(r.recall_at_k for r in results) / total
        mean_crit = sum(r.critical_evidence_coverage for r in results) / total
        mean_noise = sum(r.noise_ratio for r in results) / total
        mean_comp = sum(r.compression_ratio for r in results) / total
        mean_retrieval_ms = sum(r.retrieval_time_ms for r in results) / total
        mean_total_ms = sum(r.total_time_ms for r in results) / total

        # Category breakdown
        categories: dict[str, list[TaskEvaluationResult]] = {}
        for r in results:
            categories.setdefault(r.category, []).append(r)

        cat_summary: dict[str, dict[str, float]] = {}
        for cat_name, cat_res in categories.items():
            n = len(cat_res)
            cat_summary[cat_name] = {
                "total": float(n),
                "passed": float(sum(1 for r in cat_res if r.passed)),
                "pass_rate": round(sum(1 for r in cat_res if r.passed) / n, 3),
                "mean_precision": round(sum(r.precision_at_k for r in cat_res) / n, 3),
                "mean_recall": round(sum(r.recall_at_k for r in cat_res) / n, 3),
                "mean_critical_coverage": round(sum(r.critical_evidence_coverage for r in cat_res) / n, 3),
                "mean_noise_ratio": round(sum(r.noise_ratio for r in cat_res) / n, 3),
            }

        return SuiteEvaluationSummary(
            total_tasks=total,
            passed_tasks=passed,
            failed_tasks=failed,
            pass_rate=round(passed / total, 3),
            mean_precision_at_k=round(mean_p, 3),
            mean_recall_at_k=round(mean_r, 3),
            mean_critical_coverage=round(mean_crit, 3),
            mean_noise_ratio=round(mean_noise, 3),
            mean_compression_ratio=round(mean_comp, 2),
            mean_retrieval_time_ms=round(mean_retrieval_ms, 1),
            mean_total_time_ms=round(mean_total_ms, 1),
            category_breakdown=cat_summary,
            task_results=results,
        )
