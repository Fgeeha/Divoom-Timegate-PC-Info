"""Linux telemetry collector using psutil and optional nvidia-smi."""

import logging
import subprocess
import time
from typing import Optional

import psutil

from .base import BaseCollector, Metrics

logger = logging.getLogger(__name__)

_CPU_TEMP_KEYS = ("coretemp", "k10temp", "zenpower", "cpu_thermal", "cpu-thermal")
_CPU_TEMP_LABELS = ("Package id 0", "Tdie", "Tccd1", "CPU", "")


class LinuxCollector(BaseCollector):
    def __init__(self) -> None:
        psutil.cpu_percent(interval=None)  # discard first dummy reading
        self._prev_net = psutil.net_io_counters()
        self._prev_time = time.monotonic()

    def collect(self) -> Metrics:
        cpu_pct = psutil.cpu_percent(interval=None)
        cpu_temp = self._get_cpu_temp()
        mem = psutil.virtual_memory()
        net_up, net_down = self._get_net_speeds()
        gpu_pct, gpu_temp = self._get_nvidia_gpu()

        return Metrics(
            cpu_pct=cpu_pct,
            cpu_temp=cpu_temp,
            gpu_pct=gpu_pct,
            gpu_temp=gpu_temp,
            ram_used_gb=mem.used / 1024**3,
            ram_pct=mem.percent,
            net_up_mbps=net_up,
            net_down_mbps=net_down,
        )

    def _get_cpu_temp(self) -> Optional[float]:
        try:
            temps = psutil.sensors_temperatures()
        except AttributeError:
            return None  # Windows stub or missing sensor support

        for key in _CPU_TEMP_KEYS:
            if key not in temps:
                continue
            entries = temps[key]
            # Prefer package/die sensors; fall back to all
            preferred = [e.current for e in entries if e.label in _CPU_TEMP_LABELS]
            values = preferred or [e.current for e in entries]
            if values:
                return max(values)
        return None

    def _get_net_speeds(self) -> tuple[float, float]:
        current = psutil.net_io_counters()
        now = time.monotonic()
        elapsed = max(now - self._prev_time, 1e-3)
        up = (current.bytes_sent - self._prev_net.bytes_sent) / elapsed / 1024**2
        down = (current.bytes_recv - self._prev_net.bytes_recv) / elapsed / 1024**2
        self._prev_net = current
        self._prev_time = now
        return max(0.0, up), max(0.0, down)

    def _get_nvidia_gpu(self) -> tuple[Optional[float], Optional[float]]:
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu,temperature.gpu",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split(",")
                if len(parts) == 2:
                    return float(parts[0].strip()), float(parts[1].strip())
        except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
            pass
        return None, None
