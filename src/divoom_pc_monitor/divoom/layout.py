"""Display layout definitions and command builder for Divoom Times Gate.

Layout (5 displays, 128×128 px each):
  Display 0 — PC metrics  : CPU load/temp, GPU load/temp, RAM, network
  Display 1 — Weather     : city, temp, feels-like, condition, humidity, wind, pressure
  Display 2 — Weather detail: big temp + all detail lines
  Display 3 — Date/time   : clock, date, city, condition
  Display 4 — Noise       : clock, date, city+temp, noise level from device mic
"""

from dataclasses import dataclass

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


# Shorthand helpers keep the table below compact
def _pc(tid, x, y, w, color):
    return TextItem(tid, x=x, y=y, font=2, width=w, height=16, color=color, update_time=2)


def _wx(tid, x, y, font, w, h, color):
    return TextItem(tid, x=x, y=y, font=font, width=w, height=h, color=color, update_time=30)


def _time(tid, x, y, font, w, h, color, ut):
    return TextItem(tid, x=x, y=y, font=font, width=w, height=h, color=color, update_time=ut)


# ---------------------------------------------------------------------------
# Layouts per display (index = LcdIndex, 0–4)
# ---------------------------------------------------------------------------
DISPLAY_ITEMS: list[list[TextItem]] = [

    # Display 0 — PC metrics (all on one screen, compact grid)
    [
        _pc(TEXT_CPU_LOAD, x=0,   y=4,   w=68,  color="#00FF44"),   # CPU 45%
        _pc(TEXT_CPU_TEMP, x=68,  y=4,   w=60,  color="#FF8800"),   # 72C
        _pc(TEXT_GPU_LOAD, x=0,   y=28,  w=68,  color="#00AAFF"),   # GPU 80%
        _pc(TEXT_GPU_TEMP, x=68,  y=28,  w=60,  color="#FF4400"),   # 65C
        _pc(TEXT_RAM_PCT,  x=0,   y=52,  w=68,  color="#AAAAAA"),   # RAM 60%
        _pc(TEXT_RAM_USED, x=68,  y=52,  w=60,  color="#FFFFFF"),   # 12.3G
        _pc(TEXT_NET_UP,   x=0,   y=76,  w=128, color="#00FFAA"),   # UP 1.2M/s
        _pc(TEXT_NET_DOWN, x=0,   y=100, w=128, color="#FF00AA"),   # DN 5.6M/s
    ],

    # Display 1 — Weather overview
    [
        _wx(TEXT_WEATHER_CITY,  x=0,  y=6,   font=4, w=128, h=20, color="#FFFFFF"),   # Moscow
        _wx(TEXT_WEATHER_TEMP,  x=0,  y=32,  font=4, w=76,  h=20, color="#FFA040"),   # 22C
        _wx(TEXT_WEATHER_FEELS, x=76, y=36,  font=2, w=52,  h=16, color="#888888"),   # FL:19C
        _wx(TEXT_WEATHER_DESC,  x=0,  y=58,  font=2, w=128, h=16, color="#88CCFF"),
        _wx(TEXT_WEATHER_HUM,   x=0,  y=82,  font=2, w=68,  h=16, color="#00FFFF"),   # HUM:65%
        _wx(TEXT_WEATHER_WIND,  x=68, y=82,  font=2, w=60,  h=16, color="#00FF88"),   # N 5.2m/s
        _wx(TEXT_WEATHER_PRESS, x=0,  y=106, font=2, w=128, h=16, color="#666666"),   # 1013hPa
    ],

    # Display 2 — Weather detail (big temperature + all detail lines)
    [
        _wx(TEXT_WEATHER_TEMP,  x=0, y=8,   font=4, w=128, h=20, color="#FFA040"),   # 22C  (big)
        _wx(TEXT_WEATHER_FEELS, x=0, y=36,  font=2, w=128, h=16, color="#888888"),   # FL: 19C
        _wx(TEXT_WEATHER_HUM,   x=0, y=60,  font=2, w=128, h=16, color="#00FFFF"),   # HUM: 65%
        _wx(TEXT_WEATHER_WIND,  x=0, y=84,  font=2, w=128, h=16, color="#00FF88"),   # N 5.2m/s
        _wx(TEXT_WEATHER_PRESS, x=0, y=108, font=2, w=128, h=16, color="#666666"),   # 1013 hPa
    ],

    # Display 3 — Date / time
    [
        _time(TEXT_TIME_CLOCK,   x=0, y=16,  font=4, w=128, h=20, color="#FFFFFF",  ut=1),
        _time(TEXT_TIME_DATE,    x=0, y=48,  font=4, w=128, h=20, color="#FFD700",  ut=60),
        _wx  (TEXT_WEATHER_CITY, x=0, y=80,  font=2, w=128, h=16, color="#888888"),
        _wx  (TEXT_WEATHER_DESC, x=0, y=104, font=2, w=128, h=16, color="#88CCFF"),
    ],

    # Display 4 — Noise meter + time
    [
        _time(TEXT_TIME_CLOCK,   x=0,  y=6,  font=4, w=128, h=20, color="#FFFFFF",  ut=1),
        _time(TEXT_TIME_DATE,    x=0,  y=34, font=2, w=128, h=16, color="#FFD700",  ut=60),
        _wx  (TEXT_WEATHER_CITY, x=0,  y=58, font=2, w=68,  h=16, color="#888888"),
        _wx  (TEXT_WEATHER_TEMP, x=68, y=58, font=2, w=60,  h=16, color="#FFA040"),
        TextItem(TEXT_NOISE, x=0, y=86, font=4, width=128, height=20,
                 color="#FF8800", update_time=3),
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
        "ItemList": [_item(server_url, it) for it in items],
    }
