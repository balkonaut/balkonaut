import asyncio

import pytest

from balkonaut.collector import run
from balkonaut.storage import Storage


class FlakyAdapter:
    calls = 0

    def read(self):
        self.calls += 1
        if self.calls == 2:
            raise RuntimeError("HA weg")
        return {"grid_power": self.calls}


def test_run_survives_errors():
    adapter, storage = FlakyAdapter(), Storage(":memory:")
    with pytest.raises(TimeoutError):
        asyncio.run(asyncio.wait_for(run(adapter, storage, interval=0.01), 0.1))
    assert adapter.calls > 2
    assert storage.db.execute("SELECT count(*) FROM raw").fetchone()[0] >= 1


def test_manual_values_only_when_missing():
    """Von Hand eingetragene Werte füllen nur Lücken, ein gemeldeter Wert geht vor."""
    class Adapter:
        def read(self):
            return {"battery_soc_min": 15.0, "battery_soc_max": None}
    storage = Storage(":memory:")
    manual = {"battery_soc_min": 10.0, "battery_soc_max": 95.0, "output_power_limit": 600.0}
    with pytest.raises(TimeoutError):
        asyncio.run(asyncio.wait_for(run(Adapter(), storage, interval=0.01, manual=manual), 0.05))
    assert {k: v for k, (_, v) in storage.latest().items()} == {
        "battery_soc_min": 15.0, "battery_soc_max": 95.0, "output_power_limit": 600.0}
