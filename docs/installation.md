# Installation

Balkonaut läuft als Docker-Container, zum Beispiel auf einer NAS.

1. Repository herunterladen und in das Verzeichnis wechseln.
2. Container bauen und starten:

    ```bash
    docker compose up -d --build
    ```

3. Prüfen, ob der Dienst läuft: `http://<adresse>:8000/api/health` muss `{"status": "ok"}` liefern.
