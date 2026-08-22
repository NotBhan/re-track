"""Source file searching and focused code snippet extraction service for RE:Track."""

import logging
from pathlib import Path
import re
from typing import Optional, Sequence

from app.application.ports.filesystem import FileSystemPort
from app.application.ports.source_search import SourceSearchPort
from app.services.local_filesystem import LocalFileSystemAdapter

logger = logging.getLogger(__name__)

STOP_WORDS = frozenset({
    "where", "what", "find", "how", "with", "from", "this", "that",
    "the", "and", "for", "are", "can", "you", "does", "show", "tell",
    "when", "into", "been", "have", "each", "were", "which", "their",
    "will", "about", "there", "then", "them", "some", "such", "than",
})


class SourceSearchService(SourceSearchPort):
    """Encapsulates filesystem source scanning, term matching, and snippet extraction."""

    def __init__(self, filesystem: Optional[FileSystemPort] = None) -> None:
        self._fs = filesystem or LocalFileSystemAdapter()

    def build_search_terms(
        self,
        task_prompt: str,
        extracted_symbols: Sequence[str] = (),
        relevant_file_hints: Sequence[str] = (),
    ) -> list[str]:
        """Generate deduplicated, prioritized search terms from prompt, symbols, and hints."""
        clean_hints = [h.strip() for h in relevant_file_hints if h.strip()]
        clean_symbols = [s.strip() for s in extracted_symbols if s.strip()]

        # Sub-token expansion from camelCase / snake_case symbols
        sub_tokens: list[str] = []
        for sym in clean_symbols:
            parts = [p for p in re.split(r"[_./\\]|(?<=[a-z])(?=[A-Z])", sym) if len(p) > 2]
            for p in parts:
                p_low = p.lower()
                if p_low not in STOP_WORDS and p not in clean_symbols and p not in sub_tokens:
                    sub_tokens.append(p)

        # Clean prompt words (strip punctuation, stop words, and numbers)
        prompt_words: list[str] = []
        for raw_w in task_prompt.split():
            clean_w = re.sub(r"^[^\w]+|[^\w]+$", "", raw_w)
            if len(clean_w) > 2 and clean_w.lower() not in STOP_WORDS and clean_w not in clean_symbols and clean_w not in prompt_words:
                prompt_words.append(clean_w)

        # Root/stem variants (e.g. budgeting -> budget, routers -> router, dtos -> dto)
        root_variants: list[str] = []
        for w in clean_symbols + prompt_words:
            w_low = w.lower()
            roots = []
            if w_low.endswith("ing") and len(w_low) > 5:
                roots.append(w_low[:-3])
                roots.append(w_low[:-3] + "e")
            elif w_low.endswith("tion") and len(w_low) > 6:
                roots.append(w_low[:-4])
                roots.append(w_low[:-4] + "te")
            elif w_low.endswith("ies") and len(w_low) > 5:
                roots.append(w_low[:-3] + "y")
            elif w_low.endswith("es") and len(w_low) > 4:
                roots.append(w_low[:-2])
            elif w_low.endswith("s") and not w_low.endswith("ss") and len(w_low) > 3:
                roots.append(w_low[:-1])
            elif w_low.endswith("ed") and len(w_low) > 4:
                roots.append(w_low[:-2])
                roots.append(w_low[:-1])

            for r in roots:
                if len(r) > 2 and r not in STOP_WORDS and r not in root_variants and r not in prompt_words:
                    root_variants.append(r)

        # High-specificity terms first: file hints -> extracted symbols -> symbol parts -> root variants -> prompt words
        all_terms = clean_hints + clean_symbols + sub_tokens + root_variants + prompt_words
        return list(dict.fromkeys(all_terms))[:35]

    def extract_relevant_snippets(
        self,
        repo_path: Path,
        indexed_files: Sequence[Path],
        search_terms: Sequence[str],
        max_files: int = 8,
        max_snippets: int = 5,
        max_file_size: int = 256_000,
    ) -> tuple[list[str], list[str]]:
        """Search repository files using staged relevance scoring and extract focused snippets.

        Stage 1: Fast in-memory metadata & path matching (0 disk I/O) across all files.
        Stage 2: Targeted deep content inspection on top candidate files.
        Stage 3: Dynamic confidence cutoff and precision trimming.
        Stage 4: Focused snippet formatting.
        """
        if not search_terms or not indexed_files:
            return [], []

        file_hints_set = {t.lower().lstrip("./") for t in search_terms if "." in t}
        exact_symbols_set = {t.lower() for t in search_terms if "." not in t and len(t) > 2}
        distinct_terms = list(dict.fromkeys([t.lower() for t in search_terms if len(t) > 2]))
        source_exts = {".py", ".ts", ".tsx", ".js", ".jsx", ".rs", ".go", ".java", ".c", ".cpp"}

        # --- STAGE 1: In-Memory Metadata & Path Relevance (Zero Disk I/O) ---
        stage1_scored: list[tuple[float, str, Path]] = []

        for fpath in indexed_files:
            try:
                rel = str(fpath.relative_to(repo_path) if fpath.is_relative_to(repo_path) else fpath).lstrip("./")
                rel_lower = rel.lower()
                stem_lower = fpath.stem.lower()
                name_lower = fpath.name.lower()
                ext = fpath.suffix.lower()

                s1_score = 0.0
                is_source = ext in source_exts
                is_doc_or_bench = rel_lower.startswith("benchmarks/") or rel_lower.startswith("docs/")

                # 1. Exact or suffix match with explicit file hint (+35 pts)
                for hint in file_hints_set:
                    if rel_lower == hint or rel_lower.endswith("/" + hint) or name_lower == hint:
                        s1_score += 35.0

                # 2. Filename or Stem exact match with symbol (+25 pts)
                for sym in exact_symbols_set:
                    if sym == stem_lower or sym == name_lower:
                        s1_score += 25.0
                    elif sym in stem_lower:
                        s1_score += 15.0
                    elif sym in rel_lower:
                        s1_score += 8.0

                # 3. Path components match distinct terms (+8 pts per distinct term)
                terms_in_path = 0
                for term in distinct_terms:
                    if term in rel_lower:
                        terms_in_path += 1
                        s1_score += 8.0

                if terms_in_path >= 2:
                    s1_score += terms_in_path * 6.0

                # Source code files get natural priority for implementation context
                if is_source and s1_score > 0:
                    s1_score += 6.0
                elif is_doc_or_bench and s1_score > 0:
                    s1_score *= 0.7

                if s1_score > 0.0:
                    stage1_scored.append((s1_score, rel, fpath))

            except Exception:
                continue

        stage1_scored.sort(key=lambda item: (item[0], len(item[1].split("/"))), reverse=True)
        # Select top 25 candidate files for deep inspection
        candidates_to_inspect = stage1_scored[:25]

        # --- STAGE 2: Targeted Content Inspection (Only on Top 25 candidates) ---
        stage2_scored: list[tuple[float, str, Path]] = []
        for s1_score, rel, fpath in candidates_to_inspect:
            score = s1_score
            try:
                if self._fs.get_file_size(fpath) < max_file_size:
                    content = self._fs.read_text(fpath, errors="replace")
                    content_lower = content.lower()

                    for sym in exact_symbols_set:
                        if sym in content_lower:
                            # Definitions (class, def, function, interface) boost
                            if re.search(rf"\b(class|def|interface|function|const|let)\s+{re.escape(sym)}\b", content, re.IGNORECASE):
                                score += 18.0
                            else:
                                occurrences = len(re.findall(rf"\b{re.escape(sym)}\b", content_lower))
                                score += min(12.0, occurrences * 3.0)

                    for term in distinct_terms:
                        if term in content_lower:
                            occurrences = len(re.findall(rf"\b{re.escape(term)}\b", content_lower))
                            score += min(4.0, occurrences * 1.0)
            except Exception as ce:
                logger.debug("SourceSearch content read error in %s: %s", rel, ce)

            stage2_scored.append((score, rel, fpath))

        stage2_scored.sort(key=lambda item: (item[0], len(item[1].split("/"))), reverse=True)

        # --- STAGE 3: Dynamic Confidence Cutoff & Precision Trimming ---
        if stage2_scored:
            max_score = stage2_scored[0][0]
            score_cutoff = max(10.0, max_score * 0.30)
            confident_candidates = [c for c in stage2_scored if c[0] >= score_cutoff][:max_files]
        else:
            confident_candidates = []

        # --- STAGE 4: Snippet Extraction for Top Confident Candidates ---
        relevant_snippets: list[str] = []
        for score, rel_path, full_path in confident_candidates[:max_snippets]:
            try:
                text = self._fs.read_text(full_path, errors="replace")
                lines = text.splitlines()
                matching_indices = [
                    i for i, line in enumerate(lines)
                    if any(t.lower() in line.lower() for t in search_terms if len(t) > 2)
                ]
                if matching_indices:
                    first_idx = max(0, matching_indices[0] - 4)
                    last_idx = min(len(lines), matching_indices[0] + 25)
                    snippet = "\n".join(lines[first_idx:last_idx])
                    relevant_snippets.append(
                        f"### `{rel_path}` (Lines {first_idx+1}-{last_idx})\n```\n{snippet}\n```"
                    )
            except Exception as e:
                logger.debug("SourceSearch snippet error in %s: %s", rel_path, e)

        matched_rel_paths = [rel for _, rel, _ in confident_candidates]
        return relevant_snippets, matched_rel_paths

    def search(
        self,
        repo_path: Path,
        indexed_files: Sequence[Path],
        query: str,
        limit: int = 10,
    ) -> list[dict]:
        """Search repository code for query terms and return ranked candidates with matched symbols and snippets."""
        if not query.strip() or not indexed_files:
            return []

        search_terms = self.build_search_terms(task_prompt=query)
        exact_symbols_set = {t.lower() for t in search_terms if "." not in t and len(t) > 2}
        distinct_terms = list(dict.fromkeys([t.lower() for t in search_terms if len(t) > 2]))
        source_exts = {".py", ".ts", ".tsx", ".js", ".jsx", ".rs", ".go", ".java", ".c", ".cpp"}

        scored_candidates: list[dict] = []
        repo_canon = repo_path.resolve()

        for fpath in indexed_files:
            try:
                f_canon = fpath.resolve()
                if not f_canon.is_relative_to(repo_canon):
                    continue  # Symlink leaves repository root boundary
                if not f_canon.exists() or not f_canon.is_file():
                    continue  # Broken symlink or non-file

                rel = str(fpath.relative_to(repo_path) if fpath.is_relative_to(repo_path) else fpath).lstrip("./")
                rel_lower = rel.lower()
                stem_lower = fpath.stem.lower()
                name_lower = fpath.name.lower()
                ext = fpath.suffix.lower()

                score = 0.0
                matched_symbols: list[str] = []

                for sym in exact_symbols_set:
                    if sym == stem_lower or sym == name_lower:
                        score += 30.0
                        matched_symbols.append(sym)
                    elif sym in stem_lower:
                        score += 15.0
                        matched_symbols.append(sym)
                    elif sym in rel_lower:
                        score += 10.0
                        matched_symbols.append(sym)

                for term in distinct_terms:
                    if term in rel_lower:
                        score += 8.0

                snippet = ""
                if self._fs.exists(fpath) and self._fs.get_file_size(fpath) < 256_000:
                    content = self._fs.read_text(fpath, errors="replace")
                    content_lower = content.lower()

                    for sym in exact_symbols_set:
                        if sym in content_lower:
                            if sym not in matched_symbols:
                                matched_symbols.append(sym)
                            if re.search(rf"\b(class|def|interface|function|const|let)\s+{re.escape(sym)}\b", content, re.IGNORECASE):
                                score += 20.0
                            else:
                                score += min(15.0, len(re.findall(rf"\b{re.escape(sym)}\b", content_lower)) * 3.0)

                    for term in distinct_terms:
                        if term in content_lower:
                            score += min(5.0, len(re.findall(rf"\b{re.escape(term)}\b", content_lower)) * 1.0)

                    if score > 0.0:
                        lines = content.splitlines()
                        matching_indices = [
                            i for i, line in enumerate(lines)
                            if any(t in line.lower() for t in distinct_terms)
                        ]
                        if matching_indices:
                            first_idx = max(0, matching_indices[0] - 2)
                            last_idx = min(len(lines), matching_indices[0] + 15)
                            snippet = "\n".join(lines[first_idx:last_idx])

                if ext in source_exts and score > 0:
                    score += 5.0

                if score > 0.0:
                    scored_candidates.append({
                        "file_path": rel,
                        "score": round(score, 2),
                        "matched_symbols": list(dict.fromkeys(matched_symbols)),
                        "snippet": snippet,
                    })
            except Exception:
                continue

        scored_candidates.sort(key=lambda item: item["score"], reverse=True)
        return scored_candidates[:limit]
