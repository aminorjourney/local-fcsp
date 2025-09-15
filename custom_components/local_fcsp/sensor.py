import asyncio
import json
import logging
from datetime import timedelta

from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    CONF_SCAN_INTERVAL,
    CONF_TIME_FORMAT,
    DEFAULT_TIME_FORMAT,
    TIME_FORMAT_24H,
    TIME_FORMAT_12H,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    UpdateFailed,
    DataUpdateCoordinator,
)
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers import device_registry as dr
from homeassistant.util import dt as hass_dt

from .coordinator import (
    normalize_inverter_states,
    clean_string,
    firmware_to_hex_string,
    clean_inverter_info_list,
    interpret_charger_status,
    interpret_inverter_state,
    dump_json,
)

from fcsp_api import FCSP

_LOGGER = logging.getLogger(__name__)

# Define sensors so we know what to call things. Names are important.

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

# Coordinate all the things with the coordinators.

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


# Retreive all the data, and make it look pretty

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

            self.home_integration_attached = bool(inverter_info)

            now = hass_dt.utcnow()
            if charger_info != self.data.get("charger_info"):
                self._last_update_times["charge_station"] = now
            if inverter_info != self.data.get("inverter_info"):
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
            if self.data:
                _LOGGER.warning("Using cached data due to update failure")
                return self.data
            raise UpdateFailed(f"FCSP update failed: {err}") from err

# Helper to set up the Power Cut Sensor.


    def get_inverter_state_raw(self):
        inv_info = self.data.get("inverter_info") or []
        if not inv_info:
            return 0
        raw = inv_info[0].get("state", 0)
        try:
            return int(raw)
        except Exception:
            normalized = str(raw).replace("_", " ").strip().lower()
            return 0 if normalized in ("not ready", "0", "off", "inverter off") else 1

    def is_power_cut_active(self):
        return self.get_inverter_state_raw() != 0

# The actual sensor entities.

class LocalFCSPSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, name, key_or_func, unit, source, coordinator, icon, device_key, entry_id, hass, enabled_default=True):
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
            inv = inverter_info[0] if inverter_info else {}
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
        data = self.coordinator.data
        if self._attr_name == "Raw Data":
            source_data = data.get(self._source)
            if self._device_key == "home_integration" and isinstance(source_data, list) and source_data:
                inv = source_data[0]
                return {
                    "vendor": clean_string(inv.get("vendor")),
                    "model": clean_string(inv.get("model")),
                    "serial_number": clean_string(inv.get("slno")),
                    "name": clean_string(inv.get("name")),
                    "state": inv.get("state"),
                    "firmware (hex)": inv.get("firmware_hex"),
                }
            if self._device_key == "charge_station":
                return source_data if isinstance(source_data, dict) else {"data": source_data}

        if self._attr_name == "Info":
            if self._device_key == "charge_station":
                source_data = data.get("charger_info")
                status_data = data.get("status") or {}
                max_amps = status_data.get("max_amps")
                return {
                    "model_name": source_data.get("vHw"),
                    "model_number": source_data.get("catalogNo"),
                    "serial_number": source_data.get("traceNo"),
                    "software_version": source_data.get("vWiFi"),
                    "ip_address": source_data.get("ipAddr"),
                    "hardware_current_limit": f"{max_amps} A" if max_amps else "Unknown",
                    "V2G System Attached": self.coordinator.home_integration_attached,
                }
            elif self._device_key == "home_integration":
                source_data = data.get("inverter_info")
                if source_data and isinstance(source_data, list) and source_data:
                    inv = source_data[0]
                    return {
                        "vendor": clean_string(inv.get("vendor")),
                        "model": clean_string(inv.get("model")),
                        "serial_number": clean_string(inv.get("slno")),
                        "firmware": inv.get("firmware"),
                    }
                return {}

        if self._attr_name == "Last Updated":
            return {}

        if self._attr_name in {"FCSP Config Status", "FCSP Network Info", "FCSP Device Summary"}:
            data_val = data.get(self._source)
            return data_val if isinstance(data_val, dict) else {"data": data_val}

        return self._attributes

    @property
    def available(self):
        if self._device_key == "home_integration":
            return self.coordinator.home_integration_attached
        return bool(self.coordinator.data)

    @property
    def native_value(self):
        data = self.coordinator.data
        if not data:
            return None

        if self._attr_name in ("Info", "Raw Data"):
            return "See Attributes"

        if self._attr_name == "Status" and self._device_key == "charge_station":
            return interpret_charger_status(data.get("charger_info"), data.get("inverter_info"))

        if self._attr_name == "Status" and self._device_key == "home_integration":
            return interpret_inverter_state(data.get("inverter_info"))

        if self._attr_name == "Last Updated":
            last_update_dt = self.coordinator._last_update_times.get(self._device_key)
            if last_update_dt is None:
                return "Unknown"
            local_dt = hass_dt.as_local(last_update_dt)
            fmt_pref = self._hass.config_entries.async_get_entry(self._entry_id).options.get(
                CONF_TIME_FORMAT, DEFAULT_TIME_FORMAT
            )
            fmt_str = TIME_FORMAT_24H if fmt_pref == "24h" else TIME_FORMAT_12H
            return local_dt.strftime(fmt_str)

        source_data = data.get(self._source)
        if callable(self._key_or_func):
            try:
                return self._key_or_func(source_data)
            except Exception as e:
                _LOGGER.error(f"Error processing sensor value for {self._attr_name}: {e}")
                return None
        else:
            return source_data.get(self._key_or_func) if isinstance(source_data, dict) else None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
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

# Define the Power Cut Sensor we created a helper for earlier.


class PowerCutSensor(CoordinatorEntity, SensorEntity):
    """Quasi-binary sensor for power cut status using the FCSP coordinator."""

    def __init__(self, coordinator, entry_id, hass):
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._hass = hass
        self._attr_name = "Power Cut"
        self._attr_unique_id = f"power_cut_{entry_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"power_cut_device_{entry_id}")},
            manufacturer="Home Integration System",
            name="Power Cut Monitor",
            model="Power Cut Sensor",
        )
        self._attr_has_entity_name = True
        self._state = "Awaiting Data"  # Start with Awaiting Data

    @property
    def native_value(self):
        """Return 'On', 'Off', or 'Awaiting Data' for power cut state."""
        if not getattr(self.coordinator, "home_integration_attached", False):
            return "Awaiting Data"

        try:
            active = self.coordinator.is_power_cut_active()
            return "On" if active else "Off"
        except Exception as e:
            _LOGGER.error(f"Error checking PowerCutSensor: {e}")
            return "Awaiting Data"

    @property
    def available(self):
        return getattr(self.coordinator, "home_integration_attached", False)

    @property
    def icon(self):
        """Dynamic icon based on power cut state."""
        val = self.native_value
        if val == "Awaiting Data":
            return "mdi:clock-outline"
        return "mdi:transmission-tower-off" if val == "On" else "mdi:transmission-tower"

    @callback
    def _handle_coordinator_update(self):
        self.async_write_ha_state()

# Previous versions used binary sensors, so we're making sure they aren't around any more.


async def cleanup_old_power_cut_binary_sensor(hass, entry_id):
    """Remove old Power Cut Binary Sensor if it exists."""
    entity_registry = er.async_get(hass)
    old_entity_id = f"binary_sensor.power_cut_monitor_{entry_id}"  # legacy ID

    old_entity = entity_registry.async_get(old_entity_id)
    if old_entity:
        _LOGGER.info(
            "Removing old Power Cut Binary Sensor '%s' for entry %s",
            old_entity_id,
            entry_id,
        )
        entity_registry.async_remove(old_entity.entity_id)

# Setup the Entries in HA using the various things we've made to this point.

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    existing_coordinator = hass.data[DOMAIN][entry.entry_id]
    fcsp = existing_coordinator._fcsp
    cache = getattr(existing_coordinator, "_cache_store", None)
    cached_data = getattr(existing_coordinator, "data", None)

    scan_interval_seconds = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    scan_interval = timedelta(seconds=scan_interval_seconds)
    debug = entry.options.get("debug", True)

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

    # Cleanup phantom HIS devices
    hass.data.setdefault(DOMAIN, {})
    cleaned_set = hass.data[DOMAIN].setdefault("cleanup_done", set())
    if entry.entry_id not in cleaned_set:
        if not coordinator.home_integration_attached:
            device_registry = dr.async_get(hass)
            device = device_registry.async_get_device(
                identifiers={(DOMAIN, f"home_integration_{entry.entry_id}")}
            )
            if device:
                _LOGGER.warning("Removing phantom HIS device for entry %s", entry.entry_id)
                device_registry.async_remove_device(device.id)
        cleaned_set.add(entry.entry_id)

    # Add standard sensors
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

    # Remove old Power Cut Binary Sensor
    await cleanup_old_power_cut_binary_sensor(hass, entry.entry_id)

    #  Add new PowerCutSensor if applicable
    if coordinator.home_integration_attached:
        sensor = PowerCutSensor(coordinator, entry.entry_id, hass)
        _LOGGER.debug("Creating PowerCutSensor for entry %s", entry.entry_id)
        async_add_entities([sensor], update_before_add=True)
