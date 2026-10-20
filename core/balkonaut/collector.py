"""Collector: fragt den Adapter periodisch ab, speichert die Werte und aggregiert abgeschlossene Stunden."""
import asyncio
import logging
import time

log = logging.getLogger(__name__)


async def run(adapter, storage, interval=10):
    while True:
        now = int(time.time())
        try:
            storage.add(now, await asyncio.to_thread(adapter.read))
            storage.aggregate(now)
        except Exception:
            log.exception("Messung fehlgeschlagen")
        await asyncio.sleep(interval - time.time() % interval)
