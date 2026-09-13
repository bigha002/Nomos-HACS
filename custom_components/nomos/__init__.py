"""The NOMOS integration: Home Assistant devices designed in-house."""

from __future__ import annotations

import json
import logging

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, Platform
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import TemplateError
from homeassistant.helpers.event import (
    TrackTemplate,
    TrackTemplateResult,
    async_track_template_result,
)
from homeassistant.helpers.template import Template

from .const import CONF_DEVICE_ID, CONF_DEVICE_TYPE, DOMAIN, stat_template_key, stats_topic
from .models import DEVICE_TYPES

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a NOMOS device from a config entry."""
    device_type = DEVICE_TYPES[entry.data[CONF_DEVICE_TYPE]]
    _LOGGER.info(
        "Setting up NOMOS device %r: type=%s id=%s",
        entry.data.get(CONF_NAME, entry.title),
        device_type.key,
        entry.data[CONF_DEVICE_ID],
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.debug("Forwarded entry %s to platforms: %s", entry.entry_id, PLATFORMS)

    if device_type.stat_count:
        _async_setup_stat_templates(hass, entry, device_type.stat_count)
    else:
        _LOGGER.debug("Device type %s has no stat templates to track", device_type.key)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a NOMOS config entry."""
    _LOGGER.info("Unloading NOMOS device entry %s", entry.entry_id)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    else:
        _LOGGER.warning("Failed to unload platforms for entry %s", entry.entry_id)
    return unload_ok


def _async_setup_stat_templates(hass: HomeAssistant, entry: ConfigEntry, stat_count: int) -> None:
    """Track each configured stat template and publish rendered results to the device.

    All templates for this entry are tracked in a single
    async_track_template_result() call so that one Home Assistant state
    change affecting several stat lines republishes once, not once per line.
    """
    topic = stats_topic(entry.data[CONF_DEVICE_TYPE], entry.data[CONF_DEVICE_ID])

    stats: list[str] = [""] * stat_count
    index_by_template: dict[Template, int] = {}
    track_templates: list[TrackTemplate] = []

    for i in range(stat_count):
        template_str = entry.options.get(stat_template_key(i), "")
        if not template_str:
            continue
        template = Template(template_str, hass)
        index_by_template[template] = i
        track_templates.append(TrackTemplate(template, None, None))
        _LOGGER.debug("Stat %d template for entry %s: %r", i, entry.entry_id, template_str)

    if not track_templates:
        _LOGGER.debug("No stat templates configured yet for entry %s (topic %s)", entry.entry_id, topic)
        return

    _LOGGER.info(
        "Tracking %d stat template(s) for entry %s, publishing to %s",
        len(track_templates),
        entry.entry_id,
        topic,
    )

    async def _publish() -> None:
        payload = json.dumps({"stats": stats})
        _LOGGER.debug("Publishing to %s: %s", topic, payload)
        if not await mqtt.async_publish(hass, topic, payload):
            _LOGGER.warning("Failed to publish stats to %s", topic)

    @callback
    def _handle_update(_event: Event | None, updates: list[TrackTemplateResult]) -> None:
        changed = False
        for update in updates:
            index = index_by_template[update.template]
            result = update.result
            if isinstance(result, TemplateError):
                _LOGGER.warning(
                    "Stat %d template errored for entry %s: %s", index, entry.entry_id, result
                )
                text = ""
            else:
                text = "" if result is None else str(result)
            if stats[index] != text:
                _LOGGER.debug("Stat %d changed for entry %s: %r -> %r", index, entry.entry_id, stats[index], text)
                stats[index] = text
                changed = True
        if changed:
            hass.async_create_task(_publish())

    info = async_track_template_result(hass, track_templates, _handle_update)
    entry.async_on_unload(info.async_remove)
    info.async_refresh()

    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload a config entry when its options (stat templates) change."""
    _LOGGER.info("Options changed for entry %s, reloading", entry.entry_id)
    await hass.config_entries.async_reload(entry.entry_id)
