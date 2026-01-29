"""Fan entities for getAir SmartControl."""
import logging
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import GetAirCoordinator
from .const import DOMAIN, MANUFACTURER

_LOGGER = logging.getLogger(__name__)

# Map of getAir speed values (0.5-4.0) to percentage (0-100)
SPEED_TO_PERCENT = {
    0.5: 15,
    1.0: 30,
    1.5: 45,
    2.0: 60,
    2.5: 75,
    3.0: 85,
    3.5: 95,
    4.0: 100,
}

PERCENT_TO_SPEED = {v: k for k, v in SPEED_TO_PERCENT.items()}


class GetAirZoneFan(CoordinatorEntity, FanEntity):
    """Representation of a getAir Zone as a Fan entity."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = FanEntityFeature.SET_SPEED | FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF

    def __init__(
        self,
        coordinator: GetAirCoordinator,
        device_id: str,
        zone_idx: int,
        zone_name: str,
    ):
        """
        Initialize the fan entity.

        :param coordinator: Data coordinator
        :param device_id: Device ID
        :param zone_idx: Zone index (1-3)
        :param zone_name: Zone name for display
        """
        super().__init__(coordinator)
        self._device_id = device_id
        self._zone_idx = zone_idx
        self._attr_unique_id = f"{device_id}_zone_{zone_idx}"
        self._attr_translation_key = f"zone_{zone_idx}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._device_id}_zone_{self._zone_idx}")},
            name=self.coordinator.data["zones"][self._zone_idx]["name"],
            manufacturer=MANUFACTURER,
            model="SmartControl Zone",
            via_device=(DOMAIN, self._device_id),
        )

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage."""
        if not self.coordinator.data:
            return None

        speed = self.coordinator.data["zones"][self._zone_idx].get("speed")
        if speed is None:
            return None

        # Find closest percentage
        closest_percent = min(PERCENT_TO_SPEED.keys(), key=lambda x: abs(PERCENT_TO_SPEED[x] - speed))
        return closest_percent

    @property
    def is_on(self) -> bool:
        """Return True if fan is on."""
        return self.percentage and self.percentage > 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}

        zone_data = self.coordinator.data["zones"][self._zone_idx]
        
        return {
            "mode": zone_data.get("mode"),
            "temperature": zone_data.get("temperature"),
            "humidity": zone_data.get("humidity"),
            "target_temperature": zone_data.get("target_temp"),
            "target_humidity_level": zone_data.get("target_hmdty_level"),
            "outdoor_temperature": zone_data.get("outdoor_temp"),
            "outdoor_humidity": zone_data.get("outdoor_humidity"),
            "runtime_hours": zone_data.get("runtime"),
            "filter_runtime_hours": zone_data.get("last_filter_change"),
            "auto_mode_voc": zone_data.get("auto_mode_voc"),
            "auto_mode_silent": zone_data.get("auto_mode_silent"),
            "active_time_profile": zone_data.get("time_profile"),
            "mode_deadline": zone_data.get("mode_deadline"),
        }

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        if percentage is None:
            percentage = 30  # Default to 30%

        await self.async_set_percentage(percentage)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan."""
        # Set to minimum speed (0.5 = 15%)
        await self.async_set_percentage(15)

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage."""
        # Find closest speed value
        closest_speed = PERCENT_TO_SPEED.get(
            min(PERCENT_TO_SPEED.keys(), key=lambda x: abs(x - percentage))
        )

        if closest_speed is None:
            _LOGGER.error(f"Invalid percentage: {percentage}")
            return

        _LOGGER.debug(f"Setting zone {self._zone_idx} speed to {closest_speed}")

        success = await self.coordinator.async_set_zone_speed(self._zone_idx, closest_speed)
        if success:
            self.async_write_ha_state()
        else:
            _LOGGER.error(f"Failed to set zone {self._zone_idx} speed")


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up fan entities."""
    coordinator: GetAirCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    device_id: str = hass.data[DOMAIN][config_entry.entry_id]["device_id"]
    enabled_zones: dict = hass.data[DOMAIN][config_entry.entry_id]["enabled_zones"]

    entities = []
    
    for zone_idx in range(1, 4):
        if enabled_zones.get(f"zone_{zone_idx}", True):
            zone_name = f"Zone {zone_idx}"
            entity = GetAirZoneFan(coordinator, device_id, zone_idx, zone_name)
            entities.append(entity)

    async_add_entities(entities)
