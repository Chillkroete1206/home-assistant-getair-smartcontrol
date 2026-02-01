"""Text entities for getAir SmartControl."""
import logging
from dataclasses import dataclass

from homeassistant.components.text import TextEntity, TextEntityDescription, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import GetAirCoordinator
from .const import DOMAIN, MANUFACTURER

_LOGGER = logging.getLogger(__name__)


@dataclass
class GetAirTextEntityDescription(TextEntityDescription):
    """Describe getAir text entity."""

    zone_idx: int | None = None
    data_key: str | None = None


TEXT_DESCRIPTIONS = []

# Add zone name text entities
for zone_idx in range(1, 4):
    TEXT_DESCRIPTIONS.append(
        GetAirTextEntityDescription(
            key=f"zone_{zone_idx}_name",
            translation_key="zone_name",
            data_key="name",
            mode=TextMode.TEXT,
            zone_idx=zone_idx,
        )
    )


class GetAirText(CoordinatorEntity, TextEntity):
    """Representation of a getAir text entity."""

    _attr_has_entity_name = True
    _attr_native_max = 50  # Maximum length for zone name
    _attr_native_min = 1   # Minimum length
    entity_description: GetAirTextEntityDescription

    def __init__(
        self,
        coordinator: GetAirCoordinator,
        device_id: str,
        description: GetAirTextEntityDescription,
    ):
        """Initialize the text entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._device_id = device_id
        self._zone_idx = description.zone_idx
        self._attr_unique_id = f"{device_id}_zone_{self._zone_idx}_{description.key}"

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
    def native_value(self) -> str | None:
        """Return the current zone name."""
        if not self.coordinator.data:
            return None

        zone_data = self.coordinator.data["zones"].get(self._zone_idx, {})
        return zone_data.get(self.entity_description.data_key)

    async def async_set_value(self, value: str) -> None:
        """Set the zone name."""
        _LOGGER.debug(
            "Setting zone %s name to: %s",
            self._zone_idx,
            value,
        )
        
        success = await self.coordinator.async_set_zone_property(
            self._zone_idx,
            self.entity_description.data_key,
            value,
        )
        
        if success:
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error(
                "Failed to set zone %s name",
                self._zone_idx,
            )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up text entities."""
    coordinator: GetAirCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    device_id: str = hass.data[DOMAIN][config_entry.entry_id]["device_id"]
    enabled_zones: dict = hass.data[DOMAIN][config_entry.entry_id]["enabled_zones"]

    entities = []

    for description in TEXT_DESCRIPTIONS:
        # Skip zone text entities if zone is not enabled
        if description.zone_idx is not None:
            if not enabled_zones.get(f"zone_{description.zone_idx}", True):
                continue

        entity = GetAirText(coordinator, device_id, description)
        entities.append(entity)

    async_add_entities(entities)
