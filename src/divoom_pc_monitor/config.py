"""Configuration loading: TOML file → env vars → CLI overrides → defaults."""

import logging
import os
import socket
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class DeviceConfig:
    ip: str = ""
    autodiscover: bool = True


@dataclass
class ServerConfig:
    listen_host: str = ""
    listen_port: int = 3380


@dataclass
class MonitorConfig:
    update_interval: int = 1


@dataclass
class AppConfig:
    device: DeviceConfig
    server: ServerConfig
    monitor: MonitorConfig

    def __init__(self) -> None:
        self.device = DeviceConfig()
        self.server = ServerConfig()
        self.monitor = MonitorConfig()


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

    if config_path is not None and config_path.exists():
        with open(config_path, "rb") as fh:
            raw = tomllib.load(fh)
        _apply_toml(cfg, raw)
        logger.debug("Loaded config from %s", config_path)

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

    srv = raw.get("server", {})
    cfg.server.listen_host = str(srv.get("listen_host", cfg.server.listen_host))
    cfg.server.listen_port = int(srv.get("listen_port", cfg.server.listen_port))

    mon = raw.get("monitor", {})
    raw_interval = int(mon.get("update_interval", cfg.monitor.update_interval))
    cfg.monitor.update_interval = max(1, raw_interval)


def _apply_env(cfg: AppConfig) -> None:
    if val := os.environ.get("DIVOOM_DEVICE_IP"):
        cfg.device.ip = val
    if val := os.environ.get("DIVOOM_SERVER_HOST"):
        cfg.server.listen_host = val
    if val := os.environ.get("DIVOOM_SERVER_PORT"):
        cfg.server.listen_port = int(val)
