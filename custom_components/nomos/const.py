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


def stats_topic(device_type: str, device_id: str) -> str:
    """Return the MQTT topic a device of this type/ID listens for stat text on.

    Kept separate from command_topic() since it carries a different payload
    shape (a fixed-size JSON array of strings) rather than a bare command.
    """
    return f"nomos/{device_type}/{device_id}/stats"


def lamps_topic(device_type: str, device_id: str) -> str:
    """Return the MQTT topic a device of this type/ID listens for lamp states on.

    Same shape convention as stats_topic() (a JSON array), just a separate
    topic/array since lamps are booleans, not strings.
    """
    return f"nomos/{device_type}/{device_id}/lamps"


def title_topic(device_type: str, device_id: str) -> str:
    """Return the MQTT topic a device of this type/ID listens for its screen title on.

    A single raw string, not JSON-wrapped -- matches command_topic()'s
    bare-string convention since there's only ever one value.
    """
    return f"nomos/{device_type}/{device_id}/title"


def progress_topic(device_type: str, device_id: str) -> str:
    """Return the MQTT topic a device of this type/ID listens for its progress bar on.

    Payload is {"title": str, "percent": int} -- an empty title is the
    signal to the device that no progress bar should be shown right now.
    """
    return f"nomos/{device_type}/{device_id}/progress"
