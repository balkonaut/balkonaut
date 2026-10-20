"""Problem-Sensor: an, solange Balkonaut Warnungen meldet."""
from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BalkonautConfigEntry, BalkonautCoordinator, device_info


async def async_setup_entry(
    hass: HomeAssistant, entry: BalkonautConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([BalkonautProblem(entry.runtime_data, entry)])


class BalkonautProblem(CoordinatorEntity[BalkonautCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "warnungen"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: BalkonautCoordinator, entry: BalkonautConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_warnungen"
        self._attr_device_info = device_info(entry)

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data["warnungen"])

    @property
    def extra_state_attributes(self) -> dict:
        return {"warnungen": [w["text"] for w in self.coordinator.data["warnungen"]]}
