"""Diagnose-Download: Konfiguration und letzter Status."""
from typing import Any

from homeassistant.core import HomeAssistant

from . import BalkonautConfigEntry


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: BalkonautConfigEntry) -> dict[str, Any]:
    coordinator = entry.runtime_data
    return {
        "entry": {"data": dict(entry.data), "options": dict(entry.options)},
        "last_update_success": coordinator.last_update_success,
        "status": coordinator.data,
    }
