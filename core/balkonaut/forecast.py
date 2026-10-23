"""Tagesprognose je Fläche von Forecast.Solar (frei, ohne Schlüssel, 12 Abrufe je Stunde und IP-Adresse)."""
import json
import urllib.request

URL = "https://api.forecast.solar/estimate/watthours/day"


def today(lat, lon, tilt, azimuth, kwp):
    """Erwartete Erzeugung heute in kWh, Azimut wie in Home Assistant (0 = Nord, 180 = Süd)."""
    with urllib.request.urlopen(f"{URL}/{lat}/{lon}/{tilt}/{azimuth - 180}/{kwp}", timeout=30) as r:
        days = json.load(r)["result"]  # {"2026-10-23": Wh, "2026-10-24": Wh}, Datum in Ortszeit des Standorts
    return days[min(days)] / 1000
