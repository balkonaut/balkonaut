"""SQLite-Speicher: Rohwerte mit begrenzter Aufbewahrung und Stundenaggregate.

Stundenaggregat je Messgröße: mean (bei Leistung in W gleich der Energie der Stunde in Wh),
mean_pos/mean_neg (positiver/negativer Anteil, z. B. Netzbezug/Einspeisung),
last (letzter Wert, für Zähler und Ladestand), n (Anzahl Rohwerte).
Tageswerte entstehen in der Auswertung aus den Stundenwerten, damit Tagesgrenzen in Ortszeit liegen.
"""
import bisect
import functools
import json
import sqlite3
import threading

RAW_DAYS = 14  # ponytail: feste Aufbewahrung der Rohwerte, konfigurierbar machen, falls jemand mehr braucht

SCHEMA = """
CREATE TABLE IF NOT EXISTS raw (key TEXT, ts INTEGER, value REAL, PRIMARY KEY (key, ts)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS hourly (
    key TEXT, hour INTEGER, mean REAL, mean_pos REAL, mean_neg REAL, last REAL, n INTEGER,
    PRIMARY KEY (key, hour)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS regulation_daily (day TEXT PRIMARY KEY, data TEXT);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value) WITHOUT ROWID;
-- erste eigene Messung; Rohwerte werden nach RAW_DAYS gelöscht, min(raw.ts) taugt dafür nicht auf Dauer
INSERT OR IGNORE INTO meta SELECT 'first_raw', min(ts) FROM raw HAVING min(ts) IS NOT NULL;
"""


def locked(method):
    """Zugriffe nacheinander: die App nutzt die Verbindung aus Event-Loop und Threads zugleich."""
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        with self.lock:
            return method(self, *args, **kwargs)
    return wrapper


class Storage:
    def __init__(self, path):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.RLock()
        self.db.executescript(SCHEMA)

    @locked
    def add(self, ts, values):
        """values: {Messgröße: Wert}; None-Werte werden übersprungen."""
        rows = [(k, ts, v) for k, v in values.items() if v is not None]
        with self.db:
            self.db.executemany("INSERT OR REPLACE INTO raw VALUES (?, ?, ?)", rows)
            if rows:
                self.db.execute("INSERT OR IGNORE INTO meta VALUES ('first_raw', ?)", (ts,))

    @locked
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

    @locked
    def hourly(self, now=None):
        """Stundenwerte (key, hour, mean, mean_pos, mean_neg, last); mit now inklusive der laufenden Stunde.
        Bei Leistungen sind deren Mittelwerte auf den verstrichenen Anteil skaliert, damit mean weiter Wh entspricht;
        Ladestand, Prognose und andere Größen bleiben Mittelwerte."""
        rows = self.db.execute("SELECT key, hour, mean, mean_pos, mean_neg, last FROM hourly").fetchall()
        if now is not None:
            hour = now // 3600 * 3600
            f = (now - hour) / 3600
            for key, h, mean, pos, neg, last in self.db.execute("""
                    SELECT key, ?, avg(value), avg(max(value, 0)), avg(min(value, 0)),
                           (SELECT value FROM raw r WHERE r.key = raw.key AND r.ts >= ? ORDER BY ts DESC LIMIT 1)
                    FROM raw WHERE ts >= ? GROUP BY key""", (hour, hour, hour)):
                k = f if key.endswith("_power") else 1
                rows.append((key, h, mean * k, pos * k, neg * k, last))
        return sorted(rows, key=lambda r: (r[0], r[1]))

    @locked
    def latest(self):
        """Letzter Rohwert je Messgröße: {key: (ts, value)}."""
        return {k: (ts, v) for k, ts, v in self.db.execute(
            "SELECT key, max(ts), value FROM raw GROUP BY key")}  # SQLite: value gehört zur Zeile mit max(ts)

    @locked
    def first(self):
        """Beginn der ersten gespeicherten Stunde, None bei leerer Datenbank."""
        (ts,) = self.db.execute(
            "SELECT min(t) FROM (SELECT min(ts) / 3600 * 3600 AS t FROM raw UNION SELECT min(hour) FROM hourly)").fetchone()
        return ts

    def backfill(self, series, start, until):
        """Verlauf {Messgröße: [(ts, wert)]} als Treppenfunktion abtasten und als Stundenwerte
        für [start, until) nachtragen. Vorhandene Stunden bleiben unverändert."""
        tmp = Storage(":memory:")
        times = {k: [t for t, _ in s] for k, s in series.items()}
        for t in range(int(start), int(until), 10):  # wie der Collector
            values = {}
            for k, s in series.items():
                i = bisect.bisect_right(times[k], t) - 1
                values[k] = s[i][1] if i >= 0 else None
            tmp.add(t, values)
        tmp.aggregate(until)
        rows = tmp.db.execute("SELECT * FROM hourly WHERE hour < ?", (until,)).fetchall()
        with self.db:
            self.db.executemany("INSERT OR IGNORE INTO hourly VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
        return len({r[1] for r in rows})

    @locked
    def series(self, since, keys, until=float("inf")):
        """Rohwerte in [since, until) als {ts: {Messgröße: Wert}}, zeitlich sortiert."""
        out = {}
        marks = ",".join("?" * len(keys))
        for ts, key, value in self.db.execute(
                f"SELECT ts, key, value FROM raw WHERE ts >= ? AND ts < ? AND key IN ({marks}) ORDER BY ts",
                (since, until, *keys)):
            out.setdefault(ts, {})[key] = value
        return out

    @locked
    def export(self):
        """Gesamte Historie zum Umzug: Stundenwerte als Zeilen und Tageswerte der Regelgüte."""
        return {"hourly": self.db.execute("SELECT * FROM hourly ORDER BY key, hour").fetchall(),
                "regulation": {day: json.loads(data) for day, data in self.db.execute("SELECT * FROM regulation_daily")}}

    @locked
    def merge(self, data):
        """Export einer anderen Balkonaut-Datenbank übernehmen. Stunden vor der ersten eigenen Rohmessung werden
        ersetzt (genauer als ein Import aus dem HA-Verlauf), spätere bleiben wie selbst gemessen. Gibt die Zahl der
        übernommenen Stunden zurück."""
        row = self.db.execute("SELECT value / 3600 * 3600 FROM meta WHERE key = 'first_raw'").fetchone()
        before = row[0] if row else float("inf")
        rows = [tuple(r) for r in data["hourly"]]
        with self.db:
            self.db.executemany("INSERT OR REPLACE INTO hourly VALUES (?, ?, ?, ?, ?, ?, ?)", [r for r in rows if r[1] < before])
            self.db.executemany("INSERT OR IGNORE INTO hourly VALUES (?, ?, ?, ?, ?, ?, ?)", [r for r in rows if r[1] >= before])
            self.db.executemany("INSERT OR IGNORE INTO regulation_daily VALUES (?, ?)",
                                [(day, json.dumps(v)) for day, v in data["regulation"].items()])
        return len({r[1] for r in rows if r[1] < before})

    @locked
    def regulation_days(self, first, last):
        """Gespeicherte Tageswerte der Regelgüte {JJJJ-MM-TT: dict} für first bis last (Text-Datum, einschließlich)."""
        return {day: json.loads(data) for day, data in self.db.execute(
            "SELECT day, data FROM regulation_daily WHERE day BETWEEN ? AND ?", (first, last))}

    @locked
    def save_regulation_day(self, day, data):
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO regulation_daily VALUES (?, ?)", (day, json.dumps(data)))
