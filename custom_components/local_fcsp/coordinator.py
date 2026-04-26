import logging
import json
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as hass_dt

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data cleaning helpers
# ---------------------------------------------------------------------------

def real_inverter_connected(inverter_info: dict) -> bool:
    """Check if the inverter is real or the FCSP's built-in placeholder.
    The FCSP reports a dummy inverter with vendor='Supreme Electronics' and
    model='Star' when no Home Integration System is physically attached.
    Any other vendor/model combination is treated as a real inverter.
    """
    if not inverter_info or not isinstance(inverter_info, dict):
        return False
    vendor = (inverter_info.get("vendor") or "").strip().lower()
    model = (inverter_info.get("model") or "").strip().lower()
    return not (vendor == "supreme electronics" and model == "star")


def normalize_inverter_states(inverter_info_list):
    """Convert legacy string inverter states to numeric codes."""
    str_to_num = {"not ready": 0, "inverter active": 5}
    for inv in inverter_info_list:
        state = inv.get("state")
        if isinstance(state, str):
            normalized = state.replace("_", " ").strip().lower()
            inv["state"] = str_to_num.get(normalized, state)
    return inverter_info_list


def clean_string(value):
    return value.replace("\x00", "").strip() if isinstance(value, str) else value


def firmware_to_hex_string(firmware_str):
    try:
        firmware_bytes = firmware_str.encode("latin1").decode("unicode_escape").encode("latin1")
        return " ".join(f"{b:02X}" for b in firmware_bytes)
    except Exception as e:
        _LOGGER.warning("Error converting firmware to hex: %s", e)
        return clean_string(firmware_str)


def firmware_string_to_version(firmware_str):
    try:
        firmware_bytes = firmware_str.encode("latin1").decode("unicode_escape").encode("latin1")
        if len(firmware_bytes) >= 3:
            return f"{firmware_bytes[0]}.{firmware_bytes[1]}.{firmware_bytes[2]}"
    except Exception as e:
        _LOGGER.warning("Error parsing firmware version: %s", e)
    return clean_string(firmware_str)


def clean_inverter_info_list(raw_list):
    cleaned = []
    for item in raw_list:
        if not isinstance(item, dict):
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


def interpret_inverter_state(inverter_info):
    """Return human-readable inverter state."""
    if not inverter_info:
        return None
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


def dump_json(data):
    """Pretty-print JSON for debug sensors."""
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


class FcspDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator for FCSP data."""

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
        self.data = cached_data or {}

        # Determine HIS attachment from cached data on startup
        cached_inverters = self.data.get("inverter_info") or []
        self._home_integration_attached = any(
            real_inverter_connected(inv) for inv in cached_inverters
        )

    async def _async_update_data(self):
        """Fetch all endpoints, clean inverter data, cache, and return."""
        import asyncio
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, self._fcsp.connect)

            charger_info  = await loop.run_in_executor(None, self._fcsp.get_charger_info)
            config_status = await loop.run_in_executor(None, self._fcsp.get_config_status)
            network_info  = await loop.run_in_executor(None, self._fcsp.get_network_info)
            inverter_info = await loop.run_in_executor(None, self._fcsp.get_inverter_info)

            inverter_info = normalize_inverter_states(inverter_info or [])
            inverter_info = clean_inverter_info_list(inverter_info)
            real_inverters = [inv for inv in inverter_info if real_inverter_connected(inv)]

            self.home_integration_attached = bool(real_inverters)
            self._fail_count = 0
            self._offline = False
            self._last_update_dt = hass_dt.utcnow()

            fresh_data = {
                "charger_info":  charger_info,
                "inverter_info": real_inverters if real_inverters else None,
                "config_status": config_status,
                "network_info":  network_info,
            }

            if self._cache_store:
                await self._cache_store.save(fresh_data)

            _LOGGER.debug(
                "FCSP data fetched (inverter_count=%s). Keys: %s",
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
                cached_inverters = self.data.get("inverter_info") or []
                self.home_integration_attached = any(
                    real_inverter_connected(inv) for inv in cached_inverters
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
    def offline(self) -> bool:
        return self._offline

    @property
    def consecutive_failures(self) -> int:
        return self._fail_count

    def get_inverter_state_raw(self) -> int:
        inv_info = (self.data or {}).get("inverter_info") or []
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
        _LOGGER.debug(
            "Checking power cut: raw inverter state=%s, active=%s", raw, raw != 0
        )
        return raw != 0
