<img src="https://raw.githubusercontent.com/balkonaut/balkonaut/main/docs/assets/logo.svg" alt="Balkonaut" width="96" align="right">

# Balkonaut

[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz)
[![Version](https://img.shields.io/github/v/release/balkonaut/balkonaut)](https://github.com/balkonaut/balkonaut/releases)
[![Validate](https://github.com/balkonaut/balkonaut/actions/workflows/validate.yml/badge.svg)](https://github.com/balkonaut/balkonaut/actions/workflows/validate.yml)
[![Lizenz](https://img.shields.io/github/license/balkonaut/balkonaut)](https://github.com/balkonaut/balkonaut/blob/main/LICENSE)

**Antworten statt Rohdaten für dein Balkonkraftwerk mit Speicher.**

Das Energy-Dashboard von Home Assistant zeigt, wie viel Strom geflossen ist. Balkonaut beantwortet die
Fragen dahinter: Wie viel spare ich wirklich? Wann hat sich die Anlage bezahlt gemacht? Arbeitet der Akku
gut, und regelt die Nulleinspeisung sauber?

![Balkonaut in der Seitenleiste von Home Assistant: Energiefluss, Akku-Ring und Bilanz](https://raw.githubusercontent.com/balkonaut/balkonaut/main/docs/assets/panel.png)

## Was Balkonaut kann

- **Bilanz** für heute, Monat, Jahr und gesamt: Erzeugung, Eigenverbrauch, Netzbezug, Einspeisung,
  Autarkiegrad und Ersparnis in Euro
- **Amortisation** mit Datum, ab dem sich die Anlage voraussichtlich bezahlt gemacht hat
- **Akku-Auswertung**: Vollzyklen, Gesundheit, Wirkungsgrad, Stunden mit vollem oder leerem Akku
- **Nulleinspeisung**: wie gut der Speicher den Hausverbrauch trifft, was an Einspeisung und Bezug übrig bleibt
- **Ertragswächter**: Vergleich mit der Prognose von Forecast.Solar, Warnung bei auffälligen Abweichungen
- **Monatsbericht** zum Drucken
- **Karte** für das Dashboard mit Energiefluss und Akku-Ring, **Seitenleiste** mit allen Ansichten
- **Saubere Messwerte**: feste Regeln, welche Quelle für welche Größe zählt (z. B. über alle Phasen
  saldierter Netzbezug statt der Phasenzähler eines Shelly Pro 3EM)

Alles läuft in Home Assistant: Balkonaut misst selbst, speichert in einer eigenen Datenbank im
Konfigurationsordner und übernimmt beim ersten Start den Verlauf aus dem Recorder.

## Installation

[![In HACS öffnen](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=balkonaut&repository=balkonaut&category=integration)

1. Über den Knopf das Repository in HACS öffnen, oder in HACS oben rechts *⋮ → Benutzerdefinierte Repositories*
   `https://github.com/balkonaut/balkonaut` mit Typ *Integration* hinzufügen.
2. *Herunterladen*, danach Home Assistant neu starten.

Ohne HACS: `custom_components/balkonaut` aus dem [neuesten Release](https://github.com/balkonaut/balkonaut/releases)
in den Ordner `custom_components` der Home-Assistant-Konfiguration kopieren und neu starten.

Voraussetzung: Home Assistant 2026.10 oder neuer.

## Einrichtung

[![Integration hinzufügen](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=balkonaut)

*Eigenständig in Home Assistant* wählen. Die Namen der Entitäten muss man nicht kennen:

1. **Geräte wählen**: Netzmessung, Speicher oder Wechselrichter, optional ein zusätzlicher Wechselrichter und
   eine Messung am Einspeisepunkt. Was man nicht hat, bleibt leer.
2. **Entitäten prüfen**: Balkonaut schlägt zu jeder Messgröße eine Entität vor und zeigt die aktuellen Werte mit
   Richtung, z. B. „Netzleistung: 312 W (Bezug)“. Stimmt eine Richtung nicht, die Messgröße unter
   *Vorzeichen drehen* wählen.
3. **Zusammenfassung**: welche Funktionen mit der Zuordnung verfügbar sind und welche nicht.

Danach unter *Konfigurieren* Arbeitspreis, Einspeisevergütung, Anschaffungskosten und Inbetriebnahme eintragen.
Die Zuordnung lässt sich später über *⋮ → Neu konfigurieren* ändern, ohne Messdaten zu verlieren.

### Unterstützte Geräte

Für diese Geräte kennt Balkonaut die Entitäten genau, samt Vorzeichen:

| Gerät | Integration in Home Assistant |
|---|---|
| APsystems EZHI | APsystems EZHI Local API (HACS) |
| APsystems EZ1-M | APsystems |
| Shelly Pro 3EM, Shelly Plug | Shelly |
| Forecast.Solar (Prognose) | Forecast.Solar |
| Deye (Hybrid und Mikrowechselrichter), aus dem Quellcode abgeleitet | Solarman (HACS) |
| Huawei SUN2000, LUNA2000, Power Meter, aus dem Quellcode abgeleitet | Huawei Solar (HACS) |
| Hoymiles HM/HMS, aus dem Quellcode abgeleitet | OpenDTU, AhoyDTU (MQTT), Hoymiles WiFi (HACS) |
| Anker Solix Solarbank, aus dem Quellcode abgeleitet | Anker Solix (HACS) |
| Zendure SolarFlow, Hyper, AIO, aus dem Quellcode abgeleitet | Zendure (HACS) |
| EcoFlow PowerStream, STREAM, aus dem Quellcode abgeleitet | EcoFlow Cloud (HACS) |
| Growatt MIN, MIC, MOD, SPH, aus dem Quellcode abgeleitet | Growatt Server |

Andere Geräte gehen auch: Balkonaut schlägt Entitäten nach Art und Einheit vor, wenn das eindeutig ist, sonst
wählt man selbst. Damit ein Gerät fest dazukommt, die Diagnose-Datei (*⋮ → Diagnose herunterladen*) mit Hersteller,
Modell und Integration an ein [Issue](https://github.com/balkonaut/balkonaut/issues) hängen.

## Karte und Seitenleiste

*Balkonaut* erscheint nach der Einrichtung in der Seitenleiste mit Übersicht, Verlauf, Nulleinspeisung und
Monatsbericht. Die Karte wird automatisch geladen; im Dashboard *Karte hinzufügen* und nach *Balkonaut* suchen
oder als YAML:

```yaml
type: custom:balkonaut-card
```

## Sensoren und Warnungen

- Ersparnis, Erzeugung, Eigenverbrauch, Netzbezug und Autarkie für heute, Monat und Jahr
- Amortisation: bisher gespart, Rest, Ersparnis pro Jahr, amortisiert am
- Akku: Vollzyklen, Gesundheit, Wirkungsgrad
- Problem-Sensor *Warnungen* und Ereignis *Warnung* für Benachrichtigungen, Beispiel-Automation im
  [Handbuch](https://balkonaut.github.io/balkonaut/installation/#benachrichtigung-bei-warnungen)
- Hinweis unter *Reparaturen*, wenn eine zugeordnete Entität verschwindet, z. B. nach einer Umbenennung

## Ohne Home Assistant oder mit der Docker-App

Balkonaut gibt es auch als Docker-Container, etwa für eine NAS, mit eigener Web-Oberfläche. Die Integration kann
dann im Modus *Mit einer Balkonaut-App* deren Werte anzeigen oder die Messdaten mit der Aktion
*Balkonaut: Historie aus Balkonaut-App übernehmen* in den eigenständigen Betrieb übernehmen.
Details im [Handbuch](https://balkonaut.github.io/balkonaut/installation/).

## Handbuch

Das ausführliche [Handbuch](https://balkonaut.github.io/balkonaut/) auf Deutsch: Installation, Einstellungen, Auswertung, Messquellen und
Schnittstelle.

## Lizenz

[Apache-2.0](https://github.com/balkonaut/balkonaut/blob/main/LICENSE)
