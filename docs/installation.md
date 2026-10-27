# Installation

Balkonaut gibt es auf zwei getrennten Wegen. Beide rechnen gleich, messen und speichern aber jeder für sich.

| | [Docker-App](docker.md) | [Home-Assistant-Integration](integration.md) |
|---|---|---|
| Läuft | als eigener Container, z. B. auf einer NAS | in Home Assistant, auch unter Home Assistant OS |
| Liest die Geräte | direkt im Heimnetz, andere auf Wunsch über Home Assistant | aus Entitäten anderer Integrationen oder direkt im Heimnetz |
| Oberfläche | eigene Weboberfläche | Seitenleiste, Sensoren und Karte in Home Assistant |
| Einstellungen | [im Browser](einstellungen.md) | unter *Konfigurieren* der Integration |

Wer Home Assistant nutzt, nimmt meist die Integration. Die Docker-App passt, wenn es kein Home Assistant gibt oder
Balkonaut unabhängig davon laufen soll. Ihre Weboberfläche lässt sich trotzdem in Home Assistant anzeigen, siehe
[In Home Assistant einbinden](docker.md#in-home-assistant-einbinden).
