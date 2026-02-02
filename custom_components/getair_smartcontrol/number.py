"""Number entities for getAir SmartControl."""
import logging
from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import GetAirCoordinator
from .const import DOMAIN, MANUFACTURER

_LOGGER = logging.getLogger(__name__)


@dataclass
class GetAirNumberEntityDescription(NumberEntityDescription):
    """Describe getAir number entity."""

    zone_idx: int | None = None
    data_key: str | None = None


NUMBER_DESCRIPTIONS = []

# Add zone-specific numbers
for zone_idx in range(1, 4):
    # Target temperature (0x2030)
    NUMBER_DESCRIPTIONS.append(
        GetAirNumberEntityDescription(
            key=f"{zone_idx}_{{zone_name}}_target_temp",
            translation_key="zone_target_temperature_control",
            name="Zieltemperatur",
            data_key="target_temp",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            native_min_value=10.0,
            native_max_value=30.0,
            native_step=0.5,
            mode=NumberMode.SLIDER,
            icon="mdi:thermometer",
            zone_idx=zone_idx,
        )
    )
    
    # Filter runtime reset (0x2006)
    NUMBER_DESCRIPTIONS.append(
        GetAirNumberEntityDescription(
            key=f"{zone_idx}_{{zone_name}}_filter_runtime",
            translation_key="zone_filter_runtime_control",
            name="Filter-Laufzeit",
            data_key="last_filter_change",
            native_unit_of_measurement=UnitOfTime.HOURS,
            native_min_value=0,
            native_max_value=10000,
            native_step=1,
            mode=NumberMode.BOX,
            icon="mdi:air-filter",
            zone_idx=zone_idx,
        )
    )
    
    # Mode deadline (0x2021) - UNIX TIMESTAMP (direkt, für Power-User)
    NUMBER_DESCRIPTIONS.append(
        GetAirNumberEntityDescription(
            key=f"{zone_idx}_{{zone_name}}_mode_deadline_unix",
            translation_key="zone_mode_deadline_unix_control",
            name="Modus-Deadline (Unix)",
            data_key="mode_deadline",
            native_min_value=0,
            native_max_value=2147483647,  # Max Unix timestamp (2038)
            native_step=1,
            mode=NumberMode.BOX,
            icon="mdi:timer-cog-outline",
            zone_idx=zone_idx,
            entity_registry_enabled_default=False,  # Hidden by default
        )
    )
    
    # Mode deadline OFFSET (0-120 Minuten ab jetzt, benutzerfreundlich!)
    NUMBER_DESCRIPTIONS.append(
        GetAirNumberEntityDescription(
            key=f"{zone_idx}_{{zone_name}}_mode_deadline_offset",
            translation_key="zone_mode_deadline_offset_control",
            name="Modus-Dauer (Minuten ab jetzt)",
            data_key="mode_deadline_offset",  # Special handling
            native_min_value=0,
            native_max_value=120,  # 0-120 Minuten
            native_step=5,  # 5-Minuten-Schritte
            mode=NumberMode.SLIDER,
            icon="mdi:timer-plus-outline",
            zone_idx=zone_idx,
        )
    )


class GetAirNumber(CoordinatorEntity, NumberEntity):
    """Representation of a getAir number."""

    _attr_has_entity_name = False
    entity_description: GetAirNumberEntityDescription

    def __init__(
        self,
        coordinator: GetAirCoordinator,
        device_id: str,
        description: GetAirNumberEntityDescription,
    ):
        """Initialize the number entity."""
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
        """Return the name of the number."""
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

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        if not self.coordinator.data:
            return None

        zone_data = self.coordinator.data["zones"].get(self._zone_idx, {})
        data_key = self.entity_description.data_key
        
        # Special handling for mode_deadline_offset
        if data_key == "mode_deadline_offset":
            # Show remaining minutes until deadline
            deadline_unix = zone_data.get("mode_deadline")
            
            if deadline_unix is None or deadline_unix == 0:
                return 0  # No deadline set
            
            try:
                import time
                current_unix = int(time.time())
                remaining_seconds = int(deadline_unix) - current_unix
                remaining_minutes = max(0, remaining_seconds // 60)
                
                return float(remaining_minutes)
            except (ValueError, TypeError):
                return 0
        
        # Normal property - read directly
        value = zone_data.get(data_key)
        
        if value is not None:
            try:
                return float(value)
            except (ValueError, TypeError):
                _LOGGER.warning(
                    "Could not convert %s value to float: %s",
                    data_key,
                    value,
                )
                return None
        
        return None

    async def async_set_native_value(self, value: float) -> None:
        """Set the number value."""
        data_key = self.entity_description.data_key
        
        # Special handling for mode_deadline_offset
        if data_key == "mode_deadline_offset":
            # User entered minutes from now
            import time
            current_unix = int(time.time())
            minutes_offset = int(value)
            deadline_unix = current_unix + (minutes_offset * 60)
            
            _LOGGER.debug(
                "Setting mode_deadline_offset: %d minutes from now (Unix: %d)",
                minutes_offset,
                deadline_unix,
            )
            
            # Write to actual mode_deadline property
            success = await self.coordinator.async_set_zone_property(
                self._zone_idx,
                "mode_deadline",
                deadline_unix,
            )
        else:
            # Normal property - write directly
            _LOGGER.debug(
                "Setting %s for zone %s to %s",
                data_key,
                self._zone_idx,
                value,
            )
            
            success = await self.coordinator.async_set_zone_property(
                self._zone_idx,
                data_key,
                value,
            )
        
        if success:
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error(
                "Failed to set %s for zone %s",
                data_key if data_key != "mode_deadline_offset" else "mode_deadline",
                self._zone_idx,
            )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number entities."""
    coordinator: GetAirCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    device_id: str = hass.data[DOMAIN][config_entry.entry_id]["device_id"]
    enabled_zones: dict = hass.data[DOMAIN][config_entry.entry_id]["enabled_zones"]

    entities = []

    for description in NUMBER_DESCRIPTIONS:
        # Skip zone numbers if zone is not enabled
        if description.zone_idx is not None:
            if not enabled_zones.get(f"zone_{description.zone_idx}", True):
                continue

        entity = GetAirNumber(coordinator, device_id, description)
        entities.append(entity)

    async_add_entities(entities)
