"""Tests for configuration loading."""

from pathlib import Path

from divoom_pc_monitor.config import apply_cli_overrides, load_config


def test_defaults():
    cfg = load_config()
    assert cfg.server.listen_port == 3380
    assert cfg.monitor.update_interval == 1
    assert cfg.device.autodiscover is True
    assert cfg.device.ip == ""


def test_load_from_toml(tmp_path: Path):
    toml = (
        '[device]\nip = "192.168.1.200"\nautodiscover = false\n'
        "[server]\nlisten_host = \"192.168.1.10\"\nlisten_port = 9090\n"
        "[monitor]\nupdate_interval = 5\n"
    )
    config_file = tmp_path / "config.toml"
    config_file.write_text(toml)
    cfg = load_config(config_file)
    assert cfg.device.ip == "192.168.1.200"
    assert cfg.device.autodiscover is False
    assert cfg.server.listen_host == "192.168.1.10"
    assert cfg.server.listen_port == 9090
    assert cfg.monitor.update_interval == 5


def test_missing_config_file_uses_defaults(tmp_path: Path):
    cfg = load_config(tmp_path / "nonexistent.toml")
    assert cfg.server.listen_port == 3380


def test_env_overrides_device_ip(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DIVOOM_DEVICE_IP", "10.0.0.42")
    cfg = load_config()
    assert cfg.device.ip == "10.0.0.42"


def test_env_overrides_server_port(monkeypatch):
    monkeypatch.setenv("DIVOOM_SERVER_PORT", "8888")
    cfg = load_config()
    assert cfg.server.listen_port == 8888


def test_cli_overrides():
    cfg = load_config()
    cfg = apply_cli_overrides(cfg, device_ip="10.0.0.1", server_port=7777)
    assert cfg.device.ip == "10.0.0.1"
    assert cfg.server.listen_port == 7777


def test_cli_none_does_not_override():
    cfg = load_config()
    original_port = cfg.server.listen_port
    cfg = apply_cli_overrides(cfg, device_ip=None, server_port=None)
    assert cfg.server.listen_port == original_port


def test_update_interval_minimum_enforced(tmp_path: Path):
    toml = "[monitor]\nupdate_interval = 0\n"
    (tmp_path / "c.toml").write_text(toml)
    cfg = load_config(tmp_path / "c.toml")
    assert cfg.monitor.update_interval >= 1
