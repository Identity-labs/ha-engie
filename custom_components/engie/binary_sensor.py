"""Binary sensors for ENGIE Particuliers."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
from .coordinator import EngieCoordinator
from .entity import build_account_device_info
from .sensor import _snapshot


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EngieCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities: list[BinarySensorEntity] = [EngieAuthSensor(coordinator, entry)]
    snapshot = _snapshot(coordinator)
    seen: set[str] = set()
    for billing in (snapshot.billing if snapshot else []) or []:
        if billing.account_id in seen:
            continue
        seen.add(billing.account_id)
        entities.append(EngieEnergyCutSensor(coordinator, entry, billing.account_id))
    async_add_entities(entities)


class EngieAuthSensor(CoordinatorEntity[EngieCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    _attr_translation_key = "authentication"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: EngieCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_authentication"
        self._attr_device_info = build_account_device_info(entry)

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.last_update_success and self.coordinator.api.authenticated)


class EngieEnergyCutSensor(CoordinatorEntity[EngieCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    _attr_translation_key = "energy_cut"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(
        self, coordinator: EngieCoordinator, entry: ConfigEntry, account_id: str
    ) -> None:
        super().__init__(coordinator)
        self._account_id = account_id
        self._attr_unique_id = f"{entry.entry_id}_{account_id}_energy_cut"
        self._attr_device_info = build_account_device_info(entry)

    def _billing(self):
        snapshot = _snapshot(self.coordinator)
        if snapshot is None:
            return None
        for item in snapshot.billing:
            if item.account_id == self._account_id:
                return item
        return None

    @property
    def is_on(self) -> bool | None:
        billing = self._billing()
        if billing is None:
            return None
        return bool(billing.balance.energie_coupee)
