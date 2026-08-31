"""Config flow for the NOMOS integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig

from .const import CONF_DEVICE_ID, CONF_DEVICE_TYPE, DOMAIN
from .models import DEVICE_TYPES


class NomosConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for adding one NOMOS device."""

    VERSION = 1

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
