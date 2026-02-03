"""Button entities for getAir SmartControl."""
import logging
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import GetAirCoordinator
from .const import DOMAIN, MANUFACTURER

_LOGGER = logging.getLogger(__name__)


@dataclass
class GetAirButtonEntityDescription(ButtonEntityDescription):
    """Describe getAir button entity."""

    zone_idx: int | None = None
    data_key: str | None = None
    reset_value: int | float = 0


BUTTON_DESCRIPTIONS = []

# Add zone-specific buttons
for zone_idx in range(1, 4):
    # Filter runtime reset button
    BUTTON_DESCRIPTIONS.append(
        GetAirButtonEntityDescription(
            key=f"{zone_idx}_{{zone_name}}_reset_filter_runtime",
            translation_key="zone_reset_filter_runtime",
            name="Filter-Laufzeit zurücksetzen",
            data_key="last_filter_change",
            icon="mdi:air-filter",
            zone_idx=zone_idx,
            reset_value=0,
        )
    )
    
    # Mode deadline reset button
    BUTTON_DESCRIPTIONS.append(
        GetAirButtonEntityDescription(
            key=f"{zone_idx}_{{zone_name}}_reset_mode_deadline",
            translation_key="zone_reset_mode_deadline",
            name="Modus-Deadline zurücksetzen",
            data_key="mode_deadline",
            icon="mdi:timer-off-outline",
            zone_idx=zone_idx,
            reset_value=0,
        )
    )


class GetAirButton(CoordinatorEntity, ButtonEntity):
    """Representation of a getAir button."""

    _attr_has_entity_name = False
    entity_description: GetAirButtonEntityDescription

    def __init__(
        self,
        coordinator: GetAirCoordinator,
        device_id: str,
        description: GetAirButtonEntityDescription,
    ):
        """Initialize the button entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._device_id = device_id
        self._zone_idx = description.zone_idx
        
        # Build entity_id with getair prefix, device_id, and zone name
        zone_name = coordinator.data["zones"][self._zone_idx]["name"]
        zone_name_clean = zone_name.lower().replace(" ", "_").replace("-", "_")
        zone_name_clean = "".join(c if c.isalnum() or c == "_" else "_" for c in zone_name_clean)
        
        key_with_zone = description.key.replace("{zone_name}", zone_name_clean)
        self._attr_unique_id = f"getair_{device_id}_{key_with_zone}"

    @property
    def name(self) -> str:
        """Return the name of the button."""
        if self.coordinator.data:
            zone_name = self.coordinator.data["zones"][self._zone_idx]["name"]
            return f"{zone_name} {self.entity_description.name}"
        return self.entity_description.name

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

    async def async_press(self) -> None:
        """Handle the button press."""
        data_key = self.entity_description.data_key
        reset_value = self.entity_description.reset_value
        
        _LOGGER.info(
            "Resetting %s for zone %s to %s",
            data_key,
            self._zone_idx,
            reset_value,
        )
        
        success = await self.coordinator.async_set_zone_property(
            self._zone_idx,
            data_key,
            reset_value,
        )
        
        if success:
            _LOGGER.info(
                "Successfully reset %s for zone %s",
                data_key,
                self._zone_idx,
            )
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error(
                "Failed to reset %s for zone %s",
                data_key,
                self._zone_idx,
            )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button entities."""
    coordinator: GetAirCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    device_id: str = hass.data[DOMAIN][config_entry.entry_id]["device_id"]
    enabled_zones: dict = hass.data[DOMAIN][config_entry.entry_id]["enabled_zones"]

    entities = []

    for description in BUTTON_DESCRIPTIONS:
        # Skip zone buttons if zone is not enabled
        if description.zone_idx is not None:
            if not enabled_zones.get(f"zone_{description.zone_idx}", True):
                continue

        entity = GetAirButton(coordinator, device_id, description)
        entities.append(entity)

    async_add_entities(entities)
