"""
CodeGraphContext (CGC) Structural Graph Service for RE:Track.

Interacts with the CGC CLI / graph database to extract code structural
relationships (call graphs, class hierarchies, caller/callee trees, and imports)
without consuming LLM inference or context tokens.
"""

import asyncio
import json
import logging
from pathlib import Path
import shutil
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CodeSymbolRelation(BaseModel):
    """Structural relationship between code entities."""

    source: str
    relation: str  # CALLS, IMPORTS, EXTENDS, DEFINES
    target: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None


class StructuralContextResult(BaseModel):
    """Aggregated structural context retrieved from CodeGraphContext."""

    symbols_found: list[str] = Field(default_factory=list)
    callers: list[str] = Field(default_factory=list)
    callees: list[str] = Field(default_factory=list)
    related_files: list[str] = Field(default_factory=list)
    relations: list[CodeSymbolRelation] = Field(default_factory=list)
    is_available: bool = True
    error_message: Optional[str] = None

    def to_markdown(self) -> str:
        """Format structural relationships as compact Markdown."""
        if not self.is_available:
            return ""

        lines = []
        if self.symbols_found:
            lines.append(f"**Identified Symbols**: {', '.join(f'`{s}`' for s in self.symbols_found)}")

        if self.callers:
            lines.append("\n**Callers (Upstream Invocations)**:")
            for c in self.callers[:10]:
                lines.append(f"- `{c}`")

        if self.callees:
            lines.append("\n**Callees (Downstream Invocations)**:")
            for c in self.callees[:10]:
                lines.append(f"- `{c}`")

        if self.related_files:
            lines.append("\n**Structurally Coupled Files**:")
            for f in self.related_files[:10]:
                lines.append(f"- `{f}`")

        return "\n".join(lines)


class CGCService:
    """Service interacting with CodeGraphContext CLI."""

    def __init__(self, cgc_bin_path: Optional[str] = None) -> None:
        self._cgc_bin = cgc_bin_path or shutil.which("cgc")

    @property
    def is_installed(self) -> bool:
        return self._cgc_bin is not None

    async def ensure_indexed(self, repo_path: Path, force: bool = False) -> bool:
        """Run `cgc index` on the target repository."""
        if not self.is_installed:
            logger.warning("CGC binary not found on PATH; skipping CGC indexing")
            return False

        cmd = [self._cgc_bin, "index"]
        if force:
            cmd.append("--force")
        cmd.append(str(repo_path.resolve()))

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(repo_path),
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=45.0)
            if process.returncode == 0:
                logger.info("CGC indexing complete for %s", repo_path)
                return True
            else:
                logger.warning("CGC index failed (code %d): %s", process.returncode, stderr.decode())
                return False
        except Exception as e:
            logger.warning("Error running CGC index on %s: %s", repo_path, e)
            return False

    async def query_structural_context(
        self,
        repo_path: Path,
        target_symbols: list[str],
    ) -> StructuralContextResult:
        """Query code graph relationships for the specified target symbols."""
        if not self.is_installed:
            return StructuralContextResult(
                is_available=False,
                error_message="CGC CLI is not installed",
            )

        if not target_symbols:
            return StructuralContextResult(is_available=True)

        found_symbols = []
        callers = []
        callees = []
        related_files = set()
        relations = []

        for symbol in target_symbols[:8]:
            # Run Cypher query on code graph to retrieve CALLS and DEFINES relations
            query = (
                f"MATCH (s)-[r:CALLS]->(t) "
                f"WHERE s.name CONTAINS '{symbol}' OR t.name CONTAINS '{symbol}' "
                f"RETURN s.name AS src, type(r) AS rel, t.name AS tgt, "
                f"s.file_path AS s_file, t.file_path AS t_file LIMIT 15"
            )

            cmd = [self._cgc_bin, "query", query]
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(repo_path),
                )
                stdout, _ = await asyncio.wait_for(process.communicate(), timeout=8.0)
                out_str = stdout.decode()
                
                # Parse stdout rows or matches
                for line in out_str.splitlines():
                    if "|" in line and "src" not in line and "---" not in line:
                        parts = [p.strip() for p in line.split("|") if p.strip()]
                        if len(parts) >= 3:
                            src, rel, tgt = parts[0], parts[1], parts[2]
                            found_symbols.append(symbol)
                            relations.append(
                                CodeSymbolRelation(
                                    source=src,
                                    relation=rel,
                                    target=tgt,
                                )
                            )
                            if symbol in src:
                                callees.append(tgt)
                            if symbol in tgt:
                                callers.append(src)
                            if len(parts) >= 4 and parts[3]:
                                related_files.add(parts[3])
            except Exception as e:
                logger.debug("CGC query error for symbol %s: %s", symbol, e)

        return StructuralContextResult(
            symbols_found=list(set(found_symbols)),
            callers=list(set(callers)),
            callees=list(set(callees)),
            related_files=list(related_files),
            relations=relations,
            is_available=True,
        )
