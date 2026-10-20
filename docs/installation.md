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

## Image automatisch bauen (Gitea Actions)

Liegt das Repository in einer eigenen Gitea-Instanz, kann ein Gitea Runner auf der NAS bei jedem Push auf `main`
die Tests ausführen und das Image `balkonaut:latest` bauen (`.gitea/workflows/deploy.yml`):

1. In Gitea im Repository unter *Einstellungen → Actions → Runner* einen Runner anlegen und das Registrierungs-Token kopieren.
2. Den Runner auf der NAS starten:

    ```bash
    docker run -d --name gitea-runner --restart unless-stopped \
      -e GITEA_INSTANCE_URL=http://<gitea-adresse> \
      -e GITEA_RUNNER_REGISTRATION_TOKEN=<token> \
      -e GITEA_RUNNER_NAME=nas \
      -v <ordner>/gitea-runner:/data \
      -v /var/run/docker.sock:/var/run/docker.sock \
      docker.io/gitea/runner:3
    ```

3. Nach einem erfolgreichen Lauf den Container mit dem neuen Image neu erstellen, im Verzeichnis von Balkonaut:

    ```bash
    docker compose up -d
    ```

    oder in Dockhand den Stack neu starten. `git pull` und `--build` sind dafür nicht nötig.

Den Container selbst startet der Workflow bewusst nicht: Der Runner entfernt am Ende eines Jobs alle Container,
die der Job gestartet hat.

!!! warning "Zugriff auf Docker"
    Der Runner hat über `/var/run/docker.sock` vollen Zugriff auf Docker und damit auf die NAS. Nur für eigene,
    private Repositories verwenden.

## Verlauf aus Home Assistant übernehmen

Home Assistant speichert standardmäßig die letzten zehn Tage. Diesen Verlauf kann Balkonaut einmalig
übernehmen, damit die Auswertung nicht bei null beginnt:

```bash
docker compose exec balkonaut python -m app.backfill 10
```

Die Zahl gibt an, wie viele Tage vor dem ersten eigenen Messwert übernommen werden.
Stunden, die Balkonaut schon selbst gemessen hat, bleiben unverändert. Der Befehl kann gefahrlos
mehrfach laufen.

## Home-Assistant-Integration

Die Integration holt die Werte der laufenden Balkonaut-App als Gerät *Balkonaut* mit Sensoren nach Home Assistant
(Bilanz für heute, Monat und Jahr, Amortisation, Akku). Sie ersetzt die REST-Sensoren aus der YAML-Konfiguration.

1. Den Ordner `custom_components/balkonaut` aus diesem Repository nach `config/custom_components/balkonaut` in
   Home Assistant kopieren, z. B. mit dem Add-on *Samba share* oder *Studio Code Server*.
2. Home Assistant neu starten.
3. *Einstellungen → Geräte & Dienste → Integration hinzufügen → Balkonaut*, Adresse der App eingeben
   (z. B. `http://192.168.1.10:8000`).

Das Abfrageintervall (Standard 5 Minuten) lässt sich danach unter *Konfigurieren* ändern. Die Installation über
HACS folgt, sobald das Repository öffentlich ist.

## In Home Assistant einbinden

Übersicht und Handbuch lassen sich als eigene Dashboards in die Seitenleiste von Home Assistant holen:
*Einstellungen → Dashboards → Dashboard hinzufügen → Webseite*, als URL
`http://<adresse>:8000/` für die Übersicht oder `http://<adresse>:8000/handbuch/` für dieses Handbuch.

Wird Home Assistant über HTTPS aufgerufen, blockiert der Browser eine Seite mit `http://`.
Dann muss Balkonaut ebenfalls über HTTPS erreichbar sein, zum Beispiel über einen Reverse Proxy.
