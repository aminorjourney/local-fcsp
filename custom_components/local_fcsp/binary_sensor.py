from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    if not coordinator.home_integration_attached:
        return

    async_add_entities([PowerCutBinarySensor(coordinator, entry.entry_id)])


class PowerCutBinarySensor(CoordinatorEntity, BinarySensorEntity):
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
    def is_on(self):
        if not self.coordinator.home_integration_attached:
            return False  # No inverter? No power cut detection.

        inverter_info = self.coordinator.data.get("inverter_info") or []
        if not inverter_info:
            return False
        try:
            state = int(inverter_info[0].get("state"))
        except (ValueError, TypeError):
            return False
        # True means power cut (grid not present)
        return state not in (1, 5)

    @property
    def icon(self):
        return self._attr_icon_on if self.is_on else self._attr_icon_off

    @property
    def available(self):
        return self.coordinator.data is not None

