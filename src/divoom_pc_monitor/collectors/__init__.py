"""Telemetry collector factory."""

import sys

from .base import BaseCollector, Metrics, MetricsState


def get_collector() -> BaseCollector:
    """Return the appropriate collector for the current platform."""
    if sys.platform.startswith("linux"):
        from .linux import LinuxCollector

        return LinuxCollector()
    if sys.platform == "win32":
        from .windows import WindowsCollector

        return WindowsCollector()
    raise RuntimeError(
        f"Unsupported platform: {sys.platform!r}. "
        "Only Linux and Windows are supported."
    )


__all__ = ["get_collector", "BaseCollector", "Metrics", "MetricsState"]
