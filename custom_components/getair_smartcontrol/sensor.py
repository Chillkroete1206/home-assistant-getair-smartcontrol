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
        name="Luftqualität (IAQ)",
        data_key="air_quality",
        native_unit_of_measurement="ppm",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:air-filter",
        zone_idx=None,
    ),
    GetAirSensorEntityDescription(
        key="system_air_pressure_hpa",
        translation_key="system_air_pressure",
        name="Luftdruck",
        data_key="air_pressure",
        native_unit_of_measurement=UnitOfPressure.HPA,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gauge",
        zone_idx=None,
    ),
    GetAirSensorEntityDescription(
        key="system_humidity_percent",
        translation_key="system_humidity",
        name="Luftfeuchtigkeit",
        data_key="humidity",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.HUMIDITY,
        icon="mdi:water-percent",
        zone_idx=None,
    ),
    GetAirSensorEntityDescription(
        key="system_temperature_celsius",
        translation_key="system_temperature",
        name="Temperatur",
        data_key="temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        icon="mdi:thermometer",
        zone_idx=None,
    ),
    GetAirSensorEntityDescription(
        key="system_runtime_hours",
        translation_key="system_runtime",
        name="Gesamtlaufzeit",
        data_key="runtime",
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:timer-outline",
        zone_idx=None,
    ),
    GetAirSensorEntityDescription(
        key="system_boot_time_datetime",
        translation_key="system_boot_time",
        name="Boot-Zeit",
        data_key="boot_time",
        icon="mdi:restart",
        zone_idx=None,
    ),
    GetAirSensorEntityDescription(
        key="system_iaq_accuracy_level",
        translation_key="system_iaq_accuracy",
        name="IAQ-Genauigkeit",
        data_key="iaq_accuracy",
        icon="mdi:target",
        zone_idx=None,
    ),
    GetAirSensorEntityDescription(
        key="system_num_zones_count",
        translation_key="system_num_zones",
        name="Anzahl Zonen",
        data_key="num_zones",
        icon="mdi:numeric",
        zone_idx=None,
    ),
    GetAirSensorEntityDescription(
        key="system_last_update_datetime",
        translation_key="last_update",
        name="Letzte Aktualisierung",
        data_key="last_update",
        icon="mdi:clock-check-outline",
        zone_idx=None,
    ),
    GetAirSensorEntityDescription(
        key="system_connection_status",
        translation_key="connection_status",
        name="Verbindungsstatus",
        data_key="connection_status",
        icon="mdi:lan-connect",
        zone_idx=None,
    ),
    GetAirSensorEntityDescription(
        key="system_type_name",
        translation_key="system_type",
        name="System-Typ",
        data_key="system_type_name",
        icon="mdi:devices",
        zone_idx=None,
    ),
    GetAirSensorEntityDescription(
        key="system_version",
        translation_key="system_version",
        name="Systemversion",
        data_key="system_version",
        icon="mdi:tag-outline",
        zone_idx=None,
    ),
    GetAirSensorEntityDescription(
        key="system_fw_app_version",
        translation_key="system_fw_app_version",
        name="Firmware-Version",
        data_key="fw_app_version",
        icon="mdi:chip",
        zone_idx=None,
    ),
    GetAirSensorEntityDescription(
        key="system_notification",
        translation_key="system_notification",
        name="Benachrichtigung",
        data_key="notification",
        icon="mdi:bell-outline",
        zone_idx=None,
    ),
    GetAirSensorEntityDescription(
        key="system_notification_time",
        translation_key="system_notification_time",
        name="Benachrichtigungszeit",
        data_key="notify_time",
        icon="mdi:bell-clock-outline",
        zone_idx=None,
    ),
]

# Add zone-specific sensors with descriptive keys
for zone_idx in range(1, 4):
    for data_key, key_suffix, translation_key, name_de, icon, unit, device_class, state_class in [
        ("temperature", "temperature_celsius", "zone_temperature", "Temperatur (innen)", "mdi:thermometer", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT),
        ("humidity", "humidity_percent", "zone_humidity", "Luftfeuchtigkeit (innen)", "mdi:water-percent", PERCENTAGE, SensorDeviceClass.HUMIDITY, SensorStateClass.MEASUREMENT),
        ("outdoor_temp", "outdoor_temperature_celsius", "zone_outdoor_temperature", "Temperatur (außen)", "mdi:thermometer-lines", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT),
        ("outdoor_humidity", "outdoor_humidity_percent", "zone_outdoor_humidity", "Luftfeuchtigkeit (außen)", "mdi:water-outline", PERCENTAGE, SensorDeviceClass.HUMIDITY, SensorStateClass.MEASUREMENT),
        ("runtime", "runtime_hours", "zone_runtime", "Laufzeit", "mdi:timer-sand", UnitOfTime.HOURS, None, SensorStateClass.TOTAL),
        ("last_filter_change", "filter_runtime_hours", "zone_filter_runtime", "Filter-Laufzeit", "mdi:air-filter", UnitOfTime.HOURS, None, SensorStateClass.TOTAL),
        ("target_temp", "target_temperature_celsius", "zone_target_temperature", "Zieltemperatur", "mdi:thermometer-auto", UnitOfTemperature.CELSIUS, None, SensorStateClass.MEASUREMENT),
        ("target_hmdty_level", "target_humidity_level", "zone_target_humidity", "Ziel-Luftfeuchtigkeitsbereich", "mdi:water-percent-alert", None, None, None),
        ("time_profile", "time_profile_id", "zone_time_profile", "Aktives Zeitprofil", "mdi:clock-time-eight-outline", None, None, None),
        ("mode_deadline_datetime", "mode_deadline_readable", "zone_mode_deadline_datetime", "Modus-Deadline", "mdi:calendar-clock", None, SensorDeviceClass.TIMESTAMP, None),
        ("mode_deadline_duration", "mode_deadline_remaining_minutes", "zone_mode_deadline_remaining", "Modus-Deadline (verbleibend)", "mdi:timer-sand", "min", None, SensorStateClass.MEASUREMENT),
    ]:
        SENSOR_DESCRIPTIONS.append(
            GetAirSensorEntityDescription(
                key=f"zone_{zone_idx}_{key_suffix}",
                translation_key=translation_key,
                name=name_de,
                icon=icon,
                data_key=data_key,
                native_unit_of_measurement=unit,
                state_class=state_class,
                device_class=device_class,
                zone_idx=zone_idx,
            )
        )


class GetAirSensor(CoordinatorEntity, SensorEntity):
    """Representation of a getAir sensor."""

    _attr_has_entity_name = False
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
        """Return the name of the sensor."""
        # Get translated name from entity description
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
            system_data = self.coordinator.data["system"]
            return DeviceInfo(
                identifiers={(DOMAIN, self._device_id)},
                name=f"getAir {system_data.get('system_type', 'SmartControl')}",
                manufacturer=MANUFACTURER,
                model=system_data.get("system_type", "SmartControl"),
                sw_version=system_data.get("fw_version", "Unknown"),
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

        # Special handling for mode_deadline sensors
        if self._zone_idx and self.entity_description.data_key == "mode_deadline_datetime":
            # Convert Unix timestamp to datetime object for TIMESTAMP sensor
            deadline_unix = zone_data.get("mode_deadline")
            if deadline_unix and deadline_unix > 0:
                try:
                    from datetime import datetime, timezone
                    dt = datetime.fromtimestamp(int(deadline_unix), tz=timezone.utc)
                    return dt  # Return datetime object, not string!
                except (ValueError, TypeError, OSError):
                    return None
            return None
        
        if self._zone_idx and self.entity_description.data_key == "mode_deadline_duration":
            # Calculate remaining minutes
            deadline_unix = zone_data.get("mode_deadline")
            if deadline_unix and deadline_unix > 0:
                try:
                    import time
                    current_unix = int(time.time())
                    remaining_seconds = int(deadline_unix) - current_unix
                    remaining_minutes = max(0, remaining_seconds // 60)
                    return remaining_minutes
                except (ValueError, TypeError):
                    return 0
            return 0

        # Format datetime strings (boot_time, last_update, notify_time)
        if self.entity_description.data_key in ("boot_time", "last_update", "notify_time") and isinstance(value, str):
            return format_datetime(value)


        # Show "Keine" for empty notification
        if self.entity_description.data_key == "notification" and not value:
            return "Keine"

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

    # Dynamically add sensors for non-empty time-profile names
    extra_descriptions: list[GetAirSensorEntityDescription] = []
    try:
        system_data = coordinator.data.get("system", {}) if coordinator.data else {}
        for i in range(1, 11):
            profile_name_key = f"time_profile_{i}_name"
            profile_name = system_data.get(profile_name_key)
            if profile_name and profile_name.strip():  # Only if name exists and is not empty
                _LOGGER.info("Adding sensor for time profile %d: %s", i, profile_name)
                extra_descriptions.append(
                    GetAirSensorEntityDescription(
                        key=f"time_profile_{i}_name",
                        translation_key=f"time_profile_{i}_name",
                        name=f"Zeitprofil {i} Name",
                        icon="mdi:calendar-clock",
                        data_key=profile_name_key,
                        zone_idx=None,
                    )
                )
    except Exception as e:
        _LOGGER.warning("Error creating dynamic time profile sensors: %s", e)
        extra_descriptions = []

    for description in SENSOR_DESCRIPTIONS + extra_descriptions:
        # Skip zone sensors if zone is not enabled
        if description.zone_idx is not None:
            if not enabled_zones.get(f"zone_{description.zone_idx}", True):
                continue

        entity = GetAirSensor(coordinator, device_id, description)
        entities.append(entity)

    async_add_entities(entities)
