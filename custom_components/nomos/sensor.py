"""Sensor platform for NOMOS devices."""

from __future__ import annotations

import json
import logging

from homeassistant.components import mqtt
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_DEVICE_ID, CONF_DEVICE_TYPE, DOMAIN, MANUFACTURER, state_topic
from .models import DEVICE_TYPES, NomosSensorDescriptor

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up NOMOS sensors for a config entry."""
    device_type = DEVICE_TYPES[entry.data[CONF_DEVICE_TYPE]]
    async_add_entities(NomosSensor(entry, descriptor) for descriptor in device_type.sensors)


class NomosSensor(SensorEntity):
    """A sensor whose value comes from a NOMOS device's MQTT state topic."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, descriptor: NomosSensorDescriptor) -> None:
        """Initialize the sensor from its descriptor."""
        self._descriptor = descriptor
        self._device_type = entry.data[CONF_DEVICE_TYPE]
        self._device_id = entry.data[CONF_DEVICE_ID]

        self._attr_unique_id = f"{entry.unique_id}_{descriptor.key}"
        self._attr_name = descriptor.name
        self._attr_device_class = descriptor.device_class
        self._attr_state_class = descriptor.state_class
        self._attr_native_unit_of_measurement = descriptor.native_unit_of_measurement
        self._attr_icon = descriptor.icon
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
            name=entry.data[CONF_NAME],
            manufacturer=MANUFACTURER,
            model=DEVICE_TYPES[self._device_type].model,
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to the device's MQTT state topic."""

        @callback
        def message_received(msg: mqtt.ReceiveMessage) -> None:
            try:
                payload = json.loads(msg.payload)
            except ValueError:
                _LOGGER.warning("Ignoring non-JSON payload on %s: %s", msg.topic, msg.payload)
                return

            if self._descriptor.json_key not in payload:
                return

            self._attr_native_value = payload[self._descriptor.json_key]
            self.async_write_ha_state()

        self.async_on_remove(
            await mqtt.async_subscribe(
                self.hass,
                state_topic(self._device_type, self._device_id),
                message_received,
                qos=0,
            )
        )
