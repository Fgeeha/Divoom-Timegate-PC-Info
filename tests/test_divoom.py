"""Tests for Divoom client and layout builder."""

import itertools
from unittest.mock import MagicMock, patch

import requests  # noqa: I001
from PIL import Image

from divoom_pc_monitor.divoom.background import bg_filename, build_backgrounds
from divoom_pc_monitor.divoom.client import DivoomClient
from divoom_pc_monitor.divoom.layout import (
    DISPLAY_ITEMS,
    HEADER_H,
    SCREENS,
    bar,
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
    resp.text = "Request data illegal json"
    resp.json.side_effect = ValueError("No JSON object")
    resp.raise_for_status = MagicMock()
    with patch("requests.Session.post", return_value=resp):
        client = DivoomClient("192.168.1.100")
        assert client.post({"bad": "payload"}) is False


def test_client_injects_token_when_set():
    mock_resp = _make_response({"error_code": 0})
    with patch("requests.Session.post", return_value=mock_resp) as mock_post:
        client = DivoomClient("192.168.1.100", token="secret123")
        assert client.post({"Command": "Draw/Test"}) is True
        _, kwargs = mock_post.call_args
        assert kwargs["json"]["DeviceToken"] == "secret123"
        assert kwargs["json"]["Command"] == "Draw/Test"


def test_client_no_token_field_when_none():
    """token=None (default) → DeviceToken field must NOT be in payload."""
    mock_resp = _make_response({"error_code": 0})
    with patch("requests.Session.post", return_value=mock_resp) as mock_post:
        client = DivoomClient("192.168.1.100")  # token=None by default
        client.post({"Command": "Draw/Test"})
        _, kwargs = mock_post.call_args
        assert "DeviceToken" not in kwargs["json"]


def test_client_sends_empty_token_field():
    """token="" → DeviceToken: "" IS sent (some firmware needs the field present)."""
    mock_resp = _make_response({"error_code": 0})
    with patch("requests.Session.post", return_value=mock_resp) as mock_post:
        client = DivoomClient("192.168.1.100", token="")
        client.post({"Command": "Draw/Test"})
        _, kwargs = mock_post.call_args
        assert kwargs["json"]["DeviceToken"] == ""


def test_client_string_error_code_returns_false():
    """Firmware returns {"error_code": "DeviceToken is err"} — must be treated as failure."""
    with patch("requests.Session.post",
               return_value=_make_response({"error_code": "DeviceToken is err"})):
        client = DivoomClient("192.168.1.100")
        assert client.post({"Command": "Draw/Test"}) is False


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


# --- Screen geometry and backgrounds ---


def test_items_stay_inside_the_128px_panel():
    for idx, screen in enumerate(SCREENS):
        for it in screen.items:
            assert it.y >= HEADER_H, f"display {idx} slot {it.text_id} under the title band"
            assert it.y + it.height <= 128, f"display {idx} slot {it.text_id} runs off the bottom"
            assert it.x + it.width <= 128, f"display {idx} slot {it.text_id} runs off the right"


def test_items_on_a_screen_do_not_overlap():
    for idx, screen in enumerate(SCREENS):
        for a, b in itertools.combinations(screen.items, 2):
            rows_overlap = a.y < b.y + b.height and b.y < a.y + a.height
            cols_overlap = a.x < b.x + b.width and b.x < a.x + a.width
            assert not (rows_overlap and cols_overlap), (
                f"display {idx}: slots {a.text_id} and {b.text_id} overlap"
            )


def test_bar_encodes_percentage():
    assert bar(0) == "[----------]"
    assert bar(100) == "[##########]"
    assert bar(50) == "[#####-----]"
    assert bar(None) == "[??????????]"
    assert bar(150) == "[##########]", "out-of-range input must clamp, not overflow"
    assert bar(-5) == "[----------]"
    assert all(len(bar(p)) == 12 for p in range(0, 101))


def test_backgrounds_render_one_gif_per_display(tmp_path):
    build_backgrounds(tmp_path)
    for idx in range(len(SCREENS)):
        path = tmp_path / bg_filename(idx)
        assert path.exists(), f"no background for display {idx}"
        with Image.open(path) as img:
            assert img.size == (128, 128)
