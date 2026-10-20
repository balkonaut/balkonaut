"""SQLite-Speicher: Rohwerte mit begrenzter Aufbewahrung und Stundenaggregate.

Stundenaggregat je Messgröße: mean (bei Leistung in W gleich der Energie der Stunde in Wh),
mean_pos/mean_neg (positiver/negativer Anteil, z. B. Netzbezug/Einspeisung),
last (letzter Wert, für Zähler und Ladestand), n (Anzahl Rohwerte).
Tageswerte entstehen in der Auswertung aus den Stundenwerten, damit Tagesgrenzen in Ortszeit liegen.
"""
import sqlite3

RAW_DAYS = 14  # ponytail: feste Aufbewahrung der Rohwerte, konfigurierbar machen, falls jemand mehr braucht

SCHEMA = """
CREATE TABLE IF NOT EXISTS raw (key TEXT, ts INTEGER, value REAL, PRIMARY KEY (key, ts)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS hourly (
    key TEXT, hour INTEGER, mean REAL, mean_pos REAL, mean_neg REAL, last REAL, n INTEGER,
    PRIMARY KEY (key, hour)) WITHOUT ROWID;
"""


class Storage:
    def __init__(self, path):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.executescript(SCHEMA)

    def add(self, ts, values):
        """values: {Messgröße: Wert}; None-Werte werden übersprungen."""
        with self.db:
            self.db.executemany("INSERT OR REPLACE INTO raw VALUES (?, ?, ?)",
                                [(k, ts, v) for k, v in values.items() if v is not None])

    def aggregate(self, now):
        """Alle abgeschlossenen Stunden aggregieren, die noch fehlen, und alte Rohwerte löschen."""
        end = now // 3600 * 3600
        (start,) = self.db.execute(
            "SELECT coalesce(max(hour) + 3600, (SELECT min(ts) FROM raw) / 3600 * 3600, ?) FROM hourly", (end,)
        ).fetchone()
        if start >= end:
            return
        with self.db:
            self.db.execute("""
                INSERT OR REPLACE INTO hourly
                SELECT key, ts / 3600 * 3600 AS hour, avg(value), avg(max(value, 0)), avg(min(value, 0)), NULL, count(*)
                FROM raw WHERE ts >= ? AND ts < ? GROUP BY key, hour""", (start, end))
            self.db.execute("""
                UPDATE hourly SET last = (SELECT value FROM raw WHERE raw.key = hourly.key
                    AND raw.ts >= hourly.hour AND raw.ts < hourly.hour + 3600 ORDER BY ts DESC LIMIT 1)
                WHERE hour >= ? AND hour < ?""", (start, end))
            self.db.execute("DELETE FROM raw WHERE ts < ?", (now - RAW_DAYS * 86400,))

    def hourly(self):
        return self.db.execute(
            "SELECT key, hour, mean, mean_pos, mean_neg, last FROM hourly ORDER BY key, hour").fetchall()
