import asyncio
import json
import logging
from datetime import timedelta, datetime

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL, CONF_SCAN_INTERVAL, CONF_TIME_FORMAT, DEFAULT_TIME_FORMAT, TIME_FORMAT_24H, TIME_FORMAT_12H
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

from .coordinator import (
    normalize_inverter_states,
    clean_string,
    firmware_to_hex_string,
    clean_inverter_info_list,
    interpret_charger_status,
    interpret_inverter_state,
    dump_json,
    format_elapsed_time,
)

from fcsp_api import FCSP

_LOGGER = logging.getLogger(__name__)

# --- Utility Functions ---

# We removed the utility functions and cast banish. They now live in the coordinator.py. Roll for Initiative if you disagree. 

SENSORS = [
    ("Info", lambda data: "Click To View", None, "charger_info", "mdi:information", False, "charge_station", True),
    ("Status", None, None, None, "mdi:ev-plug-ccs1", False, "charge_station", True),
    ("Info", lambda data: "Click To View", None, "inverter_info", "mdi:information", False, "home_integration", True),
    ("Status", lambda data: interpret_inverter_state(data), None, "inverter_info", "mdi:sine-wave", False, "home_integration", True),

    ("Raw Data", lambda data: "See Attributes", None, "charger_info", "mdi:file-search-outline", True, "charge_station", False),
    ("Raw Data", lambda data: "See Attributes", None, "inverter_info", "mdi:file-search-outline", True, "home_integration", False),

    ("Last Updated", None, None, "charger_info", "mdi:timer", False, "charge_station", True),
    ("Last Updated", None, None, "inverter_info", "mdi:timer", False, "home_integration", True),

    ("FCSP Config Status", dump_json, None, "config_status", "mdi:clipboard-check", True, None, False),
    ("FCSP Network Info", dump_json, None, "network_info", "mdi:access-point-network", True, None, False),
    ("FCSP Device Summary", dump_json, None, "device_summary", "mdi:information-outline", True, None, False),
]

# --- Coordinator class with cache support ---

class FCSPDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, fcsp: FCSP, scan_interval: timedelta, cache=None, cache_store=None):
        super().__init__(
            hass,
            _LOGGER,
            name="Local FCSP Data Coordinator",
            update_interval=scan_interval,
        )
        self._fcsp = fcsp
        self._cache_store = cache_store
        self.home_integration_attached = False
        self._last_update_times = {}
        self.data = cache or {}

    async def _async_update_data(self):
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._fcsp.connect)

            charger_info = await loop.run_in_executor(None, self._fcsp.get_charger_info)
            config_status = await loop.run_in_executor(None, self._fcsp.get_config_status)
            network_info = await loop.run_in_executor(None, self._fcsp.get_network_info)
            status = await loop.run_in_executor(None, self._fcsp.get_status)
            device_summary = await loop.run_in_executor(None, self._fcsp.get_device_summary)
            inverter_info = await loop.run_in_executor(None, self._fcsp.get_inverter_info)
            inverter_info = normalize_inverter_states(inverter_info or [])
            inverter_info = clean_inverter_info_list(inverter_info or [])

            self.home_integration_attached = bool(inverter_info and len(inverter_info) > 0)

            now = hass_dt.utcnow()

            if charger_info != (self.data.get("charger_info") if self.data else None):
                self._last_update_times["charge_station"] = now

            if inverter_info != (self.data.get("inverter_info") if self.data else None):
                self._last_update_times["home_integration"] = now

            fresh_data = {
                "charger_info": charger_info,
                "inverter_info": inverter_info,
                "config_status": config_status,
                "network_info": network_info,
                "status": status,
                "device_summary": device_summary,
            }

            if self._cache_store:
                await self._cache_store.save(fresh_data)

            return fresh_data

        except Exception as err:
            _LOGGER.error(f"Error communicating with FCSP: {err}")
            # Fallback to cache if possible
            if self.data:
                _LOGGER.warning("Using cached data due to update failure")
                return self.data
            raise UpdateFailed(f"FCSP update failed: {err}") from err

# --- Sensor entity class ---

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
        self._refresh_task = None

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

    @property
    def extra_state_attributes(self):
        if self._attr_name == "Raw Data":
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
                        "firmware (hex)": inv.get("firmware_hex"), #cleaned version in hexadecimal
                    }
                return {}
            elif self._device_key == "charge_station":
                return source_data if isinstance(source_data, dict) else {"data": source_data}

        if self._attr_name == "Info":
            if self._device_key == "charge_station":
                source_data = self.coordinator.data.get("charger_info")
                status_data = self.coordinator.data.get("status") or {}
                max_amps = status_data.get("max_amps")
                inverter_count = status_data.get("inverter_count", 0)
                return {
                    "model_name": source_data.get("vHw"),
                    "model_number": source_data.get("catalogNo"),
                    "serial_number": source_data.get("traceNo"),
                    "software_version": source_data.get("vWiFi"),
                    "ip_address": source_data.get("ipAddr"),
                    "hardware_current_limit": f"{max_amps} A" if max_amps else "Unknown",
                    "V2G System Attached": bool(inverter_count),
                }
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
                        "firmware": inv.get("firmware"), #human-readable software version
                    }
                return {}

        if self._attr_name == "Last Updated":
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

    @property
    def native_value(self):
        data = self.coordinator.data
        if not data:
            return None

        if self._attr_name in ("Info", "Raw Data"):
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
            local_dt = hass_dt.as_local(last_update_dt)

            # Fetch preferred format (defaults to 12h if not found)
            fmt_pref = self._hass.config_entries.async_get_entry(self._entry_id).options.get(CONF_TIME_FORMAT, DEFAULT_TIME_FORMAT)
            fmt_str = TIME_FORMAT_24H if fmt_pref == "24h" else TIME_FORMAT_12H
            return local_dt.strftime(fmt_str)

        source_data = self.coordinator.data.get(self._source)

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
        # "Last Updated" sensors update every 60 seconds to keep freshness info current
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

# --- Entry Setup ---

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    existing_coordinator = hass.data[DOMAIN][entry.entry_id]
    fcsp = existing_coordinator._fcsp

    # Access cache and cached_data from the existing coordinator
    cache = getattr(existing_coordinator, "_cache_store", None)
    cached_data = getattr(existing_coordinator, "data", None)

    scan_interval_seconds = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    scan_interval = timedelta(seconds=scan_interval_seconds)
    debug = entry.options.get("debug", True)

    # Create a new coordinator with fresh settings or reuse existing cached data
    coordinator = FCSPDataUpdateCoordinator(
        hass=hass,
        fcsp=fcsp,
        scan_interval=scan_interval,
        cache=cached_data,
        cache_store=cache,
    )

    try:
        await asyncio.wait_for(coordinator.async_config_entry_first_refresh(), timeout=60)
    except asyncio.TimeoutError:
        _LOGGER.error("Timeout while waiting for initial data refresh from FCSP.")
        raise

    entities = []
    for (
        name,
        key_or_func,
        unit,
        source,
        icon,
        debug_only,
        device_key,
        enabled_default,
    ) in SENSORS:
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
