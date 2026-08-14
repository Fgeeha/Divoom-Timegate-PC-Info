"""HTTP client for the Divoom Times Gate local API."""

import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class DivoomClient:
    """Send JSON commands to the Divoom device at POST http://<ip>/post."""

    def __init__(self, device_ip: str, token: Optional[str] = None, timeout: int = 5) -> None:
        self._url = f"http://{device_ip}/post"
        # None  → don't send DeviceToken field at all
        # ""    → send DeviceToken: "" (some firmware needs the field present but empty)
        # "abc" → send DeviceToken: "abc"
        self._token: Optional[str] = token
        self._timeout = timeout
        self._session = requests.Session()

    def _build(self, payload: dict) -> dict:
        """Inject DeviceToken when token is not None."""
        if self._token is not None:
            return {"DeviceToken": self._token, **payload}
        return payload

    def post(self, payload: dict, *, _auto_retry: bool = True) -> bool:
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
        try:
            data = resp.json()
        except ValueError:
            logger.error("Divoom returned non-JSON: %r", resp.text[:200])
            return False

        ec = data.get("error_code")
        if ec == 0:
            return True

        # Auto-discover token on first "DeviceToken is err" response
        if _auto_retry and isinstance(ec, str) and "DeviceToken" in ec:
            token = self._fetch_token()
            if token is not None:
                self._token = token
                logger.info("Auto-discovered DeviceToken, retrying...")
                return self.post(payload, _auto_retry=False)
            logger.error(
                "Device requires a DeviceToken but auto-discovery failed.\n"
                "Add to ~/.divoom-pc-monitor/config.toml:\n"
                "  [device]\n"
                "  token = \"your_token\"\n"
                "Or set env var DIVOOM_DEVICE_TOKEN=your_token\n"
                "Find the token in the Divoom app → device settings."
            )
            return False

        logger.warning("Divoom error: %s | response: %s", ec, data)
        return False

    def _fetch_token(self) -> Optional[str]:
        """Try to read DeviceToken from the local device API (no auth required)."""
        try:
            resp = self._session.post(
                self._url,
                json={"Command": "Device/GetDeviceToken"},
                timeout=self._timeout,
            )
            data = resp.json()
            if data.get("error_code") == 0:
                token = data.get("DeviceToken") or data.get("Token")
                if token is not None:
                    return str(token)
        except Exception as exc:
            logger.debug("_fetch_token failed: %s", exc)
        return None

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
