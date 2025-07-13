# Hey, welcome to my TED talk. Here's the stuff we need to pay attention to and store as constants.

"""Constants for Ford Charge Station Pro Local integration."""

DOMAIN = "local_fcsp"

# === Station Details ===
# This includes the DevKey, which is currently public knowledge. This may change one day, because people be like that.
DEFAULT_DEVKEY = "1bcr1ee0j58v9vzvy31n7w0imfz5dqi85tzem7om"

# Default IP address — this *will* need to be customized per install.
# (Pro tip: your router probably knows it. I don't.)
DEFAULT_HOST = "192.168.1.100"

# === Config Options ===
CONF_SCAN_INTERVAL = "scan_interval"
CONF_API_TIMEOUT = "timeout"

# Note: this is in seconds. You *can* go shorter, but it’s not advised.
# Polling too frequently can make your charger act weird. Ask me how I know.
DEFAULT_SCAN_INTERVAL = 60

CONF_DEBUG = "debug"
DEFAULT_DEBUG = True

# === General Constants ===
API_TIMEOUT = 60  # seconds

# Feel free to rename it, but why would you?
DEFAULT_NAME = "Ford Charge Station Pro"

# === Device Info ===
ATTR_MANUFACTURER = "Siemens"  # Yep. Siemens.
ATTR_MODEL = "Charge Station Pro"
