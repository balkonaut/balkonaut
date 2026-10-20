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
