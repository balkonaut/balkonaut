"""Erwarteter PV-Ertrag je Monat aus PVGIS (Gemeinsame Forschungsstelle der EU, frei, ohne Schlüssel)."""
import json
import urllib.parse
import urllib.request

URL = "https://re.jrc.ec.europa.eu/api/v5_3/PVcalc"


def monthly(lat, lon, planes, loss=14):
    """planes: [(neigung, azimut, kwp)] mit Azimut wie in Home Assistant (0 = Nord, 180 = Süd).
    Ergebnis: erwarteter Ertrag aller Flächen in kWh für Januar bis Dezember."""
    total = [0.0] * 12
    for tilt, azimuth, kwp in planes:
        query = urllib.parse.urlencode({"lat": lat, "lon": lon, "peakpower": kwp, "loss": loss, "angle": tilt,
                                        "aspect": azimuth - 180, "outputformat": "json"})  # PVGIS: 0 = Süd
        with urllib.request.urlopen(f"{URL}?{query}", timeout=60) as r:
            for m in json.load(r)["outputs"]["monthly"]["fixed"]:
                total[m["month"] - 1] += m["E_m"]
    return total
