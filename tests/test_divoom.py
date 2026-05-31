"""Tests for Divoom client and layout builder."""

from unittest.mock import MagicMock, patch

import requests  # noqa: I001

from divoom_pc_monitor.divoom.client import DivoomClient
from divoom_pc_monitor.divoom.layout import (
    DISPLAY_ITEMS,
    build_layout_command,
)

# --- DivoomClient tests ---


def _make_response(json_data: dict, content_type: str = "application/json") -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = json_data
    resp.headers = {"Content-Type": content_type}
    resp.raise_for_status = MagicMock()
    return resp


def test_client_success():
    with patch("requests.Session.post", return_value=_make_response({"error_code": 0})):
        client = DivoomClient("192.168.1.100")
        assert client.post({"Command": "test"}) is True


def test_client_device_error():
    with patch("requests.Session.post", return_value=_make_response({"error_code": 1})):
        client = DivoomClient("192.168.1.100")
        assert client.post({"Command": "test"}) is False


def test_client_network_error():
    with patch("requests.Session.post", side_effect=requests.RequestException("timeout")):
        client = DivoomClient("192.168.1.100")
        assert client.post({"Command": "test"}) is False


def test_client_non_json_response():
    resp = MagicMock()
    resp.headers = {"Content-Type": "text/plain"}
    resp.text = "Request data illegal json"
    resp.raise_for_status = MagicMock()
    with patch("requests.Session.post", return_value=resp):
        client = DivoomClient("192.168.1.100")
        assert client.post({"bad": "payload"}) is False


# --- Layout tests ---


def test_build_layout_command_structure():
    cmd = build_layout_command(0, "http://10.0.0.1:3380", "http://10.0.0.1:3380/images/bg.gif")
    assert cmd["Command"] == "Draw/SendHttpItemList"
    assert cmd["LcdIndex"] == 0
    assert cmd["NewFlag"] == 1
    assert "BackgroudGif" in cmd  # firmware typo must be preserved
    assert isinstance(cmd["ItemList"], list)
    assert len(cmd["ItemList"]) > 0


def test_all_items_use_internet_text_type():
    server_url = "http://192.168.1.10:3380"
    bg_url = f"{server_url}/images/bg.gif"
    for idx in range(len(DISPLAY_ITEMS)):
        cmd = build_layout_command(idx, server_url, bg_url)
        for item in cmd["ItemList"]:
            assert item["type"] == 23, f"Display {idx} has non-internet-text item"


def test_all_items_have_minimum_update_time():
    server_url = "http://192.168.1.10:3380"
    bg_url = f"{server_url}/images/bg.gif"
    for idx in range(len(DISPLAY_ITEMS)):
        cmd = build_layout_command(idx, server_url, bg_url)
        for item in cmd["ItemList"]:
            assert item["update_time"] >= 1, f"update_time < 1 on display {idx}"


def test_item_text_string_contains_server_url():
    server_url = "http://10.0.0.1:3380"
    cmd = build_layout_command(0, server_url, f"{server_url}/images/bg.gif")
    for item in cmd["ItemList"]:
        assert server_url in item["TextString"]


def test_five_displays_defined():
    assert len(DISPLAY_ITEMS) == 5


def test_each_display_has_at_least_one_item():
    for idx, items in enumerate(DISPLAY_ITEMS):
        assert len(items) > 0, f"Display {idx} has no items"


def test_bg_gif_url_in_command():
    bg_url = "http://10.0.0.1:3380/images/bg.gif"
    cmd = build_layout_command(0, "http://10.0.0.1:3380", bg_url)
    assert cmd["BackgroudGif"] == bg_url
