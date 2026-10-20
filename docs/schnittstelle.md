# Schnittstelle (API)

Balkonaut stellt seine Werte als JSON bereit, z. B. für Home Assistant. Die Schnittstelle unter `/api/v1/`
bleibt stabil: Felder kommen höchstens hinzu, bestehende ändern sich erst mit `/api/v2/`.
Eine technische Übersicht aller Abfragen liefert `http://<adresse>:8000/docs`.

| Abfrage | Inhalt |
|---|---|
| `GET /api/v1/status` | Aktuelle Messwerte, Bilanz und Akku für heute, Monat, Jahr und gesamt, Amortisation |
| `GET /api/v1/verlauf?ansicht=tag\|woche\|monat\|jahr&datum=JJJJ-MM-TT` | Balken der Verlaufsansicht und Bilanz des Zeitraums |
| `GET /api/v1/nulleinspeisung` | Regelgüte der Nulleinspeisung der letzten 7 Tage |
| `GET /api/health` | `{"status": "ok"}`, wenn der Dienst läuft |

## Aufbau von `/api/v1/status`

- `stand`: Zeitpunkt des letzten Messwerts
- `live`: letzter Wert je Messgröße (Namen wie in den [Einstellungen](einstellungen.md), Leistung in W)
- `bilanz.tag|monat|jahr|gesamt`: `erzeugung`, `abgabe`, `netzbezug`, `einspeisung`, `eigenverbrauch`,
  `hausverbrauch` (kWh), `eigenverbrauchsquote`, `autarkiegrad` (Anteil 0 bis 1), `ersparnis` (€)
- `akku.tag|monat|jahr|gesamt`: `zyklen`, `zyklen_gesamt`, `zyklen_pro_jahr`, `gesundheit` (%), `kapazitaet` (kWh),
  `wirkungsgrad`, `verluste_wechselrichter` (Anteil 0 bis 1), `stunden_voll`, `einspeisung_bei_vollem_akku`,
  `stunden_leer`, `netzbezug_bei_leerem_akku` (kWh), `kosten_bei_leerem_akku` (€)
- `amortisation`: `kosten`, `bisher_gespart`, `ersparnis_pro_jahr`, `rest` (€), `basis` (`inbetriebnahme` oder
  `messtage`), `jahre_bis_amortisation`, `amortisiert_am` (Datum), `zaehler_plausibel`, `messtage`

Fehlt ein Wert (z. B. ohne Akku-Messgrößen), steht dort `null`.

## Werte als Sensoren in Home Assistant

Mit der REST-Integration von Home Assistant werden Werte zu Sensoren. Beispiel für die `configuration.yaml`:

```yaml
rest:
  - resource: http://<adresse>:8000/api/v1/status
    scan_interval: 300
    sensor:
      - name: Balkonaut Ersparnis heute
        value_template: "{{ value_json.bilanz.tag.ersparnis | round(2) }}"
        unit_of_measurement: "€"
        device_class: monetary
      - name: Balkonaut Autarkie heute
        value_template: "{{ ((value_json.bilanz.tag.autarkiegrad or 0) * 100) | round(0) }}"
        unit_of_measurement: "%"
      - name: Balkonaut Ersparnis gesamt
        value_template: "{{ value_json.amortisation.bisher_gespart | round(0) }}"
        unit_of_measurement: "€"
        device_class: monetary
      - name: Balkonaut amortisiert am
        value_template: "{{ value_json.amortisation.amortisiert_am }}"
        device_class: date
      - name: Balkonaut Akku Vollzyklen
        value_template: "{{ value_json.akku.gesamt.zyklen_gesamt | round(0) }}"
```

Nach dem Ändern der `configuration.yaml` in Home Assistant *Entwicklerwerkzeuge → YAML → REST-Entitäten neu laden*
oder Home Assistant neu starten.
