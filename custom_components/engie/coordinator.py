"""Polling coordinator for prices, consumption, and billing."""

from __future__ import annotations

from datetime import timedelta
import logging

from engie_particuliers.models import AccountSnapshot
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EngieAPI
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class EngieCoordinator(DataUpdateCoordinator[AccountSnapshot]):
    """Polls current tariffs, recent daily consumption, and billing."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: EngieAPI,
        entry: ConfigEntry,
    ) -> None:
        interval = int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=max(interval, 300)),
        )
        self.api = api
        self.entry = entry
        self._history_bootstrapped = False

    async def _async_update_data(self) -> AccountSnapshot:
        try:
            snapshot = await self.api.async_get_snapshot()
        except ConfigEntryAuthFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"ENGIE data unavailable: {err}") from err
        self.hass.async_create_task(self._async_sync_history(snapshot))
        return snapshot

    async def _async_sync_history(self, snapshot: AccountSnapshot) -> None:
        from . import statistics as stats

        first = not self._history_bootstrapped
        self._history_bootstrapped = True
        try:
            if first:
                await stats.async_import_history(self.hass, self)
            else:
                await stats.async_heal_recent(self.hass, self, snapshot)
        except Exception:  # noqa: BLE001 — history import must not fail the poll
            if first:
                self._history_bootstrapped = False
            _LOGGER.exception("ENGIE history import failed")
