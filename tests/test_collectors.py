"""Tests for telemetry collectors."""

import sys
import threading

import psutil
import pytest

from divoom_pc_monitor.collectors.base import Metrics, MetricsState


def test_metrics_defaults():
    m = Metrics()
    assert m.cpu_pct == 0.0
    assert m.cpu_temp is None
    assert m.gpu_pct is None
    assert m.gpu_temp is None
    assert m.ram_pct == 0.0


def test_metrics_state_update_and_get():
    state = MetricsState()
    m = Metrics(cpu_pct=55.0, ram_pct=70.0)
    state.update(m)
    result = state.get()
    assert result.cpu_pct == 55.0
    assert result.ram_pct == 70.0


def test_metrics_state_thread_safety():
    state = MetricsState()
    errors = []

    def writer():
        for i in range(100):
            try:
                state.update(Metrics(cpu_pct=float(i)))
            except Exception as exc:
                errors.append(exc)

    def reader():
        for _ in range(100):
            try:
                _ = state.get()
            except Exception as exc:
                errors.append(exc)

    threads = [threading.Thread(target=writer), threading.Thread(target=reader)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors


@pytest.mark.skipif(sys.platform != "linux", reason="Linux collector only")
def test_linux_collector_collect():
    psutil.cpu_percent(interval=0.1)  # warm up
    from divoom_pc_monitor.collectors.linux import LinuxCollector

    c = LinuxCollector()
    m = c.collect()
    assert 0.0 <= m.cpu_pct <= 100.0
    assert 0.0 <= m.ram_pct <= 100.0
    assert m.ram_used_gb >= 0.0
    assert m.net_up_mbps >= 0.0
    assert m.net_down_mbps >= 0.0


@pytest.mark.skipif(sys.platform != "linux", reason="Linux collector only")
def test_linux_collector_net_speeds_non_negative():
    import time  # noqa: PLC0415

    from divoom_pc_monitor.collectors.linux import LinuxCollector

    c = LinuxCollector()
    time.sleep(0.05)
    m = c.collect()
    assert m.net_up_mbps >= 0.0
    assert m.net_down_mbps >= 0.0
