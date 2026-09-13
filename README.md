# NOMOS Devices for Home Assistant

A custom [HACS](https://hacs.xyz) integration for adding NOMOS-designed
devices to Home Assistant. Each device type (Scale, and others to come) is
registered in one place ("custom_components/nomos/models.py"), so wiring up a
new device is mostly a matter of describing its sensors, not writing new
plumbing.

## How it works

NOMOS devices talk to Home Assistant over **MQTT**. Each device publishes a
single JSON state payload to a topic, and (optionally) listens on a command
topic for actions like "tare":

```
nomos/<device_type>/<device_id>/state    <-  device publishes, e.g.:
                                              {"weight": 82.4, "battery": 87, "stable": true}
nomos/<device_type>/<device_id>/command  ->  device subscribes, e.g.:
                                              TARE
```

`device_type` is the type key from `models.py` (currently only `scale`).
`device_id` is whatever slug you give the device when you add it in the UI.

This integration does **not** rely on Home Assistant's generic MQTT
discovery format - it defines its own entities per device type, so you get a
config flow, a proper device grouping, and full control over naming and
units, all driven from one Python file per device type.

## Requirements

- Home Assistant with the core **MQTT** integration already configured
  (pointed at whatever broker your NOMOS devices publish to).
- HACS, to install this as a custom repository (see below).

## Installing (as a custom repository)

This repo is not in the default HACS store, so add it manually:

1. In Home Assistant, open **HACS**.
2. Click the three-dot menu (top right) -> **Custom repositories**.
3. Paste this repo's URL, set the type to **Integration**, click **Add**.
4. Find **NOMOS Devices** in HACS and install it.
5. Restart Home Assistant.
6. Go to **Settings -> Devices & services -> Add integration**, search for
   **NOMOS**, and add a device.

No approval or review process is required for a custom repository - see the
note at the bottom of this file if you ever want to submit it to the default
HACS store instead.

## Adding a device (currently: Scale)

When you add the integration you'll be asked for:

- **Device type** - e.g. `Scale`.
- **Device ID** - a short slug, e.g. `kitchen`. This becomes part of the MQTT
  topics above, so it must match what your device's firmware publishes to.
- **Name** - the friendly name Home Assistant shows for the device.

### NOMOS Scale

The Scale device type is a placeholder for hardware that doesn't exist yet.
It currently defines:

| Entity | Platform | JSON key | Notes |
|---|---|---|---|
| Weight | `sensor` | `weight` | kg, numeric |
| Battery | `sensor` | `battery` | %, numeric |
| Stable Reading | `binary_sensor` | `stable` | true/false |
| Tare | `button` | - | publishes `TARE` to the command topic |

You can try it out without any real hardware using `mosquitto_pub`:

```bash
mosquitto_pub -h <broker> -t nomos/scale/kitchen/state \
  -m '{"weight": 82.4, "battery": 87, "stable": true}'
```

(assuming you added the device with device ID `kitchen`).

### NOMOS Display

Unlike Scale, Display doesn't report sensor data - it's a screen, so data
flows the other way: entities you set push their value to the device.

```
nomos/display/<device_id>/stats  ->  device subscribes, e.g.:
                                      {"stats": ["Outside: 54°F", "3 lights on", ...]}
```

Adding a Display device gives you 8 `text` entities named **Stat 1**...**Stat
8** on it. Setting one (by hand, from a dashboard, or from an automation)
republishes the full 8-value array to the `stats` topic above, and the
device shows each string on its matching row. For example, to keep Stat 1
mirroring another sensor:

```yaml
automation:
  - alias: "NOMOS Display: outdoor temp on Stat 1"
    trigger:
      - platform: state
        entity_id: sensor.outdoor_temperature
    action:
      - service: text.set_value
        target:
          entity_id: text.workshopconsole_stat_1
        data:
          value: "{{ states('sensor.outdoor_temperature') }}°F"
```

Values are restored across Home Assistant restarts and re-pushed to the
device automatically.

You can watch this without hardware too:

```bash
mosquitto_sub -h <broker> -t nomos/display/<device_id>/stats -v
```

## Adding a new device type

1. In `custom_components/nomos/models.py`, add a new `NomosDeviceType` with
   its own `key` (e.g. `"fan_controller"`) and describe its sensors,
   binary sensors, and buttons - or, for a device that displays
   Home-Assistant-driven data instead of reporting its own, set
   `stat_count` to however many writable "Stat N" text entities it has.
2. Add it to the `DEVICE_TYPES` dict.
3. Add its display name to `strings.json` and
   `translations/en.json` under `selector.device_type.options`.

Nothing else needs to change - the config flow, sensor/binary_sensor/
button/text platforms, MQTT wiring, and device grouping all read from that
registry.

## Development / validation

`.github/workflows/validate.yml` runs [hassfest](https://developers.home-assistant.io/docs/creating_integration_manifest/#hassfest)
and the [HACS validation action](https://github.com/hacs/action) on every
push. Both should pass before you rely on a release.

## Publishing to the default HACS store (optional, later)

Custom repositories work fine indefinitely and need no review. If you later
want this discoverable without users pasting a URL in, HACS has a formal
submission process to their [`hacs/default`](https://github.com/hacs/default)
repo: brand assets registered in `home-assistant/brands`, a passing HACS
Action + hassfest, at least one GitHub release, and a PR reviewed by the HACS
team (their docs note this can take a while). Not required to use or share
this integration today.
