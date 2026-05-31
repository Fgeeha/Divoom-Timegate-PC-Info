"""HTTP client for the Divoom Times Gate local API."""

import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class DivoomClient:
    """Send JSON commands to the Divoom device at POST http://<ip>/post."""

    def __init__(self, device_ip: str, token: str = "", timeout: int = 5) -> None:
        self._url = f"http://{device_ip}/post"
        self._token = token
        self._timeout = timeout
        self._session = requests.Session()

    def _build(self, payload: dict) -> dict:
        """Inject DeviceToken when configured."""
        if self._token:
            return {"DeviceToken": self._token, **payload}
        return payload

    def post(self, payload: dict) -> bool:
        """Send *payload* to the device. Returns True if error_code == 0."""
        try:
            resp = self._session.post(
                self._url, json=self._build(payload), timeout=self._timeout
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.error("Network error sending to Divoom: %s", exc)
            return False

        # Firmware sometimes returns JSON with a non-JSON Content-Type header.
        # Always try to parse JSON first; fall back to text logging on failure.
        try:
            data = resp.json()
        except ValueError:
            logger.error("Divoom returned non-JSON: %r", resp.text[:200])
            return False

        ec = data.get("error_code")
        if ec == 0:
            return True

        logger.warning("Divoom error: %s | response: %s", ec, data)
        return False

    def get_channel_index(self) -> Optional[int]:
        """Return the current active channel index, or None on failure."""
        try:
            resp = self._session.post(
                self._url,
                json=self._build({"Command": "Channel/GetIndex"}),
                timeout=self._timeout,
            )
            data = resp.json()
            if data.get("error_code") == 0:
                return int(data.get("SelectIndex", 0))
        except Exception as exc:
            logger.debug("get_channel_index failed: %s", exc)
        return None

    def set_channel_index(self, index: int) -> bool:
        """Restore the device to *index* (e.g. the clock face before we took over)."""
        return self.post({"Command": "Channel/SetIndex", "SelectIndex": index})

    def close(self) -> None:
        self._session.close()
