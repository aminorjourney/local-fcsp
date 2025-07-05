"""Constants for the Local Ford Charge Station Pro integration."""

DOMAIN = "local_fcsp"

# Default device connection details
DEFAULT_DEVKEY = "1bcr1ee0j58v9vzvy31n7w0imfz5dqi85tzem7om"
DEFAULT_HOST = "192.168.1.100"
DEFAULT_PORT = 443

# Configuration keys and default values
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 30  # seconds
CONF_SHOW_RAW_DATA = "show_raw_data"
CONF_SHOW_LAST_UPDATED = "show_last_updated"

DEFAULT_SHOW_RAW_DATA = False
DEFAULT_SHOW_LAST_UPDATED = False

CONF_DEBUG = "debug"
DEFAULT_DEBUG = True

# API timeout default
API_TIMEOUT = 10  # seconds

# Integration display name
DEFAULT_NAME = "Ford Charge Station Pro"

# Device info constants
ATTR_MANUFACTURER = "Siemens"
ATTR_MODEL = "Charge Station Pro"
