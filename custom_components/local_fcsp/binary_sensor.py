import logging
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the PowerCutBinarySensor from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.debug("Adding PowerCutBinarySensor entity...")
    async_add_entities([PowerCutBinarySensor(coordinator, entry.entry_id)])


class PowerCutBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """
    Binary sensor to detect a power cut using the Home Integration System.

    This sensor is only available if a Home Integration System is attached.
    It interprets inverter state values to determine whether grid power is down.
    """

    def __init__(self, coordinator, entry_id):
        """Initialize the Power Cut sensor."""
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
    def available(self):
        """
        Return True if Home Integration is attached and data is present.

        If there's no inverter attached, this sensor should not be exposed.
        """
        _LOGGER.debug(f"PowerCutBinarySensor available check: coordinator.home_integration_attached={self.coordinator.home_integration_attached}")
        available = self.coordinator.home_integration_attached and bool(self.coordinator.data)
        _LOGGER.debug(f"PowerCutBinarySensor available: {available}")
        return available

    @property
    def is_on(self):
        """
        Return True if a power cut is detected.

        A power cut is inferred when the inverter reports state 1 or 5.
        """
        _LOGGER.debug(f"PowerCutBinarySensor is_on check: home_integration_attached={self.coordinator.home_integration_attached}")

        if not self.coordinator.home_integration_attached:
            _LOGGER.debug("PowerCutBinarySensor is_off: No inverter attached.")
            return False

        inverter_info = self.coordinator.data.get("inverter_info") or []
        _LOGGER.debug(f"Inverter info for PowerCutBinarySensor: {inverter_info}")

        if not inverter_info:
            _LOGGER.debug("PowerCutBinarySensor is_off: inverter_info empty or missing.")
            return False

        try:
            state = int(inverter_info[0].get("state"))
        except (ValueError, TypeError, IndexError) as e:
            _LOGGER.warning(f"PowerCutBinarySensor error parsing inverter state: {e}")
            return False

        # State 1 and 5 = grid is down => power cut
        power_cut = state in (1, 5)
        _LOGGER.debug(f"PowerCutBinarySensor is_on evaluated as: {power_cut} (state={state})")
        return power_cut

    @property
    def icon(self):
        """Return the appropriate icon based on power cut state."""
        return self._attr_icon_on if self.is_on else self._attr_icon_off

