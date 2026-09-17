"""Price sensors for the Energy dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CURRENCY_EURO
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, UNIT_EUR_KWH
from .coordinator import EngiePriceCoordinator
from .entity import build_contract_device_info


@dataclass(frozen=True, slots=True)
class SensorSpec:
    translation_key: str
    unique_suffix: str
    attr: str
    unit: str | None
    device_class: SensorDeviceClass | None
    display_precision: int
    cadran: str | None = None
    icon: str | None = None
    state_class: SensorStateClass | None = SensorStateClass.MEASUREMENT


def _contract_specs() -> list[SensorSpec]:
    return [
        SensorSpec(
            translation_key="price_kwh_ttc",
            unique_suffix="price_kwh_ttc",
            attr="price_kwh_ttc",
            unit=UNIT_EUR_KWH,
            device_class=None,
            display_precision=5,
            icon="mdi:currency-eur",
        ),
        SensorSpec(
            translation_key="price_kwh_ht",
            unique_suffix="price_kwh_ht",
            attr="price_kwh_ht",
            unit=UNIT_EUR_KWH,
            device_class=None,
            display_precision=5,
            icon="mdi:currency-eur",
        ),
        SensorSpec(
            translation_key="abonnement_ttc",
            unique_suffix="abonnement_ttc",
            attr="abonnement_ttc",
            unit=CURRENCY_EURO,
            device_class=SensorDeviceClass.MONETARY,
            display_precision=2,
            icon="mdi:cash",
            state_class=None,
        ),
    ]


def _cadran_specs(cadran: str) -> list[SensorSpec]:
    slug = cadran.lower()
    return [
        SensorSpec(
            translation_key="cadran_price_kwh_ttc",
            unique_suffix=f"{slug}_price_kwh_ttc",
            attr="price_kwh_ttc",
            unit=UNIT_EUR_KWH,
            device_class=None,
            display_precision=5,
            cadran=cadran,
            icon="mdi:chart-timeline-variant",
        ),
        SensorSpec(
            translation_key="cadran_price_kwh_ht",
            unique_suffix=f"{slug}_price_kwh_ht",
            attr="price_kwh_ht",
            unit=UNIT_EUR_KWH,
            device_class=None,
            display_precision=5,
            cadran=cadran,
            icon="mdi:chart-timeline-variant",
        ),
    ]


def _iter_specs(price: Any) -> list[SensorSpec]:
    specs = list(_contract_specs())
    seen: set[str] = set()
    for cadran in getattr(price, "cadrans", None) or []:
        name = str(getattr(cadran, "cadran", "") or "").strip()
        if not name or name.upper() in seen:
            continue
        seen.add(name.upper())
        specs.extend(_cadran_specs(name))
    return specs


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EngiePriceCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    known: set[str] = set()

    def _entities_for(prices: list[Any]) -> list[EngiePriceSensor]:
        created: list[EngiePriceSensor] = []
        for price in prices or []:
            contract_id = str(getattr(price, "contract_id", "") or "")
            if not contract_id:
                continue
            for spec in _iter_specs(price):
                unique_id = f"{entry.entry_id}_{contract_id}_{spec.unique_suffix}"
                if unique_id in known:
                    continue
                known.add(unique_id)
                created.append(EngiePriceSensor(coordinator, entry, contract_id, spec))
        return created

    async_add_entities(_entities_for(coordinator.data or []))

    @callback
    def _on_update() -> None:
        new_entities = _entities_for(coordinator.data or [])
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_on_update))


class EngiePriceSensor(CoordinatorEntity[EngiePriceCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        coordinator: EngiePriceCoordinator,
        entry: ConfigEntry,
        contract_id: str,
        spec: SensorSpec,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._contract_id = contract_id
        self._spec = spec
        self._attr_unique_id = f"{entry.entry_id}_{contract_id}_{spec.unique_suffix}"
        self._attr_translation_key = spec.translation_key
        self._attr_native_unit_of_measurement = spec.unit
        self._attr_device_class = spec.device_class
        self._attr_state_class = spec.state_class
        self._attr_suggested_display_precision = spec.display_precision
        if spec.icon:
            self._attr_icon = spec.icon
        if spec.cadran:
            self._attr_translation_placeholders = {"cadran": spec.cadran}
        price = self._current_price()
        if price is not None:
            self._attr_device_info = build_contract_device_info(entry, price)

    @property
    def device_info(self):
        price = self._current_price()
        if price is not None:
            return build_contract_device_info(self._entry, price)
        return getattr(self, "_attr_device_info", None)

    @property
    def available(self) -> bool:
        return super().available and self._current_price() is not None

    @property
    def native_value(self) -> float | None:
        price = self._current_price()
        if price is None:
            return None
        if self._spec.cadran:
            cadran = self._current_cadran(price)
            if cadran is None:
                return None
            return getattr(cadran, self._spec.attr, None)
        return getattr(price, self._spec.attr, None)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        price = self._current_price()
        if price is None:
            return {}
        attrs: dict[str, Any] = {
            "energy": getattr(price, "energy", None),
            "contract_id": getattr(price, "contract_id", None),
            "type_comptage": getattr(price, "type_comptage", None),
            "puissance": getattr(price, "puissance", None),
            "as_of": getattr(price, "as_of", None),
            "source": getattr(price, "source", None),
            "notes": getattr(price, "notes", None),
        }
        if self._spec.cadran:
            cadran = self._current_cadran(price)
            attrs["cadran"] = self._spec.cadran
            if cadran is not None:
                attrs["as_of"] = getattr(cadran, "as_of", None) or attrs["as_of"]
                attrs["source"] = getattr(cadran, "source", None) or attrs["source"]
        return {key: value for key, value in attrs.items() if value not in (None, "")}

    def _current_price(self) -> Any | None:
        for item in self.coordinator.data or []:
            if str(getattr(item, "contract_id", "") or "") == self._contract_id:
                return item
        return None

    def _current_cadran(self, price: Any) -> Any | None:
        wanted = (self._spec.cadran or "").upper()
        for cadran in getattr(price, "cadrans", None) or []:
            if str(getattr(cadran, "cadran", "") or "").upper() == wanted:
                return cadran
        return None
