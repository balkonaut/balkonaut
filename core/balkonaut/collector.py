"""Collector: fragt den Adapter periodisch ab, speichert die Werte und aggregiert abgeschlossene Stunden."""
import asyncio
import logging
import time

log = logging.getLogger(__name__)


async def run(adapter, storage, interval=10, manual=None):
    """manual: von Hand eingetragene Werte (z. B. Ladegrenzen), gelten nur, solange das Gerät keinen Wert meldet."""
    while True:
        now = int(time.time())
        try:
            values = await asyncio.to_thread(adapter.read)
            for key, value in (manual or {}).items():
                if values.get(key) is None:
                    values[key] = value
            storage.add(now, values)
            storage.aggregate(now)
        except Exception:
            log.exception("Messung fehlgeschlagen")
        await asyncio.sleep(interval - time.time() % interval)
