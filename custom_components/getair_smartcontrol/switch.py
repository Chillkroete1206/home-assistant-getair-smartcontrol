"""Switch entities for getAir SmartControl."""
import logging
from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import GetAirCoordinator
from .const import DOMAIN, MANUFACTURER

_LOGGER = logging.getLogger(__name__)


@dataclass
class GetAirSwitchEntityDescription(SwitchEntityDescription):
    """Describe getAir switch entity."""

    zone_idx: int | None = None
    data_key: str | None = None


SWITCH_DESCRIPTIONS = []

# Add zone-specific switches
for zone_idx in range(1, 4):
    for data_key, key_suffix, translation_key, name_de in [
        ("auto_mode_voc", "voc", "zone_auto_mode_voc_switch", "VOC Auto-Modus"),
        ("auto_mode_silent", "silent", "zone_auto_mode_silent_switch", "Silent-Modus"),
    ]:
        SWITCH_DESCRIPTIONS.append(
            GetAirSwitchEntityDescription(
                key=f"{zone_idx}_{{zone_name}}_{key_suffix}",  # Placeholder for zone name
                translation_key=translation_key,
                name=name_de,
                data_key=data_key,
                zone_idx=zone_idx,
            )
        )

class GetAirSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a getAir switch."""

    _attr_has_entity_name = False
    entity_description: GetAirSwitchEntityDescription

    def __init__(
        self,
        coordinator: GetAirCoordinator,
        device_id: str,
        description: GetAirSwitchEntityDescription,
    ):
        """Initialize the switch entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._device_id = device_id
        self._zone_idx = description.zone_idx

        # Set icon based on data_key
        if description.data_key == "auto_mode_voc":
            self._attr_icon = "mdi:air-filter"
        elif description.data_key == "auto_mode_silent":
            self._attr_icon = "mdi:weather-night"
        elif description.data_key == "auto_update_enabled":
            self._attr_icon = "mdi:update"

        # Build entity_id with getair prefix, device_id, and zone name
        if self._zone_idx:
            # Get zone name from coordinator and sanitize it for entity_id
            zone_name = coordinator.data["zones"][self._zone_idx]["name"]
            # Sanitize zone name: lowercase, replace spaces/special chars with underscore
            zone_name_clean = zone_name.lower().replace(" ", "_").replace("-", "_")
            zone_name_clean = "".join(c if c.isalnum() or c == "_" else "_" for c in zone_name_clean)
            
            # Replace placeholder in key with actual zone name
            key_with_zone = description.key.replace("{zone_name}", zone_name_clean)
            
            # Entity ID pattern: getair_<device_id>_<zone_idx>_<zone_name>_<suffix>
            self._attr_unique_id = f"getair_{device_id}_{key_with_zone}"
        else:
            # System-level switch: getair_<device_id>_<key>
            self._attr_unique_id = f"getair_{device_id}_{description.key}"

    @property
    def name(self) -> str:
        """Return the name of the switch."""
        if self._zone_idx and self.coordinator.data:
            zone_name = self.coordinator.data["zones"][self._zone_idx]["name"]
            return f"{zone_name} {self.entity_description.name}"
        return self.entity_description.name

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
        """Return the switch state."""
        if not self.coordinator.data:
            return None

        if self._zone_idx:
            zone_data = self.coordinator.data["zones"].get(self._zone_idx, {})
            return zone_data.get(self.entity_description.data_key)
        else:
            system_data = self.coordinator.data["system"]
            return system_data.get(self.entity_description.data_key)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        _LOGGER.debug(
            "Turning on %s for %s",
            self.entity_description.data_key,
            f"zone {self._zone_idx}" if self._zone_idx else "system",
        )

        if self._zone_idx:
            success = await self.coordinator.async_set_zone_property(
                self._zone_idx,
                self.entity_description.data_key,
                True,
            )
        else:
            success = await self.coordinator.async_set_system_property(
                self.entity_description.data_key,
                True,
            )

        if success:
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to turn on switch")

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        _LOGGER.debug(
            "Turning off %s for %s",
            self.entity_description.data_key,
            f"zone {self._zone_idx}" if self._zone_idx else "system",
        )

        if self._zone_idx:
            success = await self.coordinator.async_set_zone_property(
                self._zone_idx,
                self.entity_description.data_key,
                False,
            )
        else:
            success = await self.coordinator.async_set_system_property(
                self.entity_description.data_key,
                False,
            )

        if success:
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to turn off switch")


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch entities."""
    coordinator: GetAirCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    device_id: str = hass.data[DOMAIN][config_entry.entry_id]["device_id"]
    enabled_zones: dict = hass.data[DOMAIN][config_entry.entry_id]["enabled_zones"]

    entities = []

    for description in SWITCH_DESCRIPTIONS:
        # Skip zone switches if zone is not enabled
        if description.zone_idx is not None:
            if not enabled_zones.get(f"zone_{description.zone_idx}", True):
                continue

        entity = GetAirSwitch(coordinator, device_id, description)
        entities.append(entity)

    async_add_entities(entities)
