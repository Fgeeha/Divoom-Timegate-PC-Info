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
    TEXT_CPU_BAR,
    TEXT_CPU_LOAD,
    TEXT_CPU_ROW,
    TEXT_CPU_TEMP,
    TEXT_DISK_BAR,
    TEXT_DISK_ROW,
    TEXT_GPU_BAR,
    TEXT_GPU_LOAD,
    TEXT_GPU_ROW,
    TEXT_GPU_TEMP,
    TEXT_LOADAVG,
    TEXT_NET_DN_ROW,
    TEXT_NET_DOWN,
    TEXT_NET_UP,
    TEXT_NET_UP_ROW,
    TEXT_NOISE,
    TEXT_NOISE_BAR,
    TEXT_RAM_BAR,
    TEXT_RAM_PCT,
    TEXT_RAM_ROW,
    TEXT_RAM_USED,
    TEXT_TIME_CLOCK,
    TEXT_TIME_DATE,
    TEXT_UPTIME,
    TEXT_WEATHER_CITY,
    TEXT_WEATHER_DESC,
    TEXT_WEATHER_FEELS,
    TEXT_WEATHER_HUM,
    TEXT_WEATHER_PRESS,
    TEXT_WEATHER_TEMP,
    TEXT_WEATHER_WIND,
    bar,
    fit,
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
        # Trim centrally: the layout owns the per-slot width budget, so no
        # formatter below needs to hardcode a truncation length.
        return {"DispData": fit(slot_id, text)}

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
    # ── PC metrics (individual slots, used by other displays / API) ──────────
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

    # ── Combined PC rows (display 0) ─────────────────────────────────────────
    if slot_id == TEXT_CPU_ROW:
        temp = f" {m.cpu_temp:.0f}C" if m.cpu_temp is not None else " --C"
        return f"CPU {m.cpu_pct:.0f}%{temp}"

    if slot_id == TEXT_GPU_ROW:
        pct = f"{m.gpu_pct:.0f}%" if m.gpu_pct is not None else "--%"
        temp = f" {m.gpu_temp:.0f}C" if m.gpu_temp is not None else " --C"
        return f"GPU {pct}{temp}"

    if slot_id == TEXT_RAM_ROW:
        # Drop the decimal past 10G — "RAM 77% 100.0G" would overrun font 4
        return f"RAM {m.ram_pct:.0f}% {_fmt_gb(m.ram_used_gb)}"

    if slot_id == TEXT_NET_UP_ROW:
        return f"UP: {_fmt_net(m.net_up_mbps)}"

    if slot_id == TEXT_NET_DN_ROW:
        return f"DN: {_fmt_net(m.net_down_mbps)}"

    # ── Load bars (display 0) ────────────────────────────────────────────────
    if slot_id == TEXT_CPU_BAR:
        return bar(m.cpu_pct)
    if slot_id == TEXT_GPU_BAR:
        return bar(m.gpu_pct)
    if slot_id == TEXT_RAM_BAR:
        return bar(m.ram_pct)

    # ── System detail (display 2) ────────────────────────────────────────────
    if slot_id == TEXT_DISK_ROW:
        return f"DISK {m.disk_pct:.0f}% {_fmt_gb(m.disk_used_gb)}"
    if slot_id == TEXT_DISK_BAR:
        return bar(m.disk_pct)
    if slot_id == TEXT_UPTIME:
        return _fmt_uptime(m.uptime_s)
    if slot_id == TEXT_LOADAVG:
        return f"LOAD {m.load_avg:.2f}" if m.load_avg is not None else "LOAD --"

    # ── Weather ───────────────────────────────────────────────────────────────
    if slot_id == TEXT_WEATHER_TEMP:
        return f"{w.temp:.0f}{w.unit_symbol}" if w.temp is not None else "--"
    if slot_id == TEXT_WEATHER_FEELS:
        return f"FL {w.feels_like:.0f}{w.unit_symbol}" if w.feels_like is not None else "FL --"
    # "H"/"P" short labels: humidity and wind share one 128px row, and
    # "HUM 100%" + "NNW 12m/s" does not fit side by side (see layout.CHAR_PX).
    if slot_id == TEXT_WEATHER_HUM:
        return f"H {w.humidity}%" if w.humidity is not None else "H --"
    if slot_id == TEXT_WEATHER_WIND:
        if w.wind_speed is not None:
            prefix = f"{w.wind_dir} " if w.wind_dir else ""
            return f"{prefix}{w.wind_speed:.0f}m/s"
        return "-- m/s"
    if slot_id == TEXT_WEATHER_DESC:
        return w.description or "--"
    if slot_id == TEXT_WEATHER_CITY:
        return w.city or "--"
    if slot_id == TEXT_WEATHER_PRESS:
        return f"P {w.pressure}hPa" if w.pressure is not None else "P --"

    # ── Date / time ───────────────────────────────────────────────────────────
    if slot_id == TEXT_TIME_DATE:
        now = _get_now(tz)
        return f"{now.day} {now.strftime('%b')}"   # "31 May"
    if slot_id == TEXT_TIME_CLOCK:
        return _get_now(tz).strftime("%H:%M")       # "15:48"

    # ── Noise ─────────────────────────────────────────────────────────────────
    if slot_id == TEXT_NOISE:
        return f"NOISE {n.level}" if n.level is not None else "NOISE --"
    if slot_id == TEXT_NOISE_BAR:
        return bar(float(n.level) if n.level is not None else None)

    return None


def _fmt_gb(gb: float) -> str:
    return f"{gb:.0f}G" if gb >= 10 else f"{gb:.1f}G"


def _fmt_uptime(seconds: float) -> str:
    days, rem = divmod(int(seconds), 86400)
    hours, minutes = divmod(rem // 60, 60)
    if days:
        return f"UP {days}d {hours:02d}h"
    return f"UP {hours:02d}h {minutes:02d}m"


def _fmt_speed(label: str, mbps: float) -> str:
    if mbps >= 1.0:
        return f"{label} {mbps:.1f}M/s"
    return f"{label} {mbps * 1024:.0f}K/s"


def _fmt_net(mbps: float) -> str:
    """Compact network speed without directional label (used in combined rows)."""
    if mbps >= 1.0:
        return f"{mbps:.1f}M/s"
    return f"{mbps * 1024:.0f}K/s"


def _get_now(tz_str: str) -> datetime:
    if tz_str:
        try:
            return datetime.now(ZoneInfo(tz_str))
        except (ZoneInfoNotFoundError, KeyError):
            logger.warning("Unknown timezone %r, falling back to local time", tz_str)
    return datetime.now()
