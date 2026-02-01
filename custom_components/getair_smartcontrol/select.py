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
# Using German names directly since Home Assistant doesn't translate select options well
AVAILABLE_MODES = [
    "ventilate",        # API value
    "ventilate_hr",     
    "ventilate_inv",    
    "night",            
    "auto",             
    "rush",             
    "rush_hr",          
    "rush_inv",         
]

# Human-readable mode labels (German)
MODE_LABELS = {
    "ventilate": "Normales Lüften",
    "ventilate_hr": "Lüften mit WRG",
    "ventilate_inv": "Inverses Lüften",
    "night": "Nachtmodus",
    "auto": "Automatik",
    "rush": "Stoßlüften",
    "rush_hr": "Stoßlüften mit WRG",
    "rush_inv": "Inverses Stoßlüften",
}

# Target humidity level options
HUMIDITY_LEVEL_LABELS = {
    "thirty-fifty": "30-50%",
    "fourty-sixty": "40-60%",
    "fifty-seventy": "50-70%",
}


@dataclass
class GetAirSelectEntityDescription(SelectEntityDescription):
    """Describe getAir select entity."""

    zone_idx: int | None = None
    data_key: str | None = None


SELECT_DESCRIPTIONS = []

# Add zone-specific mode selectors
for zone_idx in range(1, 4):
    # Operating mode
    SELECT_DESCRIPTIONS.append(
        GetAirSelectEntityDescription(
            key=f"{zone_idx}_{{zone_name}}_mode",
            translation_key="zone_mode",
            name="Betriebsmodus",
            zone_idx=zone_idx,
            data_key="mode",
            icon="mdi:fan-auto",
        )
    )
    
    # Target humidity level (0x2031)
    SELECT_DESCRIPTIONS.append(
        GetAirSelectEntityDescription(
            key=f"{zone_idx}_{{zone_name}}_target_humidity",
            translation_key="zone_target_humidity_control",
            name="Ziel-Luftfeuchtigkeit",
            zone_idx=zone_idx,
            data_key="target_hmdty_level",
            icon="mdi:water-percent",
        )
    )
    
    # Time profile (0x2050)
    SELECT_DESCRIPTIONS.append(
        GetAirSelectEntityDescription(
            key=f"{zone_idx}_{{zone_name}}_time_profile",
            translation_key="zone_time_profile_control",
            name="Zeitprofil",
            zone_idx=zone_idx,
            data_key="time_profile",
            icon="mdi:clock-outline",
        )
    )



class GetAirSelect(CoordinatorEntity, SelectEntity):
    """Representation of a getAir select entity."""

    _attr_has_entity_name = False
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
        
        # Build entity_id with getair prefix, device_id, and zone name
        zone_name = coordinator.data["zones"][self._zone_idx]["name"]
        zone_name_clean = zone_name.lower().replace(" ", "_").replace("-", "_")
        zone_name_clean = "".join(c if c.isalnum() or c == "_" else "_" for c in zone_name_clean)
        
        key_with_zone = description.key.replace("{zone_name}", zone_name_clean)
        self._attr_unique_id = f"getair_{device_id}_{key_with_zone}"

    @property
    def name(self) -> str:
        """Return the name of the select."""
        if self.coordinator.data:
            zone_name = self.coordinator.data["zones"][self._zone_idx]["name"]
            return f"{zone_name} {self.entity_description.name}"
        return self.entity_description.name

    @property
    def options(self) -> list[str]:
        """Return the list of available options with labels."""
        data_key = self.entity_description.data_key
        
        # Mode selector
        if data_key == "mode":
            return [MODE_LABELS[mode] for mode in AVAILABLE_MODES]
        
        # Target humidity selector
        elif data_key == "target_hmdty_level":
            return list(HUMIDITY_LEVEL_LABELS.values())
        
        # Time profile selector - show only profiles that have names
        elif data_key == "time_profile":
            if not self.coordinator.data:
                _LOGGER.warning("Time profile options: No coordinator data available")
                return ["Kein Profil"]  # Fallback
            
            system_data = self.coordinator.data.get("system", {})
            available_profiles = ["Kein Profil"]  # Always include "no profile" option
            
            # Check profiles 1-10 and add those with names
            for i in range(1, 11):
                profile_name = system_data.get(f"time_profile_{i}_name", "")
                if profile_name and profile_name.strip():  # Only if name exists and is not empty
                    available_profiles.append(profile_name)
            
            return available_profiles
        
        return []

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
        """Return the current option (translated to label)."""
        if not self.coordinator.data:
            return None

        zone_data = self.coordinator.data["zones"].get(self._zone_idx, {})
        data_key = self.entity_description.data_key
        api_value = zone_data.get(data_key)
        
        if api_value is None:
            return None
        
        # Mode selector
        if data_key == "mode":
            if api_value in MODE_LABELS:
                return MODE_LABELS[api_value]
        
        # Target humidity selector
        elif data_key == "target_hmdty_level":
            if api_value in HUMIDITY_LEVEL_LABELS:
                return HUMIDITY_LEVEL_LABELS[api_value]
        
        # Time profile selector - show actual profile name
        elif data_key == "time_profile":
            try:
                profile_num = int(api_value)
                
                # Profile 0 = no profile
                if profile_num == 0:
                    return "Kein Profil"
                
                # Get actual profile name from system data
                system_data = self.coordinator.data.get("system", {})
                profile_name = system_data.get(f"time_profile_{profile_num}_name", "")
                
                if profile_name and profile_name.strip():
                    return profile_name
                else:
                    # Fallback if name not found
                    return f"Profil {profile_num}"
                    
            except (ValueError, TypeError):
                pass
        
        return str(api_value)  # Fallback

    async def async_select_option(self, option: str) -> None:
        """Select a new option (convert from label to API value)."""
        data_key = self.entity_description.data_key
        api_value = None
        
        # Mode selector - convert label to API value
        if data_key == "mode":
            for mode, label in MODE_LABELS.items():
                if label == option:
                    api_value = mode
                    break
        
        # Target humidity selector
        elif data_key == "target_hmdty_level":
            for value, label in HUMIDITY_LEVEL_LABELS.items():
                if label == option:
                    api_value = value
                    break
        
        # Time profile selector - convert name back to profile number
        elif data_key == "time_profile":
            # Special case: "Kein Profil" = 0
            if option == "Kein Profil":
                api_value = 0
            else:
                # Find profile number by name
                system_data = self.coordinator.data.get("system", {})
                for i in range(1, 11):
                    profile_name = system_data.get(f"time_profile_{i}_name", "")
                    if profile_name == option:
                        api_value = i
                        break
        
        if api_value is None:
            _LOGGER.error("Unknown option: %s for %s", option, data_key)
            return
        
        _LOGGER.debug("Setting zone %s %s to %s (type: %s) (%s)", 
                     self._zone_idx, data_key, api_value, type(api_value).__name__, option)
        
        # Use the appropriate coordinator method
        if data_key == "mode":
            success = await self.coordinator.async_set_zone_mode(self._zone_idx, api_value)
        elif data_key == "time_profile":
            # Special handling: time_profile needs to use active_time_profile in API
            success = await self.coordinator.async_set_zone_property(
                self._zone_idx,
                "active_time_profile",  # API uses 'active_time_profile'
                api_value,
            )
        else:
            success = await self.coordinator.async_set_zone_property(
                self._zone_idx,
                data_key,
                api_value,
            )
        
        if success:
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to set zone %s %s to %s", self._zone_idx, data_key, api_value)


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

        entity = GetAirSelect(coordinator, device_id, description)
        entities.append(entity)

    async_add_entities(entities)
