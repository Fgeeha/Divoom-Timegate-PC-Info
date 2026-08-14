"""Display layout definitions and command builder for Divoom Times Gate.

Layout (5 displays, 128×128 px each):
  Display 0 — SYSTEM : CPU / GPU / RAM, each as a value row plus a load bar
  Display 1 — WEATHER: city, temp, feels-like, condition, humidity, wind, pressure
  Display 2 — DETAIL : network up/down, disk usage + bar, uptime, load average
  Display 3 — TIME   : big clock, date, city, condition
  Display 4 — NOISE  : clock, date, city+temp, device mic level + bar

Each display also gets its own background GIF (see ``divoom/background.py``),
which draws the title band and the separator rules listed in ``SCREENS``.
"""

from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Text slot IDs — map to GET /text/{id} on our FastAPI server
# ---------------------------------------------------------------------------

# PC metrics (0–7)
TEXT_CPU_LOAD = 0
TEXT_CPU_TEMP = 1
TEXT_GPU_LOAD = 2
TEXT_GPU_TEMP = 3
TEXT_RAM_USED = 4
TEXT_RAM_PCT  = 5
TEXT_NET_UP   = 6
TEXT_NET_DOWN = 7

# Weather (10–16)
TEXT_WEATHER_TEMP  = 10
TEXT_WEATHER_FEELS = 11
TEXT_WEATHER_HUM   = 12
TEXT_WEATHER_WIND  = 13
TEXT_WEATHER_DESC  = 14
TEXT_WEATHER_CITY  = 15
TEXT_WEATHER_PRESS = 16

# Date / time (17–18)
TEXT_TIME_DATE  = 17
TEXT_TIME_CLOCK = 18

# Noise level from device microphone (19)
TEXT_NOISE = 19

# Combined PC-metric rows for display 0 (one endpoint = one full row)
TEXT_CPU_ROW    = 20  # "CPU 45% 72C"
TEXT_GPU_ROW    = 21  # "GPU 80% 65C"
TEXT_RAM_ROW    = 22  # "RAM 60% 8.0G"
TEXT_NET_UP_ROW = 23  # "UP: 1.2M/s"
TEXT_NET_DN_ROW = 24  # "DN: 5.6M/s"

# Load bars (25–28) — text bars, since the firmware has no progress-bar item
TEXT_CPU_BAR   = 25
TEXT_GPU_BAR   = 26
TEXT_RAM_BAR   = 27
TEXT_NOISE_BAR = 28

# System detail rows for display 2 (29–32)
TEXT_DISK_ROW = 29  # "DISK 62% 410G"
TEXT_DISK_BAR = 30
TEXT_UPTIME   = 31  # "UP 3d 04h"
TEXT_LOADAVG  = 32  # "LOAD 1.42"


# ---------------------------------------------------------------------------
# Character-width budget
# ---------------------------------------------------------------------------
# The firmware exposes no font metrics, so these are calibration constants, not
# facts. They are deliberately generous: overshooting makes a long string scroll
# (ugly but complete), undershooting silently truncates data. If your unit
# scrolls text that should fit, raise the value for that font; if text runs off
# the right edge, lower it.
CHAR_PX: dict[int, float] = {2: 7.5, 4: 9.5, 32: 7.5}
_DEFAULT_CHAR_PX = 8.0


@dataclass(frozen=True)
class TextItem:
    text_id: int
    x: int
    y: int
    font: int           # See CLAUDE.md §4.4 for font index reference
    width: int          # TextWidth
    height: int         # Textheight
    color: str = "#FFFFFF"
    speed: int = 100    # scroll speed
    direction: int = 0  # 0 = left scroll
    update_time: int = 2

    @property
    def max_chars(self) -> int:
        return max(1, int(self.width / CHAR_PX.get(self.font, _DEFAULT_CHAR_PX)))


@dataclass(frozen=True)
class Screen:
    """Everything the background renderer needs to draw one display."""

    title: str
    accent: str                       # header band / stripe color
    rules: tuple[int, ...] = ()       # y coords of horizontal separator rules
    items: tuple[TextItem, ...] = field(default_factory=tuple)


def _item(server_url: str, item: TextItem) -> dict:
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


# Shorthand helpers keep the tables below compact.
# Rows below the 14px title band: font 4 value rows are 20px, font 2 rows 14px.
def _big(tid, y, color, w=128, x=0, ut=2):
    return TextItem(tid, x=x, y=y, font=4, width=w, height=20, color=color, update_time=ut)


def _small(tid, y, color, w=128, x=0, ut=2):
    return TextItem(tid, x=x, y=y, font=2, width=w, height=14, color=color, update_time=ut)


# ---------------------------------------------------------------------------
# Screens (index = LcdIndex, 0–4)
# ---------------------------------------------------------------------------
HEADER_H = 14  # title band drawn into the background GIF

SCREENS: tuple[Screen, ...] = (

    # ── Display 0 — SYSTEM ───────────────────────────────────────────────────
    # Each metric is a value row (font 4) with a load bar (font 2) beneath it.
    Screen(
        title="SYSTEM", accent="#00FFCC", rules=(52, 90),
        items=(
            _big  (TEXT_CPU_ROW, y=16,  color="#00FFCC"),
            _small(TEXT_CPU_BAR, y=36,  color="#00FFCC"),
            _big  (TEXT_GPU_ROW, y=54,  color="#44AAFF"),
            _small(TEXT_GPU_BAR, y=74,  color="#44AAFF"),
            _big  (TEXT_RAM_ROW, y=92,  color="#FFFFFF"),
            _small(TEXT_RAM_BAR, y=112, color="#FFFFFF"),
        ),
    ),

    # ── Display 1 — WEATHER ──────────────────────────────────────────────────
    # The city is font 2 here even though it heads the screen: font 4 only fits
    # 13 chars, which cuts most real city names. The temperature is the headline.
    Screen(
        title="WEATHER", accent="#FFB830", rules=(56, 78),
        items=(
            _small(TEXT_WEATHER_CITY,  y=16,  color="#FFFFFF", ut=30),
            _big  (TEXT_WEATHER_TEMP,  y=34,  color="#FFB830", w=72, ut=30),
            _small(TEXT_WEATHER_FEELS, y=40,  color="#AAAAAA", w=56, x=72, ut=30),
            _small(TEXT_WEATHER_DESC,  y=60,  color="#88CCFF", ut=30),
            _small(TEXT_WEATHER_HUM,   y=82,  color="#00CCFF", w=52, ut=30),
            _small(TEXT_WEATHER_WIND,  y=82,  color="#66FF66", w=76, x=52, ut=30),
            _small(TEXT_WEATHER_PRESS, y=104, color="#888888", ut=30),
        ),
    ),

    # ── Display 2 — DETAIL ───────────────────────────────────────────────────
    # Was a duplicate of display 1; now carries the data no other screen shows.
    Screen(
        title="DETAIL", accent="#FF6633", rules=(60, 94),
        items=(
            _big  (TEXT_NET_UP_ROW, y=16,  color="#00FF88"),
            _big  (TEXT_NET_DN_ROW, y=38,  color="#FF6633"),
            _small(TEXT_DISK_ROW,   y=62,  color="#FFFFFF", ut=30),
            _small(TEXT_DISK_BAR,   y=78,  color="#FFAA00", ut=30),
            _small(TEXT_UPTIME,     y=98,  color="#AAAAAA", ut=60),
            _small(TEXT_LOADAVG,    y=112, color="#88CCFF", ut=5),
        ),
    ),

    # ── Display 3 — TIME ─────────────────────────────────────────────────────
    Screen(
        title="TIME", accent="#FFD700", rules=(80,),
        items=(
            _big  (TEXT_TIME_CLOCK,   y=24,  color="#FFFFFF", ut=1),
            _big  (TEXT_TIME_DATE,    y=54,  color="#FFD700", ut=60),
            _small(TEXT_WEATHER_CITY, y=84,  color="#AAAAAA", ut=30),
            _small(TEXT_WEATHER_DESC, y=106, color="#88CCFF", ut=30),
        ),
    ),

    # ── Display 4 — NOISE ────────────────────────────────────────────────────
    # No half-width weather here: a slot's budget is the narrowest place it
    # appears, so a 64px city column would truncate the city on every screen.
    Screen(
        title="NOISE", accent="#FF8800", rules=(54, 76),
        items=(
            _big  (TEXT_TIME_CLOCK,   y=16,  color="#FFFFFF", ut=1),
            _small(TEXT_TIME_DATE,    y=40,  color="#FFD700", ut=60),
            _small(TEXT_WEATHER_CITY, y=58,  color="#AAAAAA", ut=30),
            _big  (TEXT_NOISE,        y=80,  color="#FF8800", ut=3),
            _small(TEXT_NOISE_BAR,    y=104, color="#FF8800", ut=3),
        ),
    ),
)

# Back-compat alias — several call sites only care about the item tables.
DISPLAY_ITEMS: list[list[TextItem]] = [list(s.items) for s in SCREENS]

# Tightest char budget per slot. A slot shown on two displays at different
# widths gets the smaller one, so it fits everywhere it appears.
SLOT_CHAR_BUDGET: dict[int, int] = {}
for _screen in SCREENS:
    for _it in _screen.items:
        _prev = SLOT_CHAR_BUDGET.get(_it.text_id)
        SLOT_CHAR_BUDGET[_it.text_id] = (
            _it.max_chars if _prev is None else min(_prev, _it.max_chars)
        )
del _screen, _it, _prev


def fit(slot_id: int, text: str) -> str:
    """Trim `text` to what the narrowest placement of `slot_id` can show.

    Prefers a word boundary, so a long weather description reads "light
    intensity" rather than "light intensity d".
    """
    budget = SLOT_CHAR_BUDGET.get(slot_id)
    if budget is None or len(text) <= budget:
        return text
    cut = text[:budget]
    space = cut.rfind(" ")
    # Only back off to the word boundary if it still fills most of the line
    return cut[:space] if space >= budget * 0.6 else cut


def bar(pct: Optional[float], cells: int = 10) -> str:
    """Render a percentage as a text bar: 45 → ``[####------]``.

    The firmware has no progress-bar item and colors are frozen at layout time
    (CLAUDE.md §4.5), so this is the only way to encode magnitude on screen.
    """
    if pct is None:
        return "[" + "?" * cells + "]"
    filled = round(max(0.0, min(100.0, pct)) / 100 * cells)
    return "[" + "#" * filled + "-" * (cells - filled) + "]"


def build_layout_command(lcd_index: int, server_url: str, bg_gif_url: str) -> dict:
    """Build a Draw/SendHttpItemList payload for the given display."""
    return {
        "Command": "Draw/SendHttpItemList",
        "LcdIndex": lcd_index,
        "NewFlag": 1,
        "BackgroudGif": bg_gif_url,  # Intentional firmware typo — must match exactly
        "ItemList": [_item(server_url, it) for it in SCREENS[lcd_index].items],
    }
