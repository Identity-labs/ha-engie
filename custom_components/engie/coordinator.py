"""Price polling coordinator."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EngieAPI
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class EngiePriceCoordinator(DataUpdateCoordinator[list[Any]]):
    """Polls current €/kWh prices for every energy contract."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: EngieAPI,
        entry: ConfigEntry,
    ) -> None:
        interval = int(
            entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_prices_{entry.entry_id}",
            update_interval=timedelta(seconds=max(interval, 300)),
        )
        self.api = api
        self.entry = entry

    async def _async_update_data(self) -> list[Any]:
        try:
            prices = await self.api.async_get_prices()
        except ConfigEntryAuthFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"ENGIE prices unavailable: {err}") from err
        return list(prices or [])
