"""The NOMOS integration: Home Assistant devices designed in-house."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, Platform
from homeassistant.core import HomeAssistant

from .const import CONF_DEVICE_ID, CONF_DEVICE_TYPE, DOMAIN, progress_topic
from .models import DEVICE_TYPES
from .progress import NomosProgressState

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.TEXT,
    Platform.SWITCH,
    Platform.NUMBER,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a NOMOS device from a config entry."""
    device_type = DEVICE_TYPES[entry.data[CONF_DEVICE_TYPE]]
    _LOGGER.info(
        "Setting up NOMOS device %r: type=%s id=%s",
        entry.data.get(CONF_NAME, entry.title),
        device_type.key,
        entry.data[CONF_DEVICE_ID],
    )

    hass.data.setdefault(DOMAIN, {})
    entry_state: dict = {"config": entry.data}
    if device_type.has_progress:
        entry_state["progress"] = NomosProgressState(
            hass=hass,
            topic=progress_topic(entry.data[CONF_DEVICE_TYPE], entry.data[CONF_DEVICE_ID]),
        )
    hass.data[DOMAIN][entry.entry_id] = entry_state

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.debug("Forwarded entry %s to platforms: %s", entry.entry_id, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a NOMOS config entry."""
    _LOGGER.info("Unloading NOMOS device entry %s", entry.entry_id)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    else:
        _LOGGER.warning("Failed to unload platforms for entry %s", entry.entry_id)
    return unload_ok
