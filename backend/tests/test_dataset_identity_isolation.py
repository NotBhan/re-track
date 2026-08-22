"""Tests for Dataset Identity Isolation and Cross-Repository Data Separation."""

from pathlib import Path
import pytest

from app.application.domain.dataset_identity import derive_dataset_name
from app.application.dto import (
    AgentContextRequest,
    AgentContextResponse,
    IndexRepositoryRequest,
)
from app.application.ports.memory import MemoryDatasetPort, MemoryPort
from app.application.use_cases.context import ContextUseCases
from app.application.use_cases.indexing import IndexingUseCases


class MockMemoryDatasetService(MemoryPort, MemoryDatasetPort):
    """Isolated in-memory memory storage indexed strictly by dataset_name."""

    def __init__(self) -> None:
        self.datasets: dict[str, list[dict]] = {}

    async def cognify(self, dataset_name: str) -> None:
        pass

    async def search(self, dataset_name: str, query: str, top_k: int = 10) -> list[dict]:
        memories = self.datasets.get(dataset_name, [])
        # Simple substring matching
        matches = [m for m in memories if query.lower() in m.get("text", "").lower()]
        return matches[:top_k]

    async def list_datasets(self) -> list[str]:
        return list(self.datasets.keys())

    async def delete_dataset(self, dataset_name: str) -> None:
        self.datasets.pop(dataset_name, None)

    async def add_memory(self, dataset_name: str, memory_id: str, text: str, metadata: dict | None = None) -> None:
        if dataset_name not in self.datasets:
            self.datasets[dataset_name] = []
        self.datasets[dataset_name].append({"id": memory_id, "text": text, "metadata": metadata or {}})


def test_derive_dataset_name_uniqueness_for_same_basename(tmp_path: Path):
    path_work = tmp_path / "work" / "api_service"
    path_personal = tmp_path / "personal" / "api_service"

    path_work.mkdir(parents=True)
    path_personal.mkdir(parents=True)

    dataset_work = derive_dataset_name(path_work)
    dataset_personal = derive_dataset_name(path_personal)

    assert dataset_work != dataset_personal
    assert dataset_work.startswith("api_service_")
    assert dataset_personal.startswith("api_service_")
    assert len(dataset_work) == len("api_service_") + 10


def test_derive_dataset_name_deterministic_for_same_path(tmp_path: Path):
    path_a = tmp_path / "my_project"
    path_a.mkdir(parents=True)

    ds1 = derive_dataset_name(path_a)
    ds2 = derive_dataset_name(path_a)

    assert ds1 == ds2


def test_derive_dataset_name_with_explicit_override(tmp_path: Path):
    path_a = tmp_path / "my_project"
    path_a.mkdir(parents=True)

    ds = derive_dataset_name(path_a, explicit_dataset_name="custom_suite")
    assert ds.startswith("custom_suite_")


@pytest.mark.asyncio
async def test_cross_repository_memory_isolation_and_deletion(tmp_path: Path):
    path_repo1 = tmp_path / "client1" / "service"
    path_repo2 = tmp_path / "client2" / "service"
    path_repo1.mkdir(parents=True)
    path_repo2.mkdir(parents=True)

    ds1 = derive_dataset_name(path_repo1)
    ds2 = derive_dataset_name(path_repo2)

    assert ds1 != ds2

    memory_service = MockMemoryDatasetService()

    # Ingest memories into ds1
    await memory_service.add_memory(
        dataset_name=ds1,
        memory_id="m1",
        text="Client 1 proprietary algorithm: QuantumHash",
        metadata={"file": "algo.py"},
    )

    # Ingest memories into ds2
    await memory_service.add_memory(
        dataset_name=ds2,
        memory_id="m2",
        text="Client 2 proprietary algorithm: SolarSort",
        metadata={"file": "solar.py"},
    )

    # Query ds2 for ds1's secret - must be empty
    results_ds2 = await memory_service.search(dataset_name=ds2, query="QuantumHash")
    assert len(results_ds2) == 0

    # Query ds1 for ds1's secret - must return m1
    results_ds1 = await memory_service.search(dataset_name=ds1, query="QuantumHash")
    assert len(results_ds1) == 1
    assert results_ds1[0]["id"] == "m1"

    # Delete ds1 - must not affect ds2
    await memory_service.delete_dataset(ds1)
    assert ds1 not in await memory_service.list_datasets()
    assert ds2 in await memory_service.list_datasets()

    results_ds2_after = await memory_service.search(dataset_name=ds2, query="SolarSort")
    assert len(results_ds2_after) == 1
    assert results_ds2_after[0]["id"] == "m2"
