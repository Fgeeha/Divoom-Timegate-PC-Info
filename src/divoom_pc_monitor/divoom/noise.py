"""Read the noise/loudness level from the Divoom Times Gate microphone."""

import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# Command may vary by firmware version; returns {"error_code": 0, "Loudness": N}.
_CMD = "Device/GetNoiseLoudness"


class NoisePoller:
    """Poll the device noise sensor once per call."""

    def __init__(self, device_ip: str, token: str = "", timeout: int = 3) -> None:
        self._url = f"http://{device_ip}/post"
        self._token = token
        self._timeout = timeout

    def poll(self) -> Optional[int]:
        """Return noise level 0–100, or None on any failure."""
        payload: dict = {"Command": _CMD}
        if self._token:
            payload["DeviceToken"] = self._token
        try:
            resp = requests.post(self._url, json=payload, timeout=self._timeout)
            data = resp.json()
            if data.get("error_code") == 0:
                return int(data.get("Loudness", 0))
        except Exception as exc:
            logger.debug("Noise poll failed: %s", exc)
        return None
