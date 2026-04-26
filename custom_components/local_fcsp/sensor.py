import asyncio
import logging
from dataclasses import dataclass
from typing import Callable, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricCurrent,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as hass_dt

from .const import (
    CONF_TIME_FORMAT,
    DEFAULT_TIME_FORMAT,
    DOMAIN,
    TIME_FORMAT_12H,
    TIME_FORMAT_24H,
)
from .coordinator import (
    FcspDataUpdateCoordinator,
    clean_string,
    dump_json,
    interpret_charger_status,
    interpret_inverter_state,
)

_LOGGER = logging.getLogger(__name__)

_FULL_DATA = "__full_data__"

# ---------------------------------------------------------------------------
# Charger state options for ENUM device class
# ---------------------------------------------------------------------------

CHARGER_STATE_OPTIONS = [
    "Idle",
    "Vehicle Connected",
    "Charging Vehicle",
    "Powering Home",
    "Preparing To Power Home",
    "Power Transferring",
    "Charger Fault",
    "Unknown",
]

INVERTER_STATE_OPTIONS = [
    "Inverter Off",
    "Preparing To Power Home",
    "Inverter Standby",  # State 3 — exact meaning unconfirmed; labelled conservatively.
    "Powering Home",     # See README for details on state 3.
    "Unknown State",
]

# ---------------------------------------------------------------------------
# Extended SensorEntityDescription
# ---------------------------------------------------------------------------

@dataclass(frozen=True, kw_only=True)
class FcspSensorEntityDescription(SensorEntityDescription):
    """Extends SensorEntityDescription with FCSP-specific fields."""
    value_fn: Callable = None
    source_key: str = None
    device_key: str = None
    debug_only: bool = False


# ---------------------------------------------------------------------------
# Sensor definitions
# ---------------------------------------------------------------------------

# --- Value functions ---

def _charger_status(data):
    return interpret_charger_status(data.get("charger_info"), data.get("inverter_info"))

def _max_amps(data):
    info = data.get("charger_info") or {}
    val = info.get("maxAmps")
    return float(val) if val is not None else None

def _ip_address(info):
    return clean_string(info.get("ipAddr")) if info else None

def _wifi_firmware(info):
    return clean_string(info.get("vWiFi")) if info else None

def _system_firmware(info):
    return clean_string(info.get("vSystem")) if info else None

def _hw_version(info):
    return clean_string(info.get("vHw")) if info else None

def _wifi_mac(info):
    return clean_string(info.get("wifiAddr")) if info else None

def _ble_mac(info):
    return clean_string(info.get("bleAddr")) if info else None

def _passcode(info):
    return clean_string(info.get("passcode")) if info else None

def _model_number(info):
    return clean_string(info.get("catalogNo")) if info else None

def _serial_number(info):
    return clean_string(info.get("traceNo")) if info else None

def _inverter_status(inv_list):
    return interpret_inverter_state(inv_list)

def _inverter_firmware(inv_list):
    if inv_list and isinstance(inv_list, list):
        return clean_string(inv_list[0].get("firmware"))
    return None

def _inverter_serial(inv_list):
    if inv_list and isinstance(inv_list, list):
        return clean_string(inv_list[0].get("slno"))
    return None

def _inverter_model(inv_list):
    if inv_list and isinstance(inv_list, list):
        return clean_string(inv_list[0].get("model"))
    return None

def _inverter_vendor(inv_list):
    if inv_list and isinstance(inv_list, list):
        return clean_string(inv_list[0].get("vendor"))
    return None


SENSORS: list[FcspSensorEntityDescription] = [

    # --- Charge Station ---

    FcspSensorEntityDescription(
        key="charge_station_status",
        name="Status",
        icon="mdi:ev-plug-ccs1",
        device_class=SensorDeviceClass.ENUM,
        options=CHARGER_STATE_OPTIONS,
        value_fn=_charger_status,
        source_key=_FULL_DATA,
        device_key="charge_station",
    ),
    FcspSensorEntityDescription(
        key="charge_station_breaker_limit",
        name="Breaker Circuit Limit",
        icon="mdi:fuse",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_max_amps,
        source_key=_FULL_DATA,
        device_key="charge_station",
    ),
    FcspSensorEntityDescription(
        key="charge_station_ip_address",
        name="IP Address",
        icon="mdi:ip-network",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_ip_address,
        source_key="charger_info",
        device_key="charge_station",
    ),
    FcspSensorEntityDescription(
        key="charge_station_system_software",
        name="System Software",
        icon="mdi:tag",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_wifi_firmware,
        source_key="charger_info",
        device_key="charge_station",
    ),
    FcspSensorEntityDescription(
        key="charge_station_firmware_version",
        name="Firmware Version",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_system_firmware,
        source_key="charger_info",
        device_key="charge_station",
    ),
    FcspSensorEntityDescription(
        key="charge_station_hardware_version",
        name="Hardware Version",
        icon="mdi:integrated-circuit-chip",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_hw_version,
        source_key="charger_info",
        device_key="charge_station",
    ),
    FcspSensorEntityDescription(
        key="charge_station_wifi_mac",
        name="WiFi MAC Address",
        icon="mdi:wifi-settings",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_wifi_mac,
        source_key="charger_info",
        device_key="charge_station",
    ),
    FcspSensorEntityDescription(
        key="charge_station_ble_mac",
        name="Bluetooth MAC Address",
        icon="mdi:bluetooth",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_ble_mac,
        source_key="charger_info",
        device_key="charge_station",
    ),
    FcspSensorEntityDescription(
        key="charge_station_passcode",
        name="Station Password",
        icon="mdi:key-variant",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_passcode,
        source_key="charger_info",
        device_key="charge_station",
    ),
    FcspSensorEntityDescription(
        key="charge_station_model_number",
        name="Model Number",
        icon="mdi:barcode",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_model_number,
        source_key="charger_info",
        device_key="charge_station",
    ),
    FcspSensorEntityDescription(
        key="charge_station_serial_number",
        name="Serial Number",
        icon="mdi:identifier",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_serial_number,
        source_key="charger_info",
        device_key="charge_station",
    ),
    FcspSensorEntityDescription(
        key="charge_station_last_updated",
        name="Last Updated",
        icon="mdi:timer",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=None,
        source_key="charger_info",
        device_key="charge_station",
    ),

    # --- Home Integration System ---

    FcspSensorEntityDescription(
        key="his_status",
        name="Intelligent Backup Power",
        icon="mdi:home-outline",
        device_class=SensorDeviceClass.ENUM,
        options=INVERTER_STATE_OPTIONS,
        value_fn=_inverter_status,
        source_key="inverter_info",
        device_key="home_integration",
    ),
    FcspSensorEntityDescription(
        key="his_firmware",
        name="Inverter Firmware",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_inverter_firmware,
        source_key="inverter_info",
        device_key="home_integration",
    ),
    FcspSensorEntityDescription(
        key="his_serial_number",
        name="Inverter Serial Number",
        icon="mdi:identifier",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_inverter_serial,
        source_key="inverter_info",
        device_key="home_integration",
    ),
    FcspSensorEntityDescription(
        key="his_model",
        name="Inverter Model",
        icon="mdi:information-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_inverter_model,
        source_key="inverter_info",
        device_key="home_integration",
    ),
    FcspSensorEntityDescription(
        key="his_vendor",
        name="Inverter Vendor",
        icon="mdi:domain",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_inverter_vendor,
        source_key="inverter_info",
        device_key="home_integration",
    ),
    FcspSensorEntityDescription(
        key="his_last_updated",
        name="Last Updated",
        icon="mdi:timer",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=None,
        source_key="inverter_info",
        device_key="home_integration",
    ),

    # --- Debug / Raw (disabled by default) ---

    FcspSensorEntityDescription(
        key="debug_raw_charger",
        name="Raw Charger Data",
        icon="mdi:file-search-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=dump_json,
        source_key="charger_info",
        device_key="charge_station",
        debug_only=True,
    ),
    FcspSensorEntityDescription(
        key="debug_raw_inverter",
        name="Raw Inverter Data",
        icon="mdi:file-search-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=dump_json,
        source_key="inverter_info",
        device_key="home_integration",
        debug_only=True,
    ),
    FcspSensorEntityDescription(
        key="debug_raw_config",
        name="Raw Config Status",
        icon="mdi:clipboard-check",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=dump_json,
        source_key="config_status",
        device_key=None,
        debug_only=True,
    ),
    FcspSensorEntityDescription(
        key="debug_raw_network",
        name="Raw Network Info",
        icon="mdi:access-point-network",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=dump_json,
        source_key="network_info",
        device_key=None,
        debug_only=True,
    ),
]


# ---------------------------------------------------------------------------
# Legacy entity unique IDs — cleaned up on setup
# ---------------------------------------------------------------------------

# Unique ID patterns from pre-2026.4.0 that should be removed on upgrade.
LEGACY_UNIQUE_IDS = [
    "local_fcsp_{device_key}_info_{entry_id}",
    "local_fcsp_{device_key}_raw_data_{entry_id}",
    "local_fcsp_{device_key}_status_{entry_id}",
    "local_fcsp_{device_key}_last_updated_{entry_id}",
]

LEGACY_UNIQUE_ID_NAMES = [
    "info",
    "raw_data",
    "fcsp_config_status",
    "fcsp_network_info",
    "fcsp_device_summary",
]


async def cleanup_legacy_entities(hass: HomeAssistant, entry_id: str):
    """Remove stale entities from pre-2026.4.0 versions."""
    entity_registry = er.async_get(hass)

    # Build list of known legacy unique IDs
    legacy_ids = []
    for device_key in ["charge_station", "home_integration", "None"]:
        for name in LEGACY_UNIQUE_ID_NAMES:
            legacy_ids.append(f"local_fcsp_{device_key}_{name}_{entry_id}")

    # Also catch the old binary sensor
    legacy_ids.append(f"binary_sensor.power_cut_monitor_{entry_id}")

    removed = 0
    for unique_id in legacy_ids:
        entity = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
        if entity:
            _LOGGER.info("Removing legacy entity '%s' for entry %s", entity, entry_id)
            entity_registry.async_remove(entity)
            removed += 1

    if removed:
        _LOGGER.info("Removed %d legacy entities for entry %s", removed, entry_id)


# ---------------------------------------------------------------------------
# LocalFCSPSensor
# ---------------------------------------------------------------------------

class LocalFCSPSensor(CoordinatorEntity, SensorEntity):

    entity_description: FcspSensorEntityDescription

    def __init__(
        self,
        description: FcspSensorEntityDescription,
        coordinator: FcspDataUpdateCoordinator,
        entry_id: str,
        hass: HomeAssistant,
    ):
        super().__init__(coordinator)
        self.entity_description = description
        self._entry_id = entry_id
        self._hass = hass
        self._attr_unique_id = f"local_fcsp_{description.key}_{entry_id}"
        self._attr_has_entity_name = True
        self._refresh_task = None

    @property
    def device_info(self) -> DeviceInfo:
        data = self.coordinator.data or {}
        device_key = self.entity_description.device_key

        if device_key == "charge_station":
            info = data.get("charger_info") or {}
            return DeviceInfo(
                identifiers={(DOMAIN, f"charge_station_{self._entry_id}")},
                name="Ford Charge Station Pro",
                manufacturer="Siemens / Ford",
                model="VersiCharge SG",
                model_id=clean_string(info.get("catalogNo")) or None,
                serial_number=clean_string(info.get("traceNo")) or None,
                hw_version=clean_string(info.get("vHw")) or None,
                sw_version=clean_string(info.get("vSystem")) or None,
                configuration_url=(
                    f"https://{info['ipAddr']}" if info.get("ipAddr") else None
                ),
            )

        if device_key == "home_integration":
            inv_list = data.get("inverter_info") or [{}]
            inv = inv_list[0] if inv_list else {}
            return DeviceInfo(
                identifiers={(DOMAIN, f"home_integration_{self._entry_id}")},
                name="Home Integration System",
                manufacturer=clean_string(inv.get("vendor")) or "Delta Electronics",
                model=clean_string(inv.get("model")) or "E4_BDI",
                serial_number=clean_string(inv.get("slno")) or None,
                sw_version=clean_string(inv.get("firmware")) or None,
            )

        return None

    @property
    def native_value(self):
        data = self.coordinator.data
        if not data:
            return None

        desc = self.entity_description

        if desc.key.endswith("_last_updated"):
            last_update_dt = self.coordinator._last_update_dt
            if last_update_dt is None:
                return "Unknown"
            local_dt = hass_dt.as_local(last_update_dt)
            entry = self._hass.config_entries.async_get_entry(self._entry_id)
            fmt_pref = (
                entry.options.get(CONF_TIME_FORMAT, DEFAULT_TIME_FORMAT)
                if entry
                else DEFAULT_TIME_FORMAT
            )
            fmt_str = TIME_FORMAT_24H if fmt_pref == "24h" else TIME_FORMAT_12H
            return local_dt.strftime(fmt_str)

        if desc.value_fn is None:
            return None

        source = (
            data
            if desc.source_key == _FULL_DATA
            else data.get(desc.source_key)
        )
        try:
            return desc.value_fn(source)
        except Exception as e:
            _LOGGER.error(
                "Error computing value for %s: %s", desc.key, e
            )
            return None

    @property
    def available(self):
        if self.entity_description.device_key == "home_integration":
            return self.coordinator.home_integration_attached
        return bool(self.coordinator.data)

    @property
    def icon(self):
        """Return dynamic icon based on current state."""
        key = self.entity_description.key
        val = self.native_value

        if key == "charge_station_status":
            return {
                "Idle":                     "mdi:ev-station",
                "Vehicle Connected":        "mdi:ev-plug-ccs1",
                "Charging Vehicle":         "mdi:car-electric",
                "Powering Home":            "mdi:home-lightning-bolt-outline",
                "Preparing To Power Home":  "mdi:timer-sand",
                "Power Transferring":       "mdi:transfer",
                "Charger Fault":            "mdi:alert-circle",
                "Unknown":                  "mdi:help-circle",
            }.get(val, "mdi:ev-plug-ccs1")

        if key == "his_status":
            return {
                "Powering Home":            "mdi:home-lightning-bolt-outline",
                "Preparing To Power Home":  "mdi:timer-sand",
                "Inverter Standby":         "mdi:timer-sand",
                "Inverter Off":             "mdi:home-outline",
                "Unknown State":            "mdi:help-circle",
            }.get(val, "mdi:home-outline")

        return self.entity_description.icon

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if self.entity_description.key.endswith("_last_updated"):
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


# ---------------------------------------------------------------------------
# PowerCutSensor
# ---------------------------------------------------------------------------

class PowerCutSensor(CoordinatorEntity, SensorEntity):
    """Quasi-binary sensor reporting grid power cut status via HIS inverter state."""

    def __init__(self, coordinator: FcspDataUpdateCoordinator, entry_id: str, hass: HomeAssistant):
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._hass = hass
        self._attr_name = "Grid Status"
        self._attr_unique_id = f"power_cut_{entry_id}"
        self._attr_has_entity_name = True
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = ["Grid Connected", "Power Cut", "Unknown"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"home_integration_{entry_id}")},
        )

    @property
    def native_value(self):
        if not getattr(self.coordinator, "home_integration_attached", False):
            return "Unknown"
        try:
            return "Power Cut" if self.coordinator.is_power_cut_active() else "Grid Connected"
        except Exception as e:
            _LOGGER.error("Error checking PowerCutSensor: %s", e)
            return None

    @property
    def available(self):
        return bool(self.coordinator.data)

    @property
    def icon(self):
        val = self.native_value
        if val == "Power Cut":
            return "mdi:transmission-tower-off"
        if val == "Unknown":
            return "mdi:help-circle"
        return "mdi:transmission-tower"

    @callback
    def _handle_coordinator_update(self):
        self.async_write_ha_state()


# ---------------------------------------------------------------------------
# Legacy binary sensor cleanup
# ---------------------------------------------------------------------------

async def cleanup_old_power_cut_binary_sensor(hass: HomeAssistant, entry_id: str):
    """Remove legacy binary_sensor.power_cut_monitor_* entity if it still exists."""
    entity_registry = er.async_get(hass)
    old_entity_id = f"binary_sensor.power_cut_monitor_{entry_id}"
    old_entity = entity_registry.async_get(old_entity_id)
    if old_entity:
        _LOGGER.info(
            "Removing legacy Power Cut binary sensor '%s' for entry %s",
            old_entity_id,
            entry_id,
        )
        entity_registry.async_remove(old_entity.entity_id)


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator: FcspDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    debug = entry.options.get("debug", True)

    # Remove orphan and phantom devices from older versions
    cleaned_set = hass.data[DOMAIN].setdefault("cleanup_done", set())
    if entry.entry_id not in cleaned_set:
        device_registry = dr.async_get(hass)

        # Legacy orphan devices created by pre-2026.4.0 versions
        for identifier in [
            f"online_device_{entry.entry_id}",
            f"power_cut_device_{entry.entry_id}",
        ]:
            device = device_registry.async_get_device(
                identifiers={(DOMAIN, identifier)}
            )
            if device:
                _LOGGER.info(
                    "Removing legacy orphan device '%s' for entry %s",
                    identifier, entry.entry_id,
                )
                device_registry.async_remove_device(device.id)

        # Remove phantom HIS device if no inverter is attached
        if not coordinator.home_integration_attached:
            device = device_registry.async_get_device(
                identifiers={(DOMAIN, f"home_integration_{entry.entry_id}")}
            )
            if device:
                _LOGGER.warning(
                    "Removing phantom HIS device for entry %s", entry.entry_id
                )
                device_registry.async_remove_device(device.id)

        cleaned_set.add(entry.entry_id)

    # Clean up legacy entities from pre-2026.4.0
    await cleanup_legacy_entities(hass, entry.entry_id)
    await cleanup_old_power_cut_binary_sensor(hass, entry.entry_id)

    entities = []
    for desc in SENSORS:
        if desc.debug_only and not debug:
            continue
        if desc.device_key == "home_integration" and not coordinator.home_integration_attached:
            continue
        entities.append(
            LocalFCSPSensor(
                description=desc,
                coordinator=coordinator,
                entry_id=entry.entry_id,
                hass=hass,
            )
        )

    async_add_entities(entities, True)

    if coordinator.home_integration_attached:
        _LOGGER.debug("Creating PowerCutSensor for entry %s", entry.entry_id)
        async_add_entities(
            [PowerCutSensor(coordinator, entry.entry_id, hass)],
            update_before_add=True,
        )
