"""Tests for the FastAPI server endpoints."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from divoom_pc_monitor.collectors.base import (
    Metrics,
    MetricsState,
    NoiseData,
    NoiseState,
    WeatherData,
    WeatherState,
)
from divoom_pc_monitor.server import create_app


def _make_app(metrics: Metrics, tmp_path: Path) -> TestClient:
    state = MetricsState()
    state.update(metrics)
    app = create_app(state, WeatherState(), NoiseState(), tmp_path)
    return TestClient(app)


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    return _make_app(
        Metrics(
            cpu_pct=42.5, cpu_temp=65.0,
            gpu_pct=80.0, gpu_temp=70.0,
            ram_used_gb=8.0, ram_pct=50.0,
            net_up_mbps=1.5, net_down_mbps=10.2,
        ),
        tmp_path,
    )


# --- PC metric slots ---

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


def test_optional_fields_none(tmp_path: Path):
    tc = _make_app(Metrics(cpu_pct=10.0), tmp_path)  # gpu_pct=None, cpu_temp=None
    assert "CPU --C" in tc.get("/text/1").json()["DispData"]
    assert "GPU --%" in tc.get("/text/2").json()["DispData"]
    assert "GPU --C" in tc.get("/text/3").json()["DispData"]


def test_net_speed_kb_format(tmp_path: Path):
    tc = _make_app(Metrics(net_up_mbps=0.5), tmp_path)  # < 1 MB/s → KB/s
    assert "K/s" in tc.get("/text/6").json()["DispData"]


# --- Weather slots ---

def test_weather_slots_no_data(tmp_path: Path):
    """Empty WeatherState returns graceful fallback strings, not 404."""
    tc = _make_app(Metrics(), tmp_path)
    assert tc.get("/text/10").status_code == 200   # TEXT_WEATHER_TEMP
    assert tc.get("/text/10").json()["DispData"] == "--"
    assert tc.get("/text/14").json()["DispData"] == "--"  # TEXT_WEATHER_DESC


def test_weather_slots_with_data(tmp_path: Path):
    state = MetricsState()
    wx = WeatherState()
    wx.update(WeatherData(
        city="Moscow", temp=22.0, feels_like=19.0, humidity=65,
        pressure=1013, wind_speed=5.2, wind_dir="N",
        description="Partly cloudy", unit_symbol="C",
    ))
    app = create_app(state, wx, NoiseState(), tmp_path)
    tc = TestClient(app)

    assert "22C" in tc.get("/text/10").json()["DispData"]
    assert "FL:19C" in tc.get("/text/11").json()["DispData"]
    assert "65" in tc.get("/text/12").json()["DispData"]
    assert "5.2m/s" in tc.get("/text/13").json()["DispData"]
    assert "Partly cloudy" in tc.get("/text/14").json()["DispData"]
    assert "Moscow" in tc.get("/text/15").json()["DispData"]
    assert "1013" in tc.get("/text/16").json()["DispData"]


# --- Time slots ---

def test_time_slots_return_strings(tmp_path: Path):
    tc = _make_app(Metrics(), tmp_path)
    date_val = tc.get("/text/17").json()["DispData"]
    clock_val = tc.get("/text/18").json()["DispData"]
    assert len(date_val) > 0   # e.g. "31 May"
    assert ":" in clock_val    # e.g. "15:48"


# --- Noise slot ---

def test_noise_slot_no_data(tmp_path: Path):
    tc = _make_app(Metrics(), tmp_path)
    assert "NOISE:--" in tc.get("/text/19").json()["DispData"]


def test_noise_slot_with_level(tmp_path: Path):
    state = MetricsState()
    n = NoiseState()
    n.update(NoiseData(level=42))
    app = create_app(state, WeatherState(), n, tmp_path)
    tc = TestClient(app)
    assert "42" in tc.get("/text/19").json()["DispData"]
