# Docker-App

Die Docker-App läuft als eigener Container, etwa auf einer NAS oder einem Raspberry Pi, ganz ohne Home Assistant. Sie
liest die Geräte direkt im Heimnetz (welche, steht unter [Unterstützte Geräte](geraete.md#gerate-direkt-im-heimnetz)),
andere Geräte auf Wunsch über Home Assistant, speichert die Messwerte selbst und zeigt alles in einer eigenen
Weboberfläche. Wer Home Assistant ohnehin nutzt, ist mit der [Home-Assistant-Integration](integration.md) meist
einfacher dran.

Aus dem Handbuch geht es über *Zurück zu Balkonaut* im Menü oder über das Logo zurück zur Übersicht.

## Installation mit dem fertigen Image

1. Einen Ordner anlegen, darin eine Datei `docker-compose.yml`:

    ```yaml
    services:
      balkonaut:
        image: ghcr.io/balkonaut/balkonaut:latest
        ports:
          - "${BALKONAUT_PORT:-8000}:8000"
        volumes:
          - ./data:/data
        restart: unless-stopped
    ```

2. Starten: `docker compose up -d`
3. `http://<adresse>:8000/` öffnen und unter *Einstellungen* die Geräte per IP-Adresse hinzufügen, Standort und
   Flächen sowie Preise eintragen (siehe [Einstellungen](einstellungen.md)).
4. Neue Versionen holen: `docker compose pull && docker compose up -d`. Die Messdaten im Ordner `data/` bleiben.

In Dockhand geht das als neuer Stack mit diesem Inhalt oder als Git-Stack direkt aus dem Repository
`https://github.com/balkonaut/balkonaut`, dessen `docker-compose.yml` ebenfalls das fertige Image nutzt.
Aktualisiert wird dort über *Nach Updates suchen*.

Ist Port 8000 auf dem Rechner schon belegt, neben der `docker-compose.yml` eine Datei `.env` anlegen (Vorlage:
[`.env.example`](https://github.com/balkonaut/balkonaut/blob/main/.env.example)) mit zum Beispiel
`BALKONAUT_PORT=8080` (in Dockhand als Variable des Stacks). Balkonaut ist dann unter `http://<adresse>:8080/`
erreichbar.

Das Image gibt es für amd64 und arm64. Jede Version trägt zusätzlich einen Tag `sha-<commit>`, mit dem sich bei
Problemen eine ältere Version festhalten lässt.

## Selbst bauen

1. Repository herunterladen und in das Verzeichnis wechseln.
2. In `docker-compose.yml` die Zeile `# build: .` aktivieren (Raute entfernen), dann Container bauen und starten:

    ```bash
    docker compose up -d --build
    ```

3. `http://<adresse>:8000/` öffnen. Bis alles eingerichtet ist, zeigt die Übersicht oben die Kachel
   *Einrichtung* mit den Schritten, jeweils mit Link zum passenden Abschnitt: unter *Einstellungen* die Geräte per IP-Adresse hinzufügen,
   optional Standort und Flächen eintragen, dann Preise und Kosten (siehe [Einstellungen](einstellungen.md)). Wer lieber eine Datei pflegt, kopiert `config.example.yaml`
   nach `data/config.yaml` und passt sie an.
4. Prüfen, ob der Dienst läuft: `http://<adresse>:8000/api/health` muss `{"status": "ok"}` liefern.

Alle Daten liegen im Ordner `data/`: Konfiguration (`config.yaml`) und Messdaten (`balkonaut.db`).
Für ein Backup genügt es, diesen Ordner zu sichern.

## Verlauf aus Home Assistant übernehmen

Nur mit der [Verbindung zu Home Assistant](einstellungen.md#verbindung-zu-home-assistant). Home Assistant
speichert standardmäßig die letzten zehn Tage. Diesen Verlauf kann Balkonaut einmalig
übernehmen, damit die Auswertung nicht bei null beginnt:

```bash
docker compose exec balkonaut python -m app.backfill 10
```

Die Zahl gibt an, wie viele Tage vor dem ersten eigenen Messwert übernommen werden.
Stunden, die Balkonaut schon selbst gemessen hat, bleiben unverändert. Der Befehl kann gefahrlos
mehrfach laufen.

## In Home Assistant einbinden

Die Docker-App und die Integration sind getrennt, die Integration liest nicht aus der Docker-App. In Home Assistant
lässt sich die Docker-App trotzdem anzeigen:

- Übersicht und Handbuch als eigene Dashboards in der Seitenleiste von Home Assistant:
  *Einstellungen → Dashboards → Dashboard hinzufügen → Webseite*, als URL
  `http://<adresse>:8000/` für die Übersicht oder `http://<adresse>:8000/handbuch/` für dieses Handbuch.
- Einzelne Werte als Sensoren über die REST-Integration von Home Assistant, siehe
  [Schnittstelle](schnittstelle.md#werte-als-sensoren-in-home-assistant).

Wird Home Assistant über HTTPS aufgerufen, blockiert der Browser eine Seite mit `http://`.
Dann muss Balkonaut ebenfalls über HTTPS erreichbar sein, zum Beispiel über einen Reverse Proxy.

## Später zur Integration wechseln

Die gespeicherten Messdaten der Docker-App lassen sich in die Integration übernehmen, siehe
[Umzug von der Docker-App](integration.md#umzug-von-der-docker-app).

## Tests bei jedem Push (Gitea Actions)

Liegt das Repository in einer eigenen Gitea-Instanz, kann ein Gitea Runner auf der NAS bei jedem Push auf `main`
Tests, Integrationstests, hassfest und das Handbuch prüfen (`.gitea/workflows/deploy.yml`). Das Image selbst baut
GitHub als `ghcr.io/balkonaut/balkonaut:latest`, jede Release-Version zusätzlich mit eigenem Tag (z. B. `:1.0.0`); aktualisiert wird mit `docker compose pull && docker compose up -d`
oder in Dockhand über *Nach Updates suchen*.

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

!!! warning "Zugriff auf Docker"
    Der Runner hat über `/var/run/docker.sock` vollen Zugriff auf Docker und damit auf die NAS. Nur für eigene,
    private Repositories verwenden.
