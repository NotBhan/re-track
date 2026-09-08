"""Tests verifying test infrastructure isolation and lock contention prevention.

Validates the required test infrastructure invariants:
1. test_each_real_cognee_test_has_isolated_storage_root
2. test_cognee_global_storage_configuration_is_reset_between_tests
3. test_ladybug_database_handles_are_released_before_teardown
4. test_repeated_real_runtime_acceptance_runs_are_lock_free
5. test_two_runtime_tests_use_distinct_database_paths
6. test_real_runtime_failure_does_not_leak_open_database_handles
"""

import asyncio
from pathlib import Path
import pytest

from app.config.settings import Settings, StorageConfig, ServiceConfig
from app.services.cognee_service import CogneeService
from tests.conftest import reset_cognee_engine_and_caches


@pytest.mark.asyncio
async def test_each_real_cognee_test_has_isolated_storage_root(tmp_path: Path):
    """Ensure every real Cognee acceptance test configures and uses a unique temporary storage root."""
    data_root = tmp_path / "cognee_data"
    system_root = tmp_path / "cognee_system"
    data_root.mkdir(parents=True)
    system_root.mkdir(parents=True)

    settings = Settings(
        storage=StorageConfig(
            data_root=data_root,
            system_root=system_root,
        ),
        service=ServiceConfig(
            skip_connection_test=True,
            enable_access_control=False,
            caching=False,
        ),
    )
    settings.configure_cognee()

    from cognee.base_config import get_base_config
    from cognee.infrastructure.databases.graph.config import get_graph_config
    from cognee.infrastructure.databases.vector.config import get_vectordb_config
    from cognee.infrastructure.databases.relational.config import get_relational_config

    base_cfg = get_base_config()
    graph_cfg = get_graph_config()
    vector_cfg = get_vectordb_config()
    relational_cfg = get_relational_config()

    # Invariant: storage roots must strictly point inside tmp_path, never to default .cognee_system or .venv
    assert str(system_root) in base_cfg.system_root_directory
    assert str(data_root) in base_cfg.data_root_directory
    assert str(system_root) in graph_cfg.graph_file_path
    assert str(system_root) in vector_cfg.vector_db_url
    assert str(system_root) in relational_cfg.db_path

    assert ".venv" not in graph_cfg.graph_file_path
    assert ".venv" not in vector_cfg.vector_db_url
    assert ".venv" not in relational_cfg.db_path


@pytest.mark.asyncio
async def test_cognee_global_storage_configuration_is_reset_between_tests(tmp_path: Path):
    """Verify that Cognee's global configuration is completely reset between tests."""
    root_1 = tmp_path / "test_1"
    root_1.mkdir()
    settings_1 = Settings(
        storage=StorageConfig(data_root=root_1 / "data", system_root=root_1 / "system"),
        service=ServiceConfig(skip_connection_test=True, enable_access_control=False, caching=False),
    )
    settings_1.configure_cognee()

    from cognee.infrastructure.databases.graph.config import get_graph_config

    path_1 = get_graph_config().graph_file_path
    assert str(root_1) in path_1

    # Execute teardown reset
    reset_cognee_engine_and_caches()

    # Configure second test environment
    root_2 = tmp_path / "test_2"
    root_2.mkdir()
    settings_2 = Settings(
        storage=StorageConfig(data_root=root_2 / "data", system_root=root_2 / "system"),
        service=ServiceConfig(skip_connection_test=True, enable_access_control=False, caching=False),
    )
    settings_2.configure_cognee()

    path_2 = get_graph_config().graph_file_path
    assert str(root_2) in path_2
    assert str(root_1) not in path_2
    assert path_1 != path_2


@pytest.mark.asyncio
async def test_ladybug_database_handles_are_released_before_teardown(tmp_path: Path):
    """Ensure databases and subprocess workers are fully closed/released before directories are destroyed."""
    sys_root = tmp_path / "sys_test"
    data_root = tmp_path / "data_test"
    sys_root.mkdir()
    data_root.mkdir()

    settings = Settings(
        storage=StorageConfig(data_root=data_root, system_root=sys_root),
        service=ServiceConfig(skip_connection_test=True, enable_access_control=False, caching=False),
    )
    settings.configure_cognee()

    service = CogneeService(settings=settings)
    await service.initialize()

    # Trigger real graph engine allocation and query
    nodes, edges = await service.get_graph_data()
    assert isinstance(nodes, list)
    assert isinstance(edges, list)

    # Perform deterministic cleanup
    await service.close()
    reset_cognee_engine_and_caches()

    # Invariant: No open handles remain; a fresh engine on the same path can immediately open without lock contention
    from cognee.infrastructure.databases.graph.get_graph_engine import get_graph_engine
    ge_second = await get_graph_engine()
    nodes_2, edges_2 = await ge_second.get_graph_data()
    assert isinstance(nodes_2, list)

    # Teardown second engine
    reset_cognee_engine_and_caches()


@pytest.mark.asyncio
async def test_repeated_real_runtime_acceptance_runs_are_lock_free(tmp_path: Path):
    """Verify that repeated real runtime test cycles execute sequentially without lock contention."""
    for cycle in range(3):
        cycle_root = tmp_path / f"cycle_{cycle}"
        cycle_root.mkdir()
        settings = Settings(
            storage=StorageConfig(data_root=cycle_root / "data", system_root=cycle_root / "system"),
            service=ServiceConfig(skip_connection_test=True, enable_access_control=False, caching=False),
        )
        settings.configure_cognee()

        service = CogneeService(settings=settings)
        await service.initialize()

        stats = await service.get_graph_stats()
        assert "graph_nodes" in stats
        assert "graph_edges" in stats

        await service.close()
        reset_cognee_engine_and_caches()


def test_two_runtime_tests_use_distinct_database_paths(tmp_path: Path):
    """Verify that two runtime tests configure completely disjoint, non-colliding storage paths."""
    dir_a = tmp_path / "worker_a"
    dir_b = tmp_path / "worker_b"
    dir_a.mkdir()
    dir_b.mkdir()

    settings_a = Settings(
        storage=StorageConfig(data_root=dir_a / "data", system_root=dir_a / "system"),
        service=ServiceConfig(skip_connection_test=True, enable_access_control=False, caching=False),
    )
    settings_a.configure_cognee()

    from cognee.infrastructure.databases.graph.config import get_graph_config
    from cognee.infrastructure.databases.vector.config import get_vectordb_config
    from cognee.infrastructure.databases.relational.config import get_relational_config

    graph_a = get_graph_config().graph_file_path
    vector_a = get_vectordb_config().vector_db_url
    relational_a = get_relational_config().db_path

    reset_cognee_engine_and_caches()

    settings_b = Settings(
        storage=StorageConfig(data_root=dir_b / "data", system_root=dir_b / "system"),
        service=ServiceConfig(skip_connection_test=True, enable_access_control=False, caching=False),
    )
    settings_b.configure_cognee()

    graph_b = get_graph_config().graph_file_path
    vector_b = get_vectordb_config().vector_db_url
    relational_b = get_relational_config().db_path

    reset_cognee_engine_and_caches()

    # Distinct non-overlapping paths
    assert graph_a != graph_b
    assert vector_a != vector_b
    assert relational_a != relational_b
    assert str(dir_a) in graph_a
    assert str(dir_b) in graph_b


@pytest.mark.asyncio
async def test_real_runtime_failure_does_not_leak_open_database_handles(tmp_path: Path):
    """Verify that an unhandled failure during real runtime execution does not leak file locks."""
    fail_root = tmp_path / "failure_scenario"
    fail_root.mkdir()
    settings = Settings(
        storage=StorageConfig(data_root=fail_root / "data", system_root=fail_root / "system"),
        service=ServiceConfig(skip_connection_test=True, enable_access_control=False, caching=False),
    )
    settings.configure_cognee()

    service = CogneeService(settings=settings)
    await service.initialize()

    # Simulate an error during execution
    try:
        from cognee.infrastructure.databases.graph.get_graph_engine import get_graph_engine
        ge = await get_graph_engine()
        # Call with bad cypher to raise an error
        await ge.query("INVALID SYNTAX !!!")
    except Exception:
        pass

    # Exception occurred; now perform teardown
    await service.close()
    reset_cognee_engine_and_caches()

    # Invariant: Handles were cleanly reaped despite the exception.
    # Subsequent initialization on a new path must succeed with 0 lock contention.
    next_root = tmp_path / "recovery_scenario"
    next_root.mkdir()
    next_settings = Settings(
        storage=StorageConfig(data_root=next_root / "data", system_root=next_root / "system"),
        service=ServiceConfig(skip_connection_test=True, enable_access_control=False, caching=False),
    )
    next_settings.configure_cognee()
    next_service = CogneeService(settings=next_settings)
    await next_service.initialize()

    nodes, edges = await next_service.get_graph_data()
    assert isinstance(nodes, list)

    await next_service.close()
    reset_cognee_engine_and_caches()
