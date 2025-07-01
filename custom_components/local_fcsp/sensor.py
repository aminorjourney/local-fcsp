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

from fcsp_api import FCSP

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=60)
DOMAIN = "local_fcsp"


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
            inv_state = inverter_info[0].get("state")
            if inv_state == 1:
                return "Preparing To Power Home"
            elif inv_state == 5:
                return "Powering Home"
            else:
                return "Charging Vehicle"
        return "Power Transferring"
    return state or "Unknown"


def dump_json(data):
    try:
        return json.dumps(data, indent=2)
    except Exception as e:
        _LOGGER.error(f"Error dumping JSON data: {e}")
        return "Error dumping JSON"


SENSORS = [
    ("Station Info", lambda data: "Online" if data else None, None, "charger_info", "mdi:ev-plug-ccs1", False, "charge_station"),
    ("Status", None, None, None, "mdi:ev-station", False, "charge_station"),
    ("Inverter Info", lambda data: "Available" if data else None, None, "inverter_info", "mdi:home-import-outline", False, "home_integration"),
    ("System State", lambda data: data[0].get("state") if data and len(data) > 0 else None, None, "inverter_info", "mdi:transmission-tower", False, "home_integration"),
    ("Status Raw JSON", dump_json, None, "status", "mdi:file-document", True, None),
    ("Charger Info Raw JSON", dump_json, None, "charger_info", "mdi:file-document", True, None),
    ("Inverter Info Raw JSON", dump_json, None, "inverter_info", "mdi:file-document", True, None),
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    fcsp = data["fcsp"]
    home_integration_attached = data.get("home_integration_attached", False)
    debug = entry.options.get("debug", False)

    coordinator = FCSPDataUpdateCoordinator(hass, fcsp)
    await coordinator.async_config_entry_first_refresh()

    entities = []

    for name, key_or_func, unit, source, icon, debug_only, device_key in SENSORS:
        if debug_only and not debug:
            continue
        if device_key == "home_integration" and not home_integration_attached:
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
            )
        )

    async_add_entities(entities, True)


class FCSPDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, fcsp: FCSP):
        super().__init__(
            hass,
            _LOGGER,
            name="Local FCSP Data Coordinator",
            update_interval=SCAN_INTERVAL,
        )
        self._fcsp = fcsp

    async def _async_update_data(self):
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._fcsp.connect)
            charger_info = await loop.run_in_executor(None, self._fcsp.get_charger_info)
            inverter_info = await loop.run_in_executor(None, self._fcsp.get_inverter_info)
            status = await loop.run_in_executor(None, self._fcsp.get_status)
            return {
                "charger_info": charger_info,
                "inverter_info": inverter_info,
                "status": status,
            }
        except Exception as err:
            _LOGGER.error(f"Error communicating with FCSP: {err}")
            raise UpdateFailed(f"FCSP update failed: {err}") from err


class LocalFCSPSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, name, key_or_func, unit, source, coordinator, icon, device_key, entry_id, hass):
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
        self._attr_unique_id = f"local_fcsp_{name.lower().replace(' ', '_')}_{entry_id}"
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit
        self._attr_has_entity_name = True  # <---- THIS IS THE CRUCIAL FIX!
        self._attr_device_info = self._get_device_info()

    def _get_device_info(self):
        config = self._hass.data[DOMAIN][self._entry_id]["config"]
        if self._device_key == "charge_station":
            return DeviceInfo(
                identifiers={(DOMAIN, f"charge_station_{self._entry_id}")},
                manufacturer="Siemens",
                name="Ford Charge Station Pro",
                model="Charge Station Pro",
            )
        elif self._device_key == "home_integration":
            inverter_info = self.coordinator.data.get("inverter_info") or [{}]
            manufacturer = inverter_info[0].get("vendor", "Unknown")
            model = inverter_info[0].get("model", "Unknown")
            return DeviceInfo(
                identifiers={(DOMAIN, f"home_integration_{self._entry_id}")},
                manufacturer=manufacturer,
                name="Home Integration System",
                model=model,
            )
        return None

    @property
    def name(self):
        return self._attr_name

    @property
    def icon(self):
        return self._attr_icon

    @property
    def native_unit_of_measurement(self):
        return self._attr_native_unit_of_measurement

    @property
    def extra_state_attributes(self):
        return self._attributes

    @property
    def available(self):
        return self.coordinator.data is not None

    @property
    def native_value(self):
        data = self.coordinator.data
        if not data:
            return None

        if self._attr_name == "Status":
            charger_info = data.get("charger_info")
            inverter_info = data.get("inverter_info")
            value = interpret_charger_status(charger_info, inverter_info)
            self._attributes = {}
            _LOGGER.debug(f"native_value for {self._attr_unique_id} = {value}")
            return value

        source_data = data.get(self._source)
        if source_data is None:
            return None

        if self._attr_name == "Inverter Info":
            if source_data and len(source_data) > 0:
                status_data = data.get("status") or {}
                inverter_count = status_data.get("inverter_count", "Unknown")
                self._attributes = {
                    "vendor": source_data[0].get("vendor"),
                    "model": source_data[0].get("model"),
                    "serial number": source_data[0].get("slno"),
                    "inverters_connected": inverter_count,
                }
                return "Available"
            return None

        if self._attr_name == "Station Info":
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
            return "Online"

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
