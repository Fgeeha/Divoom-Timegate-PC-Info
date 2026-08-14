"""Windows telemetry collector using psutil and optional LibreHardwareMonitor."""

import logging
import time
from typing import Optional

import psutil

from .base import BaseCollector, Metrics, system_extras

logger = logging.getLogger(__name__)


class WindowsCollector(BaseCollector):
    def __init__(self) -> None:
        psutil.cpu_percent(interval=None)  # discard first dummy reading
        self._prev_net = psutil.net_io_counters()
        self._prev_time = time.monotonic()
        self._lhm = self._try_init_lhm()

    def _try_init_lhm(self):
        """Connect to LibreHardwareMonitor WMI namespace (optional)."""
        try:
            import wmi  # type: ignore[import-untyped]

            c = wmi.WMI(namespace="root/LibreHardwareMonitor")
            # Verify namespace is accessible
            list(c.Sensor(SensorType="Temperature"))[:1]
            logger.info("LibreHardwareMonitor WMI interface available")
            return c
        except Exception as exc:
            logger.debug("LibreHardwareMonitor not available: %s", exc)
        return None

    def collect(self) -> Metrics:
        cpu_pct = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        net_up, net_down = self._get_net_speeds()
        cpu_temp, gpu_pct, gpu_temp = self._get_lhm_sensors()

        return Metrics(
            cpu_pct=cpu_pct,
            cpu_temp=cpu_temp,
            gpu_pct=gpu_pct,
            gpu_temp=gpu_temp,
            ram_used_gb=mem.used / 1024**3,
            ram_pct=mem.percent,
            net_up_mbps=net_up,
            net_down_mbps=net_down,
            **system_extras(),
        )

    def _get_net_speeds(self) -> tuple[float, float]:
        current = psutil.net_io_counters()
        now = time.monotonic()
        elapsed = max(now - self._prev_time, 1e-3)
        up = (current.bytes_sent - self._prev_net.bytes_sent) / elapsed / 1024**2
        down = (current.bytes_recv - self._prev_net.bytes_recv) / elapsed / 1024**2
        self._prev_net = current
        self._prev_time = now
        return max(0.0, up), max(0.0, down)

    def _get_lhm_sensors(self) -> tuple[Optional[float], Optional[float], Optional[float]]:
        if not self._lhm:
            return None, None, None
        cpu_temp = gpu_pct = gpu_temp = None
        try:
            for sensor in self._lhm.Sensor():
                name: str = sensor.Name.lower()
                stype: str = sensor.SensorType
                val = float(sensor.Value)
                if stype == "Temperature" and "cpu" in name and "package" in name:
                    cpu_temp = val
                elif stype == "Load" and "gpu" in name and "core" in name:
                    gpu_pct = val
                elif stype == "Temperature" and "gpu" in name and "core" in name:
                    gpu_temp = val
        except Exception as exc:
            logger.debug("LHM sensor query failed: %s", exc)
        return cpu_temp, gpu_pct, gpu_temp
