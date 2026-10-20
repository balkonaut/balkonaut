"""Diagnose-Download: Konfiguration ohne Adresse und letzte Antwort der App."""
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant

from . import BalkonautConfigEntry


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: BalkonautConfigEntry) -> dict[str, Any]:
    coordinator = entry.runtime_data
    return {
        "entry": async_redact_data({"data": dict(entry.data), "options": dict(entry.options)}, {CONF_URL}),
        "last_update_success": coordinator.last_update_success,
        "failures": coordinator.failures,
        "status": coordinator.data,
    }
