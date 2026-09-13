"""Config flow for the NOMOS integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    TemplateSelector,
)

from .const import CONF_DEVICE_ID, CONF_DEVICE_TYPE, DOMAIN, stat_template_key
from .models import DEVICE_TYPES

_LOGGER = logging.getLogger(__name__)


class NomosConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for adding one NOMOS device."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> NomosOptionsFlowHandler:
        """Get the options flow for this device, if its device type has one."""
        return NomosOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Ask for a device type, an MQTT device ID, and a friendly name."""
        errors: dict[str, str] = {}

        if user_input is not None:
            device_type = user_input[CONF_DEVICE_TYPE]
            device_id = cv.slugify(user_input[CONF_DEVICE_ID])
            _LOGGER.debug(
                "Add-device form submitted: device_type=%s device_id=%s", device_type, device_id
            )

            if not device_id:
                errors[CONF_DEVICE_ID] = "invalid_device_id"
                _LOGGER.debug("Rejected device_id %r: slugifies to empty string", user_input[CONF_DEVICE_ID])
            else:
                unique_id = f"{device_type}_{device_id}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                _LOGGER.info("Creating NOMOS device entry: %s (%s)", unique_id, device_type)
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data={
                        CONF_DEVICE_TYPE: device_type,
                        CONF_DEVICE_ID: device_id,
                        CONF_NAME: user_input[CONF_NAME],
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_DEVICE_TYPE, default="scale"): SelectSelector(
                    SelectSelectorConfig(
                        options=list(DEVICE_TYPES.keys()),
                        translation_key=CONF_DEVICE_TYPE,
                    )
                ),
                vol.Required(CONF_DEVICE_ID): cv.string,
                vol.Required(CONF_NAME): cv.string,
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)


class NomosOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow for device types with template-driven stat slots (stat_count > 0).

    Deliberately does NOT store the entry as `self.config_entry` in __init__ --
    that assignment pattern was deprecated by Home Assistant in late 2024 (the
    base class now exposes config_entry as a computed read-only property) and
    the temporary backward-compatibility setter was removed in the 2025.12
    release. Assigning to it now raises, which is what turned into the "Config
    flow could not be loaded: 500 Internal Server Error" you saw -- the base
    class already gives us `self.config_entry` for free, so __init__ doesn't
    need to do anything with it at all.
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show one template field per stat slot the device type declares."""
        entry = self.config_entry
        _LOGGER.debug("Options flow opened for entry %s", entry.entry_id)

        device_type = DEVICE_TYPES[entry.data[CONF_DEVICE_TYPE]]

        if device_type.stat_count == 0:
            _LOGGER.debug(
                "Device type %s has no stat slots; aborting options flow", device_type.key
            )
            return self.async_abort(reason="no_options")

        if user_input is not None:
            _LOGGER.info("Saving %d stat template(s) for entry %s", device_type.stat_count, entry.entry_id)
            return self.async_create_entry(data=user_input)

        schema_dict: dict[Any, Any] = {}
        for i in range(device_type.stat_count):
            key = stat_template_key(i)
            default = entry.options.get(key, "")
            schema_dict[vol.Optional(key, default=default)] = TemplateSelector()

        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema_dict))
