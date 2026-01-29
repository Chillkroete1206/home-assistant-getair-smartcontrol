"""API Client für getAir SmartControl Integration."""
import logging
import json
from pathlib import Path
import sys

_LOGGER = logging.getLogger(__name__)


class GetAirAPIClient:
    """Wrapper um die getAir API für Home Assistant Integration."""

    def __init__(self, credentials_data: dict, config_path: str = None):
        """
        Initialize the API client.

        :param credentials_data: Dictionary with auth_url, api_url, client_id, username, password
        :param config_path: Path to Home Assistant config directory (optional)
        """
        _LOGGER.debug("Initializing GetAirAPIClient with credentials for user: %s", 
                     credentials_data.get("username", "unknown"))
        self.credentials_data = credentials_data
        self._api = None
        self._api_class = None
        
        # Determine credentials file path
        if config_path:
            # Use HA's .storage directory which is always writable
            storage_dir = Path(config_path) / ".storage"
            storage_dir.mkdir(parents=True, exist_ok=True)
            self._credentials_path = storage_dir / "getair_credentials.json"
            _LOGGER.debug("Using HA storage path: %s", self._credentials_path)
        else:
            # Fallback to /tmp with unique name
            import hashlib
            user_hash = hashlib.md5(credentials_data.get("username", "default").encode()).hexdigest()[:8]
            self._credentials_path = Path(f"/tmp/.getair_credentials_{user_hash}")
            _LOGGER.warning("No config_path provided, using temporary path: %s", self._credentials_path)
        
        self._initialize_api()

    def _initialize_api(self):
        """Initialize the API from the local api_cc1 module."""
        try:
            _LOGGER.debug("Attempting to import api_cc1 module...")
            # Import the API class from the local api_cc1 module
            from .api_cc1 import API
            self._api_class = API
            _LOGGER.info("Successfully imported api_cc1.API class")
        except ImportError as err:
            _LOGGER.error("Could not import api_cc1 module: %s", err, exc_info=True)
            raise

    def connect(self) -> bool:
        """
        Connect to the API.

        :return: True if successful
        """
        _LOGGER.debug("connect: Starting connection attempt...")
        
        try:
            # Check if we already have an API object - if yes, just reconnect it
            if self._api is not None:
                _LOGGER.debug("connect: Reusing existing API object for reconnection")
                
                # Ensure credentials file exists  
                if not self._credentials_path.exists():
                    _LOGGER.warning("connect: Credentials file missing, recreating...")
                    self._credentials_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(self._credentials_path, "w") as f:
                        json.dump(self.credentials_data, f)
                    import os
                    os.chmod(self._credentials_path, 0o600)
                
                # Reset reconnect flag if it exists
                if hasattr(self._api, '_reconnect_in_progress'):
                    self._api._reconnect_in_progress = False
                
                # CRITICAL: Clear device cache so get_device() creates fresh device with new API state
                if hasattr(self._api, '_devices'):
                    self._api._devices.clear()
                    _LOGGER.debug("connect: Cleared device cache to force fresh device objects")
                
                # Call connect on existing API object
                _LOGGER.debug("connect: Calling API.connect() on existing object...")
                connect_result = self._api.connect()
                _LOGGER.debug("connect: API.connect() returned: %s", connect_result is not None)
                
                if connect_result is None:
                    _LOGGER.error("connect: API.connect() returned None - authentication failed")
                    return False
                
                _LOGGER.info("connect: Successfully reconnected to getAir API (reused existing API object)")
                return True
            
            # First time connection - create new API object
            _LOGGER.debug("connect: First connection, creating new API object...")
            
            if not self._api_class:
                _LOGGER.error("connect: API class not initialized")
                return False

            # Write credentials to persistent file
            _LOGGER.debug("connect: Writing credentials to %s", self._credentials_path)
            
            try:
                # Ensure parent directory exists
                self._credentials_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(self._credentials_path, "w") as f:
                    json.dump(self.credentials_data, f)
                
                # Set restrictive permissions (owner read/write only)
                import os
                os.chmod(self._credentials_path, 0o600)
                
                _LOGGER.debug("connect: Credentials file written successfully to persistent location")
            except Exception as file_err:
                _LOGGER.error("connect: Failed to write credentials file: %s", file_err)
                return False

            # Initialize API with persistent credentials path
            _LOGGER.debug("connect: Initializing API class with credentials file...")
            try:
                self._api = self._api_class(str(self._credentials_path))
                
                # CRITICAL: Disable AUTO_RECONNECT to avoid conflicts with our reconnect logic
                # We manage reconnects ourselves in the coordinator
                if hasattr(self._api, 'AUTO_RECONNECT'):
                    self._api.AUTO_RECONNECT = False
                    _LOGGER.debug("connect: Disabled AUTO_RECONNECT in api_cc1")
                
                _LOGGER.debug("connect: API class initialized with persistent credentials")
            except Exception as init_err:
                _LOGGER.error("connect: Failed to initialize API class: %s", init_err, exc_info=True)
                return False

            # Connect to API
            _LOGGER.debug("connect: Calling API.connect()...")
            try:
                connect_result = self._api.connect()
                _LOGGER.debug("connect: API.connect() returned: %s (type: %s)", 
                            connect_result, type(connect_result).__name__)
                
                if connect_result is None:
                    _LOGGER.error("connect: API.connect() returned None - authentication failed")
                    return False
                
                _LOGGER.info("connect: Successfully connected to getAir API")
                return True
                
            except Exception as conn_err:
                _LOGGER.error("connect: API.connect() raised exception: %s", conn_err, exc_info=True)
                return False

        except Exception as err:
            _LOGGER.error("connect: Unexpected error during connection: %s", err, exc_info=True)
            return False

    def get_device(self, device_id: str, skip_fetch: bool = True):
        """
        Get a device object.

        :param device_id: Device ID (MAC address)
        :param skip_fetch: Skip initial fetch
        :return: Device object or None
        """
        _LOGGER.debug("get_device: Getting device %s (skip_fetch=%s)", device_id, skip_fetch)
        
        if not self._api:
            _LOGGER.error("get_device: API not connected - cannot get device")
            return None

        try:
            _LOGGER.debug("get_device: Calling API.get_device()...")
            device = self._api.get_device(device_id, skip_fetch=skip_fetch)
            
            if device is None:
                _LOGGER.error("get_device: API.get_device() returned None for device %s", device_id)
            else:
                _LOGGER.debug("get_device: Successfully got device object: %s", type(device).__name__)
                
            return device
            
        except Exception as err:
            _LOGGER.error("get_device: Error getting device %s: %s", device_id, err, exc_info=True)
            return None

    def is_connected(self) -> bool:
        """Check if API is connected."""
        if self._api is None:
            _LOGGER.debug("is_connected: API object is None")
            return False
        
        try:
            has_token = hasattr(self._api, '_api_token') and self._api._api_token is not None
            _LOGGER.debug("is_connected: API object exists, has token: %s", has_token)
            return has_token
        except Exception as err:
            _LOGGER.error("is_connected: Error checking connection status: %s", err)
            return False

    def ensure_credentials_file(self) -> bool:
        """
        Ensure the credentials file exists.
        
        This is important because the api_cc1 library may need to access
        the credentials file for token refresh or other operations.
        
        :return: True if file exists or was created successfully
        """
        try:
            if not self._credentials_path.exists():
                _LOGGER.warning(
                    "ensure_credentials_file: Credentials file missing at %s, recreating...",
                    self._credentials_path
                )
                
                # Ensure parent directory exists
                self._credentials_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write credentials
                with open(self._credentials_path, "w") as f:
                    json.dump(self.credentials_data, f)
                
                # Set restrictive permissions
                import os
                os.chmod(self._credentials_path, 0o600)
                
                _LOGGER.info("ensure_credentials_file: Credentials file recreated successfully")
                return True
            else:
                _LOGGER.debug("ensure_credentials_file: Credentials file exists")
                return True
                
        except Exception as err:
            _LOGGER.error("ensure_credentials_file: Failed to ensure credentials file: %s", err)
            return False
