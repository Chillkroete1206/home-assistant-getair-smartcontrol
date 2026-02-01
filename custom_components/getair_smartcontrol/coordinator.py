"""DataUpdateCoordinator für getAir SmartControl."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api_client import GetAirAPIClient

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=60)


class GetAirCoordinator(DataUpdateCoordinator):
    """Coordinator für getAir SmartControl API-Updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_client: GetAirAPIClient,
        device_id: str,
        polling_interval: int = 60,
    ):
        """
        Initialize the coordinator.

        :param hass: Home Assistant instance
        :param api_client: API Client
        :param device_id: Device ID (MAC address)
        :param polling_interval: Polling interval in seconds
        """
        super().__init__(
            hass,
            _LOGGER,
            name="GetAir SmartControl",
            update_interval=timedelta(seconds=polling_interval),
        )
        self.api_client = api_client
        self.device_id = device_id
        _LOGGER.info(
            "Coordinator initialized for device %s with polling interval %ds",
            device_id,
            polling_interval,
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """
        Fetch data from the API.

        :return: Dictionary with device data
        :raises UpdateFailed: If API call fails
        :raises ConfigEntryAuthFailed: If authentication fails
        """
        _LOGGER.debug("Starting data update for device %s", self.device_id)

        try:
            # Check API connection status
            if not self.api_client.is_connected():
                _LOGGER.warning("API client not connected, attempting reconnection...")
                reconnect_success = await self.hass.async_add_executor_job(
                    self.api_client.connect
                )
                if not reconnect_success:
                    _LOGGER.error("Failed to reconnect to API")
                    raise ConfigEntryAuthFailed("API authentication failed - reconnection unsuccessful")
                _LOGGER.info("Successfully reconnected to API")

            # Fetch device data in a separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            device_data = await loop.run_in_executor(
                None, self._fetch_device_data
            )

            _LOGGER.debug("Data update successful for device %s", self.device_id)
            return device_data

        except ConfigEntryAuthFailed:
            _LOGGER.error("Authentication failed for device %s", self.device_id)
            raise
        except UpdateFailed:
            raise
        except Exception as err:
            _LOGGER.exception(
                "Unexpected error fetching data for device %s: %s",
                self.device_id,
                err,
            )
            raise UpdateFailed(f"Error communicating with getAir API: {err}")

    def _fetch_device_data(self) -> Dict[str, Any]:
        """
        Fetch device data from the API (runs in executor).

        :return: Dictionary with system and zone data
        """
        _LOGGER.debug("_fetch_device_data: Starting for device %s", self.device_id)

        try:
            # Ensure credentials file exists (important for api_cc1 token refresh)
            if not self.api_client.ensure_credentials_file():
                _LOGGER.error("_fetch_device_data: Failed to ensure credentials file exists")
                raise UpdateFailed("Credentials file could not be created or accessed")

            # Get device object
            _LOGGER.debug("_fetch_device_data: Getting device object...")
            device = self.api_client.get_device(self.device_id, skip_fetch=True)

            if not device:
                _LOGGER.error("_fetch_device_data: get_device returned None for device %s", self.device_id)
                raise UpdateFailed("Could not get device from API - device object is None")

            _LOGGER.debug("_fetch_device_data: Device object obtained: %s", type(device).__name__)

            # Log available device methods for debugging
            self._log_device_methods(device)

            # Fetch latest data from API
            _LOGGER.debug("_fetch_device_data: Calling device.fetch()...")

            # Log device state before fetch
            try:
                _LOGGER.debug(
                    "_fetch_device_data: Device state before fetch - "
                    "device_id: %s, has _api: %s, has _system: %s",
                    getattr(device, 'device_id', 'N/A'),
                    hasattr(device, '_api'),
                    hasattr(device, '_system')
                )
            except Exception as debug_err:
                _LOGGER.debug("_fetch_device_data: Could not read device state: %s", debug_err)

            try:
                fetch_result = device.fetch()
                _LOGGER.debug("_fetch_device_data: device.fetch() returned: %s", fetch_result)

                if not fetch_result:
                    # Check if it's a 401 authentication error
                    # If so, try to reconnect once
                    _LOGGER.warning(
                        "_fetch_device_data: device.fetch() failed. Attempting reconnection..."
                    )

                    # Reset the reconnect flag in the API if it exists
                    if hasattr(self.api_client._api, '_reconnect_in_progress'):
                        self.api_client._api._reconnect_in_progress = False
                        _LOGGER.debug("_fetch_device_data: Reset _reconnect_in_progress flag")

                    # Try to reconnect
                    if self.api_client.connect():
                        _LOGGER.info("_fetch_device_data: Reconnection successful, waiting for token to become active...")

                        # CRITICAL: Wait for the token to propagate
                        import time
                        time.sleep(0.5)

                        # Reset reconnect flag again after our connect
                        if hasattr(self.api_client._api, '_reconnect_in_progress'):
                            self.api_client._api._reconnect_in_progress = False

                        # Try multiple times with delays - matches what status_abfragen.py does
                        max_retries = 3
                        for retry_attempt in range(max_retries):
                            _LOGGER.debug(
                                "_fetch_device_data: Retry attempt %d/%d...",
                                retry_attempt + 1,
                                max_retries
                            )

                            # Get fresh device object
                            device = self.api_client.get_device(self.device_id, skip_fetch=True)
                            if not device:
                                _LOGGER.error("_fetch_device_data: Could not get device on retry %d", retry_attempt + 1)
                                continue

                            _LOGGER.debug("_fetch_device_data: Attempting fetch (retry %d/%d)...", retry_attempt + 1, max_retries)
                            fetch_result = device.fetch()
                            _LOGGER.debug(
                                "_fetch_device_data: Retry %d fetch returned: %s",
                                retry_attempt + 1,
                                fetch_result
                            )

                            if fetch_result:
                                _LOGGER.info("_fetch_device_data: Fetch successful on retry %d", retry_attempt + 1)
                                break

                            # If not the last retry, wait before trying again
                            if retry_attempt < max_retries - 1:
                                wait_time = 0.5
                                _LOGGER.debug("_fetch_device_data: Waiting %s seconds before next retry...", wait_time)
                                time.sleep(wait_time)

                        if not fetch_result:
                            _LOGGER.error("_fetch_device_data: All %d retry attempts failed", max_retries)
                    else:
                        _LOGGER.error("_fetch_device_data: Reconnection failed")

                    # If still failing after retry
                    if not fetch_result:
                        # Try to get more information about why fetch failed
                        error_details = []

                        # Check if API client is still connected
                        if hasattr(self.api_client, '_api') and self.api_client._api:
                            token_status = getattr(self.api_client._api, '_api_token', None)
                            error_details.append(f"API token present: {token_status is not None}")
                        else:
                            error_details.append("API client has no _api object")

                        # Check device internal state
                        if hasattr(device, '_api'):
                            error_details.append(f"Device has _api: {device._api is not None}")

                        if hasattr(device, '_last_error'):
                            error_details.append(f"Device last error: {device._last_error}")

                        # Try to get HTTP response status if available
                        if hasattr(device, '_last_response'):
                            error_details.append(f"Last response: {device._last_response}")

                        error_info = ", ".join(error_details) if error_details else "No additional info available"

                        _LOGGER.error(
                            "_fetch_device_data: device.fetch() failed for device %s after retry. "
                            "Details: %s. "
                            "This could indicate: authentication issues, network problems, "
                            "or device not responding.",
                            self.device_id,
                            error_info
                        )
                        raise UpdateFailed(f"Could not fetch device data - fetch() returned False. {error_info}")

            except UpdateFailed:
                raise
            except Exception as fetch_exception:
                _LOGGER.error(
                    "_fetch_device_data: Exception during device.fetch(): %s (type: %s)",
                    fetch_exception,
                    type(fetch_exception).__name__,
                    exc_info=True
                )
                raise UpdateFailed(f"Exception during device.fetch(): {fetch_exception}")

            _LOGGER.debug("_fetch_device_data: Successfully fetched data, compiling system info...")

            # Compile system data
            try:
                # Convert boot_time Unix timestamp to ISO format datetime
                boot_time_unix = getattr(device, 'boot_time', None)
                boot_time_str = None
                if boot_time_unix:
                    try:
                        boot_datetime = datetime.fromtimestamp(
                            boot_time_unix, tz=timezone.utc
                        )
                        boot_time_str = boot_datetime.isoformat()
                    except (ValueError, OSError, OverflowError) as e:
                        _LOGGER.warning("Could not convert boot_time: %s", e)
                        boot_time_str = str(boot_time_unix)

                # Compile all system information
                system_data = {
                    "system_id": device.device_id,
                    "system_type": device.system_type,
                    "system_type_name": getattr(device, 'system_type_name', device.system_type),
                    "system_version": getattr(device, 'system_version', ""),
                    "fw_version": device.fw_app_version_str,
                    "fw_app_version": getattr(device, 'fw_app_version', 0),
                    "air_quality": device.air_quality,
                    "air_pressure": device.air_pressure,
                    "humidity": device.indoor_humidity,
                    "temperature": device.indoor_temperature,
                    "runtime": device._system.runtime,
                    "boot_time": boot_time_str,
                    "iaq_accuracy": getattr(device._system, 'iaq_accuracy', None),
                    "num_zones": getattr(device._system, 'num_zones', 3),
                    "modelock": getattr(device._system, 'modelock', False),
                    "notification": getattr(device._system, 'notification', ""),
                    "notify_time": getattr(device._system, 'notify_time', None),
                    "supports_auto_update": getattr(device._system, 'supports_auto_update', False),
                    "auto_update_enabled": getattr(device._system, 'auto_update_enabled', False),
                    "last_update": datetime.now(tz=timezone.utc).isoformat(),
                    "connection_status": "online",
                }

                # Add time profiles info using the correct API methods
                _LOGGER.debug("_fetch_device_data: Fetching time profile names...")
                for i in range(1, 11):
                    profile_name_key = f"time_profile_{i}_name"
                    profile_data_key = f"time_profile_{i}_data"

                    try:
                        # Use the get_time_profile_name method instead of getattr
                        if hasattr(device, 'get_time_profile_name'):
                            profile_name = device.get_time_profile_name(i)
                            _LOGGER.debug("_fetch_device_data: Profile %d name: '%s'", i, profile_name)
                        else:
                            # Fallback to getattr if method doesn't exist
                            profile_name = getattr(device, profile_name_key, "")
                        
                        # Use the get_time_profile_data method if available
                        if hasattr(device, 'get_time_profile_data'):
                            profile_data = device.get_time_profile_data(i)
                        else:
                            profile_data = getattr(device, profile_data_key, None)

                        system_data[profile_name_key] = profile_name if profile_name else ""
                        system_data[profile_data_key] = profile_data

                    except Exception as profile_err:
                        _LOGGER.debug("_fetch_device_data: Could not get profile %d: %s", i, profile_err)
                        system_data[profile_name_key] = ""
                        system_data[profile_data_key] = None

                data = {
                    "system": system_data,
                    "zones": {},
                }
                _LOGGER.debug("_fetch_device_data: System data compiled successfully")
            except AttributeError as attr_err:
                _LOGGER.error(
                    "_fetch_device_data: Missing attribute while accessing system data: %s. "
                    "Available attributes: %s",
                    attr_err,
                    dir(device),
                )
                raise UpdateFailed(f"Device object missing required attributes: {attr_err}")

            # Fetch data for each zone
            _LOGGER.debug("_fetch_device_data: Fetching data for zones 1-3...")
            for zone_idx in range(1, 4):
                try:
                    _LOGGER.debug("_fetch_device_data: Selecting zone %d...", zone_idx)
                    device.select_zone(zone_idx)

                    zone_data = {
                        "name": device.name or f"Zone {zone_idx}",
                        "speed": device.speed,
                        "mode": device.mode,
                        "temperature": device.temperature,
                        "humidity": device.humidity,
                        "outdoor_temp": device.outdoor_temperature,
                        "outdoor_humidity": device.outdoor_humidity,
                        "runtime": device.runtime,
                        "last_filter_change": device.last_filter_change,
                        "target_temp": getattr(device, 'target_temp', None),
                        "target_hmdty_level": getattr(device, 'target_hmdty_level', None),
                        "auto_mode_voc": getattr(device, 'auto_mode_voc', False),
                        "auto_mode_silent": getattr(device, 'auto_mode_silent', False),
                        "mode_deadline": getattr(device, 'mode_deadline', 0),
                        "time_profile": getattr(device, 'active_time_profile', 0),
                        "zone_index": zone_idx,
                    }
                    data["zones"][zone_idx] = zone_data
                    _LOGGER.debug(
                        "_fetch_device_data: Zone %d data: name=%s, speed=%s, mode=%s, time_profile=%s",
                        zone_idx,
                        zone_data["name"],
                        zone_data["speed"],
                        zone_data["mode"],
                        zone_data["time_profile"],
                    )
                except Exception as zone_err:
                    _LOGGER.warning(
                        "_fetch_device_data: Error fetching zone %d data: %s. Skipping zone.",
                        zone_idx,
                        zone_err,
                    )
                    # Still add the zone with minimal data
                    data["zones"][zone_idx] = {
                        "name": f"Zone {zone_idx}",
                        "zone_index": zone_idx,
                    }

            _LOGGER.debug("_fetch_device_data: Completed successfully")
            return data

        except UpdateFailed:
            raise
        except Exception as err:
            _LOGGER.exception(
                "_fetch_device_data: Unexpected error: %s (type: %s)",
                err,
                type(err).__name__
            )
            raise UpdateFailed(f"Unexpected error fetching device data: {err}")

    async def async_set_zone_speed(self, zone_idx: int, speed: float) -> bool:
        """
        Set the speed for a zone.

        :param zone_idx: Zone index (1-3)
        :param speed: Speed value (0.0-4.0)
        :return: True if successful
        """
        _LOGGER.debug("async_set_zone_speed: Setting zone %d to speed %s", zone_idx, speed)

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, self._set_zone_speed_sync, zone_idx, speed
            )

            if result:
                _LOGGER.info("Successfully set zone %d speed to %s", zone_idx, speed)
                # Don't call async_request_refresh here to avoid recursion
                # The fan entity will call async_write_ha_state() to update immediately
            else:
                _LOGGER.error("Failed to set zone %d speed to %s", zone_idx, speed)

            return result

        except Exception as err:
            _LOGGER.exception("Error setting zone %d speed: %s", zone_idx, err)
            return False

    def _set_zone_speed_sync(self, zone_idx: int, speed: float) -> bool:
        """Set zone speed (synchronous, runs in executor)."""
        _LOGGER.debug("_set_zone_speed_sync: Starting for zone %d, speed %s", zone_idx, speed)

        try:
            device = self.api_client.get_device(self.device_id, skip_fetch=True)

            if not device:
                _LOGGER.error("_set_zone_speed_sync: get_device returned None")
                return False

            _LOGGER.debug("_set_zone_speed_sync: Setting AUTOSET=False")
            device.AUTOSET = False

            _LOGGER.debug("_set_zone_speed_sync: Selecting zone %d", zone_idx)
            device.select_zone(zone_idx)

            _LOGGER.debug("_set_zone_speed_sync: Setting speed to %s", speed)
            device.speed = speed

            _LOGGER.debug("_set_zone_speed_sync: Pushing changes...")
            push_result = device.push()
            _LOGGER.debug("_set_zone_speed_sync: Push result: %s", push_result)

            return push_result

        except Exception as err:
            _LOGGER.exception("_set_zone_speed_sync: Error: %s", err)
            return False

    async def async_set_zone_mode(self, zone_idx: int, mode: str) -> bool:
        """
        Set the mode for a zone.

        :param zone_idx: Zone index (1-3)
        :param mode: Mode name
        :return: True if successful
        """
        _LOGGER.debug("async_set_zone_mode: Setting zone %d to mode %s", zone_idx, mode)

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, self._set_zone_mode_sync, zone_idx, mode
            )

            if result:
                _LOGGER.info("Successfully set zone %d mode to %s", zone_idx, mode)
                await self.async_request_refresh()
            else:
                _LOGGER.error("Failed to set zone %d mode to %s", zone_idx, mode)

            return result

        except Exception as err:
            _LOGGER.exception("Error setting zone %d mode: %s", zone_idx, err)
            return False

    def _set_zone_mode_sync(self, zone_idx: int, mode: str) -> bool:
        """Set zone mode (synchronous, runs in executor)."""
        _LOGGER.debug("_set_zone_mode_sync: Starting for zone %d, mode %s", zone_idx, mode)

        try:
            device = self.api_client.get_device(self.device_id, skip_fetch=True)

            if not device:
                _LOGGER.error("_set_zone_mode_sync: get_device returned None")
                return False

            _LOGGER.debug("_set_zone_mode_sync: Setting AUTOSET=False")
            device.AUTOSET = False

            _LOGGER.debug("_set_zone_mode_sync: Selecting zone %d", zone_idx)
            device.select_zone(zone_idx)

            _LOGGER.debug("_set_zone_mode_sync: Setting mode to %s", mode)
            device.mode = mode

            _LOGGER.debug("_set_zone_mode_sync: Pushing changes...")
            push_result = device.push()
            _LOGGER.debug("_set_zone_mode_sync: Push result: %s", push_result)

            return push_result

        except Exception as err:
            _LOGGER.exception("_set_zone_mode_sync: Error: %s", err)
            return False

    async def async_set_zone_property(self, zone_idx: int, property_name: str, value: Any) -> bool:
        """
        Set a generic zone property (e.g., time_profile, target_hmdty_level).

        :param zone_idx: Zone index (1-3)
        :param property_name: Property name to set on device
        :param value: Value to set
        :return: True if successful
        """
        _LOGGER.debug(
            "async_set_zone_property: Setting zone %d property %s to %s",
            zone_idx,
            property_name,
            value,
        )

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, self._set_zone_property_sync, zone_idx, property_name, value
            )

            if result:
                _LOGGER.info("Successfully set zone %d %s to %s", zone_idx, property_name, value)
                await self.async_request_refresh()
            else:
                _LOGGER.error("Failed to set zone %d %s to %s", zone_idx, property_name, value)

            return result

        except Exception as err:
            _LOGGER.exception("Error setting zone %d property %s: %s", zone_idx, property_name, err)
            return False

    def _set_zone_property_sync(self, zone_idx: int, property_name: str, value: Any) -> bool:
        """Set a generic zone property synchronously (runs in executor)."""
        _LOGGER.debug(
            "_set_zone_property_sync: Starting for zone %d, property %s = %s",
            zone_idx,
            property_name,
            value,
        )

        try:
            device = self.api_client.get_device(self.device_id, skip_fetch=True)

            if not device:
                _LOGGER.error("_set_zone_property_sync: get_device returned None")
                return False

            _LOGGER.debug("_set_zone_property_sync: Setting AUTOSET=False")
            device.AUTOSET = False

            _LOGGER.debug("_set_zone_property_sync: Selecting zone %d", zone_idx)
            device.select_zone(zone_idx)

            # Try setting common attribute names
            try:
                setattr(device, property_name, value)
            except Exception:
                # fallback: some attributes use active_ prefix
                try:
                    setattr(device, f"active_{property_name}", value)
                except Exception as err:
                    _LOGGER.error("_set_zone_property_sync: Could not set property %s: %s", property_name, err)
                    return False

            _LOGGER.debug("_set_zone_property_sync: Pushing changes...")
            push_result = device.push()
            _LOGGER.debug("_set_zone_property_sync: Push result: %s", push_result)

            return push_result

        except Exception as err:
            _LOGGER.exception("_set_zone_property_sync: Error: %s", err)
            return False

    async def async_set_system_property(self, property_name: str, value: Any) -> bool:
        """
        Set a system-level property on the device.

        :param property_name: Property name to set
        :param value: Value to set
        :return: True if successful
        """
        _LOGGER.debug("async_set_system_property: Setting system %s to %s", property_name, value)
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, self._set_system_property_sync, property_name, value
            )

            if result:
                _LOGGER.info("Successfully set system %s to %s", property_name, value)
                await self.async_request_refresh()
            else:
                _LOGGER.error("Failed to set system %s to %s", property_name, value)

            return result
        except Exception as err:
            _LOGGER.exception("Error setting system property %s: %s", property_name, err)
            return False

    def _set_system_property_sync(self, property_name: str, value: Any) -> bool:
        """Set a system-level property synchronously (runs in executor)."""
        _LOGGER.debug("_set_system_property_sync: Setting %s = %s", property_name, value)
        try:
            device = self.api_client.get_device(self.device_id, skip_fetch=True)
            if not device:
                _LOGGER.error("_set_system_property_sync: get_device returned None")
                return False

            try:
                setattr(device, property_name, value)
            except Exception as err:
                _LOGGER.error("_set_system_property_sync: Could not set %s: %s", property_name, err)
                return False

            push_result = device.push()
            _LOGGER.debug("_set_system_property_sync: Push result: %s", push_result)
            return push_result
        except Exception as err:
            _LOGGER.exception("_set_system_property_sync: Error: %s", err)
            return False

    def _log_device_methods(self, device) -> None:
        """Log device methods and attributes for debugging."""
        try:
            # Only log once per coordinator instance to avoid spam
            if not hasattr(self, '_methods_logged'):
                device_methods = [m for m in dir(device) if not m.startswith('_')]
                _LOGGER.debug(
                    "_log_device_methods: Available public methods/attributes: %s",
                    ", ".join(sorted(device_methods)[:20])  # Log first 20 to avoid huge logs
                )
                self._methods_logged = True
        except Exception as err:
            _LOGGER.debug("_log_device_methods: Could not log methods: %s", err)
