import logging
import json
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as hass_dt

_LOGGER = logging.getLogger(__name__)

# --- Data Cleaning Functions ---

def normalize_inverter_states(inverter_info_list):
    """Convert legacy inverter string states to numeric codes for consistency."""
    str_to_num = {"not ready": 0, "inverter active": 5}
    for inv in inverter_info_list:
        state = inv.get("state")
        if isinstance(state, str):
            normalized = state.replace("_", " ").strip().lower()
            inv["state"] = str_to_num.get(normalized, state)
    return inverter_info_list

def clean_string(value):
    """Remove null characters and whitespace from strings."""
    if isinstance(value, str):
        return value.replace("\x00", "").strip()
    return value

def firmware_to_hex_string(firmware_str):
    """Convert firmware string to raw hexadecimal representation."""
    try:
        firmware_bytes = firmware_str.encode("latin1").decode("unicode_escape").encode("latin1")
        return " ".join(f"{b:02X}" for b in firmware_bytes)
    except Exception as e:
        _LOGGER.warning(f"Error converting firmware to hex: {e}")
        return clean_string(firmware_str)

def firmware_string_to_version(firmware_str):
    """Convert firmware string to major.minor.patch format."""
    try:
        firmware_bytes = firmware_str.encode("latin1").decode("unicode_escape").encode("latin1")
        if len(firmware_bytes) >= 3:
            return f"{firmware_bytes[0]}.{firmware_bytes[1]}.{firmware_bytes[2]}"
    except Exception as e:
        _LOGGER.warning(f"Error parsing firmware version: {e}")
    return clean_string(firmware_str)

def clean_inverter_info_list(raw_list):
    """Clean inverter info dicts: normalize firmware and strip string values."""
    cleaned = []
    for item in raw_list:
        if not isinstance(item, dict):
            cleaned.append(item)
            continue
        cleaned_item = {}
        for k, v in item.items():
            if k == "firmware" and isinstance(v, str):
                cleaned_item[k] = firmware_string_to_version(v)
                cleaned_item["firmware_hex"] = firmware_to_hex_string(v)
            elif isinstance(v, str):
                cleaned_item[k] = clean_string(v)
            else:
                cleaned_item[k] = v
        cleaned.append(cleaned_item)
    return cleaned

# --- Interpretation Helpers ---

def interpret_inverter_state(inverter_info):
    """Return a human-readable inverter state."""
    if inverter_info and len(inverter_info) > 0:
        try:
            state_num = int(inverter_info[0].get("state"))
        except Exception:
            state_num = inverter_info[0].get("state")
        if state_num == 0:
            return "Inverter Off"
        elif state_num == 1:
            return "Preparing To Power Home"
        elif state_num == 5:
            return "Powering Home"
        else:
            return "Unknown State"
    return None

def interpret_charger_status(charger_info, inverter_info):
    """Return human-readable charger state, taking inverter info into account."""
    if not charger_info:
        return None
    state = charger_info.get("state")
    if state == "CS00":
        return "Idle"
    elif state == "CS01":
        return "Vehicle Connected"
    elif state == "CS02":
        if inverter_info and len(inverter_info) > 0:
            try:
                inv_state = int(inverter_info[0].get("state"))
            except Exception:
                inv_state = inverter_info[0].get("state")
            if inv_state == 0:
                return "Charging Vehicle"
            elif inv_state == 1:
                return "Preparing To Power Home"
            elif inv_state == 5:
                return "Powering Home"
            else:
                return "Power Transferring"
        return "Power Transferring"
    if state and state.startswith("CF"):
        return f"Charger Fault ({state})"
    return state or "Unknown"

# --- Misc Helpers ---

def dump_json(data):
    try:
        return json.dumps(data, indent=2)
    except Exception as e:
        _LOGGER.error(f"Error dumping JSON: {e}")
        return "Error dumping JSON"

def format_elapsed_time(dt_obj):
    """Return a human-readable elapsed time from a datetime object."""
    if not dt_obj:
        return None
    try:
        now = hass_dt.utcnow()
        diff = now - hass_dt.as_utc(dt_obj)
        seconds = int(diff.total_seconds())
        if seconds < 0:
            return "just now"
        if seconds < 60:
            return f"{seconds} second{'s' if seconds != 1 else ''} ago"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = seconds // 86400
            return f"{days} day{'s' if days != 1 else ''} ago"
    except Exception as e:
        _LOGGER.error(f"Error formatting elapsed time: {e}")
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

        # Start with any cached data (if present)
        self.data = cached_data or {}
        cached_status = self.data.get("status") or {}
        inverter_flag = cached_status.get("inverter_count", 0)
        self._home_integration_attached = inverter_flag >= 1

    async def _fetch_fcsp_data(self):
        """Run blocking API call in executor and return result."""
        return await self.hass.async_add_executor_job(self._fcsp.get_status)

    async def _async_update_data(self):
        """Fetch fresh FCSP data, clean it, and return it."""
        try:
            fresh_data = await self._fetch_fcsp_data()

            # Normalize & clean inverter info
            inverter_info = fresh_data.get("inverter_info") or []
            inverter_info = normalize_inverter_states(inverter_info)
            inverter_info = clean_inverter_info_list(inverter_info)
            fresh_data["inverter_info"] = inverter_info

            # Update attached flag based on inverter_count at root level
            inverter_flag = fresh_data.get("inverter_count", 0)
            self.home_integration_attached = inverter_flag >= 1

            # Timestamp
            self._last_update_dt = hass_dt.utcnow()

            # Persist to cache if available
            if self._cache_store:
                await self._cache_store.save(fresh_data)

            # Helpful debug: log the inverter numeric state
            inv_state = self.get_inverter_state_raw(fresh_data)
            _LOGGER.debug("FCSP fresh data fetched (inverter_state=%s). Keys: %s", inv_state, list(fresh_data.keys()))

            return fresh_data

        except Exception as e:
            _LOGGER.warning("Falling back to cached data due to error: %s", e)
            if self.data:
                inverter_flag = self.data.get("inverter_count", 0)
                self.home_integration_attached = inverter_flag >= 1
                _LOGGER.debug("Using cached data (inverter_count=%s). Keys: %s", inverter_flag, list(self.data.keys()))
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
            local_dt = hass_dt.as_local(self._last_update_dt)
            return local_dt.strftime("%b %-d, %Y at %-I:%M %p")
        except Exception as e:
            _LOGGER.error(f"Error formatting last update datetime: {e}")
            return str(self._last_update_dt)

    # --- Patched Power-cut helpers ---

    def get_inverter_state_raw(self, data=None) -> int:
        """Return the raw inverter state code (numeric), default 0.
        Checks 'inverter_states' first, then falls back to 'inverter_info'.
        """
        source = data or self.data or {}
        # Prefer inverter_states (numeric)
        inv_states = source.get("inverter_states", [])
        if inv_states:
            try:
                return int(inv_states[0])
            except Exception:
                _LOGGER.debug("Inverter state in inverter_states is not numeric: %s", inv_states[0])
                return 0
        # Fallback to inverter_info
        inv_info = source.get("inverter_info", [])
        if inv_info:
            raw = inv_info[0].get("state", 0)
            try:
                return int(raw)
            except Exception:
                normalized = str(raw).replace("_", " ").strip().lower()
                if normalized in ("not ready", "0", "off", "inverter off"):
                    return 0
                return 1
        return 0

    def is_power_cut_active(self) -> bool:
        """Return True if inverter indicates a power cut (any non-zero state)."""
        raw = self.get_inverter_state_raw()
        _LOGGER.debug("Checking power cut: raw inverter state=%s, active=%s", raw, raw != 0)
        return raw != 0
