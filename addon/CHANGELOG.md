# Änderungen

## 1.0.1

- *Einstellungen → Standort und Flächen* gibt es jetzt auch im Add-on. Sind Flächen eingetragen, ruft Balkonaut die Tagesprognose selbst ab, ohne Forecast.Solar-Integration; ohne Breiten- und Längengrad gilt der Standort aus Home Assistant.
- Die Einrichtungs-Kachel zählt den Schritt Standort mit Flächen oder einer Prognose-Entität.
- Die Warnung „keine Messwerte“ erscheint auch, wenn nur noch die Prognose ankommt.
- Akku-Auswertung: Die laufende Stunde gilt nicht mehr fälschlich als „leerer Akku“.
- Weitere Korrekturen aus einem Code-Review (Regelgüte bei 0 % bzw. 0 W, Amortisation bei sehr kleiner Ersparnis, Datenbankzugriffe).

## 1.0.0

- Kachel *Einrichtung* auf der Übersicht: zeigt, ob Entitäten, Tagesprognose und Preise eingetragen sind, und verschwindet, wenn alles erledigt ist.
- Der Link zum Datum der Inbetriebnahme springt direkt zum Feld.
- *Handbuch* in der Navigation öffnet das Handbuch auf der Website.

## 0.9.3

- Integration: Die Aktion *Historie aus Balkonaut-App übernehmen* dürfen nur noch Administratoren ausführen. Das Add-on selbst ist unverändert.

## 0.9.2

Die Version folgt jetzt der Version von Balkonaut (Release, Docker-Image, Integration).

- Energiefluss mit Modulen und Wechselrichtern, Bezeichnung für Akku und zusätzlichen Wechselrichter unter *Einstellungen*.
- Kacheln heben sich beim Überfahren mit der Maus an.
- Knopf in der Kopfzeile wechselt zwischen *Automatisch*, *Hell* und *Dunkel*.
- Fußzeile mit Version und Link zum Quellcode.
- Erzeugung zählt nur positive Anteile, nächtlicher Standby-Bezug geht nicht mehr ab.
- Ertragswächter vergleicht nur Tage mit Prognose.
- Einstellungen: Fehler bei den Flächen nennen das Feld, die Eingaben bleiben stehen.

## 0.1.1

- Handbuch: Link „Zurück zu Balkonaut“ im Menü, das Logo führt ebenfalls zurück.
- Kleine negative Werte erscheinen als 0 statt als „-0,0“.

## 0.1.0

- Erste Version als Home-Assistant-Add-on mit Weboberfläche in der Seitenleiste (Ingress).
