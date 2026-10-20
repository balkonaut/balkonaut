"""Sensoren aus /api/v1/status der Balkonaut-App."""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BalkonautConfigEntry, BalkonautCoordinator, device_info


@dataclass(frozen=True, kw_only=True)
class BalkonautSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict], StateType | date]


def _pct(value):
    return None if value is None else value * 100


def _period(period: str) -> list[BalkonautSensorDescription]:
    def bilanz(key):
        return lambda d: d["bilanz"][period][key]

    energy = {"native_unit_of_measurement": UnitOfEnergy.KILO_WATT_HOUR, "device_class": SensorDeviceClass.ENERGY,
              "suggested_display_precision": 1}
    return [
        BalkonautSensorDescription(key=f"ersparnis_{period}", translation_key=f"ersparnis_{period}",
                                   native_unit_of_measurement="EUR", device_class=SensorDeviceClass.MONETARY,
                                   suggested_display_precision=2, value_fn=bilanz("ersparnis")),
        BalkonautSensorDescription(key=f"erzeugung_{period}", translation_key=f"erzeugung_{period}",
                                   value_fn=bilanz("erzeugung"), **energy),
        BalkonautSensorDescription(key=f"eigenverbrauch_{period}", translation_key=f"eigenverbrauch_{period}",
                                   value_fn=bilanz("eigenverbrauch"), **energy),
        BalkonautSensorDescription(key=f"netzbezug_{period}", translation_key=f"netzbezug_{period}",
                                   value_fn=bilanz("netzbezug"), **energy),
        BalkonautSensorDescription(key=f"autarkie_{period}", translation_key=f"autarkie_{period}",
                                   native_unit_of_measurement=PERCENTAGE, suggested_display_precision=0,
                                   value_fn=lambda d: _pct(d["bilanz"][period]["autarkiegrad"])),
    ]


SENSORS = [
    *_period("tag"), *_period("monat"), *_period("jahr"),
    BalkonautSensorDescription(key="bisher_gespart", translation_key="bisher_gespart", native_unit_of_measurement="EUR",
                               device_class=SensorDeviceClass.MONETARY, suggested_display_precision=0,
                               value_fn=lambda d: d["amortisation"]["bisher_gespart"]),
    BalkonautSensorDescription(key="rest", translation_key="rest", native_unit_of_measurement="EUR",
                               device_class=SensorDeviceClass.MONETARY, suggested_display_precision=0,
                               value_fn=lambda d: d["amortisation"]["rest"]),
    BalkonautSensorDescription(key="ersparnis_pro_jahr", translation_key="ersparnis_pro_jahr",
                               native_unit_of_measurement="EUR", device_class=SensorDeviceClass.MONETARY,
                               suggested_display_precision=0, value_fn=lambda d: d["amortisation"]["ersparnis_pro_jahr"]),
    BalkonautSensorDescription(key="amortisiert_am", translation_key="amortisiert_am", device_class=SensorDeviceClass.DATE,
                               value_fn=lambda d: date.fromisoformat(v) if (v := d["amortisation"]["amortisiert_am"]) else None),
    BalkonautSensorDescription(key="vollzyklen", translation_key="vollzyklen", state_class=SensorStateClass.TOTAL_INCREASING,
                               suggested_display_precision=0, value_fn=lambda d: d["akku"]["gesamt"]["zyklen_gesamt"]),
    BalkonautSensorDescription(key="akku_gesundheit", translation_key="akku_gesundheit", native_unit_of_measurement=PERCENTAGE,
                               suggested_display_precision=0, value_fn=lambda d: d["akku"]["gesamt"]["gesundheit"]),
    BalkonautSensorDescription(key="akku_wirkungsgrad", translation_key="akku_wirkungsgrad",
                               native_unit_of_measurement=PERCENTAGE, suggested_display_precision=0,
                               value_fn=lambda d: _pct(d["akku"]["monat"]["wirkungsgrad"])),
]


async def async_setup_entry(
    hass: HomeAssistant, entry: BalkonautConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities(BalkonautSensor(entry.runtime_data, entry, d) for d in SENSORS)


class BalkonautSensor(CoordinatorEntity[BalkonautCoordinator], SensorEntity):
    _attr_has_entity_name = True
    entity_description: BalkonautSensorDescription

    def __init__(self, coordinator: BalkonautCoordinator, entry: BalkonautConfigEntry,
                 description: BalkonautSensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = device_info(entry)

    @property
    def native_value(self) -> StateType | date:
        return self.entity_description.value_fn(self.coordinator.data)
