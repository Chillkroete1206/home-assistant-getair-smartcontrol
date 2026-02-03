"""Datetime entities for getAir SmartControl."""
import logging
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.datetime import DateTimeEntity, DateTimeEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import GetAirCoordinator
from .const import DOMAIN, MANUFACTURER

_LOGGER = logging.getLogger(__name__)


@dataclass
class GetAirDateTimeEntityDescription(DateTimeEntityDescription):
    """Describe getAir datetime entity."""

    zone_idx: int | None = None
    data_key: str | None = None


DATETIME_DESCRIPTIONS = []

# Add zone-specific datetime entities  
for zone_idx in range(1, 4):
    # Mode deadline as datetime picker
    DATETIME_DESCRIPTIONS.append(
        GetAirDateTimeEntityDescription(
            key=f"{zone_idx}_{{zone_name}}_mode_deadline_datetime",
            translation_key="zone_mode_deadline_datetime_control",
            name="Modus-Deadline (Datum/Uhrzeit)",
            data_key="mode_deadline",
            icon="mdi:calendar-clock",
            zone_idx=zone_idx,
        )
    )


class GetAirDateTime(CoordinatorEntity, DateTimeEntity):
    """Representation of a getAir datetime entity."""

    _attr_has_entity_name = False
    entity_description: GetAirDateTimeEntityDescription

    def __init__(
        self,
        coordinator: GetAirCoordinator,
        device_id: str,
        description: GetAirDateTimeEntityDescription,
    ):
        """Initialize the datetime entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._device_id = device_id
        self._zone_idx = description.zone_idx
        
        # Build entity_id
        zone_name = coordinator.data["zones"][self._zone_idx]["name"]
        zone_name_clean = zone_name.lower().replace(" ", "_").replace("-", "_")
        zone_name_clean = "".join(c if c.isalnum() or c == "_" else "_" for c in zone_name_clean)
        
        key_with_zone = description.key.replace("{zone_name}", zone_name_clean)
        self._attr_unique_id = f"getair_{device_id}_{key_with_zone}"

    @property
    def name(self) -> str:
        """Return the name of the datetime."""
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
    def native_value(self) -> datetime | None:
        """Return the current datetime value."""
        if not self.coordinator.data:
            return None

        zone_data = self.coordinator.data["zones"].get(self._zone_idx, {})
        deadline_unix = zone_data.get("mode_deadline")
        
        if not deadline_unix or deadline_unix == 0:
            return None
        
        try:
            # Convert Unix timestamp to datetime with Home Assistant's timezone
            import homeassistant.util.dt as dt_util
            return datetime.fromtimestamp(int(deadline_unix), tz=dt_util.DEFAULT_TIME_ZONE)
        except (ValueError, TypeError, OSError):
            return None

    async def async_set_value(self, value: datetime) -> None:
        """Set the datetime value."""
        try:
            # Convert datetime to Unix timestamp
            deadline_unix = int(value.timestamp())
            
            _LOGGER.debug(
                "Setting mode_deadline for zone %s to %s (Unix: %d)",
                self._zone_idx,
                value.isoformat(),
                deadline_unix,
            )
            
            success = await self.coordinator.async_set_zone_property(
                self._zone_idx,
                "mode_deadline",
                deadline_unix,
            )
            
            if success:
                await self.coordinator.async_request_refresh()
            else:
                _LOGGER.error(
                    "Failed to set mode_deadline for zone %s",
                    self._zone_idx,
                )
        except (ValueError, TypeError) as err:
            _LOGGER.error(
                "Error converting datetime to Unix timestamp: %s",
                err,
            )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up datetime entities."""
    coordinator: GetAirCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    device_id: str = hass.data[DOMAIN][config_entry.entry_id]["device_id"]
    enabled_zones: dict = hass.data[DOMAIN][config_entry.entry_id]["enabled_zones"]

    entities = []

    for description in DATETIME_DESCRIPTIONS:
        # Skip zone datetimes if zone is not enabled
        if description.zone_idx is not None:
            if not enabled_zones.get(f"zone_{description.zone_idx}", True):
                continue

        entity = GetAirDateTime(coordinator, device_id, description)
        entities.append(entity)

    async_add_entities(entities)
