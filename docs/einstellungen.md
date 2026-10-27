# Einstellungen der Docker-App

Diese Seite gilt für die [Docker-App](docker.md). Die Integration stellt man unter *Konfigurieren* ein, siehe
[Home-Assistant-Integration](integration.md#einstellungen-diagnose-storungen).

## Preise und Anlagenkosten

Unter `http://<adresse>:8000/einstellungen` trägst du ein:

- **Arbeitspreis Netzstrom** in €/kWh, also was eine Kilowattstunde aus dem Netz kostet (ohne Grundgebühr).
- **Einspeisevergütung** in €/kWh. Bei den meisten Balkonkraftwerken 0.
- **Anschaffungskosten** der Anlage in €, inklusive Speicher.
- **Inbetriebnahme** (optional): Datum, ab dem der Abgabezähler am Einspeisepunkt zählt, meist die Inbetriebnahme. Verbessert die Amortisationsrechnung.

## Akku

Unter *Einstellungen → Akku*, alles optional:

- **Bezeichnung des Akkus**: erscheint im Energiefluss statt „Akku“, z. B. der Hersteller.
- **Untergrenze** und **Obergrenze** in %: die in der App des Herstellers eingestellten Ladegrenzen. Sie bestimmen
  Farbe und Marken des Akku-Rings, die Restzeit und die Akku-Auswertung.
- **Entladeschutz** in %: erscheint als Marke im Akku-Ring.
- **Abgabelimit** in W: eingestelltes Limit des Speichers, für die Regelgüte der Nulleinspeisung (ohne Angabe 800 W).

Die Grenzwerte braucht es nur, wenn das Gerät sie nicht meldet, etwa der direkt abgefragte APsystems EZHI. Meldet das
Gerät einen Wert, gilt der gemessene. Ein leeres Feld entfernt den eingetragenen Wert. Ändert man die Grenzen in der
App des Herstellers, hier ebenfalls anpassen. In `data/config.yaml` stehen sie im Abschnitt `battery`, z. B.
`battery: {battery_soc_min: 10, battery_soc_max: 100, battery_discharge_protection: 20, output_power_limit: 800}`.

Kommazahlen gehen mit Komma oder Punkt.

## Geräte direkt, ohne Home Assistant

Die Docker-App liest die Geräte direkt im Heimnetz, ohne Home Assistant und ohne Anmeldung. Geräte, die sie nicht
direkt liest, kommen über die [Verbindung zu Home Assistant](#verbindung-zu-home-assistant).

**Im Browser:** *Einstellungen → Geräte*, die IP-Adresse eintragen und *Hinzufügen*. Balkonaut erkennt den Typ
selbst und zeigt danach die aktuellen Werte mit Richtung, z. B. „Netz 312 W (Bezug)“ oder „Abgabe 21 W (Bezug,
Vorzeichen prüfen)“. Passt eine Richtung nicht, *Vorzeichen drehen*. Unter *Standort und Flächen* die Adresse suchen
(über OpenStreetMap, dabei geht die Adresse an diesen Dienst) oder, wenn die Seite über HTTPS geöffnet ist, *Meinen
Standort verwenden*; Breiten- und Längengrad lassen sich auch von Hand eintragen. Dazu die Flächen eintragen. Änderungen gelten sofort, ohne Neustart; die Messdaten bleiben erhalten.

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
| `apsystems_ezhi` | APsystems EZHI (in der APsystems-App den lokalen Modus aktivieren) | PV, Off-Grid-Port, Akku mit Zählern, Gesundheit und Kapazität, Abgabe ins Haus |
| `shelly_em` | Shelly Pro 3EM und andere Shelly mit drei Phasen | Netzleistung über alle Phasen saldiert |
| `shelly_em1` | Shelly Pro EM, EM Gen3 (nicht geprüft) | Netzleistung am ersten Kanal |
| `opendtu` | Hoymiles über OpenDTU (nicht geprüft) | Erzeugung und Abgabe aller Wechselrichter, mit Zähler |
| `ahoydtu` | Hoymiles über AhoyDTU (nicht geprüft) | Erzeugung und Abgabe aller Wechselrichter, ohne Zähler |
| `shelly_plug` | Shelly Plug Gen2 oder Gen3 am Einspeisepunkt | Abgabe ins Haus mit Zähler |
| `victron_mqtt` | Victron GX über MQTT (nicht geprüft) | PV (DC und AC-gekoppelt), Akku mit Ladestand, Netz über alle Phasen, Abgabe ins Haus, ohne Zähler |
| `victron_modbus` | Victron GX über Modbus TCP, Unit-ID 100 (nicht geprüft) | wie `victron_mqtt` |

Welche IP-Adresse bei Hoymiles einzutragen ist und was die Docker-App nicht direkt liest, steht unter
[Unterstützte Geräte](geraete.md#gerate-direkt-im-heimnetz). Hat das System einen Speicher, gilt dessen
Abgabe-Leistung, vom Plug zählt nur der Zähler (siehe
[Messquellen](messquellen.md)). Meldet ein Gerät eine Richtung umgekehrt, die Messgröße unter `invert` eintragen,
z. B. `invert: [output_power]`. Ladegrenzen, Entladeschutz und Abgabelimit des EZHI gibt es nur über die
APsystems-Cloud; dafür die Werte unter [Akku](#akku) eintragen. Ohne sie rechnet Balkonaut mit den zuletzt bekannten
Werten (etwa aus einem früheren Betrieb über Home Assistant), sonst mit 0 und 100 %. Der Import des Verlaufs (`app.backfill`) geht nur über Home Assistant.

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

Die Tagesprognose kommt von Forecast.Solar, abgerufen zur vollen und halben Stunde, je Fläche ein Abruf, der Tages-
und Stundenwerte liefert. Forecast.Solar erlaubt ohne Konto 12 Abrufe je Stunde und öffentlicher IP-Adresse; alle
Geräte im Heimnetz teilen sich diese Grenze, auch die Forecast.Solar-Integration in Home Assistant. Nach einem Fehler
versucht Balkonaut es erst zum nächsten dieser Zeitpunkte wieder. Den erwarteten Jahresverlauf
(langjähriges Mittel, keine Prognose) holt Balkonaut einmal bei PVGIS, wenn sich Standort oder Flächen ändern; er
dient nur der Hochrechnung der Amortisation, solange das Datum der Inbetriebnahme fehlt.

Auch mit Home Assistant (Abschnitt `home_assistant`) braucht es dafür keine Forecast.Solar-Integration:
Sind Flächen eingetragen, ruft Balkonaut die Prognose selbst ab. Fehlt `location`, gilt der Standort aus Home
Assistant. Ist eine Prognose-Entität (`pv_forecast_today`, `pv_ac_forecast_today`) zugeordnet, geht sie vor.

## Verbindung zu Home Assistant

Die Verbindung steht in `data/config.yaml` im Abschnitt `home_assistant`:

- `url`: Adresse von Home Assistant, z. B. `http://192.168.1.10:8123`
- `token`: ein langlebiges Zugriffstoken. Erstellen in Home Assistant unter
  *Profil → Sicherheit → Langlebige Zugriffstoken*.
- `entities`: welche Home-Assistant-Entität welche Messgröße liefert, jeweils mit einem Faktor.
  Ein Faktor von `-1` dreht das Vorzeichen um, wenn ein Gerät eine Richtung anders herum meldet.

Welche Messgrößen es gibt und welches Vorzeichen sie haben, steht unter [Messgrößen](messquellen.md#messgroen),
welche Quelle für welche Größe am besten geeignet ist unter [Messquellen](messquellen.md).
Nach einer Änderung an `config.yaml` den Container neu starten. Den Verlauf, den Home Assistant noch gespeichert hat,
übernimmt Balkonaut auf Wunsch einmalig, siehe [Verlauf aus Home Assistant übernehmen](docker.md#verlauf-aus-home-assistant-ubernehmen).
