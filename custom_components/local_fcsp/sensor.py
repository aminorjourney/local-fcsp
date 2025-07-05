import asyncio
import json
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
    UpdateFailed,
)
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.util import dt as hass_dt

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL, CONF_SCAN_INTERVAL

from fcsp_api import FCSP

_LOGGER = logging.getLogger(__name__)

def clean_string(value):
    if isinstance(value, str):
        # Strip null chars and whitespace
        return value.replace("\x00", "").strip()
    return value

def firmware_to_hex_string(firmware_str):
    # Convert escaped bytes string like "\x01\x02\x03" to readable hex like "01 02 03"
    try:
        # Convert escaped string to bytes
        firmware_bytes = firmware_str.encode("latin1").decode("unicode_escape").encode("latin1")
        return " ".join(f"{b:02X}" for b in firmware_bytes)
    except Exception as e:
        _LOGGER.warning(f"Error converting firmware to hex: {e}")
        # Fallback: clean and return as is
        return clean_string(firmware_str)

def clean_inverter_info_list(raw_list):
    """
    Given inverter_info raw list, clean fields:
    - strip strings,
    - convert firmware field,
    - remove control chars
    """
    cleaned = []
    for item in raw_list:
        if not isinstance(item, dict):
            cleaned.append(item)
            continue
        cleaned_item = {}
        for k, v in item.items():
            if k == "firmware" and isinstance(v, str):
                cleaned_item[k] = firmware_to_hex_string(v)
            elif isinstance(v, str):
                cleaned_item[k] = clean_string(v)
            else:
                cleaned_item[k] = v
        cleaned.append(cleaned_item)
    return cleaned

def interpret_charger_status(charger_info, inverter_info):
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
                return "Inverter Off"
            elif inv_state == 1:
                return "Preparing To Power Home"
            elif inv_state == 5:
                return "Powering Home"
            else:
                return "Charging Vehicle"
        return "Power Transferring"
    return state or "Unknown"

def interpret_inverter_state(inverter_info):
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

def dump_json(data):
    try:
        return json.dumps(data, indent=2)
    except Exception as e:
        _LOGGER.error(f"Error dumping JSON data: {e}")
        return "Error dumping JSON"

SENSORS = [
    ("Info", lambda data: "See Attributes" if data else None, None, "charger_info", "mdi:ev-plug-ccs1", False, "ford_charge_station_pro", True),
    ("Status", None, None, "status", "mdi:ev-station", False, "ford_charge_station_pro", True),
    ("Last Updated", None, None, "charger_info", "mdi:update", False, "ford_charge_station_pro", True),

    ("Info", lambda data: "See Attributes" if data else None, None, "inverter_info", "mdi:home-import-outline", False, "home_integration_system", True),
    ("State", lambda data: interpret_inverter_state(data), None, "inverter_info", "mdi:sine-wave", False, "home_integration_system", True),
    ("Last Updated", None, None, "inverter_info", "mdi:update", False, "home_integration_system", True),

    ("Raw Data", dump_json, None, "charger_info", "mdi:magnify", True, "ford_charge_station_pro", False),
    ("Raw Data", dump_json, None, "inverter_info", "mdi:magnify", True, "home_integration_system", False),

    ("Config Status", dump_json, None, "config_status", "mdi:clipboard-check", True, None, False),
    ("Network Info", dump_json, None, "network_info", "mdi:access-point-network", True, None, False),
    ("Device Summary", dump_json, None, "device_summary", "mdi:information-outline", True, None, False),
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    fcsp = data["fcsp"]

    scan_interval_seconds = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    scan_interval = timedelta(seconds=scan_interval_seconds)

    coordinator = FCSPDataUpdateCoordinator(hass, fcsp, scan_interval)

    # Await first refresh to ensure data is ready before adding sensors
    await coordinator.async_config_entry_first_refresh()

    entities = []

    debug = entry.options.get("debug", True)

    for name, key_or_func, unit, source, icon, debug_only, device_key, enabled_default in SENSORS:
        if debug_only and not debug:
            continue
        if device_key == "home_integration_system" and not coordinator.home_integration_attached:
            continue
        entities.append(
            LocalFCSPSensor(
                name=name,
                key_or_func=key_or_func,
                unit=unit,
                source=source,
                coordinator=coordinator,
                icon=icon,
                device_key=device_key,
                entry_id=entry.entry_id,
                enabled_default=enabled_default,
            )
        )

    async_add_entities(entities, True)

class FCSPDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, fcsp: FCSP, scan_interval: timedelta):
        super().__init__(
            hass,
            _LOGGER,
            name="Local FCSP Data Coordinator",
            update_interval=scan_interval,
        )
        self._fcsp = fcsp
        self.home_integration_attached = False

    async def _async_update_data(self):
        loop = asyncio.get_running_loop()
        try:
            # Connect (blocking), run in executor to avoid blocking event loop
            await loop.run_in_executor(None, self._fcsp.connect)

            charger_info = await loop.run_in_executor(None, self._fcsp.get_charger_info)
            inverter_info_raw = await loop.run_in_executor(None, self._fcsp.get_inverter_info)
            inverter_info = clean_inverter_info_list(inverter_info_raw)
            self.home_integration_attached = bool(inverter_info and len(inverter_info) > 0)

            config_status = await loop.run_in_executor(None, self._fcsp.get_config_status)
            network_info = await loop.run_in_executor(None, self._fcsp.get_network_info)
            status = await loop.run_in_executor(None, self._fcsp.get_status)
            device_summary = await loop.run_in_executor(None, self._fcsp.get_device_summary)

            return {
                "charger_info": charger_info,
                "inverter_info": inverter_info,
                "config_status": config_status,
                "network_info": network_info,
                "status": status,
                "device_summary": device_summary,
            }
        except Exception as err:
            _LOGGER.error(f"Error communicating with FCSP: {err}")
            raise UpdateFailed(f"FCSP update failed: {err}") from err

class LocalFCSPSensor(CoordinatorEntity, SensorEntity):
    def __init__(
        self,
        name,
        key_or_func,
        unit,
        source,
        coordinator,
        icon,
        device_key,
        entry_id,
        enabled_default=True,
    ):
        super().__init__(coordinator)
        self._key_or_func = key_or_func
        self._unit = unit
        self._source = source
        self._icon = icon
        self._device_key = device_key
        self._entry_id = entry_id

        self._attr_name = name
        self._attr_unique_id = f"local_fcsp_{device_key}_{name.lower().replace(' ', '_')}_{entry_id}"
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit if unit else None
        self._attr_has_entity_name = True
        self._attr_device_info = self._get_device_info()
        self._attr_entity_registry_enabled_default = enabled_default

        self._attributes = {}

    def _get_device_info(self):
        if self._device_key == "ford_charge_station_pro":
            return DeviceInfo(
                identifiers={(DOMAIN, f"ford_charge_station_pro_{self._entry_id}")},
                manufacturer="Siemens",
                name="Ford Charge Station Pro",
                model="Charge Station Pro",
            )
        elif self._device_key == "home_integration_system":
            inverter_info = self.coordinator.data.get("inverter_info") or [{}]
            inv = inverter_info[0] if len(inverter_info) > 0 else {}
            manufacturer = clean_string(inv.get("vendor", "Unknown"))
            model = clean_string(inv.get("model", "Unknown"))
            return DeviceInfo(
                identifiers={(DOMAIN, f"home_integration_system_{self._entry_id}")},
                manufacturer=manufacturer,
                name="Home Integration System",
                model=model,
            )
        return None

    @property
    def native_value(self):
        data = self.coordinator.data
        if not data:
            return None

        # Special cases for some sensors:
        if self._attr_name == "Status" and self._device_key == "ford_charge_station_pro":
            charger_info = data.get("charger_info")
            inverter_info = data.get("inverter_info")
            value = interpret_charger_status(charger_info, inverter_info)
            self._attributes = {}
            return value

        if self._attr_name == "State" and self._device_key == "home_integration_system":
            inverter_info = data.get("inverter_info")
            value = interpret_inverter_state(inverter_info)
            self._attributes = {}
            return value

        if self._attr_name == "Last Updated":
            source_data = data.get(self._source)
            if not source_data:
                return None

            timestamp_str = None
            if self._device_key == "ford_charge_station_pro":
                # Try known timestamp fields for charger_info
                timestamp_str = (
                    source_data.get("tsInfo")
                    or source_data.get("timestamp")
                    or source_data.get("lastUpdated")
                )
            elif self._device_key == "home_integration_system":
                # inverter_info is a list, get first item timestamp
                if isinstance(source_data, list) and len(source_data) > 0:
                    timestamp_str = (
                        source_data[0].get("tsInfo")
                        or source_data[0].get("timestamp")
                        or source_data[0].get("lastUpdated")
                    )

            if not timestamp_str:
                return None

            try:
                timestamp_dt = hass_dt.parse_datetime(timestamp_str)
                if timestamp_dt is None:
                    return None
                timestamp_local = hass_dt.as_local(timestamp_dt)
                now = hass_dt.now()
                diff = now - timestamp_local
                seconds = diff.total_seconds()
                if seconds < 60:
                    return "just now"
                elif seconds < 3600:
                    minutes = int(seconds / 60)
                    return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
                elif seconds < 86400:
                    hours = int(seconds / 3600)
                    return f"{hours} hour{'s' if hours != 1 else ''} ago"
                else:
                    days = int(seconds / 86400)
                    return f"{days} day{'s' if days != 1 else ''} ago"
            except Exception as e:
                _LOGGER.error(f"Error parsing last updated time: {e}")
                return None

        source_data = data.get(self._source)
        if source_data is None:
            return None

        # For "Info" sensors show attributes with detailed info
        if self._attr_name == "Info" and self._device_key == "ford_charge_station_pro":
            status_data = data.get("status") or {}
            max_amps = status_data.get("max_amps")
            self._attributes = {
                "model_name": source_data.get("vHw"),
                "model_number": source_data.get("catalogNo"),
                "serial_number": source_data.get("traceNo"),
                "software_version": source_data.get("vWiFi"),
                "ip_address": source_data.get("ipAddr"),
                "hardware_current_limit": f"{max_amps} A" if max_amps else "Unknown",
                "home_integration_system_attached": bool(source_data.get("inverter", 0)),
            }
            return "See Attributes"

        if self._attr_name == "Info" and self._device_key == "home_integration_system":
            if source_data and len(source_data) > 0:
                status_data = data.get("status") or {}
                try:
                    inverter_count = int(status_data.get("inverter_count", 0))
                except (ValueError, TypeError):
                    inverter_count = 0
                inv = source_data[0]
                self._attributes = {
                    "vendor": clean_string(inv.get("vendor")),
                    "model": clean_string(inv.get("model")),
                    "serial_number": clean_string(inv.get("slno")),
                    "inverters_connected": inverter_count,
                }
                return "See Attributes"
            return None

        # For raw JSON sensors, show "See Attributes" as state, JSON as attributes
        json_sensors = {"Raw Data", "Config Status", "Network Info", "Device Summary"}
        if self._attr_name in json_sensors:
            # For inverter_info raw data, return cleaned inverter_info list
            if self._attr_name == "Raw Data" and self._device_key == "home_integration_system":
                # Use cleaned inverter_info (already cleaned by coordinator)
                self._attributes = data.get("inverter_info")
                return "See Attributes"
            self._attributes = source_data if isinstance(source_data, dict) else {"data": source_data}
            return "See Attributes"

        if callable(self._key_or_func):
            try:
                value = self._key_or_func(source_data)
            except Exception as e:
                _LOGGER.error(f"Error processing sensor value for {self._attr_name}: {e}")
                value = None
        else:
            value = source_data.get(self._key_or_func) if isinstance(source_data, dict) else None

        self._attributes = {}
        return value

    @property
    def extra_state_attributes(self):
        # Attributes only for "Info" and raw JSON sensors
        if self._attr_name == "Info":
            return self._attributes

        json_sensors = {"Raw Data", "Config Status", "Network Info", "Device Summary"}
        if self._attr_name in json_sensors:
            return self._attributes

        return {}

    @property
    def icon(self):
        return self._attr_icon

    @property
    def native_unit_of_measurement(self):
        return self._attr_native_unit_of_measurement

    @property
    def available(self):
        return self.coordinator.data is not None
