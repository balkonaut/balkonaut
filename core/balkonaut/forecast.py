"""Prognose je Fläche von Forecast.Solar (frei, ohne Schlüssel, 12 Abrufe je Stunde und IP-Adresse): Tageswert und
Stundenwerte aus einem Abruf, zur vollen und halben Stunde."""
from datetime import datetime, timedelta
import json
import logging
import time
import urllib.request

from .analytics import TZ

URL = "https://api.forecast.solar/estimate"
SLOT = 1800  # Abruf zur vollen und halben Stunde: bei zwei Flächen 4 der 12 Abrufe je Stunde und IP-Adresse
KEYS = {"storage": "pv_forecast_today", "extra": "pv_ac_forecast_today"}  # Messgröße je Wechselrichter der Fläche

log = logging.getLogger(__name__)


def estimate(lat, lon, tilt, azimuth, kwp):
    """Erwartete Erzeugung heute: (kWh, {Stundenbeginn als Unix-Zeit: kWh}), Azimut wie in Home Assistant
    (0 = Nord, 180 = Süd)."""
    with urllib.request.urlopen(f"{URL}/{lat}/{lon}/{tilt}/{azimuth - 180}/{kwp}", timeout=30) as r:
        result = json.load(r)["result"]
    days = result["watt_hours_day"]  # {"2026-10-23": Wh, "2026-10-24": Wh}, Datum in Ortszeit des Standorts
    first = min(days)
    periods = {datetime.fromisoformat(k).replace(tzinfo=TZ): wh for k, wh in result.get("watt_hours_period", {}).items()}
    return days[first] / 1000, per_hour(periods, datetime.fromisoformat(first).date())


def per_hour(periods, day):
    """Wh je Zeitraum von Forecast.Solar ({Ende als datetime mit Zeitzone: Wh}) als {Stundenbeginn: kWh} für day.
    Ein Wert gilt bis zur Uhrzeit des Schlüssels: 08:00 gehört zur Stunde ab 07:00, 16:46 (Sonnenuntergang) zu 16:00."""
    hours = {}
    for end, wh in periods.items():
        start = (end.astimezone(TZ) - timedelta(seconds=1)).replace(minute=0, second=0, microsecond=0)
        if start.date() == day:
            hours[start.timestamp()] = hours.get(start.timestamp(), 0.0) + wh / 1000
    return hours


class Planes:
    """Eingetragene Flächen: Tagesprognose je Wechselrichter und Daten für den Jahresverlauf (PVGIS).

    location: {"lat": ..., "lon": ...} oder None,
    planes: [{"declination": ..., "azimuth": ..., "kwp": ..., "inverter": "storage" | "extra"}]
    """

    def __init__(self, location=None, planes=()):
        self.location, self.planes = location, planes
        self.values, self.hours, self.day, self.next = {}, {}, None, 0.0  # Tageswerte, Stundenwerte, ihr Tag, nächster Abruf

    def due(self):
        """Neuer Abruf fällig: zur vollen und halben Stunde, auch nach Fehlern erst dann wieder."""
        return bool(self.planes) and time.time() >= self.next

    def read(self):
        """{pv_forecast_today: kWh, ...}; bei Fehlern die letzte Prognose desselben Tages."""
        now = datetime.now(TZ)
        if self.location and self.due():
            self.next = now.timestamp() // SLOT * SLOT + SLOT  # Ortszeit weicht um ganze Stunden ab: :00 und :30
            try:
                sums, hours = {}, {}
                for p in self.planes:
                    key = KEYS[p.get("inverter", "storage")]
                    day, per_hour = estimate(
                        self.location["lat"], self.location["lon"], p["declination"], p["azimuth"], p["kwp"])
                    sums[key] = sums.get(key, 0.0) + day
                    for t, kwh in per_hour.items():
                        hours[t] = hours.get(t, 0.0) + kwh
                self.values, self.hours, self.day = sums, hours, now.date()
            except Exception as e:  # Netz, HTTP-Fehler, Abrufgrenze, unerwartete Antwort: Messung läuft weiter
                log.warning("Prognose nicht abrufbar: %s", e)
        return self.current()

    def current(self):
        """Letzte Prognose ohne Abruf; keine von gestern als heutige."""
        return self.values if self.day == datetime.now(TZ).date() else {}

    def current_hours(self):
        """Erwartete Erzeugung je Stunde heute, alle Flächen zusammen: {Stundenbeginn als Unix-Zeit: kWh}."""
        return self.hours if self.day == datetime.now(TZ).date() else {}

    def solar_planes(self):
        """(lat, lon, [(neigung, azimut, kwp)]) für PVGIS; ohne Standort oder Flächen (0.0, 0.0, [])."""
        if not (self.location and self.planes):
            return 0.0, 0.0, []
        return (self.location["lat"], self.location["lon"],
                [(p["declination"], p["azimuth"], p["kwp"]) for p in self.planes])
