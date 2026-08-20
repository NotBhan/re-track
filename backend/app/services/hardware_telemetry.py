"""Hardware telemetry adapter implementing HardwareTelemetryPort."""

import json
import logging
from pathlib import Path
import subprocess
from typing import Optional

from app.application.ports.hardware_telemetry import (
    HardwareTelemetry,
    HardwareTelemetryPort,
)

logger = logging.getLogger(__name__)


class LocalHardwareTelemetryAdapter(HardwareTelemetryPort):
    """Local OS hardware telemetry collector for RAM, CPU, VRAM, and GPU detection."""

    def get_telemetry(self) -> HardwareTelemetry:
        """Sample current hardware resource utilization."""
        ram_total = 0.0
        ram_used = 0.0
        cpu_pct = 0.0

        try:
            import psutil
            mem = psutil.virtual_memory()
            ram_total = round(mem.total / (1024 ** 3), 1)
            ram_used = round(mem.used / (1024 ** 3), 1)
            cpu_pct = round(psutil.cpu_percent(interval=None), 1)
        except Exception as exc:
            logger.debug("Failed to read system memory/cpu via psutil: %s", exc)

        vram_total = 0.0
        vram_used = 0.0
        gpu_name: Optional[str] = None

        # 1. Try Linux sysfs DRM mem_info (AMD Radeon / Intel / generic DRM drivers)
        try:
            for card in sorted(Path("/sys/class/drm").glob("card*")):
                vram_tot_f = card / "device" / "mem_info_vram_total"
                vram_used_f = card / "device" / "mem_info_vram_used"
                if vram_tot_f.exists() and vram_used_f.exists():
                    tot = int(vram_tot_f.read_text().strip()) / (1024 ** 3)
                    used = int(vram_used_f.read_text().strip()) / (1024 ** 3)
                    if tot > vram_total:
                        vram_total = round(tot, 1)
                        vram_used = round(used, 1)
                        gpu_name = "AMD Radeon GPU"
        except Exception:
            pass

        # 2. Try nvidia-smi if not already detected
        if vram_total == 0:
            try:
                res = subprocess.run(
                    [
                        "nvidia-smi",
                        "--query-gpu=memory.total,memory.used,name",
                        "--format=csv,noheader,nounits",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                if res.returncode == 0 and res.stdout.strip():
                    parts = res.stdout.strip().split("\n")[0].split(",")
                    if len(parts) >= 3:
                        vram_total = round(float(parts[0].strip()) / 1024, 1)
                        vram_used = round(float(parts[1].strip()) / 1024, 1)
                        gpu_name = parts[2].strip()
            except Exception:
                pass

        # 3. Try rocm-smi as fallback
        if vram_total == 0:
            try:
                res = subprocess.run(
                    ["rocm-smi", "--showmeminfo", "vram", "--json"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                if res.returncode == 0:
                    data = json.loads(res.stdout)
                    for k, v in data.items():
                        if "VRAM Total Memory (B)" in v and "VRAM Total Used Memory (B)" in v:
                            tot = int(v["VRAM Total Memory (B)"]) / (1024 ** 3)
                            used = int(v["VRAM Total Used Memory (B)"]) / (1024 ** 3)
                            if tot > vram_total:
                                vram_total = round(tot, 1)
                                vram_used = round(used, 1)
                                gpu_name = "AMD ROCm GPU"
            except Exception:
                pass

        return HardwareTelemetry(
            ram_total_gb=ram_total,
            ram_used_gb=ram_used,
            cpu_percent=cpu_pct,
            vram_total_gb=vram_total,
            vram_used_gb=vram_used,
            gpu_name=gpu_name,
        )
