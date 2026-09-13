"""Config flow for the NOMOS integration."""

from __future__ import annotations

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

            if not device_id:
                errors[CONF_DEVICE_ID] = "invalid_device_id"
            else:
                unique_id = f"{device_type}_{device_id}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

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
    """Options flow for device types with template-driven stat slots (stat_count > 0)."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Store the config entry this options flow belongs to."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show one template field per stat slot the device type declares."""
        device_type = DEVICE_TYPES[self.config_entry.data[CONF_DEVICE_TYPE]]

        if device_type.stat_count == 0:
            return self.async_abort(reason="no_options")

        if user_input is not None:
            return self.async_create_entry(data=user_input)

        schema_dict: dict[Any, Any] = {}
        for i in range(device_type.stat_count):
            key = stat_template_key(i)
            default = self.config_entry.options.get(key, "")
            schema_dict[vol.Optional(key, default=default)] = TemplateSelector()

        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema_dict))
