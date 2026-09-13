"""Number platform for NOMOS devices: the progress bar's percentage field.

Same "HA -> device" direction as text.py/switch.py -- setting this
republishes the combined progress payload to the device's progress topic.
The Title half of that same payload lives in text.py; both share one
NomosProgressState (see progress.py) stashed in hass.data by __init__.py.
"""

from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreNumber

from .const import CONF_DEVICE_TYPE, DOMAIN, MANUFACTURER
from .models import DEVICE_TYPES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the NOMOS progress-percent number entity for a config entry."""
    device_type = DEVICE_TYPES[entry.data[CONF_DEVICE_TYPE]]
    if not device_type.has_progress:
        return

    async_add_entities([NomosProgressPercentNumber(entry, hass)])


class NomosProgressPercentNumber(NumberEntity, RestoreNumber):
    """The progress bar's percentage, 0-100."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER

    def __init__(self, entry: ConfigEntry, hass: HomeAssistant) -> None:
        """Initialize the progress-percent entity."""
        self._entry_id = entry.entry_id
        self._state = hass.data[DOMAIN][entry.entry_id]["progress"]
        device_type = entry.data[CONF_DEVICE_TYPE]

        self._attr_unique_id = f"{entry.unique_id}_progress_percent"
        self._attr_name = "Progress Percent"
        # See text.py's NomosStatSlotText.__init__ for why this is required:
        # add_to_platform_finish() writes state before async_added_to_hass() runs.
        self._attr_native_value = 0
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
            name=entry.data[CONF_NAME],
            manufacturer=MANUFACTURER,
            model=DEVICE_TYPES[device_type].model,
        )

    async def async_added_to_hass(self) -> None:
        """Restore the last known value across restarts and push it to the device."""
        await super().async_added_to_hass()

        last_number_data = await self.async_get_last_number_data()
        if last_number_data is not None and last_number_data.native_value is not None:
            self._attr_native_value = last_number_data.native_value
            self._state.percent = self._attr_native_value
            await self._state.publish()

    async def async_set_native_value(self, value: float) -> None:
        """Set the progress percentage and push the combined progress payload."""
        _LOGGER.debug("Progress percent set for entry %s: %s", self._entry_id, value)
        self._attr_native_value = value
        self._state.percent = value
        self.async_write_ha_state()
        await self._state.publish()
