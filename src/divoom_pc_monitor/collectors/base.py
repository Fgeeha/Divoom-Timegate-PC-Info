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


class BaseCollector(ABC):
    @abstractmethod
    def collect(self) -> Metrics:
        """Collect current system metrics and return them."""
        ...
