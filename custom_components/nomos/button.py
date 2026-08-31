"""Button platform for NOMOS devices."""

from __future__ import annotations

from homeassistant.components import mqtt
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_DEVICE_ID, CONF_DEVICE_TYPE, DOMAIN, MANUFACTURER, command_topic
from .models import DEVICE_TYPES, NomosButtonDescriptor


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up NOMOS buttons for a config entry."""
    device_type = DEVICE_TYPES[entry.data[CONF_DEVICE_TYPE]]
    async_add_entities(NomosButton(entry, descriptor) for descriptor in device_type.buttons)


class NomosButton(ButtonEntity):
    """A button that publishes a fixed command payload to a NOMOS device."""

    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, descriptor: NomosButtonDescriptor) -> None:
        """Initialize the button from its descriptor."""
        self._descriptor = descriptor
        self._device_type = entry.data[CONF_DEVICE_TYPE]
        self._device_id = entry.data[CONF_DEVICE_ID]

        self._attr_unique_id = f"{entry.unique_id}_{descriptor.key}"
        self._attr_name = descriptor.name
        self._attr_icon = descriptor.icon
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
            name=entry.data[CONF_NAME],
            manufacturer=MANUFACTURER,
            model=DEVICE_TYPES[self._device_type].model,
        )

    async def async_press(self) -> None:
        """Publish this button's command payload to the device's command topic."""
        await mqtt.async_publish(
            self.hass,
            command_topic(self._device_type, self._device_id),
            self._descriptor.command_payload,
        )
