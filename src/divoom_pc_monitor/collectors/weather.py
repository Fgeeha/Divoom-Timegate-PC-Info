"""Weather data fetcher using OpenWeatherMap current weather API."""

import logging
from typing import Optional

import requests

from .base import WeatherData

logger = logging.getLogger(__name__)

_OWM_URL = "https://api.openweathermap.org/data/2.5/weather"
_WIND_DIRS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


class WeatherFetcher:
    def __init__(self, city: str, api_key: str, units: str = "metric") -> None:
        self.city = city
        self.api_key = api_key
        self.units = units

    def fetch(self) -> Optional[WeatherData]:
        """Fetch current weather. Returns None when unconfigured or on error."""
        if not self.api_key or not self.city:
            return None
        try:
            resp = requests.get(
                _OWM_URL,
                params={"q": self.city, "appid": self.api_key, "units": self.units},
                timeout=10,
            )
            resp.raise_for_status()
            return _parse(resp.json(), self.units)
        except Exception as exc:
            logger.warning("Weather fetch failed: %s", exc)
            return None


def _parse(data: dict, units: str) -> WeatherData:
    main = data.get("main", {})
    wind = data.get("wind", {})
    weather_list = data.get("weather", [{}])

    deg = wind.get("deg")
    wind_dir = _WIND_DIRS[round(deg / 45) % 8] if deg is not None else ""
    unit_symbol = "C" if units == "metric" else "F"

    return WeatherData(
        city=data.get("name", ""),
        temp=main.get("temp"),
        feels_like=main.get("feels_like"),
        humidity=main.get("humidity"),
        pressure=main.get("pressure"),
        wind_speed=wind.get("speed"),
        wind_dir=wind_dir,
        description=weather_list[0].get("description", "").capitalize(),
        unit_symbol=unit_symbol,
    )
