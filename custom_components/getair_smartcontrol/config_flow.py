"""Config flow for getAir SmartControl integration."""
import logging
from typing import Any, Dict

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, CONF_AUTH_URL, CONF_API_URL, CONF_CLIENT_ID, CONF_DEVICE_ID
from .api_client import GetAirAPIClient

_LOGGER = logging.getLogger(__name__)


class GetAirConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for getAir SmartControl."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        self._credentials: Dict[str, Any] = {}
        self._devices: list = []

    async def async_step_user(
        self, user_input: Dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initiated by the user - Step 1: Enter credentials."""
        errors = {}
        placeholders = {}

        if user_input is not None:
            _LOGGER.info("=" * 80)
            _LOGGER.info("Config flow: User credentials received")
            _LOGGER.debug(
                "Credentials (without password): auth_url=%s, api_url=%s, client_id=%s, username=%s",
                user_input.get(CONF_AUTH_URL),
                user_input.get(CONF_API_URL),
                user_input.get(CONF_CLIENT_ID),
                user_input.get(CONF_USERNAME),
            )
            
            try:
                _LOGGER.info("Validating credentials and fetching devices...")
                
                # Store credentials
                self._credentials = user_input
                
                # Fetch available devices
                devices = await self.hass.async_add_executor_job(
                    self._get_devices, user_input
                )
                
                if not devices:
                    _LOGGER.error("No devices found for this account")
                    errors["base"] = "no_devices"
                    placeholders["error_details"] = "Keine Geräte gefunden. Prüfen Sie, ob Ihr Account registrierte Geräte hat."
                else:
                    _LOGGER.info("Found %d device(s)", len(devices))
                    self._devices = devices
                    
                    # If only one device, skip selection step
                    if len(devices) == 1:
                        _LOGGER.info("Only one device found, auto-selecting")
                        return await self.async_step_select_device({CONF_DEVICE_ID: devices[0]["device_id"]})
                    
                    # Multiple devices - show selection
                    return await self.async_step_select_device()

            except CannotConnect as err:
                _LOGGER.error("Cannot connect to API: %s", str(err))
                errors["base"] = "cannot_connect"
                placeholders["error_details"] = "Verbindung zur API fehlgeschlagen. Prüfen Sie Ihre Zugangsdaten."
                
            except InvalidCredentials as err:
                _LOGGER.error("Invalid credentials: %s", str(err))
                errors["base"] = "invalid_credentials"
                placeholders["error_details"] = "Ungültige Zugangsdaten."
                
            except Exception as err:
                _LOGGER.exception("Unexpected error during config flow: %s", str(err))
                errors["base"] = "unknown"
                placeholders["error_details"] = str(err)
            
            _LOGGER.info("=" * 80)

        schema = vol.Schema({
            vol.Required(CONF_AUTH_URL, default="https://auth.getair.eu/oauth/token"): str,
            vol.Required(CONF_API_URL, default="https://be01.ga-cc.de/api/v1/"): str,
            vol.Required(CONF_CLIENT_ID, default="7jPuzDmLiKFF6oPtvsFUhBkyPahA7Lh5"): str,
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_select_device(
        self, user_input: Dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle device selection - Step 2."""
        errors = {}
        
        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID]
            _LOGGER.info("Device selected: %s", device_id)
            
            # Check if already configured
            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()
            
            # Create entry with credentials + device_id
            data = {**self._credentials, CONF_DEVICE_ID: device_id}
            
            # Find device name for title
            device_name = next(
                (d["name"] for d in self._devices if d["device_id"] == device_id),
                device_id
            )
            
            return self.async_create_entry(
                title=f"getAir {device_name}",
                data=data,
            )
        
        # Build device selection schema
        device_options = {
            d["device_id"]: f"{d['name']} ({d['device_id']})"
            for d in self._devices
        }
        
        schema = vol.Schema({
            vol.Required(CONF_DEVICE_ID): vol.In(device_options),
        })
        
        return self.async_show_form(
            step_id="select_device",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "device_count": str(len(self._devices))
            },
        )

    def _get_devices(self, credentials: Dict[str, Any]) -> list:
        """
        Get list of available devices.
        
        :param credentials: User credentials
        :return: List of devices with device_id and name
        :raises CannotConnect: If API connection fails
        """
        _LOGGER.info("Fetching devices from API...")
        
        # Create credentials data
        credentials_data = {
            "auth_url": credentials[CONF_AUTH_URL],
            "api_url": credentials[CONF_API_URL],
            "client_id": credentials[CONF_CLIENT_ID],
            "username": credentials[CONF_USERNAME],
            "password": credentials[CONF_PASSWORD],
        }

        try:
            _LOGGER.info("Creating API client")
            api_client = GetAirAPIClient(credentials_data, config_path=None)
            
            _LOGGER.info("Connecting to API")
            if not api_client.connect():
                _LOGGER.error("API connection failed")
                raise CannotConnect("Could not authenticate with API")
            
            _LOGGER.info("API connection successful")
            
            # Get devices from API - with retries since token might need time to activate
            _LOGGER.info("Fetching device list (with retries)")
            if not hasattr(api_client._api, 'get_devices'):
                _LOGGER.error("API does not support get_devices()")
                raise CannotConnect("API does not support device enumeration")
            
            # Try multiple times with delays - same pattern as coordinator
            import time
            max_retries = 3
            api_devices = None
            
            for attempt in range(max_retries):
                _LOGGER.debug("Device discovery attempt %d/%d", attempt + 1, max_retries)
                
                try:
                    api_devices = api_client._api.get_devices()
                    
                    if api_devices and len(api_devices) > 0:
                        _LOGGER.info("Successfully discovered %d device(s)", len(api_devices))
                        break
                    else:
                        _LOGGER.warning("get_devices() returned empty list on attempt %d", attempt + 1)
                        
                except Exception as get_err:
                    _LOGGER.warning("get_devices() failed on attempt %d: %s", attempt + 1, get_err)
                
                # Wait before retry (except on last attempt)
                if attempt < max_retries - 1:
                    wait_time = 0.5
                    _LOGGER.debug("Waiting %s seconds before retry...", wait_time)
                    time.sleep(wait_time)
            
            if not api_devices:
                _LOGGER.warning("No devices found after %d attempts", max_retries)
                return []
            
            # Convert to our format
            devices = []
            for dev in api_devices:
                device_id = dev.device_id
                device_name = getattr(dev, 'name', None) or f"Device {device_id}"
                
                devices.append({
                    "device_id": device_id,
                    "name": device_name,
                })
                _LOGGER.debug("Found device: %s (%s)", device_name, device_id)
            
            return devices

        except CannotConnect:
            raise
        except Exception as err:
            _LOGGER.exception("Error fetching devices: %s", str(err))
            raise CannotConnect(f"Failed to fetch devices: {err}")

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return options flow."""
        return GetAirOptionsFlow(config_entry)


class GetAirOptionsFlow(config_entries.OptionsFlow):
    """Options flow for getAir SmartControl."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry
        _LOGGER.debug("Options flow initialized for entry %s", config_entry.entry_id)

    async def async_step_init(
        self, user_input: Dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            _LOGGER.info("Options updated: %s", user_input)
            return self.async_create_entry(title="", data=user_input)

        current_options = {
            "polling_interval": self._config_entry.options.get("polling_interval", 60),
            "enable_zone_1": self._config_entry.options.get("enable_zone_1", True),
            "enable_zone_2": self._config_entry.options.get("enable_zone_2", True),
            "enable_zone_3": self._config_entry.options.get("enable_zone_3", True),
        }
        
        _LOGGER.debug("Current options: %s", current_options)

        options_schema = vol.Schema({
            vol.Optional(
                "polling_interval",
                default=current_options["polling_interval"],
            ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
            vol.Optional(
                "enable_zone_1",
                default=current_options["enable_zone_1"],
            ): bool,
            vol.Optional(
                "enable_zone_2",
                default=current_options["enable_zone_2"],
            ): bool,
            vol.Optional(
                "enable_zone_3",
                default=current_options["enable_zone_3"],
            ): bool,
        })

        return self.async_show_form(step_id="init", data_schema=options_schema)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidCredentials(HomeAssistantError):
    """Error to indicate invalid credentials."""
