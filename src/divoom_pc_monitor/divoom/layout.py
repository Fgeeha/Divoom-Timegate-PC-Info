"""Display layout definitions and command builder for Divoom Times Gate.

Each display (LcdIndex 0-4, 128x128 px) shows a subset of metrics via
internet-text items (type 23). The device polls each TextString URL every
update_time seconds and renders the returned DispData — no "Loading" screen.
"""

from dataclasses import dataclass

# Text slot IDs — map to /text/{id} on our server
TEXT_CPU_LOAD = 0   # e.g. "CPU 45%"
TEXT_CPU_TEMP = 1   # e.g. "CPU 75C"
TEXT_GPU_LOAD = 2   # e.g. "GPU 80%"
TEXT_GPU_TEMP = 3   # e.g. "GPU 65C"
TEXT_RAM_USED = 4   # e.g. "RAM 12.3G"
TEXT_RAM_PCT  = 5   # e.g. "RAM 60%"
TEXT_NET_UP   = 6   # e.g. "UP 1.2M/s"
TEXT_NET_DOWN = 7   # e.g. "DN 5.6M/s"


@dataclass(frozen=True)
class TextItem:
    text_id: int
    x: int
    y: int
    font: int          # See CLAUDE.md §4.4 for font index reference
    width: int         # TextWidth
    height: int        # Textheight
    color: str = "#FFFFFF"
    speed: int = 100   # scroll speed
    direction: int = 0 # 0 = left scroll
    update_time: int = 1  # poll interval in seconds (minimum 1)


def _item_payload(server_url: str, item: TextItem) -> dict:
    return {
        "TextId": item.text_id,
        "type": 23,  # DIVOOM_DISP_CUSTOM_DIAL_SUPPORT_NET_TEXT_MESSAGE
        "x": item.x,
        "y": item.y,
        "dir": item.direction,
        "font": item.font,
        "TextWidth": item.width,
        "Textheight": item.height,
        "TextString": f"{server_url}/text/{item.text_id}",
        "speed": item.speed,
        "color": item.color,
        "update_time": item.update_time,
    }


# Layouts per display (index = LcdIndex).
# Using font 4 (readable alphabetic) for most labels.
# Positioned to center-ish within 128x128.
DISPLAY_ITEMS: list[list[TextItem]] = [
    # Display 0 — CPU
    [
        TextItem(TEXT_CPU_LOAD, x=0, y=52, font=4, width=128, height=20, color="#00FF44"),
        TextItem(TEXT_CPU_TEMP, x=0, y=76, font=4, width=128, height=20, color="#FF8800"),
    ],
    # Display 1 — GPU
    [
        TextItem(TEXT_GPU_LOAD, x=0, y=52, font=4, width=128, height=20, color="#00AAFF"),
        TextItem(TEXT_GPU_TEMP, x=0, y=76, font=4, width=128, height=20, color="#FF4400"),
    ],
    # Display 2 — RAM
    [
        TextItem(TEXT_RAM_USED, x=0, y=52, font=4, width=128, height=20, color="#FFFFFF"),
        TextItem(TEXT_RAM_PCT,  x=0, y=76, font=4, width=128, height=20, color="#AAAAAA"),
    ],
    # Display 3 — Network
    [
        TextItem(TEXT_NET_UP,   x=0, y=52, font=4, width=128, height=20, color="#00FFAA"),
        TextItem(TEXT_NET_DOWN, x=0, y=76, font=4, width=128, height=20, color="#FF00AA"),
    ],
    # Display 4 — Overview (compact, font 2)
    [
        TextItem(TEXT_CPU_LOAD, x=0,  y=20, font=2, width=64, height=16, color="#00FF44"),
        TextItem(TEXT_GPU_LOAD, x=64, y=20, font=2, width=64, height=16, color="#00AAFF"),
        TextItem(TEXT_RAM_PCT,  x=0,  y=44, font=2, width=64, height=16, color="#FFFFFF"),
        TextItem(TEXT_NET_DOWN, x=64, y=44, font=2, width=64, height=16, color="#FF00AA"),
    ],
]


def build_layout_command(lcd_index: int, server_url: str, bg_gif_url: str) -> dict:
    """Build a Draw/SendHttpItemList payload for the given display."""
    items = DISPLAY_ITEMS[lcd_index]
    return {
        "Command": "Draw/SendHttpItemList",
        "LcdIndex": lcd_index,
        "NewFlag": 1,
        "BackgroudGif": bg_gif_url,  # Intentional firmware typo — must match exactly
        "ItemList": [_item_payload(server_url, it) for it in items],
    }
