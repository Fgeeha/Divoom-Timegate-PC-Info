"""FastAPI server exposing metric text slots and static background images."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from .collectors.base import (
    Metrics,
    MetricsState,
    NoiseData,
    NoiseState,
    WeatherData,
    WeatherState,
)
from .divoom.layout import (
    TEXT_CPU_LOAD,
    TEXT_CPU_TEMP,
    TEXT_GPU_LOAD,
    TEXT_GPU_TEMP,
    TEXT_NET_DOWN,
    TEXT_NET_UP,
    TEXT_NOISE,
    TEXT_RAM_PCT,
    TEXT_RAM_USED,
    TEXT_TIME_CLOCK,
    TEXT_TIME_DATE,
    TEXT_WEATHER_CITY,
    TEXT_WEATHER_DESC,
    TEXT_WEATHER_FEELS,
    TEXT_WEATHER_HUM,
    TEXT_WEATHER_PRESS,
    TEXT_WEATHER_TEMP,
    TEXT_WEATHER_WIND,
)

logger = logging.getLogger(__name__)


def create_app(
    state: MetricsState,
    weather_state: WeatherState,
    noise_state: NoiseState,
    images_dir: Path,
    timezone: str = "",
) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Divoom PC Monitor", docs_url=None, redoc_url=None)

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok"}

    @app.get("/text/{slot_id}")
    def get_text(slot_id: int) -> dict:
        """Return {"DispData": "..."} for the given metric slot."""
        text = _format_slot(
            slot_id, state.get(), weather_state.get(), noise_state.get(), timezone
        )
        if text is None:
            raise HTTPException(status_code=404, detail=f"Unknown slot {slot_id}")
        return {"DispData": text}

    if images_dir.exists():
        app.mount("/images", StaticFiles(directory=str(images_dir)), name="images")

    return app


def _format_slot(
    slot_id: int,
    m: Metrics,
    w: WeatherData,
    n: NoiseData,
    tz: str,
) -> Optional[str]:
    # --- PC metrics ---
    if slot_id == TEXT_CPU_LOAD:
        return f"CPU {m.cpu_pct:.0f}%"
    if slot_id == TEXT_CPU_TEMP:
        return f"CPU {m.cpu_temp:.0f}C" if m.cpu_temp is not None else "CPU --C"
    if slot_id == TEXT_GPU_LOAD:
        return f"GPU {m.gpu_pct:.0f}%" if m.gpu_pct is not None else "GPU --%"
    if slot_id == TEXT_GPU_TEMP:
        return f"GPU {m.gpu_temp:.0f}C" if m.gpu_temp is not None else "GPU --C"
    if slot_id == TEXT_RAM_USED:
        return f"RAM {m.ram_used_gb:.1f}G"
    if slot_id == TEXT_RAM_PCT:
        return f"RAM {m.ram_pct:.0f}%"
    if slot_id == TEXT_NET_UP:
        return _fmt_speed("UP", m.net_up_mbps)
    if slot_id == TEXT_NET_DOWN:
        return _fmt_speed("DN", m.net_down_mbps)

    # --- Weather ---
    if slot_id == TEXT_WEATHER_TEMP:
        return f"{w.temp:.0f}{w.unit_symbol}" if w.temp is not None else "--"
    if slot_id == TEXT_WEATHER_FEELS:
        return f"FL:{w.feels_like:.0f}{w.unit_symbol}" if w.feels_like is not None else "FL:--"
    if slot_id == TEXT_WEATHER_HUM:
        return f"HUM:{w.humidity}%" if w.humidity is not None else "HUM:--%"
    if slot_id == TEXT_WEATHER_WIND:
        if w.wind_speed is not None:
            prefix = f"{w.wind_dir} " if w.wind_dir else ""
            return f"{prefix}{w.wind_speed:.1f}m/s"
        return "--m/s"
    if slot_id == TEXT_WEATHER_DESC:
        return w.description[:16] if w.description else "--"
    if slot_id == TEXT_WEATHER_CITY:
        return w.city[:14] if w.city else "--"
    if slot_id == TEXT_WEATHER_PRESS:
        return f"{w.pressure}hPa" if w.pressure is not None else "--hPa"

    # --- Date / time ---
    if slot_id == TEXT_TIME_DATE:
        now = _get_now(tz)
        return f"{now.day} {now.strftime('%b')}"   # "31 May"
    if slot_id == TEXT_TIME_CLOCK:
        return _get_now(tz).strftime("%H:%M")       # "15:48"

    # --- Noise ---
    if slot_id == TEXT_NOISE:
        return f"NOISE:{n.level}" if n.level is not None else "NOISE:--"

    return None


def _fmt_speed(label: str, mbps: float) -> str:
    if mbps >= 1.0:
        return f"{label} {mbps:.1f}M/s"
    return f"{label} {mbps * 1024:.0f}K/s"


def _get_now(tz_str: str) -> datetime:
    if tz_str:
        try:
            return datetime.now(ZoneInfo(tz_str))
        except (ZoneInfoNotFoundError, KeyError):
            logger.warning("Unknown timezone %r, falling back to local time", tz_str)
    return datetime.now()
