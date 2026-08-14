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
    assert "FL 19C" in tc.get("/text/11").json()["DispData"]
    assert "65" in tc.get("/text/12").json()["DispData"]
    assert "5m/s" in tc.get("/text/13").json()["DispData"]
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
    assert "NOISE" in tc.get("/text/19").json()["DispData"]
    assert "--" in tc.get("/text/19").json()["DispData"]


# --- Combined PC row slots (display 0) ---

def test_combined_cpu_row(tmp_path: Path):
    tc = _make_app(Metrics(cpu_pct=45.0, cpu_temp=72.0), tmp_path)
    val = tc.get("/text/20").json()["DispData"]
    assert "CPU" in val and "45" in val and "72" in val


def test_combined_gpu_row_none(tmp_path: Path):
    tc = _make_app(Metrics(), tmp_path)  # gpu fields None
    val = tc.get("/text/21").json()["DispData"]
    assert "GPU" in val and "--" in val


def test_combined_ram_row(tmp_path: Path):
    tc = _make_app(Metrics(ram_pct=60.0, ram_used_gb=8.0), tmp_path)
    val = tc.get("/text/22").json()["DispData"]
    assert "RAM" in val and "60" in val and "8.0" in val


def test_combined_net_rows(tmp_path: Path):
    tc = _make_app(Metrics(net_up_mbps=1.2, net_down_mbps=5.6), tmp_path)
    assert "UP" in tc.get("/text/23").json()["DispData"]
    assert "DN" in tc.get("/text/24").json()["DispData"]


def test_noise_slot_with_level(tmp_path: Path):
    state = MetricsState()
    n = NoiseState()
    n.update(NoiseData(level=42))
    app = create_app(state, WeatherState(), n, tmp_path)
    tc = TestClient(app)
    assert "42" in tc.get("/text/19").json()["DispData"]


# --- Load bars ---

def test_bars_encode_magnitude(tmp_path: Path):
    tc = _make_app(Metrics(cpu_pct=0.0, gpu_pct=50.0, ram_pct=100.0), tmp_path)
    assert tc.get("/text/25").json()["DispData"] == "[----------]"
    assert tc.get("/text/26").json()["DispData"] == "[#####-----]"
    assert tc.get("/text/27").json()["DispData"] == "[##########]"


def test_bar_unknown_value(tmp_path: Path):
    tc = _make_app(Metrics(gpu_pct=None), tmp_path)
    assert tc.get("/text/26").json()["DispData"] == "[??????????]"


def test_noise_bar(tmp_path: Path):
    state = MetricsState()
    ns = NoiseState()
    ns.update(NoiseData(level=30))
    tc = TestClient(create_app(state, WeatherState(), ns, tmp_path))
    assert tc.get("/text/28").json()["DispData"] == "[###-------]"


# --- System detail slots (display 2) ---

def test_disk_and_load_slots(tmp_path: Path):
    tc = _make_app(Metrics(disk_used_gb=412.0, disk_pct=72.0, load_avg=1.42), tmp_path)
    assert tc.get("/text/29").json()["DispData"] == "DISK 72% 412G"
    assert tc.get("/text/30").json()["DispData"] == "[#######---]"
    assert tc.get("/text/32").json()["DispData"] == "LOAD 1.42"


def test_load_slot_unsupported_platform(tmp_path: Path):
    tc = _make_app(Metrics(load_avg=None), tmp_path)
    assert tc.get("/text/32").json()["DispData"] == "LOAD --"


def test_uptime_formats(tmp_path: Path):
    tc = _make_app(Metrics(uptime_s=3 * 86400 + 4 * 3600), tmp_path)
    assert tc.get("/text/31").json()["DispData"] == "UP 3d 04h"
    tc = _make_app(Metrics(uptime_s=5 * 3600 + 7 * 60), tmp_path)
    assert tc.get("/text/31").json()["DispData"] == "UP 05h 07m"


def test_ram_row_drops_decimal_past_10g(tmp_path: Path):
    tc = _make_app(Metrics(ram_pct=77.0, ram_used_gb=100.0), tmp_path)
    assert tc.get("/text/22").json()["DispData"] == "RAM 77% 100G"
    tc = _make_app(Metrics(ram_pct=20.0, ram_used_gb=8.0), tmp_path)
    assert tc.get("/text/22").json()["DispData"] == "RAM 20% 8.0G"


# --- Width budget ---

def test_long_city_is_not_truncated(tmp_path: Path):
    ws = WeatherState()
    ws.update(WeatherData(city="Saint Petersburg"))
    tc = TestClient(create_app(MetricsState(), ws, NoiseState(), tmp_path))
    assert tc.get("/text/15").json()["DispData"] == "Saint Petersburg"


def test_long_description_trims_on_word_boundary(tmp_path: Path):
    ws = WeatherState()
    ws.update(WeatherData(description="light intensity drizzle"))
    tc = TestClient(create_app(MetricsState(), ws, NoiseState(), tmp_path))
    assert tc.get("/text/14").json()["DispData"] == "light intensity"


def test_no_slot_overflows_its_width_at_worst_case():
    """Every formatter, fed extreme values, must fit the slot's narrowest spot.

    Checks `_format_slot` directly rather than the endpoint: `fit()` truncates
    on the way out, so going through HTTP would make this pass unconditionally.
    Guards the whole layout — narrowing a column or lengthening a format string
    cannot silently start clipping numbers on the device.
    """
    from divoom_pc_monitor.divoom.layout import (
        SLOT_CHAR_BUDGET,
        TEXT_WEATHER_CITY,
        TEXT_WEATHER_DESC,
    )
    from divoom_pc_monitor.server import _format_slot

    # City and condition are unbounded free text; trimming those is `fit`'s job.
    unbounded = {TEXT_WEATHER_CITY, TEXT_WEATHER_DESC}

    metrics = Metrics(
        cpu_pct=100.0, cpu_temp=100.0, gpu_pct=100.0, gpu_temp=100.0,
        ram_used_gb=128.0, ram_pct=100.0,
        net_up_mbps=999.9, net_down_mbps=999.9,
        uptime_s=365 * 86400, disk_used_gb=9999.0, disk_pct=100.0, load_avg=99.99,
    )
    weather = WeatherData(
        city="Saint Petersburg", temp=-99.0, feels_like=-99.0, humidity=100,
        pressure=1099, wind_speed=99.0, wind_dir="NNW", description="drizzle",
    )
    noise = NoiseData(level=100)

    for slot_id, budget in SLOT_CHAR_BUDGET.items():
        if slot_id in unbounded:
            continue
        raw = _format_slot(slot_id, metrics, weather, noise, "")
        assert raw is not None, f"slot {slot_id} is placed but has no formatter"
        assert len(raw) <= budget, f"slot {slot_id} overflows: {raw!r} > {budget}ch"
