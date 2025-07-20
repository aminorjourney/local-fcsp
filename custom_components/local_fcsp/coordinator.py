import logging
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

logger = logging.getLogger(__name__)

class FcspDataUpdateCoordinator(DataUpdateCoordinator):
    """Manages fetching and caching data from the Ford Charge Station Pro device.
    Or lets you use frozen peas when there are no fresh peas available."""

    def __init__(self, hass, config_entry, fcsp, cache_store, cached_data, scan_interval):
        """
        Initialize the coordinator.

        Args:
            hass: Home Assistant instance
            config_entry: ConfigEntry instance for this integration
            fcsp: FCSP client instance
            cache_store: LocalFcspCache instance for persistent storage
            cached_data: Previously saved data loaded from storage
            scan_interval: Polling interval in seconds
        """
        super().__init__(
            hass,
            logger,
            name="FCSP Coordinator",
            update_interval=timedelta(seconds=scan_interval),
        )
        self._fcsp = fcsp
        self._cache_store = cache_store
        self.data = cached_data or {}

        # Initialize private attribute for property
        inverter_info = self.data.get("inverter_info")
        self._home_integration_attached = bool(
            inverter_info and isinstance(inverter_info, list) and len(inverter_info) > 0
        )

    async def _fetch_fcsp_data(self):
        """Fetch fresh data from the FCSP device (runs in executor)."""
        return await self.hass.async_add_executor_job(self._fcsp.get_status)

    async def _async_update_data(self):
        """
        Fetch new data from the device and update cache.

        Falls back to cached data if fetching fresh data fails.
        """
        try:
            fresh_data = await self._fetch_fcsp_data()

            # Update internal data cache
            self.data = fresh_data

            # Update home integration attached flag based on fresh data
            inverter_info = fresh_data.get("inverter_info")
            self.home_integration_attached = bool(
                inverter_info and isinstance(inverter_info, list) and len(inverter_info) > 0
            )

            # Save fresh data to cache
            await self._cache_store.save(fresh_data)

            logger.debug("FCSP fresh data fetched and cached successfully.")
            return fresh_data
        except Exception as e:
            logger.warning("Falling back to cached data due to error: %s", e)
            if self.data:
                # Keep home_integration_attached consistent with cached data
                inverter_info = self.data.get("inverter_info")
                self.home_integration_attached = bool(
                    inverter_info and isinstance(inverter_info, list) and len(inverter_info) > 0
                )
                return self.data
            raise

    @property
    def home_integration_attached(self) -> bool:
        """Return True if the Home Integration System (inverter) is attached."""
        return self._home_integration_attached

    @home_integration_attached.setter
    def home_integration_attached(self, value: bool):
        self._home_integration_attached = value

