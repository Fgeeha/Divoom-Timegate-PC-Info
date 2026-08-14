"""Per-display background GIFs for the Divoom Times Gate.

The device fetches each background once, when the layout is sent, so anything
drawn here is free at runtime — but it also cannot change without re-sending
``Draw/SendHttpItemList`` (which flashes the "Loading" screen). Everything here
is therefore static chrome: a title band, a left accent stripe, and the
separator rules that group the text items above them.
"""

import logging
from pathlib import Path

from PIL import Image, ImageDraw

from .layout import HEADER_H, SCREENS

logger = logging.getLogger(__name__)

SIZE = 128
_STRIPE_W = 3
_BAND_ALPHA = 0.28  # title band is a dimmed accent so white text stays legible
_RULE_ALPHA = 0.35


def bg_filename(lcd_index: int) -> str:
    return f"bg{lcd_index}.gif"


def build_backgrounds(images_dir: Path) -> None:
    """Render one background GIF per display into `images_dir`."""
    for lcd_index, screen in enumerate(SCREENS):
        path = images_dir / bg_filename(lcd_index)
        _render(screen, path)
        logger.debug("Background for display %d: %s", lcd_index, path)


def _render(screen, path: Path) -> None:
    img = Image.new("RGB", (SIZE, SIZE), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    accent = _hex_to_rgb(screen.accent)

    # Title band + left accent stripe
    draw.rectangle([0, 0, SIZE - 1, HEADER_H - 1], fill=_dim(accent, _BAND_ALPHA))
    draw.rectangle([0, 0, _STRIPE_W - 1, SIZE - 1], fill=accent)
    draw.line([(0, HEADER_H - 1), (SIZE - 1, HEADER_H - 1)], fill=accent)
    draw.text((_STRIPE_W + 4, 3), screen.title, fill=accent)

    # Separator rules between item groups
    for y in screen.rules:
        draw.line([(_STRIPE_W + 2, y), (SIZE - 3, y)], fill=_dim(accent, _RULE_ALPHA))

    img.save(path, format="GIF")


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    v = value.lstrip("#")
    return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)


def _dim(rgb: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(int(c * factor) for c in rgb)  # type: ignore[return-value]
