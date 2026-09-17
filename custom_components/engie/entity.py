"""Device registry helpers."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, ENERGY_LABELS, MANUFACTURER


def contract_device_id(contract_id: str) -> str:
    return f"contract_{contract_id}"


def account_device_id(entry: ConfigEntry) -> str:
    return f"account_{entry.entry_id}"


def build_account_device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, account_device_id(entry))},
        name="ENGIE Particuliers",
        manufacturer=MANUFACTURER,
        model="Account",
        configuration_url="https://particuliers.engie.fr",
    )


def build_contract_device_info(entry: ConfigEntry, price: Any) -> DeviceInfo:
    energy = str(getattr(price, "energy", "") or "")
    libelle = str(getattr(price, "libelle", "") or "").strip()
    contract_id = str(getattr(price, "contract_id", "") or "")
    model = ENERGY_LABELS.get(energy, energy or "Contract")
    name = libelle or model
    return DeviceInfo(
        identifiers={(DOMAIN, contract_device_id(contract_id or entry.entry_id))},
        name=name,
        manufacturer=MANUFACTURER,
        model=model,
        serial_number=contract_id or None,
        configuration_url="https://particuliers.engie.fr",
    )
