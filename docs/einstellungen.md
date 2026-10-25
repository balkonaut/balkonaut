# Einstellungen

## Preise und Anlagenkosten

Unter `http://<adresse>:8000/einstellungen` trägst du ein:

- **Arbeitspreis Netzstrom** in €/kWh, also was eine Kilowattstunde aus dem Netz kostet (ohne Grundgebühr).
- **Einspeisevergütung** in €/kWh. Bei den meisten Balkonkraftwerken 0.
- **Anschaffungskosten** der Anlage in €, inklusive Speicher.
- **Inbetriebnahme** (optional): Datum, ab dem der Abgabezähler am Einspeisepunkt zählt, meist die Inbetriebnahme. Verbessert die Amortisationsrechnung.

Kommazahlen gehen mit Komma oder Punkt.

## Geräte direkt, ohne Home Assistant

Der Container kann die Geräte auch direkt im Heimnetz lesen, ganz ohne Home Assistant und ohne Anmeldung.

**Im Browser:** *Einstellungen → Geräte*, die IP-Adresse eintragen und *Hinzufügen*. Balkonaut erkennt den Typ
selbst und zeigt danach die aktuellen Werte mit Richtung, z. B. „Netz 312 W (Bezug)“ oder „Abgabe 21 W (Bezug,
Vorzeichen prüfen)“. Passt eine Richtung nicht, *Vorzeichen drehen*. Unter *Standort und Flächen* die Adresse suchen
(über OpenStreetMap, dabei geht die Adresse an diesen Dienst) oder, wenn die Seite über HTTPS geöffnet ist, *Meinen
Standort verwenden*; Breiten- und Längengrad lassen sich auch von Hand eintragen. Dazu die Flächen eintragen. Änderungen gelten sofort, ohne Neustart; die Messdaten bleiben erhalten.
Im Home-Assistant-Add-on fehlt der Abschnitt *Geräte*, dort kommen die Werte aus Home Assistant; *Standort und Flächen*
gibt es auch dort (siehe unten).

**Oder in `data/config.yaml`:** statt `home_assistant` den Abschnitt `devices` eintragen, je Gerät `type` und
`host` (IP-Adresse):

```yaml
devices:
  - type: apsystems_ezhi
    host: 192.168.1.20
  - type: shelly_em
    host: 192.168.1.21
  - type: shelly_plug
    host: 192.168.1.22
```

| `type` | Gerät | Messgrößen |
|---|---|---|
| `apsystems_ezhi` | APsystems EZHI (in der APsystems-App den lokalen Modus aktivieren) | PV, Off-Grid-Port, Akku mit Zählern, Gesundheit, Abgabe ins Haus |
| `shelly_em` | Shelly Pro 3EM und andere Shelly mit drei Phasen | Netzleistung über alle Phasen saldiert |
| `shelly_em1` | Shelly Pro EM, EM Gen3 (nicht geprüft) | Netzleistung am ersten Kanal |
| `opendtu` | Hoymiles über OpenDTU (nicht geprüft) | Erzeugung und Abgabe aller Wechselrichter, mit Zähler |
| `ahoydtu` | Hoymiles über AhoyDTU (nicht geprüft) | Erzeugung und Abgabe aller Wechselrichter, ohne Zähler |
| `shelly_plug` | Shelly Plug Gen2 oder Gen3 am Einspeisepunkt | Abgabe ins Haus mit Zähler |

Welche IP-Adresse bei Hoymiles einzutragen ist und was die Docker-App nicht direkt liest, steht unter
[Unterstützte Geräte](geraete.md#docker-app-gerate-direkt-im-heimnetz). Hat das System einen Speicher, gilt dessen
Abgabe-Leistung, vom Plug zählt nur der Zähler (siehe
[Messquellen](messquellen.md)). Meldet ein Gerät eine Richtung umgekehrt, die Messgröße unter `invert` eintragen,
z. B. `invert: [output_power]`. Ladegrenzen, Entladeschutz und Abgabelimit des EZHI gibt es nur über die
APsystems-Cloud; ohne sie rechnet Balkonaut mit Standardwerten. Der Import des Verlaufs (`app.backfill`) geht nur
über Home Assistant.

Für Prognose (Ertragswächter) und Jahresverlauf ohne Home Assistant Standort und Flächen eintragen (im Browser
unter *Standort und Flächen* oder in der Datei):

```yaml
location: {lat: 50.0, lon: 10.0}
planes:
  - {declination: 30, azimuth: 150, kwp: 0.87, inverter: storage}
  - {declination: 30, azimuth: 250, kwp: 0.87, inverter: extra}
```

- `declination`: Neigung der Module in Grad (0 = waagerecht, 90 = senkrecht, am Balkongeländer meist 60 bis 90)
- `azimuth`: Ausrichtung in Grad, 0 = Nord, 90 = Ost, 180 = Süd, 270 = West (wie bei Forecast.Solar in Home Assistant)
- `kwp`: Modulleistung der Fläche in kWp
- `inverter`: `storage` für Flächen am Speicher, `extra` für Flächen an einem zusätzlichen Wechselrichter

Die Tagesprognose kommt von Forecast.Solar, höchstens einmal je Stunde abgerufen. Den erwarteten Jahresverlauf
(langjähriges Mittel, keine Prognose) holt Balkonaut einmal bei PVGIS, wenn sich Standort oder Flächen ändern; er
dient nur der Hochrechnung der Amortisation, solange das Datum der Inbetriebnahme fehlt.

Auch mit Home Assistant (Abschnitt `home_assistant`, ebenso im Add-on) braucht es dafür keine Forecast.Solar-Integration:
Sind Flächen eingetragen, ruft Balkonaut die Prognose selbst ab. Fehlt `location`, gilt der Standort aus Home
Assistant. Ist eine Prognose-Entität (`pv_forecast_today`, `pv_ac_forecast_today`) zugeordnet, geht sie vor.

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
| `battery_discharge_protection` | eingestellter Entladeschutz in % (optional), erscheint als Marke im Akku-Ring | |
| `output_power_limit` | eingestelltes Abgabelimit des Speichers in W (optional, sonst 800 W) | |
| `pv_forecast_today`, `pv_ac_forecast_today` | Prognose „Erzeugung heute“ in kWh für die Fläche am Speicher bzw. am zweiten Wechselrichter, z. B. aus Forecast.Solar (optional) | |

Welche Quelle für welche Größe am besten geeignet ist, steht unter [Messquellen](messquellen.md).
Nach einer Änderung an `config.yaml` den Container neu starten.
