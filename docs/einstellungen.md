# Einstellungen

## Preise und Anlagenkosten

Unter `http://<adresse>:8000/einstellungen` trägst du ein:

- **Arbeitspreis Netzstrom** in €/kWh, also was eine Kilowattstunde aus dem Netz kostet (ohne Grundgebühr).
- **Einspeisevergütung** in €/kWh. Bei den meisten Balkonkraftwerken 0.
- **Anschaffungskosten** der Anlage in €, inklusive Speicher.
- **Inbetriebnahme** (optional): Datum, ab dem der Abgabezähler am Einspeisepunkt zählt, meist die Inbetriebnahme. Verbessert die Amortisationsrechnung.

Kommazahlen gehen mit Komma oder Punkt.

## Verbindung zu Home Assistant

Die Verbindung steht in `data/config.yaml` im Abschnitt `home_assistant`:

- `url`: Adresse von Home Assistant, z. B. `http://192.168.1.10:8123`
- `token`: ein langlebiges Zugriffstoken. Erstellen in Home Assistant unter
  *Profil → Sicherheit → Langlebige Zugriffstoken*.
- `entities`: welche Home-Assistant-Entität welche Messgröße liefert, jeweils mit einem Faktor.
  Ein Faktor von `-1` dreht das Vorzeichen um, wenn ein Gerät eine Richtung anders herum meldet.

| Messgröße | Bedeutung | Vorzeichen |
|---|---|---|
| `grid_power` | Leistung am Netzanschluss, über alle Phasen | + Bezug, − Einspeisung |
| `pv_power` | PV-Leistung am Speicher-Wechselrichter | |
| `pv_ac_power` | weitere Erzeugung, z. B. ein Mikrowechselrichter am Speicher | |
| `battery_power` | Akkuleistung | + Laden, − Entladen |
| `battery_soc` | Ladestand in % | |
| `output_power` | Abgabe des Balkonkraftwerks ins Hausnetz | + Abgabe |
| `output_energy` | Zähler der Abgabe ins Hausnetz | |
| `pv_energy` | Zähler der PV-Erzeugung | |
| `battery_charge_energy`, `battery_discharge_energy` | Zähler Akku laden und entladen | |
| `battery_capacity` | nutzbare Akkukapazität in kWh (optional) | |
| `battery_soh` | Akku-Gesundheit in % (optional) | |
| `battery_soc_min`, `battery_soc_max` | eingestellte Lade-Untergrenze und -Obergrenze in % (optional) | |
| `output_power_limit` | eingestelltes Abgabelimit des Speichers in W (optional, sonst 800 W) | |
| `pv_forecast_today`, `pv_ac_forecast_today` | Prognose „Erzeugung heute“ in kWh für die Fläche am Speicher bzw. am zweiten Wechselrichter, z. B. aus Forecast.Solar (optional) | |

Welche Quelle für welche Größe am besten geeignet ist, steht unter [Messquellen](messquellen.md).
Nach einer Änderung an `config.yaml` den Container neu starten.
