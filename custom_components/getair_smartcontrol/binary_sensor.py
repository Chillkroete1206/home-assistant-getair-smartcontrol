"""Binary sensor entities for getAir SmartControl."""
import logging
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
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


# Only keep system-level binary sensors here. Zone Silent/VOC are exposed as switches.
BINARY_SENSOR_DESCRIPTIONS = [
    # System-level binary sensors
    GetAirBinarySensorEntityDescription(
        key="modelock",
        translation_key="system_modelock",
        name="Modus-Sperre",
        icon="mdi:lock-outline",
        data_key="modelock",
        zone_idx=None,
    ),
    GetAirBinarySensorEntityDescription(
        key="supports_auto_update",
        translation_key="system_supports_auto_update",
        name="Unterstützt Auto-Update",
        icon="mdi:update",
        data_key="supports_auto_update",
        zone_idx=None,
    ),
    GetAirBinarySensorEntityDescription(
        key="auto_update_enabled",
        translation_key="system_auto_update_enabled",
        name="Auto-Update aktiviert",
        icon="mdi:download-circle-outline",
        data_key="auto_update_enabled",
        zone_idx=None,
    ),
]


class GetAirBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a getAir binary sensor."""

    _attr_has_entity_name = False
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

        # Build clean entity_id
        if self._zone_idx:
            zone_name = coordinator.data["zones"][self._zone_idx]["name"]
            zone_name_clean = zone_name.lower().replace(" ", "_").replace("-", "_")
            zone_name_clean = "".join(c if c.isalnum() or c == "_" else "_" for c in zone_name_clean)
            self._attr_unique_id = f"getair_{device_id}_zone_{self._zone_idx}_{zone_name_clean}_{description.key}"
        else:
            self._attr_unique_id = f"getair_{device_id}_{description.key}"

    @property
    def name(self) -> str:
        """Return the name of the binary sensor."""
        # Get name from entity description
        if hasattr(self.entity_description, 'name') and self.entity_description.name:
            base_name = self.entity_description.name
        else:
            # Fallback: use key as name
            base_name = self.entity_description.key.replace("_", " ").title()
        
        # For zone sensors, prepend zone name
        if self._zone_idx and self.coordinator.data:
            zone_name = self.coordinator.data["zones"][self._zone_idx]["name"]
            return f"{zone_name} {base_name}"
        
        return base_name

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
