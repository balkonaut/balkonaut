"""Ereignis je neu aufgetretener Warnung, für Automationen ohne Template."""
from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BalkonautConfigEntry, BalkonautCoordinator, device_info


def _key(warning: dict) -> tuple:
    return warning["code"], warning.get("wechselrichter")


async def async_setup_entry(
    hass: HomeAssistant, entry: BalkonautConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([BalkonautWarningEvent(entry.runtime_data, entry)])


class BalkonautWarningEvent(CoordinatorEntity[BalkonautCoordinator], EventEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "warnung"
    _attr_event_types = ["warnung"]

    def __init__(self, coordinator: BalkonautCoordinator, entry: BalkonautConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_warnung"
        self._attr_device_info = device_info(entry)
        self._known = {_key(w) for w in coordinator.data["warnungen"]}  # beim Start bestehende nicht erneut melden

    @callback
    def _handle_coordinator_update(self) -> None:
        current = {_key(w): w for w in self.coordinator.data["warnungen"]}
        for key in current.keys() - self._known:
            self._trigger_event("warnung", current[key])
        self._known = set(current)
        self.async_write_ha_state()
