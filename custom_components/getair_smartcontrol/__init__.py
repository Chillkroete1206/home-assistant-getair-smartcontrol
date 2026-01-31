"""getAir SmartControl integration for Home Assistant."""
import logging
from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api_client import GetAirAPIClient
from .coordinator import GetAirCoordinator
from .const import (
    DOMAIN,
    CONF_AUTH_URL,
    CONF_API_URL,
    CLIENT_ID,
    CONF_DEVICE_ID,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: Final = [Platform.BINARY_SENSOR, Platform.FAN, Platform.SENSOR, Platform.SELECT]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up getAir SmartControl from a config entry."""
    
    _LOGGER.info("=" * 80)
    _LOGGER.info("Setting up getAir SmartControl integration")
    _LOGGER.info("Entry ID: %s", entry.entry_id)
    _LOGGER.info("Entry Title: %s", entry.title)
    _LOGGER.info("=" * 80)
    
    # Log configuration (without sensitive data)
    _LOGGER.debug(
        "Configuration: auth_url=%s, api_url=%s, username=%s, device_id=%s",
        entry.data.get(CONF_AUTH_URL),
        entry.data.get(CONF_API_URL),
        entry.data.get(CONF_USERNAME),
        entry.data.get(CONF_DEVICE_ID),
    )
    
    # Initialize API client
    credentials_data = {
        CONF_AUTH_URL: entry.data[CONF_AUTH_URL],
        CONF_API_URL: entry.data[CONF_API_URL],
        "client_id": CLIENT_ID,
        CONF_USERNAME: entry.data[CONF_USERNAME],
        CONF_PASSWORD: entry.data[CONF_PASSWORD],
    }
    
    try:
        _LOGGER.info("Step 1/4: Creating API client")
        api_client = GetAirAPIClient(credentials_data, hass.config.path())
        _LOGGER.info("API client created successfully")
        
        # Connect to API
        _LOGGER.info("Step 2/4: Connecting to API")
        connect_result = await hass.async_add_executor_job(api_client.connect)
        
        if not connect_result:
            _LOGGER.error("API connection failed")
            raise ConfigEntryNotReady("Could not connect to getAir API")
        
        _LOGGER.info("Successfully connected to getAir API")
        
    except ConfigEntryNotReady:
        raise
    except Exception as err:
        _LOGGER.exception("Error setting up API client: %s", str(err))
        raise ConfigEntryNotReady(f"Error connecting to API: {err}")
    
    # Get device ID
    device_id = entry.data[CONF_DEVICE_ID].upper().replace(":", "")
    _LOGGER.info("Device ID (normalized): %s", device_id)
    
    # Get options with defaults
    polling_interval = entry.options.get("polling_interval", 60)
    enable_zone_1 = entry.options.get("enable_zone_1", True)
    enable_zone_2 = entry.options.get("enable_zone_2", True)
    enable_zone_3 = entry.options.get("enable_zone_3", True)
    
    _LOGGER.debug(
        "Options: polling_interval=%d, zones enabled: 1=%s, 2=%s, 3=%s",
        polling_interval,
        enable_zone_1,
        enable_zone_2,
        enable_zone_3,
    )
    
    # Create coordinator
    _LOGGER.info("Step 3/4: Creating coordinator")
    coordinator = GetAirCoordinator(
        hass,
        api_client,
        device_id,
        polling_interval=polling_interval,
    )
    _LOGGER.info("Coordinator created successfully")
    
    # Fetch initial data
    _LOGGER.info("Step 4/4: Fetching initial data")
    try:
        await coordinator.async_config_entry_first_refresh()
        _LOGGER.info("Initial data fetch completed successfully")
        
        # Log fetched data summary
        if coordinator.data:
            _LOGGER.debug("Initial data summary:")
            if "system" in coordinator.data:
                _LOGGER.debug("  System ID: %s", coordinator.data["system"].get("system_id"))
                _LOGGER.debug("  System Type: %s", coordinator.data["system"].get("system_type"))
                _LOGGER.debug("  FW Version: %s", coordinator.data["system"].get("fw_version"))
            if "zones" in coordinator.data:
                _LOGGER.debug("  Zones found: %d", len(coordinator.data["zones"]))
                for zone_idx, zone_data in coordinator.data["zones"].items():
                    _LOGGER.debug("    Zone %d: %s", zone_idx, zone_data.get("name"))
        else:
            _LOGGER.warning("Initial data is empty or None")
            
    except Exception as refresh_err:
        _LOGGER.exception("Failed to fetch initial data: %s", str(refresh_err))
        raise ConfigEntryNotReady(f"Failed to fetch initial data: {refresh_err}")
    
    # Store coordinator and device info
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "api_client": api_client,  # Store for cleanup
        "device_id": device_id,
        "enabled_zones": {
            "zone_1": enable_zone_1,
            "zone_2": enable_zone_2,
            "zone_3": enable_zone_3,
        },
    }
    
    _LOGGER.debug("Stored coordinator and device info in hass.data")
    
    # Forward entry setup
    _LOGGER.info("Setting up platforms: %s", PLATFORMS)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.info("Platforms setup completed")
    
    # Listen for option updates
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    
    _LOGGER.info("=" * 80)
    _LOGGER.info("getAir SmartControl setup completed successfully")
    _LOGGER.info("=" * 80)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    
    _LOGGER.info("Unloading getAir SmartControl entry: %s", entry.entry_id)
    
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        _LOGGER.info("Successfully unloaded platforms")
        
        # Cleanup: Remove credentials file if it exists
        entry_data = hass.data[DOMAIN].pop(entry.entry_id)
        api_client = entry_data.get("api_client")
        
        if api_client:
            await hass.async_add_executor_job(_cleanup_credentials, api_client)
        
        _LOGGER.debug("Removed entry data from hass.data")
    else:
        _LOGGER.error("Failed to unload platforms")
    
    return unload_ok


def _cleanup_credentials(api_client: GetAirAPIClient) -> None:
    """Clean up credentials file (runs in executor)."""
    try:
        if hasattr(api_client, '_credentials_path'):
            cred_path = api_client._credentials_path
            if cred_path.exists():
                cred_path.unlink()
                _LOGGER.debug("Removed credentials file: %s", cred_path)
    except Exception as err:
        _LOGGER.warning("Could not cleanup credentials file: %s", err)


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options when changed."""
    
    _LOGGER.info("Options updated for entry %s, reloading...", entry.entry_id)
    _LOGGER.debug("New options: %s", entry.options)
    
    await hass.config_entries.async_reload(entry.entry_id)
