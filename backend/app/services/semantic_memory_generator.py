"""Semantic memory generation and cognification service for RE:Track.

Turns verified repository evidence and deterministic AST models into
structured, persistent semantic memory records using a configured LLM.

Invariants:
- The LLM is a memory compression / semantic organization component, NOT a repository-truth authority.
- The input to memory generation must come exclusively from verified repository evidence (Manifest 2.0, AST, source snippets).
- Hallucinated files, symbols, or unverified features are strictly rejected.
- Output passes through CogneeSemanticMemoryAdapter as the final provenance validation boundary before persistence.
- Persisted records are strictly derived (Tier 4) and never become authoritative evidence.
"""

import hashlib
import json
import logging
import re
import time
from typing import Any, Optional

from app.application.domain.memory import (
    SemanticMemoryGenerationInput,
    SemanticMemoryGenerationResult,
    SemanticMemoryGenerationTelemetry,
    SemanticMemoryRecord,
)
from app.application.ports.llm_provider import LLMProviderPort
from app.application.ports.memory import (
    SemanticMemoryGeneratorPort,
    SemanticMemoryRepositoryPort,
)
from app.config.settings import Settings, get_settings
from app.services.cognee_service import CogneeSemanticMemoryAdapter

logger = logging.getLogger(__name__)

SEMANTIC_MEMORY_SYSTEM_PROMPT = """You are a precise semantic memory compression engine for RE:Track.
Your role is to compress VERIFIED REPOSITORY EVIDENCE into structured semantic memory records for persistent retrieval.

CRITICAL RULES AND CONSTRAINTS:
1. ONLY summarize supplied repository evidence.
2. PRESERVE exact source file paths and exact symbol names.
3. Explicitly omit anything unsupported. Never extrapolate or assume optional features exist.
4. Framework presence (e.g. FastAPI, React, Flask) NEVER implies that optional features (e.g. auth, WebSockets, routes) exist unless explicitly present in the evidence.
5. NEVER invent missing architecture, APIs, endpoints, classes, methods, or files.
6. NEVER generate speculative plans or future work.
7. NEVER include reasoning, thinking traces, or <think>...</think> tags.
8. Output MUST be strictly valid JSON matching the following schema:

{
  "memories": [
    {
      "semantic_text": "<concise description of component/behavior grounded strictly in evidence>",
      "source_files": ["<exact_path_from_evidence>"],
      "source_symbols": ["<exact_symbol_from_evidence>"],
      "relationship_kind": "behavior_summary"
    }
  ]
}
"""


def build_generation_prompt(
    generation_input: SemanticMemoryGenerationInput,
) -> str:
    """Build a strongly constrained user prompt containing only verified repository evidence."""
    parts = ["--- VERIFIED REPOSITORY EVIDENCE ---"]
    parts.append(f"Repository ID: {generation_input.repository_id}")
    parts.append(f"Repository Fingerprint: {generation_input.repository_fingerprint}")

    if generation_input.frameworks:
        parts.append(f"Detected Frameworks: {', '.join(generation_input.frameworks)}")

    parts.append("\nFiles and AST Symbols:")
    for f in generation_input.source_files:
        syms = generation_input.ast_symbols.get(f, [])
        sym_str = f" (symbols: {', '.join(syms)})" if syms else " (no symbols recorded)"
        parts.append(f"- {f}{sym_str}")

    if generation_input.source_snippets:
        parts.append("\nSource Snippets:")
        for f, snippet in generation_input.source_snippets.items():
            parts.append(f"--- File: {f} ---\n{snippet}\n")

    if generation_input.relationships:
        parts.append("\nVerified Relationships:")
        for rel in generation_input.relationships[:30]:
            parts.append(f"- {rel}")

    if generation_input.task_intent:
        parts.append("\n--- TASK / QUERY INTENT (FOR FOCUS ONLY, NOT EVIDENCE) ---")
        parts.append(f"Focus Intent: {generation_input.task_intent}")
        parts.append(
            "Note: The focus intent is query context only. Never treat intent description as repository facts or evidence."
        )

    parts.append("\nGenerate structured semantic memory records in JSON format adhering strictly to the system instructions.")
    return "\n".join(parts)


def extract_memories_from_response(raw_response: str) -> list[dict[str, Any]]:
    """Clean model response, strip <think> blocks, and parse structured memories JSON."""
    if not raw_response or not raw_response.strip():
        return []

    # Strip reasoning think blocks
    cleaned = re.sub(r"<think>.*?</think>", "", raw_response, flags=re.DOTALL).strip()

    # Try finding JSON code block
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
    if match:
        json_str = match.group(1).strip()
    else:
        # Fallback to brace extraction
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx >= start_idx:
            json_str = cleaned[start_idx : end_idx + 1]
        else:
            # Check for array
            start_arr = cleaned.find("[")
            end_arr = cleaned.rfind("]")
            if start_arr != -1 and end_arr != -1 and end_arr >= start_arr:
                json_str = cleaned[start_arr : end_arr + 1]
            else:
                return []

    try:
        data = json.loads(json_str)
    except Exception:
        return []

    if isinstance(data, dict):
        raw_items = data.get("memories", [])
        if isinstance(raw_items, list):
            return [it for it in raw_items if isinstance(it, dict)]
        return []
    elif isinstance(data, list):
        return [it for it in data if isinstance(it, dict)]
    return []


class SemanticMemoryGenerator:
    """Service that orchestrates the generation, validation, and persistence of semantic memory records."""

    def __init__(
        self,
        llm_provider: Optional[LLMProviderPort] = None,
        repository: Optional[SemanticMemoryRepositoryPort] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self.llm_provider = llm_provider
        self.repository = repository
        self.settings = settings or get_settings()

    def _select_model(
        self,
        model_config: Optional[dict[str, Any]] = None,
    ) -> tuple[Optional[str], bool, Optional[str]]:
        """Select the target model following strict priority:
        1. Explicitly configured dedicated memory model.
        2. Currently configured inference model (as documented fallback).
        If none configured, returns (None, False, None).
        """
        cfg = model_config or {}

        # 1. Check dedicated memory model
        dedicated = (
            cfg.get("memory_model")
            or getattr(self.settings, "memory_model", None)
            or getattr(getattr(self.settings, "ollama", None), "memory_model", None)
        )
        if dedicated and str(dedicated).strip():
            return str(dedicated).strip(), False, None

        # 2. Check active inference model
        inference = (
            cfg.get("model")
            or getattr(self.llm_provider, "default_model", None)
            or getattr(getattr(self.settings, "ollama", None), "llm_model", None)
        )
        if inference and str(inference).strip():
            return (
                str(inference).strip(),
                True,
                "No dedicated memory model configured; falling back to active inference model",
            )

        return None, False, None

    async def generate_semantic_memory(
        self,
        repository_id: str,
        manifest: Any,
        file_filter: Optional[list[str]] = None,
        source_snippets: Optional[dict[str, str]] = None,
        task_intent: Optional[str] = None,
        frameworks: Optional[list[str]] = None,
        model_config: Optional[dict[str, Any]] = None,
        persist: bool = True,
    ) -> SemanticMemoryGenerationResult:
        """Generate, validate, and persist semantic memory from verified repository evidence."""
        # 1. Abstention check: Verify manifest and repository evidence exist
        if not manifest or not hasattr(manifest, "files") or not manifest.files:
            return SemanticMemoryGenerationResult(
                success=False,
                status="insufficient_evidence",
                records=[],
                telemetry=SemanticMemoryGenerationTelemetry(
                    model_invoked=False,
                    inference_status="insufficient_evidence",
                    rejection_reasons=["missing_or_empty_manifest"],
                ),
                message="Repository manifest is missing or contains no indexed files.",
            )

        # 2. Extract generation input from manifest
        gen_input = SemanticMemoryGenerationInput.from_manifest(
            manifest=manifest,
            file_filter=file_filter,
            source_snippets=source_snippets,
            task_intent=task_intent,
            frameworks=frameworks,
        )
        if repository_id:
            gen_input.repository_id = repository_id

        if not gen_input.source_files:
            return SemanticMemoryGenerationResult(
                success=False,
                status="insufficient_evidence",
                records=[],
                telemetry=SemanticMemoryGenerationTelemetry(
                    model_invoked=False,
                    inference_status="insufficient_evidence",
                    rejection_reasons=["no_matching_source_files"],
                ),
                message="No matching source files available for memory generation.",
            )

        # 3. Model selection
        target_model, fallback_used, fallback_reason = self._select_model(model_config)
        if not target_model or self.llm_provider is None:
            return SemanticMemoryGenerationResult(
                success=False,
                status="not_configured",
                records=[],
                telemetry=SemanticMemoryGenerationTelemetry(
                    model_invoked=False,
                    inference_status="not_configured",
                    rejection_reasons=["no_model_configured"],
                ),
                message="No memory model or LLM inference provider configured for semantic memory generation.",
            )

        # 4. Build prompts
        user_prompt = build_generation_prompt(gen_input)
        system_prompt = SEMANTIC_MEMORY_SYSTEM_PROMPT

        # 5. Model invocation with latency and error tracking
        provider_type = getattr(self.llm_provider, "provider_type", "llm_provider")
        provider_identity = (
            provider_type.value if hasattr(provider_type, "value") else str(provider_type)
        )

        t0 = time.perf_counter()
        try:
            raw_response = await self.llm_provider.generate_completion(
                prompt=user_prompt,
                system_prompt=system_prompt,
                model=target_model,
                temperature=0.1,
                max_tokens=1024,
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
        except (ConnectionError, TimeoutError, OSError) as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            logger.warning("Semantic memory LLM provider unreachable: %s", e)
            return SemanticMemoryGenerationResult(
                success=False,
                status="provider_unavailable",
                records=[],
                telemetry=SemanticMemoryGenerationTelemetry(
                    model_invoked=True,
                    provider_identity=provider_identity,
                    model_name=target_model,
                    inference_status="provider_unavailable",
                    inference_time_ms=elapsed_ms,
                    fallback_used=fallback_used,
                    fallback_reason=fallback_reason,
                    rejection_reasons=[f"provider_error:{type(e).__name__}"],
                ),
                message=f"LLM provider unavailable: {e}",
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            logger.error("Semantic memory LLM generation error: %s", e)
            return SemanticMemoryGenerationResult(
                success=False,
                status="generation_failed",
                records=[],
                telemetry=SemanticMemoryGenerationTelemetry(
                    model_invoked=True,
                    provider_identity=provider_identity,
                    model_name=target_model,
                    inference_status="generation_failed",
                    inference_time_ms=elapsed_ms,
                    fallback_used=fallback_used,
                    fallback_reason=fallback_reason,
                    rejection_reasons=[f"generation_exception:{type(e).__name__}"],
                ),
                message=f"Memory generation failed: {e}",
            )

        # 6. Parse structured memories from LLM response
        raw_items = extract_memories_from_response(raw_response)
        candidate_count = len(raw_items)

        if candidate_count == 0:
            return SemanticMemoryGenerationResult(
                success=False,
                status="no_valid_memories",
                records=[],
                telemetry=SemanticMemoryGenerationTelemetry(
                    model_invoked=True,
                    provider_identity=provider_identity,
                    model_name=target_model,
                    inference_status="no_valid_memories",
                    inference_time_ms=elapsed_ms,
                    fallback_used=fallback_used,
                    fallback_reason=fallback_reason,
                    candidate_count=0,
                    rejection_reasons=["empty_or_malformed_llm_json"],
                ),
                message="Model returned no valid structured memory items.",
            )

        # 7. Validate each candidate against authoritative Manifest & AST
        validated_records: list[SemanticMemoryRecord] = []
        rejection_reasons: list[str] = []

        repo_fp = getattr(manifest, "repo_fingerprint", gen_input.repository_fingerprint)

        for raw_item in raw_items:
            # Clean semantic text & strip think tags
            text = str(raw_item.get("semantic_text", "")).strip()
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
            if not text:
                rejection_reasons.append("empty_semantic_text")
                continue

            # Extract and validate source files
            raw_files = raw_item.get("source_files", [])
            if isinstance(raw_files, str):
                raw_files = [raw_files]
            if not raw_files:
                rejection_reasons.append("missing_source_files")
                continue

            norm_files: list[str] = []
            files_valid = True
            for rf in raw_files:
                norm_f = str(rf).replace("\\", "/").lstrip("./")
                if norm_f not in manifest.files:
                    rejection_reasons.append(f"source_file_unknown:{norm_f}")
                    files_valid = False
                    break
                norm_files.append(norm_f)

            if not files_valid:
                continue

            # Extract and validate source symbols against AST in manifest
            raw_symbols = raw_item.get("source_symbols", [])
            if isinstance(raw_symbols, str):
                raw_symbols = [raw_symbols]

            symbols_valid = True
            norm_symbols: list[str] = []
            if raw_symbols:
                known_ast_symbols: set[str] = set()
                for nf in norm_files:
                    fp = manifest.files.get(nf)
                    if fp and getattr(fp, "symbols", None):
                        known_ast_symbols.update(fp.symbols)

                for sym in raw_symbols:
                    sym_clean = str(sym).strip()
                    if sym_clean:
                        if sym_clean not in known_ast_symbols:
                            rejection_reasons.append(f"source_symbol_unknown:{sym_clean}")
                            symbols_valid = False
                            break
                        norm_symbols.append(sym_clean)

            if not symbols_valid:
                continue

            # Attach authoritative SHA-256 hashes from manifest
            source_sha256 = [manifest.files[nf].sha256 for nf in norm_files]

            # Deterministic memory ID
            hash_key = f"{gen_input.repository_id}:{repo_fp}:{sorted(norm_files)}:{sorted(norm_symbols)}:{text}"
            mem_id = f"cognee_mem_{hashlib.sha256(hash_key.encode('utf-8')).hexdigest()[:16]}"

            # Construct candidate dictionary for Task 2 adapter validation
            candidate_dict = {
                "id": mem_id,
                "text": text,
                "repository_id": gen_input.repository_id,
                "repository_fingerprint": repo_fp,
                "source_files": norm_files,
                "source_symbols": norm_symbols,
                "source_sha256": source_sha256,
                "relationship_kind": str(raw_item.get("relationship_kind", "behavior_summary")),
                "confidence_score": float(raw_item.get("confidence_score", 1.0) or 1.0),
            }

            # Run through Task 2 adapter validation boundary
            rec, status = CogneeSemanticMemoryAdapter.map_item(
                item=candidate_dict,
                manifest=manifest,
                repository_id=gen_input.repository_id,
                repository_fingerprint=repo_fp,
            )

            if rec is not None and status == "valid":
                validated_records.append(rec)
            else:
                rejection_reasons.append(status)

        validated_count = len(validated_records)
        rejected_count = candidate_count - validated_count
        persisted_count = 0

        # 8. Persist validated records
        if persist and self.repository and validated_records:
            persisted_count, save_errors = self.repository.save_all(
                records=validated_records,
                manifest=manifest,
            )
            if save_errors:
                rejection_reasons.extend(save_errors)

        # 9. Truthful Telemetry Assembly
        overall_status = "success" if validated_records else "no_valid_memories"
        telemetry = SemanticMemoryGenerationTelemetry(
            model_invoked=True,
            provider_identity=provider_identity,
            model_name=target_model,
            inference_status=overall_status,
            inference_time_ms=elapsed_ms,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            candidate_count=candidate_count,
            validated_count=validated_count,
            persisted_count=persisted_count,
            rejected_count=rejected_count,
            rejection_reasons=rejection_reasons,
            llm_invocation_count=1,
            regenerated_count=validated_count,
            mode="incremental" if file_filter else "full",
        )

        msg = (
            f"Generated {candidate_count} memory candidates; "
            f"{validated_count} passed provenance validation; {persisted_count} persisted."
        )

        return SemanticMemoryGenerationResult(
            success=bool(validated_records),
            status=overall_status,
            records=validated_records,
            telemetry=telemetry,
            message=msg,
        )

    async def cognify_repository(
        self,
        repository_id: str,
        manifest: Any,
        delta: Optional[Any] = None,
        existing_manifest: Optional[Any] = None,
        source_snippets: Optional[dict[str, str]] = None,
        frameworks: Optional[list[str]] = None,
        task_intent: Optional[str] = None,
        model_config: Optional[dict[str, Any]] = None,
        cognee_service: Optional[Any] = None,
    ) -> SemanticMemoryGenerationResult:
        """Perform end-to-end repository cognification and incremental semantic memory lifecycle.

        Invariants:
        1. Exactly-once semantic extraction: exactly ONE LLM extraction pass is run for new/changed material.
        2. Granular incremental regeneration:
           - On file modification: invalidates only affected memories and re-extracts for changed files.
           - On file deletion: invalidates only affected memories without re-running LLM on unchanged files.
           - On same-SHA rename: updates provenance path with 0 LLM calls.
        3. No recursive self-feeding: only source/AST evidence is passed to extraction; generated memories are never fed back into extraction.
        4. Optional Cognee persistence/indexing: uses add() (without second LLM extraction) into LanceDB/Kùzu.
        """
        # 1. Manifest existence validation
        if not manifest or not hasattr(manifest, "files") or not manifest.files:
            return SemanticMemoryGenerationResult(
                success=False,
                status="insufficient_evidence",
                records=[],
                telemetry=SemanticMemoryGenerationTelemetry(
                    model_invoked=False,
                    inference_status="insufficient_evidence",
                    rejection_reasons=["missing_or_empty_manifest"],
                ),
                message="Repository manifest is missing or contains no indexed files.",
            )

        repo_path_root = getattr(manifest, "repo_path", "")
        repo_id = repository_id or getattr(manifest, "dataset_name", "") or "default_repo"

        existing_records: list[SemanticMemoryRecord] = []
        if self.repository is not None:
            existing_records = self.repository.get_by_repository(
                repository_id=repo_id,
                manifest=None,
                include_stale=True,
            )

        # 2. Check for no-op delta (no changes)
        if delta is not None and not getattr(delta, "has_changes", True) and existing_manifest is not None:
            active_mems = (
                self.repository.get_by_repository(repository_id=repo_id, manifest=manifest, include_stale=False)
                if self.repository
                else [r for r in existing_records if r.evidence_status != "stale"]
            )
            telemetry = SemanticMemoryGenerationTelemetry(
                model_invoked=False,
                provider_identity=getattr(self.llm_provider, "provider_type", "llm_provider"),
                model_name=getattr(self.llm_provider, "default_model", ""),
                inference_status="noop",
                inference_time_ms=0.0,
                candidate_count=len(active_mems),
                validated_count=len(active_mems),
                persisted_count=len(active_mems),
                llm_invocation_count=0,
                preserved_count=len(active_mems),
                mode="noop",
            )
            return SemanticMemoryGenerationResult(
                success=True,
                status="noop",
                records=active_mems,
                telemetry=telemetry,
                message="No changes detected in repository; existing semantic memory preserved.",
            )

        invalidated_count = 0
        renamed_count = 0
        target_files: list[str] = []

        current_fp = getattr(manifest, "repo_fingerprint", "")

        # 3. Handle incremental delta if present
        if delta is not None:
            # 3a. Handle Renames
            for rename_item in getattr(delta, "renamed", []):
                old_rel, new_p = rename_item
                new_rel = str(new_p)
                if repo_path_root and hasattr(new_p, "is_absolute") and new_p.is_absolute():
                    try:
                        new_rel = str(new_p.relative_to(repo_path_root))
                    except Exception:
                        new_rel = str(new_p)

                old_fp = existing_manifest.files.get(old_rel) if existing_manifest and hasattr(existing_manifest, "files") else None
                new_fp = manifest.files.get(new_rel) if manifest and hasattr(manifest, "files") else None
                old_sha = getattr(old_fp, "sha256", None) if old_fp else None
                new_sha = getattr(new_fp, "sha256", None) if new_fp else None

                if old_sha and new_sha and old_sha == new_sha:
                    # Same SHA: update provenance paths in existing records with 0 LLM calls
                    if self.repository is not None:
                        for rec in existing_records:
                            if old_rel in rec.source_files:
                                updated_files = [new_rel if f == old_rel else f for f in rec.source_files]
                                self.repository.delete(rec.memory_id, repository_id=repo_id)
                                updated_rec = SemanticMemoryRecord(
                                    memory_id=f"cognee_mem_{hashlib.sha256(f'{repo_id}:{current_fp}:{sorted(updated_files)}:{rec.semantic_text}'.encode('utf-8')).hexdigest()[:16]}",
                                    repository_id=rec.repository_id,
                                    repository_fingerprint=current_fp or rec.repository_fingerprint,
                                    semantic_text=rec.semantic_text,
                                    source_files=updated_files,
                                    source_symbols=rec.source_symbols,
                                    source_sha256=rec.source_sha256,
                                    relationship_kind=rec.relationship_kind,
                                    generated_by=rec.generated_by,
                                    generated_at=rec.generated_at,
                                    evidence_status=rec.evidence_status,
                                    confidence_score=rec.confidence_score,
                                )
                                self.repository.save(updated_rec, manifest=manifest)
                                renamed_count += 1
                else:
                    # Content changed during rename: invalidate old and mark new for extraction
                    if self.repository is not None:
                        for rec in existing_records:
                            if old_rel in rec.source_files:
                                self.repository.delete(rec.memory_id, repository_id=repo_id)
                                invalidated_count += 1
                    target_files.append(new_rel)

            # 3b. Handle Deletions
            for del_rel in getattr(delta, "deleted", []):
                if self.repository is not None:
                    for rec in existing_records:
                        if del_rel in rec.source_files:
                            self.repository.delete(rec.memory_id, repository_id=repo_id)
                            invalidated_count += 1

            # 3c. Handle Modifications
            for mod_p in getattr(delta, "modified", []):
                mod_rel = str(mod_p)
                if repo_path_root and hasattr(mod_p, "is_absolute") and mod_p.is_absolute():
                    try:
                        mod_rel = str(mod_p.relative_to(repo_path_root))
                    except Exception:
                        mod_rel = str(mod_p)
                if self.repository is not None:
                    for rec in existing_records:
                        if mod_rel in rec.source_files:
                            self.repository.delete(rec.memory_id, repository_id=repo_id)
                            invalidated_count += 1
                target_files.append(mod_rel)

            # 3d. Handle Additions
            for add_p in getattr(delta, "added", []):
                add_rel = str(add_p)
                if repo_path_root and hasattr(add_p, "is_absolute") and add_p.is_absolute():
                    try:
                        add_rel = str(add_p.relative_to(repo_path_root))
                    except Exception:
                        add_rel = str(add_p)
                target_files.append(add_rel)

            # Refresh fingerprint on all preserved records that remain valid against the new manifest
            if current_fp and self.repository is not None:
                for rec in existing_records:
                    is_file_valid = True
                    for idx, f_path in enumerate(rec.source_files):
                        norm_path = f_path.replace("\\", "/").lstrip("./")
                        if norm_path not in manifest.files:
                            is_file_valid = False
                            break
                        fp = manifest.files[norm_path]
                        if idx < len(rec.source_sha256):
                            if rec.source_sha256[idx] != getattr(fp, "sha256", None):
                                is_file_valid = False
                                break
                    if is_file_valid and rec.repository_fingerprint != current_fp:
                        self.repository.delete(rec.memory_id, repository_id=repo_id)
                        rec.repository_fingerprint = current_fp
                        self.repository.save(rec, manifest=manifest)

            # Deduplicate target files
            target_files = list(dict.fromkeys(target_files))

            # If no files need generation (e.g. only same-sha renames and/or deletions)
            if not target_files:
                active_records = (
                    self.repository.get_by_repository(repo_id, manifest=manifest, include_stale=False)
                    if self.repository
                    else []
                )
                telemetry = SemanticMemoryGenerationTelemetry(
                    model_invoked=False,
                    provider_identity=getattr(self.llm_provider, "provider_type", "llm_provider"),
                    model_name=getattr(self.llm_provider, "default_model", ""),
                    inference_status="success",
                    llm_invocation_count=0,
                    invalidated_count=invalidated_count,
                    preserved_count=len(active_records),
                    renamed_count=renamed_count,
                    mode="rename_only" if renamed_count > 0 else "deletion_only",
                )
                return SemanticMemoryGenerationResult(
                    success=True,
                    status="success",
                    records=active_records,
                    telemetry=telemetry,
                    message=f"Incremental lifecycle completed with 0 LLM calls ({invalidated_count} invalidated, {renamed_count} renamed, {len(active_records)} preserved).",
                )
        else:
            target_files = list(manifest.files.keys())

        # 4. Exactly-Once Semantic Extraction Pass for target files
        gen_result = await self.generate_semantic_memory(
            repository_id=repo_id,
            manifest=manifest,
            file_filter=target_files,
            source_snippets=source_snippets,
            task_intent=task_intent,
            frameworks=frameworks,
            model_config=model_config,
            persist=True,
        )

        # 5. Assemble composite telemetry
        all_active = (
            self.repository.get_by_repository(repo_id, manifest=manifest, include_stale=False)
            if self.repository
            else gen_result.records
        )

        gen_result.telemetry.invalidated_count = invalidated_count
        gen_result.telemetry.renamed_count = renamed_count
        gen_result.telemetry.preserved_count = max(0, len(all_active) - len(gen_result.records))
        gen_result.telemetry.mode = "incremental" if delta is not None else "full"

        # 6. Optional Cognee Vector/Graph Indexing (without duplicate LLM pass)
        if cognee_service is not None and gen_result.success and gen_result.records:
            try:
                from app.services.cognee_service import sanitize_dataset_name
                ds_name = sanitize_dataset_name(repo_id)
                formatted_memory_lines = "\n".join(
                    f"- [{', '.join(r.source_files)}] {r.semantic_text}"
                    for r in gen_result.records
                )
                await cognee_service.add(
                    data=formatted_memory_lines,
                    dataset_name=ds_name,
                )
                gen_result.vector_indexed = True
                gen_result.dataset_name = ds_name
            except Exception as e:
                logger.warning("Cognee indexing for dataset %s failed / skipped: %s", repo_id, e)
                gen_result.vector_indexed = False

        return gen_result


# Canonical alias
SemanticMemoryGenerationService = SemanticMemoryGenerator
