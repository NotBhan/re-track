"""Pure domain helpers for repository dataset identity and memory namespace derivation.

Guarantees globally unique and stable Cognee dataset names per canonical repository path,
preventing cross-repository memory contamination between distinct projects with identical basenames.
"""

import hashlib
from pathlib import Path
import re
from typing import Optional


def sanitize_dataset_name(name: str | None) -> str:
    """Sanitize a dataset name for Cognee and vector databases.

    Removes .git suffix, and replaces dots, spaces, slashes, and non-alphanumerics with underscores.
    """
    if not name:
        return "default"
    clean = str(name).strip()
    if clean.endswith(".git"):
        clean = clean[:-4]
    clean = re.sub(r"[^a-zA-Z0-9_-]", "_", clean)
    clean = re.sub(r"_+", "_", clean).strip("-_")
    return clean or "default"


def derive_dataset_name(
    repo_path: Path | str,
    explicit_dataset_name: Optional[str] = None,
) -> str:
    """Derive a deterministic, collision-proof dataset name for a repository.

    Incorporates a 10-character SHA-256 hash of the canonical absolute repository path,
    guaranteeing that two different directories with the same folder name (e.g. /work/api
    vs /personal/api) produce isolated, distinct Cognee dataset namespaces.

    Args:
        repo_path: Repository filesystem path (string or Path).
        explicit_dataset_name: Optional user-specified dataset alias.

    Returns:
        A sanitized, collision-resistant string identifier formatted as
        `{sanitized_name}_{path_hash}`.
    """
    try:
        resolved = Path(repo_path).resolve()
        canonical_str = str(resolved)
    except Exception:
        canonical_str = str(repo_path)
        resolved = Path(repo_path)

    path_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()[:10]

    if explicit_dataset_name and explicit_dataset_name.strip():
        base = sanitize_dataset_name(explicit_dataset_name)
    else:
        base = sanitize_dataset_name(resolved.name)

    return f"{base}_{path_hash}"
