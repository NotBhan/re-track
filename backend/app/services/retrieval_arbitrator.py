"""Authoritative End-to-End Retrieval Arbitration Service for RE:Track.

Combines source search, deterministic AST relationships, and validated derived memory
into an authority-first evidence pipeline prior to EvidenceService gating and LLM synthesis.
"""

import logging
from pathlib import Path
import re
from typing import Any, Optional, Sequence

from app.application.domain.arbitration import (
    ArbitratedCandidate,
    ArbitratedEvidenceResult,
    AuthorityTier,
)
from app.application.domain.intent import ParsedIntentRecord
from app.application.domain.memory import MemoryProvenance

logger = logging.getLogger(__name__)


class RetrievalArbitrator:
    """Arbitrates multi-modal retrieval candidates into an authority-first evidence set."""

    @staticmethod
    def validate_candidate_provenance(
        provenance: Optional[MemoryProvenance | dict[str, Any]],
        manifest: Optional[Any],
    ) -> tuple[bool, str]:
        """Validate candidate provenance against active repository manifest.

        Returns:
            (is_valid, rejection_reason)
        """
        if not manifest or not hasattr(manifest, "files") or not manifest.files:
            return False, "no_active_manifest"

        if provenance is None:
            return False, "missing_provenance"

        prov_obj: Optional[MemoryProvenance] = None
        if isinstance(provenance, MemoryProvenance):
            prov_obj = provenance
        elif isinstance(provenance, dict):
            prov_obj = MemoryProvenance.from_dict(provenance)

        if not prov_obj:
            return False, "invalid_provenance_structure"

        # Check cross-repository isolation
        manifest_repo_fp = getattr(manifest, "repo_fingerprint", "")
        if prov_obj.repository_fingerprint and manifest_repo_fp:
            if prov_obj.repository_fingerprint != manifest_repo_fp:
                return False, "cross_repository_mismatch"

        # Check source file existence in manifest
        norm_file = str(prov_obj.source_file).replace("\\", "/").lstrip("./")
        if norm_file not in manifest.files:
            return False, "source_file_missing_in_manifest"

        file_fp = manifest.files[norm_file]

        # Check SHA-256 integrity
        if prov_obj.source_sha256 and getattr(file_fp, "sha256", None):
            if prov_obj.source_sha256 != file_fp.sha256:
                return False, "source_sha256_stale"

        # Check symbol existence if symbol is declared
        if prov_obj.source_symbol and getattr(file_fp, "symbols", None):
            if prov_obj.source_symbol not in file_fp.symbols:
                return False, "source_symbol_missing"

        return True, "valid"

    @classmethod
    def arbitrate(
        cls,
        task_prompt: str,
        intent: ParsedIntentRecord,
        manifest: Optional[Any] = None,
        source_snippets: Sequence[str] = (),
        source_matched_files: Sequence[str] = (),
        ast_symbols: Sequence[str] = (),
        ast_call_edges: Sequence[str] = (),
        ast_definitions: Sequence[Any] = (),
        ast_imports: Sequence[str] = (),
        ast_inheritance: Sequence[str] = (),
        ast_jsx_renders: Sequence[str] = (),
        ast_relationships: Sequence[Any] = (),
        lancedb_kuzu_memories: Sequence[Any] = (),
        cognee_memories: Sequence[Any] = (),
        target_tokens: int = 3000,
        reserve_authoritative_budget: bool = True,
    ) -> ArbitratedEvidenceResult:
        """Arbitrate multi-modal evidence candidates into a ranked, budgeted result.

        Ranking strategy:
            Lexicographic sort key: (TierPriority, Relevance, Confidence, Specificity)
            Tier 1 (Source) > Tier 2 (AST) > Tier 3 (LanceDB/Kùzu) > Tier 4 (Cognee)

        Budgeting strategy:
            Authoritative tiers (1 & 2) receive reserved budget allocation.
            Lower tiers (3 & 4) only fill remaining unreserved budget without
            ever displacing higher-tier candidates.
        """
        all_candidates: list[ArbitratedCandidate] = []
        stale_rejected_count = 0
        cross_repo_rejected_count = 0

        # ---------------------------------------------------------
        # Tier 1: Filesystem Verified Source (Authoritative Source)
        # ---------------------------------------------------------
        for i, snippet in enumerate(source_snippets):
            clean_snip = snippet.strip()
            if not clean_snip:
                continue

            # Extract source file header and line range if present
            line_start: Optional[int] = None
            line_end: Optional[int] = None
            line_match = re.search(r"\(Lines\s*(\d+)(?:-(\d+))?\)", clean_snip)
            if line_match:
                line_start = int(line_match.group(1))
                line_end = int(line_match.group(2)) if line_match.group(2) else line_start

            file_match = re.search(r"(?:###|File:)\s*`?([^\n`:(]+)`?", clean_snip)
            source_file = file_match.group(1).strip() if file_match else (source_matched_files[i] if i < len(source_matched_files) else "")

            # Relevance based on extracted symbol and hint matches
            snip_lower = clean_snip.lower()
            sym_matches = sum(1 for sym in intent.extracted_symbols if sym.lower() in snip_lower)
            relevance = min(1.0, 0.5 + 0.15 * sym_matches)
            token_est = max(1, len(clean_snip) // 4)
            specificity = min(1.0, len(clean_snip) / 1000.0)

            all_candidates.append(
                ArbitratedCandidate(
                    id=f"src_snip_{i}",
                    tier=AuthorityTier.TIER_1_SOURCE,
                    content=clean_snip,
                    source_file=source_file,
                    line_start=line_start,
                    line_end=line_end,
                    relevance=relevance,
                    confidence=1.0,
                    specificity=specificity,
                    is_valid=True,
                    token_estimate=token_est,
                )
            )

        # ---------------------------------------------------------
        # Tier 2: Manifest AST (Deterministic Code Graph)
        # ---------------------------------------------------------
        # 1. Symbols
        for i, sym in enumerate(ast_symbols):
            sym_clean = sym.strip()
            if not sym_clean:
                continue
            is_intent_sym = any(sym_clean.lower() == s.lower() for s in intent.extracted_symbols)
            relevance = 1.0 if is_intent_sym else 0.75
            all_candidates.append(
                ArbitratedCandidate(
                    id=f"ast_sym_{i}",
                    tier=AuthorityTier.TIER_2_MANIFEST_AST,
                    content=f"Symbol: {sym_clean}",
                    source_file="",
                    source_symbol=sym_clean,
                    relationship_kind="symbol",
                    relevance=relevance,
                    confidence=0.95,
                    specificity=1.0,
                    is_valid=True,
                    token_estimate=5,
                )
            )

        # 2. Definitions
        for i, def_item in enumerate(ast_definitions):
            if isinstance(def_item, dict):
                sym_name = def_item.get("symbol") or def_item.get("name") or ""
                src_f = def_item.get("file") or def_item.get("path") or ""
                sig = def_item.get("signature") or def_item.get("content") or sym_name
                def_str = f"Definition: `{sym_name}` ({sig}) in `{src_f}`" if src_f else f"Definition: `{sym_name}` ({sig})"
            else:
                sym_name = ""
                src_f = ""
                def_str = f"Definition: {str(def_item).strip()}"

            all_candidates.append(
                ArbitratedCandidate(
                    id=f"ast_def_{i}",
                    tier=AuthorityTier.TIER_2_MANIFEST_AST,
                    content=def_str,
                    source_file=src_f,
                    source_symbol=sym_name or None,
                    relationship_kind="definition",
                    relevance=0.95,
                    confidence=0.95,
                    specificity=0.95,
                    is_valid=True,
                    token_estimate=max(5, len(def_str) // 4),
                )
            )

        # 3. Imports
        for i, imp in enumerate(ast_imports):
            imp_clean = imp.strip()
            if not imp_clean:
                continue
            all_candidates.append(
                ArbitratedCandidate(
                    id=f"ast_imp_{i}",
                    tier=AuthorityTier.TIER_2_MANIFEST_AST,
                    content=f"Import: {imp_clean}",
                    source_file="",
                    relationship_kind="import",
                    relevance=0.80,
                    confidence=0.95,
                    specificity=0.85,
                    is_valid=True,
                    token_estimate=max(4, len(imp_clean) // 4),
                )
            )

        # 4. Calls
        for i, edge in enumerate(ast_call_edges):
            edge_clean = edge.strip()
            if not edge_clean:
                continue
            all_candidates.append(
                ArbitratedCandidate(
                    id=f"ast_call_{i}",
                    tier=AuthorityTier.TIER_2_MANIFEST_AST,
                    content=f"Call Edge: {edge_clean}",
                    source_file="",
                    relationship_kind="call_graph",
                    relevance=0.85,
                    confidence=0.95,
                    specificity=0.9,
                    is_valid=True,
                    token_estimate=8,
                )
            )

        # 5. Inheritance
        for i, inh in enumerate(ast_inheritance):
            inh_clean = inh.strip()
            if not inh_clean:
                continue
            all_candidates.append(
                ArbitratedCandidate(
                    id=f"ast_inh_{i}",
                    tier=AuthorityTier.TIER_2_MANIFEST_AST,
                    content=f"Inheritance: {inh_clean}",
                    source_file="",
                    relationship_kind="inheritance",
                    relevance=0.85,
                    confidence=0.95,
                    specificity=0.9,
                    is_valid=True,
                    token_estimate=max(6, len(inh_clean) // 4),
                )
            )

        # 6. JSX/render relationships
        for i, jsx in enumerate(ast_jsx_renders):
            jsx_clean = jsx.strip()
            if not jsx_clean:
                continue
            all_candidates.append(
                ArbitratedCandidate(
                    id=f"ast_jsx_{i}",
                    tier=AuthorityTier.TIER_2_MANIFEST_AST,
                    content=f"JSX Render: {jsx_clean}",
                    source_file="",
                    relationship_kind="jsx_render",
                    relevance=0.85,
                    confidence=0.95,
                    specificity=0.9,
                    is_valid=True,
                    token_estimate=max(6, len(jsx_clean) // 4),
                )
            )

        # 7. Generic AST structural relationships
        for i, rel in enumerate(ast_relationships):
            if isinstance(rel, dict):
                r_kind = rel.get("kind") or rel.get("type") or "structural"
                r_text = rel.get("content") or rel.get("description") or str(rel)
                src_f = rel.get("file") or ""
            else:
                r_kind = "structural"
                r_text = str(rel).strip()
                src_f = ""

            all_candidates.append(
                ArbitratedCandidate(
                    id=f"ast_rel_{i}",
                    tier=AuthorityTier.TIER_2_MANIFEST_AST,
                    content=f"AST Structural: {r_text}",
                    source_file=src_f,
                    relationship_kind=r_kind,
                    relevance=0.80,
                    confidence=0.95,
                    specificity=0.85,
                    is_valid=True,
                    token_estimate=max(6, len(r_text) // 4),
                )
            )

        # ---------------------------------------------------------
        # Tier 3: Validated LanceDB / Kùzu Projections
        # ---------------------------------------------------------
        for i, mem in enumerate(lancedb_kuzu_memories):
            prov = getattr(mem, "provenance", None) or (mem.get("provenance") if isinstance(mem, dict) else None)
            is_valid, reason = cls.validate_candidate_provenance(prov, manifest)
            if not is_valid:
                if reason == "cross_repository_mismatch":
                    cross_repo_rejected_count += 1
                else:
                    stale_rejected_count += 1
                continue

            text_content = str(getattr(mem, "text", None) or getattr(mem, "content", None) or (mem.get("text") if isinstance(mem, dict) else str(mem)))
            src_file = getattr(prov, "source_file", "") if prov else ""
            sim_score = float(getattr(mem, "similarity", 0.0) or getattr(mem, "score", 0.0) or (mem.get("similarity", 0.0) if isinstance(mem, dict) else 0.0))
            relevance = min(1.0, max(0.1, sim_score))

            src_symbol = getattr(prov, "source_symbol", None) if prov else None
            rel_kind = getattr(prov, "relationship_kind", None) if prov else None

            all_candidates.append(
                ArbitratedCandidate(
                    id=f"kuzu_vec_{i}",
                    tier=AuthorityTier.TIER_3_LANCEDB_KUZU,
                    content=text_content,
                    source_file=src_file,
                    source_symbol=src_symbol,
                    relationship_kind=rel_kind,
                    relevance=relevance,
                    confidence=0.75,
                    specificity=0.6,
                    provenance=prov if isinstance(prov, MemoryProvenance) else MemoryProvenance.from_dict(prov) if isinstance(prov, dict) else None,
                    is_valid=True,
                    token_estimate=max(1, len(text_content) // 4),
                )
            )

        # ---------------------------------------------------------
        # Tier 4: Validated Cognee Semantic Memory
        # ---------------------------------------------------------
        for i, mem in enumerate(cognee_memories):
            prov = getattr(mem, "provenance", None) or (mem.to_provenance() if hasattr(mem, "to_provenance") else (mem.get("provenance") if isinstance(mem, dict) else None))
            is_valid, reason = cls.validate_candidate_provenance(prov, manifest)
            if not is_valid:
                if reason == "cross_repository_mismatch":
                    cross_repo_rejected_count += 1
                else:
                    stale_rejected_count += 1
                continue

            text_content = str(getattr(mem, "semantic_text", None) or getattr(mem, "text", None) or getattr(mem, "content", None) or (mem.get("text") if isinstance(mem, dict) else str(mem)))
            src_file = getattr(prov, "source_file", "") if prov else ""
            src_symbol = getattr(prov, "source_symbol", None) if prov else None
            rel_kind = getattr(prov, "relationship_kind", None) if prov else None
            score = float(getattr(mem, "score", 0.0) or getattr(mem, "similarity", 0.0) or (mem.get("score", 0.0) if isinstance(mem, dict) else 0.0))
            relevance = min(1.0, max(0.1, score))

            all_candidates.append(
                ArbitratedCandidate(
                    id=f"cognee_mem_{i}",
                    tier=AuthorityTier.TIER_4_COGNEE,
                    content=text_content,
                    source_file=src_file,
                    source_symbol=src_symbol,
                    relationship_kind=rel_kind,
                    relevance=relevance,
                    confidence=0.60,
                    specificity=0.5,
                    provenance=prov if isinstance(prov, MemoryProvenance) else MemoryProvenance.from_dict(prov) if isinstance(prov, dict) else None,
                    is_valid=True,
                    token_estimate=max(1, len(text_content) // 4),
                )
            )

        # ---------------------------------------------------------
        # Lexicographic Ranking (Descending by sort_key)
        # ---------------------------------------------------------
        # Sort key: (TierPriority, Relevance, Confidence, Specificity)
        sorted_candidates = sorted(all_candidates, key=lambda c: c.sort_key(), reverse=True)

        # ---------------------------------------------------------
        # Budget Allocation: Strict Tier-by-Tier Authority Reservation
        # ---------------------------------------------------------
        selected_candidates: list[ArbitratedCandidate] = []
        accumulated_tokens = 0
        tier_counts: dict[str, int] = {
            AuthorityTier.TIER_1_SOURCE.label: 0,
            AuthorityTier.TIER_2_MANIFEST_AST.label: 0,
            AuthorityTier.TIER_3_LANCEDB_KUZU.label: 0,
            AuthorityTier.TIER_4_COGNEE.label: 0,
        }

        # Step 1: Allocate Tier 1 (Source)
        tier_1_cands = [c for c in sorted_candidates if c.tier == AuthorityTier.TIER_1_SOURCE]
        for c in tier_1_cands:
            if accumulated_tokens + c.token_estimate <= target_tokens or not selected_candidates:
                selected_candidates.append(c)
                accumulated_tokens += c.token_estimate
                tier_counts[c.tier.label] += 1

        # Step 2: Allocate Tier 2 (AST)
        tier_2_cands = [c for c in sorted_candidates if c.tier == AuthorityTier.TIER_2_MANIFEST_AST]
        for c in tier_2_cands:
            if accumulated_tokens + c.token_estimate <= target_tokens or not selected_candidates:
                selected_candidates.append(c)
                accumulated_tokens += c.token_estimate
                tier_counts[c.tier.label] += 1

        # Step 3: Fill remaining space with Tier 3 (LanceDB/Kùzu)
        tier_3_cands = [c for c in sorted_candidates if c.tier == AuthorityTier.TIER_3_LANCEDB_KUZU]
        for c in tier_3_cands:
            if accumulated_tokens + c.token_estimate <= target_tokens:
                selected_candidates.append(c)
                accumulated_tokens += c.token_estimate
                tier_counts[c.tier.label] += 1

        # Step 4: Fill remaining space with Tier 4 (Cognee)
        tier_4_cands = [c for c in sorted_candidates if c.tier == AuthorityTier.TIER_4_COGNEE]
        for c in tier_4_cands:
            if accumulated_tokens + c.token_estimate <= target_tokens:
                selected_candidates.append(c)
                accumulated_tokens += c.token_estimate
                tier_counts[c.tier.label] += 1

        # Extract authoritative files, symbols, snippets, relationships
        auth_files = list(dict.fromkeys(
            [c.source_file for c in selected_candidates if c.source_file] +
            list(source_matched_files)
        ))
        auth_symbols = list(dict.fromkeys(
            [c.source_symbol for c in selected_candidates if c.source_symbol] +
            list(ast_symbols)
        ))
        auth_snippets = [
            c.content for c in selected_candidates if c.tier == AuthorityTier.TIER_1_SOURCE
        ]
        auth_rels = list(dict.fromkeys(
            [
                c.content.replace("Call Edge: ", "").replace("AST Edge: ", "").replace("Import: ", "").replace("Inheritance: ", "").replace("JSX Render: ", "").replace("AST Structural: ", "")
                for c in selected_candidates
                if c.relationship_kind in ("call_graph", "import", "inheritance", "jsx_render", "definition", "structural") or (c.relationship_kind and c.relationship_kind != "symbol")
            ] +
            list(ast_call_edges) +
            list(ast_imports) +
            list(ast_inheritance) +
            list(ast_jsx_renders)
        ))

        return ArbitratedEvidenceResult(
            candidates=selected_candidates,
            tier_counts=tier_counts,
            stale_rejected_count=stale_rejected_count,
            cross_repo_rejected_count=cross_repo_rejected_count,
            total_token_estimate=accumulated_tokens,
            authoritative_files=auth_files,
            authoritative_symbols=auth_symbols,
            authoritative_snippets=auth_snippets,
            authoritative_relationships=auth_rels,
        )
