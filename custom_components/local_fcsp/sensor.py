#Let's start by importing everything we need for this integration to work. 
import asyncio
import json
import logging
from datetime import timedelta, datetime

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL, CONF_SCAN_INTERVAL
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

#Not forgetting the fcsp_api library, without which this would be a complete nothing.

from fcsp_api import FCSP

_LOGGER = logging.getLogger(__name__)

#We're cleaning up the data produced by the inverter - currently in Hex.

def clean_string(value):
    if isinstance(value, str):
        return value.replace("\x00", "").strip()
    return value

def firmware_to_hex_string(firmware_str):
    try:
        firmware_bytes = firmware_str.encode("latin1").decode("unicode_escape").encode("latin1")
        return " ".join(f"{b:02X}" for b in firmware_bytes)
    except Exception as e:
        _LOGGER.warning(f"Error converting firmware to hex: {e}")
        return clean_string(firmware_str)

def clean_inverter_info_list(raw_list):
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

#Since the charger doesn't differentiate between power in and power out, here's some logic to help that, using data from both the charger and the home integration system. Obviously, it only works if the HIS is installed. 

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

#...and if the inverter is installed, this turns the numeric state codes into word states


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

#Figure out how FRESH the data is. Mmmm. Freshness. 


def format_elapsed_time(dt_obj):
    if not isinstance(dt_obj, datetime):
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
            minutes = int(seconds / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = int(seconds / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"
    except Exception as e:
        _LOGGER.error(f"Error formatting elapsed time: {e}")
        return None

# Providing HA with the sensors it needs to see the world. 
# In order, defined as:
# (Name, value function or key, unit, data source, icon, debug_only, device type, enabled_by_default)

SENSORS = [
    ("Info", lambda data: "See Attributes", None, "charger_info", "mdi:information", False, "charge_station", True),
    ("Status", None, None, None, "mdi:ev-plug-ccs1", False, "charge_station", True),
    ("Info", lambda data: "See Attributes", None, "inverter_info", "mdi:information", False, "home_integration", True),
    ("Status", lambda data: interpret_inverter_state(data), None, "inverter_info", "mdi:sine-wave", False, "home_integration", True),

    ("Info Raw JSON", lambda data: "See Attributes", None, "charger_info", "mdi:file-search-outline", True, "charge_station", False),
    ("Info Raw JSON", lambda data: "See Attributes", None, "inverter_info", "mdi:file-search-outline", True, "home_integration", False),

    # Changed names here to "Last Updated"
    ("Last Updated", None, None, "charger_info", "mdi:timer", False, "charge_station", True),
    ("Last Updated", None, None, "inverter_info", "mdi:timer", False, "home_integration", True),

    ("Ford Charge Station Pro Config Status", dump_json, None, "config_status", "mdi:clipboard-check", True, None, False),
    ("Ford Charge Station Pro Network Info", dump_json, None, "network_info", "mdi:access-point-network", True, None, False),
    ("Ford Charge Station Pro Device Summary", dump_json, None, "device_summary", "mdi:information-outline", True, None, False),
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    fcsp = data["fcsp"]
    debug = entry.options.get("debug", True)
    scan_interval_seconds = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    scan_interval = timedelta(seconds=scan_interval_seconds)

    coordinator = FCSPDataUpdateCoordinator(hass, fcsp, scan_interval)
    try:
        await asyncio.wait_for(coordinator.async_config_entry_first_refresh(), timeout=60)
    except asyncio.TimeoutError:
        _LOGGER.error("Timeout while waiting for initial data refresh from FCSP.")
        raise

    entities = []
    for name, key_or_func, unit, source, icon, debug_only, device_key, enabled_default in SENSORS:
        if debug_only and not debug:
            continue
        if device_key == "home_integration" and not coordinator.home_integration_attached:
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
                hass=hass,
                enabled_default=enabled_default,
            )
        )
    async_add_entities(entities, True)

#Give Home Assistant periodic updates like that nasty girl in class who won't shut up gossiping about your friend. 

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
        self._last_update_times = {}

    async def _async_update_data(self):
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._fcsp.connect)
            charger_info = await loop.run_in_executor(None, self._fcsp.get_charger_info)
            inverter_info = await loop.run_in_executor(None, self._fcsp.get_inverter_info)
            inverter_info = clean_inverter_info_list(inverter_info or [])
            self.home_integration_attached = bool(inverter_info and len(inverter_info) > 0)
            config_status = await loop.run_in_executor(None, self._fcsp.get_config_status)
            network_info = await loop.run_in_executor(None, self._fcsp.get_network_info)
            status = await loop.run_in_executor(None, self._fcsp.get_status)
            device_summary = await loop.run_in_executor(None, self._fcsp.get_device_summary)

            now = hass_dt.utcnow()

            previous_charger = self.data.get("charger_info") if self.data else None
            if charger_info != previous_charger:
                self._last_update_times["charge_station"] = now

            previous_inverter = self.data.get("inverter_info") if self.data else None
            if inverter_info != previous_inverter:
                self._last_update_times["home_integration"] = now

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

#Figuring out which sensor belongs with which thing. It's how we break out the different entities and sensors properly. 

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
        hass,
        enabled_default=True,
    ):
        super().__init__(coordinator)
        self._key_or_func = key_or_func
        self._unit = unit
        self._source = source
        self._icon = icon
        self._device_key = device_key
        self._entry_id = entry_id
        self._hass = hass
        self._attributes = {}
        self._attr_name = name
        self._attr_unique_id = f"local_fcsp_{device_key}_{name.lower().replace(' ', '_')}_{entry_id}"
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit
        self._attr_has_entity_name = True
        self._attr_device_info = self._get_device_info()
        self._attr_entity_registry_enabled_default = enabled_default
        self._refresh_task = None  # will hold the update timer task

    def _get_device_info(self):
        if self._device_key == "charge_station":
            return DeviceInfo(
                identifiers={(DOMAIN, f"charge_station_{self._entry_id}")},
                manufacturer="Siemens",
                name="Ford Charge Station Pro",
                model="Charge Station Pro",
            )
        elif self._device_key == "home_integration":
            inverter_info = self.coordinator.data.get("inverter_info") or [{}]
            inv = inverter_info[0] if len(inverter_info) > 0 else {}
            manufacturer = clean_string(inv.get("vendor", "Unknown"))
            model = clean_string(inv.get("model", "Unknown"))
            return DeviceInfo(
                identifiers={(DOMAIN, f"home_integration_{self._entry_id}")},
                manufacturer=manufacturer,
                name="Home Integration System",
                model=model,
            )
        return None

#This is basically for figuring out the extra "attributes" and making sure they go to the right Device/Entity.

    @property
    def extra_state_attributes(self):
        if self._attr_name == "Info Raw JSON":
            source_data = self.coordinator.data.get(self._source)
            if self._device_key == "home_integration":
                if isinstance(source_data, list) and len(source_data) > 0:
                    inv = source_data[0]
                    return {
                        "vendor": clean_string(inv.get("vendor")),
                        "model": clean_string(inv.get("model")),
                        "serial_number": clean_string(inv.get("slno")),
                        "name": clean_string(inv.get("name")),
                        "state": inv.get("state"),
                        "firmware": inv.get("firmware"),
                    }
                return {}
            elif self._device_key == "charge_station":
                return source_data if isinstance(source_data, dict) else {"data": source_data}

        if self._attr_name == "Info":
            if self._device_key == "charge_station":
                source_data = self.coordinator.data.get("charger_info")
                if source_data:
                    status_data = self.coordinator.data.get("status") or {}
                    max_amps = status_data.get("max_amps")
                    return {
                        "model_name": source_data.get("vHw"),
                        "model_number": source_data.get("catalogNo"),
                        "serial_number": source_data.get("traceNo"),
                        "software_version": source_data.get("vWiFi"),
                        "ip_address": source_data.get("ipAddr"),
                        "hardware_current_limit": f"{max_amps} A" if max_amps else "Unknown",
                        "home_integration_system_attached": bool(source_data.get("inverter", 0)),
                    }
                return {}

            elif self._device_key == "home_integration":
                source_data = self.coordinator.data.get("inverter_info")
                if source_data and isinstance(source_data, list) and len(source_data) > 0:
                    inv = source_data[0]
                    status_data = self.coordinator.data.get("status") or {}
                    try:
                        inverter_count = int(status_data.get("inverter_count", 0))
                    except (ValueError, TypeError):
                        inverter_count = 0
                    return {
                        "vendor": clean_string(inv.get("vendor")),
                        "model": clean_string(inv.get("model")),
                        "serial_number": clean_string(inv.get("slno")),
                        "inverters_connected": inverter_count,
                    }
                return {}

        if self._attr_name == "Last Updated":
            # Hey, do me a favor and ignore attributes for last-updated. That's all we want. LAST UPDATED. It's like Ronseal. It does exactly what it says on the tin. 
            return {}

        if self._attr_name in {
            "Ford Charge Station Pro Config Status",
            "Ford Charge Station Pro Network Info",
            "Ford Charge Station Pro Device Summary",
        }:
            data = self.coordinator.data.get(self._source)
            return data if isinstance(data, dict) else {"data": data}

        return self._attributes

    @property
    def available(self):
        return self.coordinator.data is not None

#Humans need better interpretability, and according to my therapist, this is how we do it. 

    @property
    def native_value(self):
        data = self.coordinator.data
        if not data:
            return None

        if self._attr_name in ("Info", "Info Raw JSON"):
            return "See Attributes"

        if self._attr_name == "Status" and self._device_key == "charge_station":
            charger_info = data.get("charger_info")
            inverter_info = data.get("inverter_info")
            value = interpret_charger_status(charger_info, inverter_info)
            self._attributes = {}
            return value

        if self._attr_name == "Status" and self._device_key == "home_integration":
            inverter_info = data.get("inverter_info")
            value = interpret_inverter_state(inverter_info)
            self._attributes = {}
            return value

        if self._attr_name == "Last Updated":
            last_update_dt = self.coordinator._last_update_times.get(self._device_key)
            if last_update_dt is None:
                return "Unknown"
            formatted = format_elapsed_time(last_update_dt)
            return formatted or "Unknown"

        source_data = data.get(self._source)
        if source_data is None:
            return None

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

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        # check every sixty seconds maybe? 
        if self._attr_name == "Last Updated":
            self._refresh_task = self.hass.loop.create_task(self._refresh_loop())

    async def async_will_remove_from_hass(self):
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
        await super().async_will_remove_from_hass()

    async def _refresh_loop(self):
        try:
            while True:
                await asyncio.sleep(60)
                self.async_write_ha_state()
        except asyncio.CancelledError:
            pass
