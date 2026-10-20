# Installation

Balkonaut läuft als Docker-Container, zum Beispiel auf einer NAS.

1. Repository herunterladen und in das Verzeichnis wechseln.
2. Konfiguration anlegen: `config.example.yaml` nach `data/config.yaml` kopieren und anpassen
   (siehe [Einstellungen](einstellungen.md)).
3. Container bauen und starten:

    ```bash
    docker compose up -d --build
    ```

4. Prüfen, ob der Dienst läuft: `http://<adresse>:8000/api/health` muss `{"status": "ok"}` liefern.

Alle Daten liegen im Ordner `data/`: Konfiguration (`config.yaml`) und Messdaten (`balkonaut.db`).
Für ein Backup genügt es, diesen Ordner zu sichern.

## In Home Assistant einbinden

Übersicht und Handbuch lassen sich als eigene Dashboards in die Seitenleiste von Home Assistant holen:
*Einstellungen → Dashboards → Dashboard hinzufügen → Webseite*, als URL
`http://<adresse>:8000/` für die Übersicht oder `http://<adresse>:8000/handbuch/` für dieses Handbuch.

Wird Home Assistant über HTTPS aufgerufen, blockiert der Browser eine Seite mit `http://`.
Dann muss Balkonaut ebenfalls über HTTPS erreichbar sein, zum Beispiel über einen Reverse Proxy.
