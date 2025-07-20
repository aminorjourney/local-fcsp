from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Only add the sensor if the Home Integration System (inverter) is attached
    if not coordinator.home_integration_attached:
        return

    async_add_entities([PowerCutBinarySensor(coordinator, entry.entry_id)])


class PowerCutBinarySensor(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._attr_name = "Power Cut Monitor"
        self._attr_unique_id = f"local_fcsp_power_cut_monitor_{entry_id}"
        self._attr_device_info = self._get_device_info()
        self._attr_icon = "mdi:transmission-tower-off"  # Default icon

    def _get_device_info(self):
        # Unique device so it appears as its own device in HA
        return DeviceInfo(
            identifiers={(DOMAIN, f"power_cut_monitor_{self._entry_id}")},
            manufacturer="Home Integration System",
            name="Power Cut Monitor",
            model="Power Cut Sensor",
        )

    @property
    def is_on(self):
        """Return True if the grid is down (power cut)."""
        inverter_info = self.coordinator.data.get("inverter_info") or []
        if not inverter_info:
            return False
        try:
            state = int(inverter_info[0].get("state"))
        except (ValueError, TypeError):
            return False
        # State 1 or 5 means grid present; anything else = power cut
        return state not in (1, 5)

    @property
    def icon(self):
        """Return the icon based on grid status."""
        return "mdi:transmission-tower-off" if self.is_on else "mdi:transmission-tower"

    @property
    def available(self):
        return self.coordinator.data is not None
