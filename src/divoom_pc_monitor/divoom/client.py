"""HTTP client for the Divoom Times Gate local API."""

import logging

import requests

logger = logging.getLogger(__name__)


class DivoomClient:
    """Send JSON commands to the Divoom device at POST http://<ip>/post."""

    def __init__(self, device_ip: str, timeout: int = 5) -> None:
        self._url = f"http://{device_ip}/post"
        self._timeout = timeout
        self._session = requests.Session()

    def post(self, payload: dict) -> bool:
        """Send *payload* to the device. Returns True if error_code == 0."""
        try:
            resp = self._session.post(self._url, json=payload, timeout=self._timeout)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.error("Network error sending to Divoom: %s", exc)
            return False

        # Firmware returns plain "Request data illegal json" on bad payloads
        content_type = resp.headers.get("Content-Type", "")
        if "json" not in content_type:
            logger.error("Divoom returned non-JSON: %r", resp.text[:200])
            return False

        try:
            data = resp.json()
        except ValueError:
            logger.error("Divoom returned invalid JSON: %r", resp.text[:200])
            return False

        if data.get("error_code") == 0:
            return True

        logger.warning("Divoom error_code=%s in response: %s", data.get("error_code"), data)
        return False

    def close(self) -> None:
        self._session.close()
