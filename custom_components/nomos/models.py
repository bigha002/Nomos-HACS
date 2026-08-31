"""Registry of NOMOS device types and the entities each one exposes.

Adding a new NOMOS device (a light, the fan controller, etc.) should mostly
mean adding a new NomosDeviceType here and registering its display name in
strings.json / translations/en.json - the config flow and the sensor,
binary_sensor, and button platforms all read from DEVICE_TYPES.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfMass


@dataclass(frozen=True)
class NomosSensorDescriptor:
    """Describes one sensor entity a NOMOS device type exposes."""

    key: str
    name: str
    json_key: str
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    native_unit_of_measurement: str | None = None
    icon: str | None = None


@dataclass(frozen=True)
class NomosBinarySensorDescriptor:
    """Describes one binary sensor entity a NOMOS device type exposes."""

    key: str
    name: str
    json_key: str
    device_class: BinarySensorDeviceClass | None = None
    icon: str | None = None


@dataclass(frozen=True)
class NomosButtonDescriptor:
    """Describes one button entity a NOMOS device type exposes."""

    key: str
    name: str
    command_payload: str
    icon: str | None = None


@dataclass(frozen=True)
class NomosDeviceType:
    """Describes a class of NOMOS device, e.g. the Scale."""

    key: str
    name: str
    model: str
    sensors: tuple[NomosSensorDescriptor, ...] = field(default_factory=tuple)
    binary_sensors: tuple[NomosBinarySensorDescriptor, ...] = field(default_factory=tuple)
    buttons: tuple[NomosButtonDescriptor, ...] = field(default_factory=tuple)


# --- NOMOS Scale ------------------------------------------------------------
# Placeholder device type: the hardware doesn't exist yet, so these fields
# are a reasonable starting guess (a weight reading, a battery level, and
# whether the reading is currently stable) rather than a spec. Adjust freely
# once the real firmware's payload is settled.

SCALE = NomosDeviceType(
    key="scale",
    name="Scale",
    model="NOMOS Scale",
    sensors=(
        NomosSensorDescriptor(
            key="weight",
            name="Weight",
            json_key="weight",
            device_class=SensorDeviceClass.WEIGHT,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        ),
        NomosSensorDescriptor(
            key="battery",
            name="Battery",
            json_key="battery",
            device_class=SensorDeviceClass.BATTERY,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=PERCENTAGE,
        ),
    ),
    binary_sensors=(
        NomosBinarySensorDescriptor(
            key="stable",
            name="Stable Reading",
            json_key="stable",
            icon="mdi:check-circle-outline",
        ),
    ),
    buttons=(
        NomosButtonDescriptor(
            key="tare",
            name="Tare",
            command_payload="TARE",
            icon="mdi:scale-balance",
        ),
    ),
)

DEVICE_TYPES: dict[str, NomosDeviceType] = {
    SCALE.key: SCALE,
}
