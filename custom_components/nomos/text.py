"""Text platform for NOMOS devices: writable title/value/screen-title fields pushed to the device.

Unlike sensor/binary_sensor (device -> HA), these entities carry data the
other way: set one's value (by hand, or from an automation driven by
whatever entity/template you want) and the result is republished to the
device's MQTT topics, matching how button.py publishes to the command topic
on press.

Each stat slot gets two entities -- a Title and a Value -- combined into one
display string ("Title: Value", or just whichever half is set) before being
published to the stats topic, so the firmware never needs to know they were
ever two separate fields. A device with `has_title` also gets a single
"Screen Title" entity, published as a raw string directly to its own topic.
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

from .const import CONF_DEVICE_ID, CONF_DEVICE_TYPE, DOMAIN, MANUFACTURER, stats_topic, title_topic
from .models import DEVICE_TYPES

_LOGGER = logging.getLogger(__name__)

# Must match DASHBOARD_STAT_MAXLEN / DASHBOARD_TITLE_MAXLEN in the LILYGO
# Display firmware -- the device truncates past this anyway, so the entity
# may as well stop you first.
STAT_MAX_LENGTH = 31
TITLE_MAX_LENGTH = 31


def _combine(title: str, value: str) -> str:
    """Combine one stat slot's title/value into the string shown on the device."""
    if title and value:
        return f"{title}: {value}"
    return title or value


def _device_info(entry: ConfigEntry, device_type_key: str) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
        name=entry.data[CONF_NAME],
        manufacturer=MANUFACTURER,
        model=DEVICE_TYPES[device_type_key].model,
    )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up NOMOS text entities for a config entry."""
    device_type = DEVICE_TYPES[entry.data[CONF_DEVICE_TYPE]]
    entities: list[TextEntity] = []

    if device_type.stat_count:
        topic = stats_topic(entry.data[CONF_DEVICE_TYPE], entry.data[CONF_DEVICE_ID])

        # Shared by every stat entity of this device: setting one slot has to
        # republish the full array, so all slots need to see each other's
        # latest value rather than each publishing its own value in isolation.
        titles: list[str] = [""] * device_type.stat_count
        values: list[str] = [""] * device_type.stat_count

        async def publish_stats() -> None:
            payload = json.dumps({"stats": [_combine(titles[i], values[i]) for i in range(device_type.stat_count)]})
            _LOGGER.debug("Publishing to %s (retained): %s", topic, payload)
            if not await mqtt.async_publish(hass, topic, payload, qos=0, retain=True):
                _LOGGER.warning("Failed to publish stats to %s", topic)

        for i in range(device_type.stat_count):
            entities.append(NomosStatSlotText(entry, i, "title", titles, publish_stats))
            entities.append(NomosStatSlotText(entry, i, "value", values, publish_stats))

    if device_type.has_title:
        entities.append(NomosScreenTitleText(entry))

    if device_type.has_progress:
        entities.append(NomosProgressTitleText(entry, hass))

    async_add_entities(entities)


class NomosStatSlotText(TextEntity, RestoreEntity):
    """Either the Title or the Value half of one stat slot."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_native_max_value = STAT_MAX_LENGTH

    def __init__(
        self, entry: ConfigEntry, index: int, kind: str, slot_list: list[str], publish
    ) -> None:
        """Initialize the title/value entity for stat slot `index`."""
        self._index = index
        self._slot_list = slot_list
        self._publish = publish
        self._entry_id = entry.entry_id
        device_type = entry.data[CONF_DEVICE_TYPE]

        label = "Title" if kind == "title" else "Value"
        self._attr_unique_id = f"{entry.unique_id}_stat_{index}_{kind}"
        self._attr_name = f"Stat {index + 1} {label}"
        # Required: add_to_platform_finish() writes state immediately on
        # registration, before async_added_to_hass() runs -- a brand new
        # entity with no prior state (RestoreEntity finds nothing) would
        # otherwise never get _attr_native_value set at all and crash with
        # AttributeError the moment HA tries to read native_value.
        self._attr_native_value = ""
        self._attr_device_info = _device_info(entry, device_type)

    async def async_added_to_hass(self) -> None:
        """Restore the last known value across restarts and push it to the device."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (None, "unknown", "unavailable"):
            self._attr_native_value = last_state.state
            self._slot_list[self._index] = last_state.state
            await self._publish()

    async def async_set_value(self, value: str) -> None:
        """Set this half of the stat slot and push the combined stats array."""
        _LOGGER.debug("Stat %d (%s) set for entry %s: %r", self._index, self._attr_name, self._entry_id, value)
        self._attr_native_value = value
        self._slot_list[self._index] = value
        self.async_write_ha_state()
        await self._publish()


class NomosScreenTitleText(TextEntity, RestoreEntity):
    """The device's screen title, pushed as a raw string to its own topic."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_native_max_value = TITLE_MAX_LENGTH

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the screen title entity."""
        self._entry_id = entry.entry_id
        device_type = entry.data[CONF_DEVICE_TYPE]
        self._topic = title_topic(entry.data[CONF_DEVICE_TYPE], entry.data[CONF_DEVICE_ID])

        self._attr_unique_id = f"{entry.unique_id}_screen_title"
        self._attr_name = "Screen Title"
        self._attr_native_value = ""  # see NomosStatSlotText.__init__ for why this is required
        self._attr_device_info = _device_info(entry, device_type)

    async def _publish(self) -> None:
        _LOGGER.debug("Publishing to %s (retained): %s", self._topic, self._attr_native_value)
        if not await mqtt.async_publish(self.hass, self._topic, self._attr_native_value, qos=0, retain=True):
            _LOGGER.warning("Failed to publish screen title to %s", self._topic)

    async def async_added_to_hass(self) -> None:
        """Restore the last known value across restarts and push it to the device."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (None, "unknown", "unavailable"):
            self._attr_native_value = last_state.state
            await self._publish()

    async def async_set_value(self, value: str) -> None:
        """Set the screen title and push it to the device."""
        _LOGGER.debug("Screen title set for entry %s: %r", self._entry_id, value)
        self._attr_native_value = value
        self.async_write_ha_state()
        await self._publish()


class NomosProgressTitleText(TextEntity, RestoreEntity):
    """The progress bar's title.

    Non-empty shows the progress bar on the device (over its bottom two stat
    rows); empty is the signal to hide it and restore those rows. See
    number.py for the Percent half of this same payload -- both share one
    NomosProgressState (see progress.py) stashed in hass.data by __init__.py.
    """

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_native_max_value = STAT_MAX_LENGTH

    def __init__(self, entry: ConfigEntry, hass: HomeAssistant) -> None:
        """Initialize the progress title entity."""
        self._entry_id = entry.entry_id
        self._state = hass.data[DOMAIN][entry.entry_id]["progress"]
        device_type = entry.data[CONF_DEVICE_TYPE]

        self._attr_unique_id = f"{entry.unique_id}_progress_title"
        self._attr_name = "Progress Title"
        self._attr_native_value = ""  # see NomosStatSlotText.__init__ for why this is required
        self._attr_device_info = _device_info(entry, device_type)

    async def async_added_to_hass(self) -> None:
        """Restore the last known value across restarts and push it to the device."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (None, "unknown", "unavailable"):
            self._attr_native_value = last_state.state
            self._state.title = last_state.state
            await self._state.publish()

    async def async_set_value(self, value: str) -> None:
        """Set the progress title and push the combined progress payload."""
        _LOGGER.debug("Progress title set for entry %s: %r", self._entry_id, value)
        self._attr_native_value = value
        self._state.title = value
        self.async_write_ha_state()
        await self._state.publish()
