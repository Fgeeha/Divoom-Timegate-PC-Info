"""Configuration loading: TOML file → env vars → CLI overrides → defaults."""

import logging
import os
import socket
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default search order when no explicit path is given.
_CONFIG_SEARCH = [
    Path.home() / ".divoom-pc-monitor" / "config.toml",
    Path("config.toml"),
]


@dataclass
class DeviceConfig:
    ip: str = ""
    autodiscover: bool = True
    token: str = ""  # DeviceToken required by some firmware versions


@dataclass
class ServerConfig:
    listen_host: str = ""
    listen_port: int = 3380


@dataclass
class MonitorConfig:
    update_interval: int = 1


@dataclass
class WeatherConfig:
    city: str = "London"
    api_key: str = ""           # env: OPENWEATHER_API_KEY
    units: str = "metric"       # metric (°C) or imperial (°F)
    update_interval: int = 600  # seconds between weather refreshes


@dataclass
class DisplayConfig:
    timezone: str = ""  # IANA name, e.g. "Europe/Moscow"; empty = system local


@dataclass
class AppConfig:
    device: DeviceConfig
    server: ServerConfig
    monitor: MonitorConfig
    weather: WeatherConfig
    display: DisplayConfig

    def __init__(self) -> None:
        self.device = DeviceConfig()
        self.server = ServerConfig()
        self.monitor = MonitorConfig()
        self.weather = WeatherConfig()
        self.display = DisplayConfig()


def _detect_lan_ip() -> str:
    """Return the primary LAN IP without sending any packets."""
    for dest in ("10.255.255.255", "8.8.8.8"):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.settimeout(0)
                s.connect((dest, 1))
                return s.getsockname()[0]
        except OSError:
            pass
    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return "0.0.0.0"


def load_config(config_path: Optional[Path] = None) -> AppConfig:
    """Load config from TOML file then apply env var overrides."""
    cfg = AppConfig()

    resolved: Optional[Path] = None
    if config_path is not None:
        if config_path.exists():
            resolved = config_path
    else:
        for candidate in _CONFIG_SEARCH:
            if candidate.exists():
                resolved = candidate
                break

    if resolved is not None:
        with open(resolved, "rb") as fh:
            raw = tomllib.load(fh)
        _apply_toml(cfg, raw)
        logger.debug("Loaded config from %s", resolved)

    _apply_env(cfg)

    if not cfg.server.listen_host:
        cfg.server.listen_host = _detect_lan_ip()
        logger.debug("Auto-detected LAN IP: %s", cfg.server.listen_host)

    return cfg


def apply_cli_overrides(
    cfg: AppConfig,
    device_ip: Optional[str] = None,
    server_host: Optional[str] = None,
    server_port: Optional[int] = None,
) -> AppConfig:
    if device_ip:
        cfg.device.ip = device_ip
    if server_host:
        cfg.server.listen_host = server_host
    if server_port is not None:
        cfg.server.listen_port = server_port
    return cfg


def _apply_toml(cfg: AppConfig, raw: dict) -> None:
    dev = raw.get("device", {})
    cfg.device.ip = str(dev.get("ip", cfg.device.ip))
    cfg.device.autodiscover = bool(dev.get("autodiscover", cfg.device.autodiscover))
    cfg.device.token = str(dev.get("token", cfg.device.token))

    srv = raw.get("server", {})
    cfg.server.listen_host = str(srv.get("listen_host", cfg.server.listen_host))
    cfg.server.listen_port = int(srv.get("listen_port", cfg.server.listen_port))

    mon = raw.get("monitor", {})
    raw_interval = int(mon.get("update_interval", cfg.monitor.update_interval))
    cfg.monitor.update_interval = max(1, raw_interval)

    wx = raw.get("weather", {})
    cfg.weather.city = str(wx.get("city", cfg.weather.city))
    cfg.weather.api_key = str(wx.get("api_key", cfg.weather.api_key))
    cfg.weather.units = str(wx.get("units", cfg.weather.units))
    cfg.weather.update_interval = max(
        60, int(wx.get("update_interval", cfg.weather.update_interval))
    )

    disp = raw.get("display", {})
    cfg.display.timezone = str(disp.get("timezone", cfg.display.timezone))


def _apply_env(cfg: AppConfig) -> None:
    if val := os.environ.get("DIVOOM_DEVICE_IP"):
        cfg.device.ip = val
    if val := os.environ.get("DIVOOM_DEVICE_TOKEN"):
        cfg.device.token = val
    if val := os.environ.get("DIVOOM_SERVER_HOST"):
        cfg.server.listen_host = val
    if val := os.environ.get("DIVOOM_SERVER_PORT"):
        cfg.server.listen_port = int(val)
    if val := os.environ.get("OPENWEATHER_API_KEY"):
        cfg.weather.api_key = val
    if val := os.environ.get("DIVOOM_TIMEZONE"):
        cfg.display.timezone = val
