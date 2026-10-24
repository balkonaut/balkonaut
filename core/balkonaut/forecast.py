"""Tagesprognose je Fläche von Forecast.Solar (frei, ohne Schlüssel, 12 Abrufe je Stunde und IP-Adresse)."""
import json
import logging
import time
import urllib.request

URL = "https://api.forecast.solar/estimate/watthours/day"
KEYS = {"storage": "pv_forecast_today", "extra": "pv_ac_forecast_today"}  # Messgröße je Wechselrichter der Fläche

log = logging.getLogger(__name__)


def today(lat, lon, tilt, azimuth, kwp):
    """Erwartete Erzeugung heute in kWh, Azimut wie in Home Assistant (0 = Nord, 180 = Süd)."""
    with urllib.request.urlopen(f"{URL}/{lat}/{lon}/{tilt}/{azimuth - 180}/{kwp}", timeout=30) as r:
        days = json.load(r)["result"]  # {"2026-10-23": Wh, "2026-10-24": Wh}, Datum in Ortszeit des Standorts
    return days[min(days)] / 1000


class Planes:
    """Eingetragene Flächen: Tagesprognose je Wechselrichter und Daten für den Jahresverlauf (PVGIS).

    location: {"lat": ..., "lon": ...} oder None,
    planes: [{"declination": ..., "azimuth": ..., "kwp": ..., "inverter": "storage" | "extra"}]
    """

    def __init__(self, location=None, planes=()):
        self.location, self.planes = location, planes
        self.values, self.at = {}, 0.0

    def read(self):
        """{pv_forecast_today: kWh, ...}, höchstens einmal je Stunde abgerufen; bei Fehlern die letzte Prognose."""
        if self.planes and self.location and time.time() - self.at >= 3600:
            self.at = time.time()
            try:
                sums = {}
                for p in self.planes:
                    key = KEYS[p.get("inverter", "storage")]
                    sums[key] = sums.get(key, 0.0) + today(
                        self.location["lat"], self.location["lon"], p["declination"], p["azimuth"], p["kwp"])
                self.values = sums
            except (OSError, ValueError, KeyError) as e:
                log.warning("Prognose nicht abrufbar: %s", e)
        return self.values

    def solar_planes(self):
        """(lat, lon, [(neigung, azimut, kwp)]) für PVGIS; ohne Standort oder Flächen (0.0, 0.0, [])."""
        if not (self.location and self.planes):
            return 0.0, 0.0, []
        return (self.location["lat"], self.location["lon"],
                [(p["declination"], p["azimuth"], p["kwp"]) for p in self.planes])
