"""Abstract base collector and shared metrics state."""

import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


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
