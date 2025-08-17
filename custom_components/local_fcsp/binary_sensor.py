import logging
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import callback
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class PowerCutBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor to detect a power cut using the FCSP inverter."""

    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._attr_name = "Power Cut"
        self._attr_unique_id = f"local_fcsp_power_cut_{entry_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"power_cut_device_{entry_id}")},
            manufacturer="Home Integration System",
            name="Power Cut Monitor",
            model="Power Cut Sensor",
        )
        self._attr_icon_on = "mdi:transmission-tower-off"
        self._attr_icon_off = "mdi:transmission-tower"

    @property
    def is_on(self) -> bool:
        """Return True if a power cut is currently active."""
        val = self.coordinator.is_power_cut_active()
        _LOGGER.debug("PowerCutBinarySensor.is_on called: %s", val)
        return val

    @property
    def icon(self) -> str:
        """Return the appropriate icon based on power cut state."""
        return self._attr_icon_on if self.is_on else self._attr_icon_off

    @callback
    def _handle_coordinator_update(self) -> None:
        """Respond to data updates from the coordinator."""
        self.async_write_ha_state()


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the Power Cut binary sensor from a config entry."""
    coordinator = hass.data[DOMAIN].get(entry.entry_id)
    if not coordinator:
        _LOGGER.error("No coordinator found for entry %s", entry.entry_id)
        return

    async_add_entities(
        [PowerCutBinarySensor(coordinator, entry.entry_id)],
        update_before_add=True,
    )
