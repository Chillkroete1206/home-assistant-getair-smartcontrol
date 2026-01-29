"""Select entities for getAir SmartControl."""
import logging
from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import GetAirCoordinator
from .const import DOMAIN, MANUFACTURER

_LOGGER = logging.getLogger(__name__)

# Available modes for getAir zones
AVAILABLE_MODES = [
    "ventilate",
    "ventilate_hr",
    "ventilate_inv",
    "night",
    "auto",
    "rush",
]


@dataclass
class GetAirSelectEntityDescription(SelectEntityDescription):
    """Describe getAir select entity."""

    zone_idx: int | None = None
    data_key: str | None = None


SELECT_DESCRIPTIONS = []

# Add zone-specific mode selectors
for zone_idx in range(1, 4):
    SELECT_DESCRIPTIONS.append(
        GetAirSelectEntityDescription(
            key=f"zone_{zone_idx}_betriebsmodus",  # German: operating mode
            translation_key="zone_mode",
            zone_idx=zone_idx,
            data_key="mode",
        )
    )


class GetAirZoneModeSelect(CoordinatorEntity, SelectEntity):
    """Representation of a getAir Zone mode selector."""

    _attr_has_entity_name = True
    _attr_options = AVAILABLE_MODES
    entity_description: GetAirSelectEntityDescription

    def __init__(
        self,
        coordinator: GetAirCoordinator,
        device_id: str,
        description: GetAirSelectEntityDescription,
    ):
        """Initialize the select entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._device_id = device_id
        self._zone_idx = description.zone_idx
        self._attr_unique_id = f"{device_id}_zone_{self._zone_idx}_betriebsmodus"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        zone_name = self.coordinator.data["zones"][self._zone_idx]["name"]
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._device_id}_zone_{self._zone_idx}")},
            name=zone_name,
            manufacturer=MANUFACTURER,
            model="SmartControl Zone",
            via_device=(DOMAIN, self._device_id),
        )

    @property
    def current_option(self) -> str | None:
        """Return the current mode."""
        if not self.coordinator.data:
            return None

        zone_data = self.coordinator.data["zones"].get(self._zone_idx, {})
        return zone_data.get("mode")

    async def async_select_option(self, option: str) -> None:
        """Select a new mode."""
        _LOGGER.debug(f"Setting zone {self._zone_idx} mode to {option}")
        success = await self.coordinator.async_set_zone_mode(self._zone_idx, option)
        if success:
            self.async_write_ha_state()
        else:
            _LOGGER.error(f"Failed to set zone {self._zone_idx} mode to {option}")


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up select entities."""
    coordinator: GetAirCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    device_id: str = hass.data[DOMAIN][config_entry.entry_id]["device_id"]
    enabled_zones: dict = hass.data[DOMAIN][config_entry.entry_id]["enabled_zones"]

    entities = []

    for description in SELECT_DESCRIPTIONS:
        # Skip zone selectors if zone is not enabled
        if description.zone_idx is not None:
            if not enabled_zones.get(f"zone_{description.zone_idx}", True):
                continue

        entity = GetAirZoneModeSelect(coordinator, device_id, description)
        entities.append(entity)

    async_add_entities(entities)
