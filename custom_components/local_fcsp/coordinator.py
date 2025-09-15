import logging
import json
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as hass_dt

_LOGGER = logging.getLogger(__name__)

# --- Data Cleaning Functions ---
# We're going to clean some of the data from the charge station pro, as changes in firmware/software have led to changes in how things are displayed by the API.


# First, we should check to see if the inverter is real or not. If there's no inverter, the FCSP 'invents' one using stock placeholder info.

def real_inverter_connected(inverter_info: dict) -> bool:
    """Check if the inverter is real or a dummy."""
    if not inverter_info or not isinstance(inverter_info, dict):
        return False

    vendor = (inverter_info.get("vendor") or "").strip().lower()
    model = (inverter_info.get("model") or "").strip().lower()
    return not (vendor == "supreme electronics" and model == "star")

# Cleanup for inverter data, including inverter states and firmware cleaning.

def normalize_inverter_states(inverter_info_list):
    """Convert legacy inverter string states to numeric codes."""
    str_to_num = {"not ready": 0, "inverter active": 5}
    for inv in inverter_info_list:
        state = inv.get("state")
        if isinstance(state, str):
            normalized = state.replace("_", " ").strip().lower()
            inv["state"] = str_to_num.get(normalized, state)
    return inverter_info_list


def clean_string(value):
    """Remove null characters and surrounding whitespace from strings."""
    return value.replace("\x00", "").strip() if isinstance(value, str) else value


def firmware_to_hex_string(firmware_str):
    """Convert firmware string to raw hexadecimal representation."""
    try:
        firmware_bytes = firmware_str.encode("latin1").decode("unicode_escape").encode("latin1")
        return " ".join(f"{b:02X}" for b in firmware_bytes)
    except Exception as e:
        _LOGGER.warning("Error converting firmware to hex: %s", e)
        return clean_string(firmware_str)

# Let's make the firmware details readable by humans, using major, minor, patch

def firmware_string_to_version(firmware_str):
    """Convert firmware string to major.minor.patch format."""
    try:
        firmware_bytes = firmware_str.encode("latin1").decode("unicode_escape").encode("latin1")
        if len(firmware_bytes) >= 3:
            return f"{firmware_bytes[0]}.{firmware_bytes[1]}.{firmware_bytes[2]}"
    except Exception as e:
        _LOGGER.warning("Error parsing firmware version: %s", e)
    return clean_string(firmware_str)


def clean_inverter_info_list(raw_list):
    """Clean inverter info dicts: normalize firmware, strip strings, and remove fakes."""
    cleaned = []
    for item in raw_list:
        if not isinstance(item, dict):
            continue  # Skip non-dicts

        cleaned_item = {}
        for k, v in item.items():
            if k == "firmware" and isinstance(v, str):
                cleaned_item[k] = firmware_string_to_version(v)
                cleaned_item["firmware_hex"] = firmware_to_hex_string(v)
            elif isinstance(v, str):
                cleaned_item[k] = clean_string(v)
            else:
                cleaned_item[k] = v

        # Only keep real inverters
        if real_inverter_connected(cleaned_item):
            cleaned.append(cleaned_item)

    return cleaned



# --- Interpretation Helpers ---

def interpret_inverter_state(inverter_info):
    """Return human-readable inverter state."""
    if inverter_info:
        try:
            state = int(inverter_info[0].get("state"))
        except Exception:
            state = inverter_info[0].get("state")
        return {
            0: "Inverter Off",
            1: "Preparing To Power Home",
            3: "State 3",
            5: "Powering Home",
        }.get(state, "Unknown State")
    return None


def interpret_charger_status(charger_info, inverter_info):
    """Return human-readable charger state, considering inverter info."""
    if not charger_info:
        return None

    state = charger_info.get("state")
    if state == "CS00":
        return "Idle"
    if state == "CS01":
        return "Vehicle Connected"
    if state == "CS02":
        if inverter_info:
            try:
                inv_state = int(inverter_info[0].get("state"))
            except Exception:
                inv_state = inverter_info[0].get("state")
            return {
                0: "Charging Vehicle",
                1: "Preparing To Power Home",
                5: "Powering Home",
            }.get(inv_state, "Power Transferring")
        return "Power Transferring"
    if state and state.startswith("CF"):
        return f"Charger Fault ({state})"
    return state or "Unknown"


# --- Misc Helpers ---

def dump_json(data):
    """Pretty-print JSON for debugging."""
    try:
        return json.dumps(data, indent=2)
    except Exception as e:
        _LOGGER.error("Error dumping JSON: %s", e)
        return "Error dumping JSON"


def format_elapsed_time(dt_obj):
    """Return a human-readable elapsed time from a datetime object."""
    if not dt_obj:
        return None
    try:
        seconds = int((hass_dt.utcnow() - hass_dt.as_utc(dt_obj)).total_seconds())
        if seconds < 0:
            return "just now"
        if seconds < 60:
            return f"{seconds} second{'s' if seconds != 1 else ''} ago"
        if seconds < 3600:
            return f"{seconds // 60} minute{'s' if seconds // 60 != 1 else ''} ago"
        if seconds < 86400:
            return f"{seconds // 3600} hour{'s' if seconds // 3600 != 1 else ''} ago"
        return f"{seconds // 86400} day{'s' if seconds // 86400 != 1 else ''} ago"
    except Exception as e:
        _LOGGER.error("Error formatting elapsed time: %s", e)
        return None


# --- Coordinator Class ---

class FcspDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator for FCSP inverter and charger data."""

    def __init__(self, hass, config_entry, fcsp, cache_store, cached_data, scan_interval):
        super().__init__(
            hass,
            _LOGGER,
            name="FCSP Coordinator",
            update_interval=timedelta(seconds=scan_interval),
        )
        self._fcsp = fcsp
        self._cache_store = cache_store
        self._last_update_dt = None
        self._fail_count = 0
        self._offline = False

        # Keep cached data intact
        self.data = cached_data or {}

        # Only create home integration stuff if it's actually real 
        cached_inverters = self.data.get("inverter_info") or []
        self._home_integration_attached = any(real_inverter_connected(inv) for inv in cached_inverters)

    async def _fetch_fcsp_data(self):
        """Run blocking API call in executor and return result."""
        return await self.hass.async_add_executor_job(self._fcsp.get_status)

    async def _async_update_data(self):
        """Fetch, clean, filter, and cache fresh FCSP data."""
        try:
            fresh_data = await self._fetch_fcsp_data()
            self._fail_count = 0
            self._offline = False

            inverter_info = clean_inverter_info_list(normalize_inverter_states(fresh_data.get("inverter_info") or []))
            real_inverters = [inv for inv in inverter_info if real_inverter_connected(inv)]

            fresh_data["inverter_info"] = real_inverters if real_inverters else None
            fresh_data["inverter_count"] = len(real_inverters) if real_inverters else 0
            self.home_integration_attached = len(real_inverters) >= 1
            self._last_update_dt = hass_dt.utcnow()

            if self._cache_store:
                await self._cache_store.save(fresh_data)

            _LOGGER.debug(
                "FCSP fresh data fetched (inverter_count=%s). Keys: %s",
                len(real_inverters),
                list(fresh_data.keys()),
            )
            return fresh_data

        except Exception as e:
            self._fail_count += 1
            if self._fail_count >= 3:
                self._offline = True
            _LOGGER.warning(
                "FCSP fetch failed (%d): %s — using cached data if available",
                self._fail_count,
                e,
            )
            if self.data:
                inverter_count = len([inv for inv in (self.data.get("inverter_info") or []) if real_inverter_connected(inv)])
                self.home_integration_attached = inverter_count >= 1
                _LOGGER.debug(
                    "Using cached data (inverter_count=%s). Keys: %s",
                    inverter_count,
                    list(self.data.keys()),
                )
                return self.data
            raise

    @property
    def home_integration_attached(self) -> bool:
        return self._home_integration_attached

    @home_integration_attached.setter
    def home_integration_attached(self, value: bool):
        self._home_integration_attached = value

    @property
    def last_update_datetime(self) -> str:
        if not self._last_update_dt:
            return "Never"
        try:
            return hass_dt.as_local(self._last_update_dt).strftime("%b %-d, %Y at %-I:%M %p")
        except Exception as e:
            _LOGGER.error("Error formatting last update datetime: %s", e)
            return str(self._last_update_dt)

    @property
    def offline(self) -> bool:
        return self._offline

    @property
    def consecutive_failures(self) -> int:
        return self._fail_count

    # --- Power-cut helpers ---

    def get_inverter_state_raw(self, data=None) -> int:
        source = data or self.data or {}
        inv_states = source.get("inverter_states", [])
        if inv_states:
            try:
                return int(inv_states[0])
            except Exception:
                _LOGGER.debug("Inverter state in inverter_states is not numeric: %s", inv_states[0])
                return 0

        inv_info = source.get("inverter_info") or []
        if inv_info:
            raw = inv_info[0].get("state", 0)
            try:
                return int(raw)
            except Exception:
                normalized = str(raw).replace("_", " ").strip().lower()
                return 0 if normalized in ("not ready", "0", "off", "inverter off") else 1
        return 0

    def is_power_cut_active(self) -> bool:
        raw = self.get_inverter_state_raw()
        _LOGGER.debug("Checking power cut: raw inverter state=%s, active=%s", raw, raw != 0)
        return raw != 0

