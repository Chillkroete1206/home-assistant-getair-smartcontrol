"""Binary sensor entities for getAir SmartControl."""
import logging
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import GetAirCoordinator
from .const import DOMAIN, MANUFACTURER

_LOGGER = logging.getLogger(__name__)


@dataclass
class GetAirBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describe getAir binary sensor entity."""

    zone_idx: int | None = None
    data_key: str | None = None


BINARY_SENSOR_DESCRIPTIONS = [
    # System-level binary sensors
    GetAirBinarySensorEntityDescription(
        key="system_modelock_state",
        translation_key="system_modelock",
        data_key="modelock",
        zone_idx=None,
    ),
]

# Add zone-specific binary sensors
for zone_idx in range(1, 4):
    for data_key, key_suffix, translation_key in [
        ("auto_mode_voc", "auto_mode_voc", "zone_auto_mode_voc"),
        ("auto_mode_silent", "auto_mode_silent", "zone_auto_mode_silent"),
    ]:
        BINARY_SENSOR_DESCRIPTIONS.append(
            GetAirBinarySensorEntityDescription(
                key=f"zone_{zone_idx}_{key_suffix}",
                translation_key=translation_key,
                data_key=data_key,
                zone_idx=zone_idx,
            )
        )


class GetAirBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a getAir binary sensor."""

    _attr_has_entity_name = True
    entity_description: GetAirBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: GetAirCoordinator,
        device_id: str,
        description: GetAirBinarySensorEntityDescription,
    ):
        """Initialize the binary sensor entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._device_id = device_id
        self._zone_idx = description.zone_idx

        if self._zone_idx:
            self._attr_unique_id = f"{device_id}_zone_{self._zone_idx}_{description.key}"
        else:
            self._attr_unique_id = f"{device_id}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        if self._zone_idx:
            zone_name = self.coordinator.data["zones"][self._zone_idx]["name"]
            return DeviceInfo(
                identifiers={(DOMAIN, f"{self._device_id}_zone_{self._zone_idx}")},
                name=zone_name,
                manufacturer=MANUFACTURER,
                model="SmartControl Zone",
                via_device=(DOMAIN, self._device_id),
            )
        else:
            # System device with full hardware info
            system_data = self.coordinator.data["system"]
            return DeviceInfo(
                identifiers={(DOMAIN, self._device_id)},
                name=f"getAir {system_data.get('system_type', 'SmartControl')}",
                manufacturer=MANUFACTURER,
                model=system_data.get("system_type", "SmartControl"),
                sw_version=system_data.get("fw_version", "Unknown"),
                serial_number=system_data.get("system_id", self._device_id),
            )

    @property
    def is_on(self) -> bool | None:
        """Return the binary sensor value."""
        if not self.coordinator.data:
            return None

        if self._zone_idx:
            zone_data = self.coordinator.data["zones"].get(self._zone_idx, {})
            return zone_data.get(self.entity_description.data_key)
        else:
            system_data = self.coordinator.data["system"]
            return system_data.get(self.entity_description.data_key)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor entities."""
    coordinator: GetAirCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    device_id: str = hass.data[DOMAIN][config_entry.entry_id]["device_id"]
    enabled_zones: dict = hass.data[DOMAIN][config_entry.entry_id]["enabled_zones"]

    entities = []

    for description in BINARY_SENSOR_DESCRIPTIONS:
        # Skip zone sensors if zone is not enabled
        if description.zone_idx is not None:
            if not enabled_zones.get(f"zone_{description.zone_idx}", True):
                continue

        entity = GetAirBinarySensor(coordinator, device_id, description)
        entities.append(entity)

    async_add_entities(entities)
