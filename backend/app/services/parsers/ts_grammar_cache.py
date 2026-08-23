"""
Thread-safe Tree-sitter grammar cache and parser allocator for TypeScript, TSX, and JavaScript.

Provides singleton-cached Language instances and thread-isolated Parser instances.
"""

from enum import Enum
import logging
from pathlib import Path
import threading
from typing import Optional

from tree_sitter import Language, Parser
import tree_sitter_javascript as tsjs
import tree_sitter_typescript as tsts

logger = logging.getLogger(__name__)


class TSLanguageDialect(str, Enum):
    TYPESCRIPT = "typescript"
    TSX = "tsx"
    JAVASCRIPT = "javascript"
    JSX = "jsx"


class TSGrammarCache:
    """Thread-safe singleton registry for Tree-sitter Language instances and Parser creation."""

    _instance: Optional["TSGrammarCache"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        try:
            self._ts_language = Language(tsts.language_typescript())
            self._tsx_language = Language(tsts.language_tsx())
            self._js_language = Language(tsjs.language())
            self._initialized = True
            logger.info("TSGrammarCache initialized with TypeScript, TSX, and JavaScript grammars.")
        except Exception as e:
            self._initialized = False
            logger.error("Failed to initialize Tree-sitter grammars: %s", e)
            raise

    @classmethod
    def get_instance(cls) -> "TSGrammarCache":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def get_language(self, dialect: TSLanguageDialect | str) -> Language:
        """Retrieve the compiled Tree-sitter Language instance for a dialect."""
        if isinstance(dialect, str):
            try:
                dialect = TSLanguageDialect(dialect.lower())
            except ValueError:
                dialect = TSLanguageDialect.TYPESCRIPT

        if dialect == TSLanguageDialect.TYPESCRIPT:
            return self._ts_language
        elif dialect in (TSLanguageDialect.TSX, TSLanguageDialect.JSX):
            # TSX grammar is a strict superset capable of parsing JSX and TSX
            return self._tsx_language
        elif dialect == TSLanguageDialect.JAVASCRIPT:
            return self._js_language
        return self._ts_language

    def create_parser(self, dialect: TSLanguageDialect | str) -> Parser:
        """Create a new, isolated Parser instance configured with the target dialect."""
        lang = self.get_language(dialect)
        return Parser(lang)

    @staticmethod
    def detect_dialect(file_path: Path | str) -> Optional[TSLanguageDialect]:
        """Detect the TypeScript/JavaScript dialect from a file extension."""
        p = Path(file_path)
        ext = p.suffix.lower()
        if ext == ".ts" and not p.name.endswith(".d.ts"):
            return TSLanguageDialect.TYPESCRIPT
        elif ext == ".tsx":
            return TSLanguageDialect.TSX
        elif ext == ".jsx":
            return TSLanguageDialect.JSX
        elif ext in (".js", ".mjs", ".cjs"):
            return TSLanguageDialect.JAVASCRIPT
        elif p.name.endswith(".d.ts"):
            return TSLanguageDialect.TYPESCRIPT
        return None
