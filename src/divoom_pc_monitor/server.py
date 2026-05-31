"""FastAPI server exposing metric text slots and static background images."""

import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from .collectors.base import Metrics, MetricsState
from .divoom.layout import (
    TEXT_CPU_LOAD,
    TEXT_CPU_TEMP,
    TEXT_GPU_LOAD,
    TEXT_GPU_TEMP,
    TEXT_NET_DOWN,
    TEXT_NET_UP,
    TEXT_RAM_PCT,
    TEXT_RAM_USED,
)

logger = logging.getLogger(__name__)


def create_app(state: MetricsState, images_dir: Path) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Divoom PC Monitor", docs_url=None, redoc_url=None)

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok"}

    @app.get("/text/{slot_id}")
    def get_text(slot_id: int) -> dict:
        """Return {"DispData": "..."} for the given metric slot."""
        text = _format_slot(slot_id, state.get())
        if text is None:
            raise HTTPException(status_code=404, detail=f"Unknown slot {slot_id}")
        return {"DispData": text}

    if images_dir.exists():
        app.mount("/images", StaticFiles(directory=str(images_dir)), name="images")

    return app


def _format_slot(slot_id: int, m: Metrics) -> Optional[str]:
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
    return None


def _fmt_speed(label: str, mbps: float) -> str:
    if mbps >= 1.0:
        return f"{label} {mbps:.1f}M/s"
    return f"{label} {mbps * 1024:.0f}K/s"
