"""Switch platform for NOMOS devices: writable lamp booleans pushed to the device.

Same "HA -> device" direction and shared-list-plus-retained-publish pattern
as the stat entities in text.py: toggling one lamp republishes the full
lamps array to the device's MQTT lamps topic.
"""

from __future__ import annotations

import json
import logging

from homeassistant.components import mqtt
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import CONF_DEVICE_ID, CONF_DEVICE_TYPE, DOMAIN, MANUFACTURER, lamps_topic
from .models import DEVICE_TYPES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up NOMOS lamp switches for a config entry."""
    device_type = DEVICE_TYPES[entry.data[CONF_DEVICE_TYPE]]
    if device_type.lamp_count == 0:
        return

    topic = lamps_topic(entry.data[CONF_DEVICE_TYPE], entry.data[CONF_DEVICE_ID])

    # Shared by every lamp entity of this device: toggling one has to
    # republish the full array, so all lamps need to see each other's latest
    # state rather than each publishing its own state in isolation.
    lamps: list[bool] = [False] * device_type.lamp_count

    async def publish() -> None:
        payload = json.dumps({"lamps": lamps})
        _LOGGER.debug("Publishing to %s (retained): %s", topic, payload)
        if not await mqtt.async_publish(hass, topic, payload, qos=0, retain=True):
            _LOGGER.warning("Failed to publish lamps to %s", topic)

    async_add_entities(NomosLamp(entry, i, lamps, publish) for i in range(device_type.lamp_count))


class NomosLamp(SwitchEntity, RestoreEntity):
    """A writable lamp switch whose state is pushed to a NOMOS device."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, index: int, lamps: list[bool], publish) -> None:
        """Initialize the lamp switch for lamp `index`."""
        self._index = index
        self._lamps = lamps
        self._publish = publish
        self._entry_id = entry.entry_id
        device_type = entry.data[CONF_DEVICE_TYPE]

        self._attr_unique_id = f"{entry.unique_id}_lamp_{index}"
        self._attr_name = f"Lamp {index + 1}"
        # Required for the same reason text.py's stat entities need
        # _attr_native_value set: add_to_platform_finish() writes state
        # immediately on registration, before async_added_to_hass() runs.
        self._attr_is_on = False
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
            name=entry.data[CONF_NAME],
            manufacturer=MANUFACTURER,
            model=DEVICE_TYPES[device_type].model,
        )

    async def async_added_to_hass(self) -> None:
        """Restore the last known state across restarts and push it to the device."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state in ("on", "off"):
            self._attr_is_on = last_state.state == "on"
            self._lamps[self._index] = self._attr_is_on
            await self._publish()

    async def async_turn_on(self, **kwargs) -> None:
        """Turn this lamp on."""
        await self._set(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn this lamp off."""
        await self._set(False)

    async def _set(self, is_on: bool) -> None:
        _LOGGER.debug("Lamp %d set for entry %s: %s", self._index, self._entry_id, is_on)
        self._attr_is_on = is_on
        self._lamps[self._index] = is_on
        self.async_write_ha_state()
        await self._publish()
