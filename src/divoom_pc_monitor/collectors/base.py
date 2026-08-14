"""Abstract base collector and shared metrics state."""

import os
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import psutil


@dataclass
class Metrics:
    cpu_pct: float = 0.0
    cpu_temp: Optional[float] = None
    gpu_pct: Optional[float] = None
    gpu_temp: Optional[float] = None
    ram_used_gb: float = 0.0
    ram_pct: float = 0.0
    net_up_mbps: float = 0.0
    net_down_mbps: float = 0.0
    uptime_s: float = 0.0
    disk_used_gb: float = 0.0
    disk_pct: float = 0.0
    load_avg: Optional[float] = None  # 1-minute load average; None where unsupported


def system_extras() -> dict:
    """Platform-independent extras shared by every collector (display 2)."""
    try:
        disk = psutil.disk_usage(os.path.abspath(os.sep))
        disk_used_gb, disk_pct = disk.used / 1024**3, disk.percent
    except OSError:
        disk_used_gb, disk_pct = 0.0, 0.0

    try:
        load_avg: Optional[float] = os.getloadavg()[0]
    except (OSError, AttributeError):
        load_avg = None  # Windows without the psutil emulation shim

    return {
        "uptime_s": max(0.0, time.time() - psutil.boot_time()),
        "disk_used_gb": disk_used_gb,
        "disk_pct": disk_pct,
        "load_avg": load_avg,
    }


@dataclass
class WeatherData:
    city: str = ""
    temp: Optional[float] = None
    feels_like: Optional[float] = None
    humidity: Optional[int] = None
    pressure: Optional[int] = None
    wind_speed: Optional[float] = None
    wind_dir: str = ""
    description: str = ""
    unit_symbol: str = "C"


@dataclass
class NoiseData:
    level: Optional[int] = None  # 0–100


class MetricsState:
    """Thread-safe container for the latest collected metrics."""

    def __init__(self) -> None:
        self._metrics: Metrics = Metrics()
        self._lock = threading.Lock()

    def update(self, metrics: Metrics) -> None:
        with self._lock:
            self._metrics = metrics

    def get(self) -> Metrics:
        with self._lock:
            return self._metrics


class WeatherState:
    """Thread-safe container for the latest weather data."""

    def __init__(self) -> None:
        self._data: WeatherData = WeatherData()
        self._lock = threading.Lock()

    def update(self, data: WeatherData) -> None:
        with self._lock:
            self._data = data

    def get(self) -> WeatherData:
        with self._lock:
            return self._data


class NoiseState:
    """Thread-safe container for the latest device noise reading."""

    def __init__(self) -> None:
        self._data: NoiseData = NoiseData()
        self._lock = threading.Lock()

    def update(self, data: NoiseData) -> None:
        with self._lock:
            self._data = data

    def get(self) -> NoiseData:
        with self._lock:
            return self._data


class BaseCollector(ABC):
    @abstractmethod
    def collect(self) -> Metrics:
        """Collect current system metrics and return them."""
        ...
