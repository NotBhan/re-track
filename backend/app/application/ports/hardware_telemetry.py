"""Abstract hardware telemetry port for system resource monitoring."""

from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass
class HardwareTelemetry:
    """Snapshot of system hardware resource utilization."""

    ram_total_gb: float
    ram_used_gb: float
    cpu_percent: float
    vram_total_gb: float
    vram_used_gb: float
    gpu_name: Optional[str] = None


class HardwareTelemetryPort(Protocol):
    """Port for sampling system RAM, CPU, VRAM, and GPU utilization."""

    def get_telemetry(self) -> HardwareTelemetry:
        """Sample current hardware telemetry metrics."""
        ...
