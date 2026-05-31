"""Tests for the FastAPI server endpoints."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from divoom_pc_monitor.collectors.base import Metrics, MetricsState
from divoom_pc_monitor.server import create_app


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    state = MetricsState()
    state.update(
        Metrics(
            cpu_pct=42.5,
            cpu_temp=65.0,
            gpu_pct=80.0,
            gpu_temp=70.0,
            ram_used_gb=8.0,
            ram_pct=50.0,
            net_up_mbps=1.5,
            net_down_mbps=10.2,
        )
    )
    app = create_app(state, tmp_path)
    return TestClient(app)


def test_healthz(client: TestClient):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_text_cpu_load(client: TestClient):
    resp = client.get("/text/0")
    assert resp.status_code == 200
    body = resp.json()
    assert "DispData" in body
    assert "CPU" in body["DispData"]
    assert "42" in body["DispData"]


def test_text_cpu_temp(client: TestClient):
    resp = client.get("/text/1")
    assert resp.status_code == 200
    assert "65" in resp.json()["DispData"]


def test_text_gpu_load(client: TestClient):
    resp = client.get("/text/2")
    assert resp.status_code == 200
    assert "GPU" in resp.json()["DispData"]


def test_text_gpu_temp(client: TestClient):
    resp = client.get("/text/3")
    assert resp.status_code == 200
    assert "70" in resp.json()["DispData"]


def test_text_ram_used(client: TestClient):
    resp = client.get("/text/4")
    assert resp.status_code == 200
    assert "RAM" in resp.json()["DispData"]


def test_text_ram_pct(client: TestClient):
    resp = client.get("/text/5")
    assert resp.status_code == 200
    assert "50" in resp.json()["DispData"]


def test_text_net_up(client: TestClient):
    resp = client.get("/text/6")
    assert resp.status_code == 200
    assert "UP" in resp.json()["DispData"]


def test_text_net_down(client: TestClient):
    resp = client.get("/text/7")
    assert resp.status_code == 200
    assert "DN" in resp.json()["DispData"]


def test_unknown_slot_returns_404(client: TestClient):
    resp = client.get("/text/999")
    assert resp.status_code == 404


def test_optional_fields_none():
    state = MetricsState()
    state.update(Metrics(cpu_pct=10.0))  # gpu_pct=None, cpu_temp=None
    app = create_app(state, Path("/tmp"))
    tc = TestClient(app)

    assert "CPU --C" in tc.get("/text/1").json()["DispData"]
    assert "GPU --%" in tc.get("/text/2").json()["DispData"]
    assert "GPU --C" in tc.get("/text/3").json()["DispData"]


def test_net_speed_kb_format():
    state = MetricsState()
    state.update(Metrics(net_up_mbps=0.5))  # < 1 MB/s -> show as KB/s
    app = create_app(state, Path("/tmp"))
    tc = TestClient(app)
    body = tc.get("/text/6").json()["DispData"]
    assert "K/s" in body
