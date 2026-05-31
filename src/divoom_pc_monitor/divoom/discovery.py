"""Auto-discover Divoom devices on the local network via the Divoom cloud API."""

import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

_DISCOVERY_URL = "https://app.divoom-gz.com/Device/ReturnSameLANDevice"


def discover_device(timeout: int = 5) -> Optional[str]:
    """Return the LAN IP of the first Divoom device found, or None on failure.

    Sends one POST to the Divoom cloud endpoint; the cloud matches by external IP
    and returns devices on the same LAN. Requires internet access.
    """
    try:
        resp = requests.post(_DISCOVERY_URL, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        devices = data.get("DeviceList", [])
        for dev in devices:
            ip = dev.get("DevicePrivateIP", "").strip()
            if ip:
                logger.info("Discovered Divoom device at %s (mac=%s)", ip, dev.get("DeviceMac"))
                return ip
    except requests.RequestException as exc:
        logger.warning("Auto-discovery request failed: %s", exc)
    except (ValueError, KeyError) as exc:
        logger.warning("Auto-discovery response parse error: %s", exc)
    return None
