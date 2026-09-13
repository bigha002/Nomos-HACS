"""Text platform for NOMOS devices: writable stat slots pushed to the device.

Unlike sensor/binary_sensor (device -> HA), these entities carry data the
other way: set one's value (by hand, or from an automation driven by
whatever entity/template you want) and the full stats array is republished
to the device's MQTT stats topic, matching how button.py publishes to the
command topic on press.
"""

from __future__ import annotations

import json
import logging

from homeassistant.components import mqtt
from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import CONF_DEVICE_ID, CONF_DEVICE_TYPE, DOMAIN, MANUFACTURER, stats_topic
from .models import DEVICE_TYPES

_LOGGER = logging.getLogger(__name__)

# Must match DASHBOARD_STAT_MAXLEN in the LILYGO Display firmware -- the
# device truncates past this anyway, so the entity may as well stop you first.
STAT_MAX_LENGTH = 31


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up NOMOS stat text entities for a config entry."""
    device_type = DEVICE_TYPES[entry.data[CONF_DEVICE_TYPE]]
    if device_type.stat_count == 0:
        return

    topic = stats_topic(entry.data[CONF_DEVICE_TYPE], entry.data[CONF_DEVICE_ID])

    # Shared by every stat entity of this device: setting one slot has to
    # republish the full array, so all slots need to see each other's
    # latest value rather than each publishing its own value in isolation.
    stats: list[str] = [""] * device_type.stat_count

    async def publish() -> None:
        payload = json.dumps({"stats": stats})
        _LOGGER.debug("Publishing to %s: %s", topic, payload)
        if not await mqtt.async_publish(hass, topic, payload):
            _LOGGER.warning("Failed to publish stats to %s", topic)

    async_add_entities(
        NomosStatText(entry, i, stats, publish) for i in range(device_type.stat_count)
    )


class NomosStatText(TextEntity, RestoreEntity):
    """A writable text slot whose value is pushed to a NOMOS device."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_native_max_value = STAT_MAX_LENGTH

    def __init__(self, entry: ConfigEntry, index: int, stats: list[str], publish) -> None:
        """Initialize the text entity for stat slot `index`."""
        self._index = index
        self._stats = stats
        self._publish = publish
        self._entry_id = entry.entry_id
        device_type = entry.data[CONF_DEVICE_TYPE]

        self._attr_unique_id = f"{entry.unique_id}_stat_{index}"
        self._attr_name = f"Stat {index + 1}"
        # Required: add_to_platform_finish() writes state immediately on
        # registration, before async_added_to_hass() runs -- a brand new
        # entity with no prior state (RestoreEntity finds nothing) would
        # otherwise never get _attr_native_value set at all and crash with
        # AttributeError the moment HA tries to read native_value.
        self._attr_native_value = ""
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
            name=entry.data[CONF_NAME],
            manufacturer=MANUFACTURER,
            model=DEVICE_TYPES[device_type].model,
        )

    async def async_added_to_hass(self) -> None:
        """Restore the last known value across restarts and push it to the device."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (None, "unknown", "unavailable"):
            self._attr_native_value = last_state.state
            self._stats[self._index] = last_state.state
            await self._publish()

    async def async_set_value(self, value: str) -> None:
        """Set this stat's text and push the full stats array to the device."""
        _LOGGER.debug("Stat %d set for entry %s: %r", self._index, self._entry_id, value)
        self._attr_native_value = value
        self._stats[self._index] = value
        self.async_write_ha_state()
        await self._publish()
