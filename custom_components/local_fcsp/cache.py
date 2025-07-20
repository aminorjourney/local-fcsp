from typing import Any, Optional
from homeassistant.helpers.storage import Store

class LocalFcspCache:
    """Persistent cache for local FCSP data to smooth startup and avoid 'unavailable' states."""

    def __init__(self, hass, version: int = 1) -> None:
        self._store = Store(hass, version, "local_fcsp")
        self._cache: dict = {}

    async def load(self) -> dict:
        """Load cached data asynchronously."""
        data = await self._store.async_load()
        self._cache = data or {}
        return self._cache

    async def save(self, data: dict) -> None:
        """Save data to cache asynchronously."""
        self._cache = data
        await self._store.async_save(data)

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """Get cached value by key."""
        return self._cache.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set cached value by key."""
        self._cache[key] = value
