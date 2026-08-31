"""Constants and MQTT topic helpers for the NOMOS integration."""

from __future__ import annotations

DOMAIN = "nomos"

CONF_DEVICE_TYPE = "device_type"
CONF_DEVICE_ID = "device_id"

MANUFACTURER = "NOMOS"


def state_topic(device_type: str, device_id: str) -> str:
    """Return the MQTT topic a device of this type/ID publishes state to."""
    return f"nomos/{device_type}/{device_id}/state"


def command_topic(device_type: str, device_id: str) -> str:
    """Return the MQTT topic a device of this type/ID listens for commands on."""
    return f"nomos/{device_type}/{device_id}/command"
