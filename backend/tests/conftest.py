import sys
from pathlib import Path

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

import pytest


def reset_cognee_engine_and_caches(timeout: float = 5.0) -> None:
    """Evict cached engine proxies, await background worker process teardown,
    and reset memoized Cognee configurations to prevent cross-test file locks."""
    import gc
    import concurrent.futures

    # 1. Force evict and close all entries across all decorated closing_lru_cache instances
    try:
        from cognee.infrastructure.databases.utils.closing_lru_cache import _DECORATED_CACHES

        all_pendings = []
        for cache in list(_DECORATED_CACHES):
            with cache._lock:
                keys = list(cache._cache.keys())
            for key in keys:
                try:
                    cache.evict_and_close(key)
                except Exception:
                    pass
            try:
                cache.cache_clear()
            except Exception:
                pass
            with cache._lock:
                for futures in cache._closing.values():
                    all_pendings.extend([f for f in futures if not f.done()])

        if all_pendings:
            concurrent.futures.wait(all_pendings, timeout=timeout)
    except Exception:
        pass

    # 2. Clear engine factory caches
    try:
        from cognee.infrastructure.databases.graph.get_graph_engine import _create_graph_engine
        _create_graph_engine.cache_clear()
    except Exception:
        pass
    try:
        from cognee.infrastructure.databases.vector.create_vector_engine import _create_vector_engine
        _create_vector_engine.cache_clear()
    except Exception:
        pass
    try:
        from cognee.infrastructure.databases.relational.create_relational_engine import (
            create_relational_engine,
        )
        create_relational_engine.cache_clear()
    except Exception:
        pass

    # 3. Clear configuration caches
    try:
        from cognee.base_config import get_base_config
        get_base_config.cache_clear()
    except Exception:
        pass
    try:
        from cognee.infrastructure.databases.graph.config import get_graph_config
        get_graph_config.cache_clear()
    except Exception:
        pass
    try:
        from cognee.infrastructure.databases.vector.config import get_vectordb_config
        get_vectordb_config.cache_clear()
    except Exception:
        pass
    try:
        from cognee.infrastructure.databases.relational.config import (
            get_migration_config,
            get_relational_config,
        )
        get_relational_config.cache_clear()
        get_migration_config.cache_clear()
    except Exception:
        pass

    # 4. Reset context global variables
    try:
        from cognee.context_global_variables import (
            graph_db_config,
            vector_db_config,
            current_dataset_id,
            llm_config,
            embedding_config,
            session_user,
        )
        graph_db_config.set(None)
        vector_db_config.set(None)
        current_dataset_id.set(None)
        llm_config.set(None)
        embedding_config.set(None)
        session_user.set(None)
    except Exception:
        pass

    # 5. Restore staticmethods on cognee.config if clobbered
    try:
        from cognee.api.v1.config.config import config as cognee_config_cls
        import cognee
        cognee.config.system_root_directory = cognee_config_cls.system_root_directory
        cognee.config.data_root_directory = cognee_config_cls.data_root_directory
    except Exception:
        pass

    # 6. Clean up storage environment variable leaks from apply_to_environment()
    import os
    for env_key in ("DATA_ROOT_DIRECTORY", "SYSTEM_ROOT_DIRECTORY"):
        os.environ.pop(env_key, None)

    # 7. Force garbage collection to drop unpinned proxies and handles
    gc.collect()


@pytest.fixture(autouse=True)
def _reset_command_singletons():
    """Reset command singletons and Cognee handles before and after each test."""
    import app.api.commands as cmds

    cmds._cognee_service = None
    cmds._indexing_service = None
    cmds._context_service = None
    reset_cognee_engine_and_caches()
    yield
    cmds._cognee_service = None
    cmds._indexing_service = None
    cmds._context_service = None
    reset_cognee_engine_and_caches()


@pytest.fixture(autouse=True)
def _isolate_persisted_settings(tmp_path, monkeypatch):
    """Prevent tests from reading or writing the developer's real settings store.

    Provider configuration flows through ``Settings.save_persisted_settings()``
    (e.g. update_provider), which defaults to ``~/.retrack/settings.json``. Without
    isolation a test run silently rewrites the live provider/model configuration of
    the machine it runs on.
    """
    from app.config import settings as settings_module

    # The Settings fields are declared as `default_factory=lambda: DEFAULT_...`, which
    # resolves these module globals at construction time, so patching them redirects
    # every default-configured Settings instance.
    monkeypatch.setattr(
        settings_module,
        "DEFAULT_SETTINGS_STORE_PATH",
        tmp_path / "isolated_settings.json",
    )
    monkeypatch.setattr(
        settings_module,
        "DEFAULT_LEGACY_SETTINGS_STORE_PATH",
        tmp_path / "isolated_legacy_settings.json",
    )

    settings_module.get_settings.cache_clear()
    yield
    settings_module.get_settings.cache_clear()


# Provider identity env vars written by Settings.apply_to_environment() (for Cognee
# compatibility). Because `Settings` reads these back on construction, a leak makes one
# test's provider configuration override another test's explicit arguments.
_PROVIDER_ENV_KEYS = (
    "LLM_PROVIDER",
    "LLM_ENDPOINT",
    "LLM_API_KEY",
    "LLM_MODEL",
    "EMBEDDING_PROVIDER",
    "EMBEDDING_ENDPOINT",
    "EMBEDDING_API_KEY",
    "EMBEDDING_MODEL",
    "EMBEDDING_DIMENSIONS",
    "HUGGINGFACE_TOKENIZER",
    "VECTOR_DB_PROVIDER",
    "GRAPH_DB_PROVIDER",
    "RELATIONAL_DB_PROVIDER",
    "DATA_ROOT_DIRECTORY",
    "SYSTEM_ROOT_DIRECTORY",
    "CACHING",
    "COGNEE_SKIP_CONNECTION_TEST",
    "ENABLE_BACKEND_ACCESS_CONTROL",
)


@pytest.fixture(autouse=True)
def _isolate_provider_environment():
    """Restore provider identity env vars after each test."""
    import os

    snapshot = {key: os.environ.get(key) for key in _PROVIDER_ENV_KEYS}
    yield
    for key, value in snapshot.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
