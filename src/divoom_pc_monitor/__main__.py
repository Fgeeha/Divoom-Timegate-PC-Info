"""CLI entry point for the Divoom Times Gate PC monitor."""

import argparse
import logging
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional

import uvicorn

logger = logging.getLogger(__name__)


def main() -> None:
    args = _parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    from divoom_pc_monitor.config import apply_cli_overrides, load_config

    cfg = load_config(args.config)
    cfg = apply_cli_overrides(
        cfg,
        device_ip=args.device_ip,
        server_host=args.server_host,
        server_port=args.server_port,
    )

    server_url = f"http://{cfg.server.listen_host}:{cfg.server.listen_port}"
    logger.info("Server URL (device must reach this): %s", server_url)

    device_ip = _resolve_device_ip(cfg)

    from divoom_pc_monitor.collectors import MetricsState, get_collector
    from divoom_pc_monitor.collectors.base import NoiseState, WeatherState
    from divoom_pc_monitor.collectors.weather import WeatherFetcher

    state = MetricsState()
    weather_state = WeatherState()
    noise_state = NoiseState()
    collector = get_collector()
    images_dir = _prepare_images()

    # Start weather thread immediately so data is ready before the device polls
    weather_fetcher = WeatherFetcher(cfg.weather.city, cfg.weather.api_key, cfg.weather.units)
    _start_weather_thread(weather_fetcher, weather_state, cfg.weather.update_interval)

    from divoom_pc_monitor.server import create_app

    app = create_app(state, weather_state, noise_state, images_dir, cfg.display.timezone)
    _start_server(app, cfg.server.listen_host, cfg.server.listen_port)
    time.sleep(1.0)  # give uvicorn time to bind

    client = None
    saved_channel: Optional[int] = None
    if device_ip:
        from divoom_pc_monitor.divoom.client import DivoomClient
        from divoom_pc_monitor.divoom.noise import NoisePoller

        client = DivoomClient(device_ip, token=cfg.device.token)
        saved_channel = client.get_channel_index()
        _send_layouts(client, server_url, images_dir)
        _start_noise_thread(NoisePoller(device_ip, token=cfg.device.token), noise_state)

    interval = cfg.monitor.update_interval
    logger.info("Collector running (interval=%ds). Press Ctrl+C to stop.", interval)
    try:
        while True:
            try:
                state.update(collector.collect())
            except Exception as exc:
                logger.error("Collector error: %s", exc)
            time.sleep(interval)
    except KeyboardInterrupt:
        pass
    finally:
        _shutdown(client, saved_channel)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Divoom Times Gate PC monitor — streams system metrics to the device display."
    )
    p.add_argument(
        "--config",
        type=Path,
        default=None,
        metavar="FILE",
        help="Path to config.toml (default: ~/.divoom-pc-monitor/config.toml or ./config.toml)",
    )
    p.add_argument("--device-ip", metavar="IP", help="Device IP (overrides config/env)")
    p.add_argument("--server-host", metavar="HOST", help="Listen host (overrides config)")
    p.add_argument("--server-port", metavar="PORT", type=int, help="Listen port (overrides config)")
    p.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO)",
    )
    return p.parse_args()


def _resolve_device_ip(cfg) -> Optional[str]:
    if cfg.device.ip:
        return cfg.device.ip
    if cfg.device.autodiscover:
        logger.info("Auto-discovering Divoom device...")
        from divoom_pc_monitor.divoom.discovery import discover_device

        ip = discover_device()
        if ip:
            return ip
    logger.warning(
        "Divoom device IP not configured. Set it via one of:\n"
        "  --device-ip <IP>              (CLI flag)\n"
        "  DIVOOM_DEVICE_IP=<IP>         (environment variable)\n"
        "  [device] ip = '<IP>'          (config.toml)\n"
        "  [device] autodiscover = true  (cloud auto-discovery)\n"
        "The metric server is still running — you can configure the device later."
    )
    return None


def _prepare_images() -> Path:
    images_dir = Path(tempfile.mkdtemp(prefix="divoom-images-"))
    bg_path = images_dir / "bg.gif"
    _create_black_gif(bg_path, size=128)
    logger.debug("Background GIF: %s", bg_path)
    return images_dir


def _create_black_gif(path: Path, size: int = 128) -> None:
    try:
        from PIL import Image

        img = Image.new("RGB", (size, size), (0, 0, 0))
        img.save(path, format="GIF")
    except ImportError:
        # Minimal valid 1×1 black GIF — firmware will scale or ignore mismatch
        path.write_bytes(
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00"
            b"\x00\x00\x00\xff\xff\xff"
            b"!\xf9\x04\x00\x00\x00\x00\x00"
            b",\x00\x00\x00\x00\x01\x00\x01\x00\x00"
            b"\x02\x02D\x01\x00;"
        )


def _start_server(app, host: str, port: int) -> None:
    thread = threading.Thread(
        target=uvicorn.run,
        kwargs={
            "app": app, "host": host, "port": port,
            "log_level": "warning", "access_log": False,
        },
        daemon=True,
    )
    thread.start()
    logger.info("HTTP server started on %s:%d", host, port)


def _send_layouts(client, server_url: str, images_dir: Path) -> None:
    from divoom_pc_monitor.divoom.layout import DISPLAY_ITEMS, build_layout_command

    bg_url = f"{server_url}/images/bg.gif"
    for lcd_index in range(len(DISPLAY_ITEMS)):
        payload = build_layout_command(lcd_index, server_url, bg_url)
        ok = client.post(payload)
        status = "OK" if ok else "FAILED"
        logger.info("Layout → display %d: %s", lcd_index, status)
        # Avoid flooding the device (§4.5 of CLAUDE.md)
        time.sleep(0.5)


def _shutdown(client, saved_channel: Optional[int]) -> None:
    """Restore device state and close the client, immune to further KeyboardInterrupt."""
    import signal as _signal

    try:
        _signal.signal(_signal.SIGINT, _signal.SIG_IGN)
    except (OSError, ValueError):
        pass

    if client is None:
        return
    try:
        if saved_channel is not None:
            print(f"\nRestoring display channel {saved_channel} ...", flush=True)
            client.set_channel_index(saved_channel)
    except BaseException:
        pass
    try:
        client.close()
    except BaseException:
        pass


def _start_weather_thread(fetcher, state, interval: int) -> None:
    def _loop() -> None:
        data = fetcher.fetch()
        if data:
            state.update(data)
        while True:
            time.sleep(interval)
            data = fetcher.fetch()
            if data:
                state.update(data)

    threading.Thread(target=_loop, daemon=True).start()


def _start_noise_thread(poller, state) -> None:
    from divoom_pc_monitor.collectors.base import NoiseData

    def _loop() -> None:
        while True:
            level = poller.poll()
            if level is not None:
                state.update(NoiseData(level=level))
            time.sleep(5)

    threading.Thread(target=_loop, daemon=True).start()


if __name__ == "__main__":
    main()
