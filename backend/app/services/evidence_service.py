"""Deterministic evidence evaluation, gating, and grounding sanitization."""

from pathlib import Path
import re
from typing import Any, Optional, Sequence

from app.application.domain.arbitration import ArbitratedEvidenceResult
from app.application.domain.evidence import EvidenceRecord, EvidenceState
from app.application.domain.intent import ParsedIntentRecord
from app.models.responses import RepositorySummary


FEATURE_KEYWORDS: dict[str, list[str]] = {
    "authentication": [
        "auth", "authenticate", "jwt", "token", "session", "login", "logout",
        "password", "user_auth", "permission", "oauth", "bearer", "credential",
    ],
    "database_models": [
        "model", "schema", "database", "orm", "table", "migration", "entity",
        "record", "queryset",
    ],
    "api_endpoints": [
        "api", "endpoint", "route", "router", "view", "controller", "handler",
        "urlpatterns", "url", "dispatch",
    ],
    "websocket_realtime": [
        "websocket", "socket", "channel", "sse", "realtime", "broadcast",
    ],
    "background_tasks": [
        "celery", "worker", "queue", "cron", "background", "job", "scheduler",
    ],
    "payment_billing": [
        "stripe", "payment", "invoice", "subscription", "checkout", "billing",
    ],
}


class EvidenceService:
    """Evaluates repository evidence sufficiency, gates model invocation, and validates grounding."""

    @staticmethod
    def extract_requested_features(prompt: str) -> list[str]:
        """Extract requested subsystem features from the prompt."""
        prompt_lower = prompt.lower()
        requested: list[str] = []
        for feat_name, keywords in FEATURE_KEYWORDS.items():
            if any(re.search(r"\b" + re.escape(kw) + r"\b", prompt_lower) for kw in keywords):
                requested.append(feat_name)
        return requested

    @staticmethod
    def validate_memory_evidence(
        memories: Sequence[Any],
        manifest: Optional[Any],
    ) -> list[Any]:
        """Filter memory results against active repository manifest.

        Discards or marks stale any memory record that cannot be proven to exist
        in the active repository files or symbols.
        """
        if not manifest or not hasattr(manifest, "files") or not manifest.files:
            return []

        valid_memories: list[Any] = []
        for mem in memories:
            prov = getattr(mem, "provenance", None) or (mem.get("provenance") if isinstance(mem, dict) else None)
            if prov and hasattr(prov, "is_valid_for_manifest"):
                if prov.is_valid_for_manifest(manifest):
                    valid_memories.append(mem)
                continue
            elif isinstance(prov, dict):
                from app.application.domain.memory import MemoryProvenance
                p_obj = MemoryProvenance.from_dict(prov)
                if p_obj.is_valid_for_manifest(manifest):
                    valid_memories.append(mem)
                continue

            src_file = getattr(mem, "source_file", None) or getattr(mem, "file_path", None) or getattr(mem, "path", None)
            if not src_file and isinstance(mem, dict):
                src_file = mem.get("source_file") or mem.get("file_path") or mem.get("path")

            if src_file:
                clean_path = str(src_file).replace("\\", "/").lstrip("./")
                if clean_path in manifest.files:
                    valid_memories.append(mem)

        return valid_memories

    @classmethod
    def assess_evidence(
        cls,
        task_prompt: str,
        intent: ParsedIntentRecord,
        repo_summary: Optional[RepositorySummary],
        indexed_files: Sequence[Path | str],
        relevant_snippets: Sequence[str] = (),
        matched_file_rels: Sequence[str] = (),
        structural_symbols: Sequence[str] = (),
        structural_relationships: Sequence[str] = (),
        derived_memories: Sequence[Any] = (),
        manifest: Optional[Any] = None,
        arbitrated_result: Optional[ArbitratedEvidenceResult] = None,
    ) -> EvidenceRecord:
        """Evaluate evidence sufficiency against task requirements."""
        if not indexed_files:
            return EvidenceRecord(
                evidence_state=EvidenceState.INDEX_UNAVAILABLE.value,
                evidence_score=0.0,
                evidence_confidence=0.0,
                abstained=True,
                abstention_reason="Repository is not indexed or contains no readable source files.",
                suggested_next_action="Index the repository before requesting context generation.",
                model_claims_allowed=False,
            )

        # Merge from arbitrated result if provided
        effective_snippets = list(relevant_snippets)
        effective_files = list(matched_file_rels)
        effective_symbols = list(structural_symbols)
        effective_relationships = list(structural_relationships)

        if arbitrated_result:
            if arbitrated_result.authoritative_snippets and not effective_snippets:
                effective_snippets = list(arbitrated_result.authoritative_snippets)
            if arbitrated_result.authoritative_files and not effective_files:
                effective_files = list(arbitrated_result.authoritative_files)
            if arbitrated_result.authoritative_symbols and not effective_symbols:
                effective_symbols = list(arbitrated_result.authoritative_symbols)
            if arbitrated_result.authoritative_relationships and not effective_relationships:
                effective_relationships = list(arbitrated_result.authoritative_relationships)

        # Normalize paths for matching
        file_strings = [str(f) for f in indexed_files]
        file_strings_lower = [f.lower() for f in file_strings]

        # Gather repository symbols and framework tags
        verified_repo_symbols: set[str] = set()
        frameworks_detected: list[str] = []
        if repo_summary:
            if hasattr(repo_summary, "key_components") and repo_summary.key_components:
                for comp in repo_summary.key_components:
                    comp_name = getattr(comp, "name", str(comp))
                    verified_repo_symbols.add(comp_name)
            if hasattr(repo_summary, "technology_stack") and repo_summary.technology_stack:
                if hasattr(repo_summary.technology_stack, "frameworks"):
                    frameworks_detected = list(repo_summary.technology_stack.frameworks)
            elif hasattr(repo_summary, "frameworks") and repo_summary.frameworks:
                frameworks_detected = list(repo_summary.frameworks)

        all_known_symbols = verified_repo_symbols | set(effective_symbols)
        all_known_symbols_lower = {s.lower() for s in all_known_symbols}

        # Check requested feature keywords against symbols, files, and snippets
        requested_features = cls.extract_requested_features(task_prompt)
        missing_features: list[str] = []
        observed_evidence: list[str] = []

        if frameworks_detected:
            observed_evidence.append(f"Framework detected: {', '.join(frameworks_detected)} (architectural structure).")
        observed_evidence.append(f"Indexed repository files: {len(indexed_files)} files analyzed.")

        for feat in requested_features:
            keywords = FEATURE_KEYWORDS[feat]
            symbol_has_feat = any(any(kw in sym for kw in keywords) for sym in all_known_symbols_lower)
            file_has_feat = any(any(kw in f for kw in keywords) for f in file_strings_lower)
            snippet_has_feat = any(any(kw in snip.lower() for kw in keywords) for snip in effective_snippets)

            if not (symbol_has_feat or file_has_feat or snippet_has_feat):
                readable_name = feat.replace("_", " ")
                missing_features.append(f"{readable_name} (no existing symbols, middleware, models, or endpoints found)")
            else:
                observed_evidence.append(f"Repository contains references matching {feat.replace('_', ' ')}.")

        # Match intent symbols and hints against discovered files and symbols
        matching_symbols = [s for s in intent.extracted_symbols if s.lower() in all_known_symbols_lower or s in all_known_symbols]
        matching_files = [f for f in effective_files if any(f.lower().endswith(h.lower()) or h.lower() in f.lower() for h in intent.relevant_file_hints) or f in intent.relevant_file_hints] if intent.relevant_file_hints else list(effective_files)

        # Weighted evidence scores
        symbol_score = min(1.0, len(matching_symbols) * 0.35 + (0.2 if effective_symbols else 0.0))
        snippet_score = min(1.0, len(effective_snippets) * 0.25)
        file_score = min(1.0, len(matching_files) * 0.25)
        rel_score = min(1.0, len(effective_relationships) * 0.20)
        framework_score = 0.05 if frameworks_detected else 0.0

        raw_score = (
            0.35 * symbol_score
            + 0.30 * snippet_score
            + 0.20 * file_score
            + 0.10 * rel_score
            + 0.05 * framework_score
        )
        evidence_score = round(min(1.0, max(0.0, raw_score)), 3)
        confidence = round(min(1.0, (len(effective_snippets) > 0) * 0.5 + (len(matching_symbols) > 0) * 0.5), 2)

        # Invariant: Filesystem path existence alone without content or symbol evidence is not sufficient
        if not effective_snippets and not matching_symbols:
            return EvidenceRecord(
                evidence_state=EvidenceState.NONE.value if evidence_score <= 0.05 else EvidenceState.INSUFFICIENT.value,
                evidence_score=min(0.15, evidence_score),
                evidence_confidence=0.0,
                evidence_files=list(dict.fromkeys(effective_files[:2])),
                evidence_symbols=list(matching_symbols),
                evidence_relationships=list(effective_relationships[:2]),
                observed_evidence=observed_evidence,
                missing_evidence=missing_features or ["Concrete code implementations or symbol definitions matching the task"],
                abstained=True,
                abstention_reason="Filesystem path references without matched code content or symbol definitions do not constitute sufficient repository evidence.",
                suggested_next_action="Specify existing symbol names or implement the requested logic as a new component.",
                model_claims_allowed=False,
            )

        # Abstain if all requested features lack repository evidence
        if requested_features and len(missing_features) == len(requested_features) and not matching_symbols and not effective_snippets:
            return EvidenceRecord(
                evidence_state=EvidenceState.NONE.value if evidence_score <= 0.05 else EvidenceState.INSUFFICIENT.value,
                evidence_score=evidence_score,
                evidence_confidence=0.0,
                evidence_files=list(dict.fromkeys(effective_files[:4])),
                evidence_symbols=list(matching_symbols),
                evidence_relationships=list(effective_relationships[:6]),
                observed_evidence=observed_evidence,
                missing_evidence=missing_features,
                abstained=True,
                abstention_reason=f"No repository evidence was found for: {', '.join(missing_features)}.",
                suggested_next_action=f"Treat {missing_features[0].split(' (')[0]} as a new subsystem to build from scratch rather than modifying an existing implementation.",
                model_claims_allowed=False,
            )

        # Sufficient evidence threshold
        if evidence_score >= 0.45 and (effective_snippets or matching_symbols):
            return EvidenceRecord(
                evidence_state=EvidenceState.SUFFICIENT.value,
                evidence_score=evidence_score,
                evidence_confidence=confidence,
                evidence_files=list(dict.fromkeys(effective_files)),
                evidence_symbols=list(matching_symbols or effective_symbols[:6]),
                evidence_relationships=list(effective_relationships),
                observed_evidence=observed_evidence,
                missing_evidence=missing_features,
                abstained=False,
                abstention_reason=None,
                suggested_next_action=None,
                model_claims_allowed=True,
            )
        elif (evidence_score >= 0.18 and (effective_snippets or matching_symbols)):
            return EvidenceRecord(
                evidence_state=EvidenceState.PARTIAL.value,
                evidence_score=evidence_score,
                evidence_confidence=confidence,
                evidence_files=list(dict.fromkeys(effective_files)),
                evidence_symbols=list(matching_symbols or effective_symbols[:4]),
                evidence_relationships=list(effective_relationships[:4]),
                observed_evidence=observed_evidence,
                missing_evidence=missing_features,
                abstained=False,
                abstention_reason=None,
                suggested_next_action="Synthesize bounded context highlighting missing dependencies.",
                model_claims_allowed=True,
            )
        else:
            return EvidenceRecord(
                evidence_state=EvidenceState.INSUFFICIENT.value if evidence_score > 0.0 else EvidenceState.NONE.value,
                evidence_score=evidence_score,
                evidence_confidence=0.0,
                evidence_files=list(dict.fromkeys(effective_files[:2])),
                evidence_symbols=list(matching_symbols),
                evidence_relationships=list(effective_relationships[:2]),
                observed_evidence=observed_evidence,
                missing_evidence=missing_features or ["Relevant codebase symbols or file implementations matching the task"],
                abstained=True,
                abstention_reason="Insufficient repository evidence to support grounded context generation.",
                suggested_next_action="Specify exact symbols or target files in your prompt, or implement the requested feature as a new component.",
                model_claims_allowed=False,
            )

    @staticmethod
    def build_abstention_package(
        task_prompt: str,
        intent: ParsedIntentRecord,
        evidence: EvidenceRecord,
    ) -> str:
        """Render markdown abstention package with evidence breakdowns."""
        md_lines = [
            "# Task Intent",
            f"**Requested Objective**: {intent.task_summary or task_prompt}",
            f"**Intent Category**: `{intent.category}`",
            "",
            "---",
            "",
            "# Observed Repository Evidence",
        ]
        if evidence.observed_evidence:
            for obs in evidence.observed_evidence:
                md_lines.append(f"- {obs}")
        else:
            md_lines.append("- Repository scanned; no matching symbols or implementations found.")

        md_lines.extend([
            "",
            "---",
            "",
            "# Missing Evidence",
        ])
        if evidence.missing_evidence:
            for miss in evidence.missing_evidence:
                md_lines.append(f"- **Absent**: {miss}")
        else:
            md_lines.append("- No matching implementation code found in indexed repository.")

        md_lines.extend([
            "",
            "---",
            "",
            "# Insufficient Repository Evidence Notice",
            f"> **Status**: `ABSTAINED` ({evidence.evidence_state})",
            f"> **Reason**: {evidence.abstention_reason or 'No authoritative repository evidence found for the requested task.'}",
            "",
            f"**Suggested Next Action**: {evidence.suggested_next_action or 'Treat this as a new feature to be created from scratch.'}",
        ])
        return "\n".join(md_lines)

    @staticmethod
    def sanitize_and_validate_grounded_response(
        raw_markdown: str,
        evidence: EvidenceRecord,
        indexed_files: Sequence[str | Path],
    ) -> str:
        """Strip reasoning tags and validate response format."""
        # Strip reasoning blocks before storage/presentation
        cleaned = re.sub(r"<think>.*?</think>", "", raw_markdown, flags=re.DOTALL).strip()
        cleaned = re.sub(r"\[THINKING\].*?\[/THINKING\]", "", cleaned, flags=re.DOTALL).strip()

        if not cleaned or len(cleaned.strip()) < 10:
            return raw_markdown

        return cleaned
