"""Constants for getAir SmartControl integration."""
import os

DOMAIN = "getair_smartcontrol"
MANUFACTURER = "getAir"

# Config flow
CONF_AUTH_URL = "auth_url"
CONF_API_URL = "api_url"
CONF_DEVICE_ID = "device_id"

# Client ID - loaded from environment variable for security
# Can be set via: export GETAIR_CLIENT_ID="your_client_id"
# Fallback to default if not set
CLIENT_ID = os.getenv("GETAIR_CLIENT_ID", "7jPuzDmLiKFF6oPtvsFUhBkyPahA7Lh5")

# Modes
MODES = ["ventilate", "ventilate_hr", "ventilate_inv", "night", "auto", "rush"]
