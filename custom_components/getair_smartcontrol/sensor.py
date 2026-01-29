"""Sensor entities for getAir SmartControl."""
import logging
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
    SensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, PERCENTAGE, UnitOfPressure, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import GetAirCoordinator
from .const import DOMAIN, MANUFACTURER

_LOGGER = logging.getLogger(__name__)


def format_datetime(iso_string: str) -> str:
    """Convert ISO datetime string to readable German format.
    
    Example: "2026-01-29T07:28:37.420528+00:00" → "29. Januar 2026 um 07:28:37"
    """
    if not iso_string:
        return None
    
    try:
        # Parse ISO format
        dt = datetime.fromisoformat(iso_string)
        
        # German month names
        german_months = {
            1: "Januar", 2: "Februar", 3: "März", 4: "April",
            5: "Mai", 6: "Juni", 7: "Juli", 8: "August",
            9: "September", 10: "Oktober", 11: "November", 12: "Dezember"
        }
        
        # Format: "29. Januar 2026 um 07:28:37"
        month_name = german_months.get(dt.month, "")
        return dt.strftime(f"%d. {month_name} %Y um %H:%M:%S")
    except Exception as e:
        _LOGGER.warning("Could not format datetime %s: %s", iso_string, e)
        return iso_string


@dataclass
class GetAirSensorEntityDescription(SensorEntityDescription):
    """Describe getAir sensor entity."""

    zone_idx: int | None = None
    data_key: str | None = None


SENSOR_DESCRIPTIONS = [
    # System-wide sensors with descriptive keys
    GetAirSensorEntityDescription(
        key="system_air_quality_iaq",
        translation_key="system_air_quality",
        data_key="air_quality",
        native_unit_of_measurement="ppm",
        state_class=SensorStateClass.MEASUREMENT,
        zone_idx=None,
    ),
    GetAirSensorEntityDescription(
        key="system_air_pressure_hpa",
        translation_key="system_air_pressure",
        data_key="air_pressure",
        native_unit_of_measurement=UnitOfPressure.HPA,
        state_class=SensorStateClass.MEASUREMENT,
        zone_idx=None,
    ),
    GetAirSensorEntityDescription(
        key="system_humidity_percent",
        translation_key="system_humidity",
        data_key="humidity",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.HUMIDITY,
        zone_idx=None,
    ),
    GetAirSensorEntityDescription(
        key="system_temperature_celsius",
        translation_key="system_temperature",
        data_key="temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        zone_idx=None,
    ),
    GetAirSensorEntityDescription(
        key="system_runtime_hours",
        translation_key="system_runtime",
        data_key="runtime",
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL,
        zone_idx=None,
    ),
    GetAirSensorEntityDescription(
        key="system_boot_time_datetime",
        translation_key="system_boot_time",
        data_key="boot_time",
        zone_idx=None,
    ),
    GetAirSensorEntityDescription(
        key="system_iaq_accuracy_level",
        translation_key="system_iaq_accuracy",
        data_key="iaq_accuracy",
        zone_idx=None,
    ),
    GetAirSensorEntityDescription(
        key="system_num_zones_count",
        translation_key="system_num_zones",
        data_key="num_zones",
        zone_idx=None,
    ),
    GetAirSensorEntityDescription(
        key="system_modelock_state",
        translation_key="system_modelock",
        data_key="modelock",
        zone_idx=None,
    ),
    GetAirSensorEntityDescription(
        key="system_last_update_datetime",
        translation_key="last_update",
        data_key="last_update",
        zone_idx=None,
    ),
    GetAirSensorEntityDescription(
        key="system_connection_status",
        translation_key="connection_status",
        data_key="connection_status",
        zone_idx=None,
    ),
]

# Add zone-specific sensors with descriptive keys
for zone_idx in range(1, 4):
    for data_key, key_suffix, translation_key, unit, device_class, state_class in [
        ("temperature", "temperature_celsius", "zone_temperature", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT),
        ("humidity", "humidity_percent", "zone_humidity", PERCENTAGE, SensorDeviceClass.HUMIDITY, SensorStateClass.MEASUREMENT),
        ("outdoor_temp", "outdoor_temperature_celsius", "zone_outdoor_temperature", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT),
        ("outdoor_humidity", "outdoor_humidity_percent", "zone_outdoor_humidity", PERCENTAGE, SensorDeviceClass.HUMIDITY, SensorStateClass.MEASUREMENT),
        ("runtime", "runtime_hours", "zone_runtime", UnitOfTime.HOURS, None, SensorStateClass.TOTAL),
        ("last_filter_change", "filter_runtime_hours", "zone_filter_runtime", UnitOfTime.HOURS, None, SensorStateClass.TOTAL),
        ("target_temp", "target_temperature_celsius", "zone_target_temperature", UnitOfTemperature.CELSIUS, None, SensorStateClass.MEASUREMENT),
        ("target_hmdty_level", "target_humidity_level", "zone_target_humidity", None, None, None),  # String value like "fourty-sixty"
        ("time_profile", "time_profile_id", "zone_time_profile", None, None, None),  # Integer ID
    ]:
        SENSOR_DESCRIPTIONS.append(
            GetAirSensorEntityDescription(
                key=f"zone_{zone_idx}_{key_suffix}",
                translation_key=translation_key,
                data_key=data_key,
                native_unit_of_measurement=unit,
                state_class=state_class,
                device_class=device_class,
                zone_idx=zone_idx,
            )
        )


class GetAirSensor(CoordinatorEntity, SensorEntity):
    """Representation of a getAir sensor."""

    _attr_has_entity_name = True
    entity_description: GetAirSensorEntityDescription

    def __init__(
        self,
        coordinator: GetAirCoordinator,
        device_id: str,
        description: GetAirSensorEntityDescription,
    ):
        """Initialize the sensor entity."""
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
    def native_value(self) -> float | str | None:
        """Return the sensor value."""
        if not self.coordinator.data:
            return None

        if self._zone_idx:
            zone_data = self.coordinator.data["zones"].get(self._zone_idx, {})
            value = zone_data.get(self.entity_description.data_key)
        else:
            system_data = self.coordinator.data["system"]
            value = system_data.get(self.entity_description.data_key)
        
        # Format datetime strings (boot_time, last_update)
        if self.entity_description.data_key in ("boot_time", "last_update") and isinstance(value, str):
            return format_datetime(value)
        
        # Convert boolean modelock to readable text
        if self.entity_description.data_key == "modelock" and isinstance(value, bool):
            return "Ja" if value else "Nein"
        
        return value


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities."""
    coordinator: GetAirCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    device_id: str = hass.data[DOMAIN][config_entry.entry_id]["device_id"]
    enabled_zones: dict = hass.data[DOMAIN][config_entry.entry_id]["enabled_zones"]

    entities = []

    for description in SENSOR_DESCRIPTIONS:
        # Skip zone sensors if zone is not enabled
        if description.zone_idx is not None:
            if not enabled_zones.get(f"zone_{description.zone_idx}", True):
                continue

        entity = GetAirSensor(coordinator, device_id, description)
        entities.append(entity)

    async_add_entities(entities)
