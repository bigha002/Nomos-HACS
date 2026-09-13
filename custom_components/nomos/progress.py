"""Shared runtime state for a device's progress bar (Title + Percent).

The Title (text platform) and Percent (number platform) halves are set up as
two separate HA entity platforms, so -- like text.py's stat slots share one
list -- they need a common place to see each other's latest value before
publishing the combined payload. One NomosProgressState is created per config
entry in __init__.py and stashed in hass.data for both platforms to find.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


@dataclass
class NomosProgressState:
    """Combined title/percent state for one device's progress bar."""

    hass: HomeAssistant
    topic: str
    title: str = ""
    percent: float = 0

    async def publish(self) -> None:
        """Publish the current title+percent as one retained JSON payload."""
        payload = json.dumps({"title": self.title, "percent": self.percent})
        _LOGGER.debug("Publishing to %s (retained): %s", self.topic, payload)
        if not await mqtt.async_publish(self.hass, self.topic, payload, qos=0, retain=True):
            _LOGGER.warning("Failed to publish progress to %s", self.topic)
