# Geplant

Was als Nächstes kommt, ohne feste Termine. Erledigte Punkte verschwinden von dieser Seite und stehen dann im
jeweiligen Kapitel des Handbuchs.

## Simulator: Was wäre, wenn …?

Balkonaut rechnet dein echtes Jahr Stunde für Stunde mit geänderter Anlage nach und zeigt, was sich an Netzbezug,
Einspeisung und Ersparnis ändert:

- **Akku größer, kleiner oder ohne:** frei wählbar auf einer eigenen Seite. Ein weiteres Modul rechnet die Kachel
  *Weiteres Akku-Modul* schon heute, siehe [Lohnt sich ein größerer Akku?](auswertung.md#lohnt-sich-ein-groerer-akku)
- **Module und Abgabelimit:** mehr oder weniger Module, anderes Limit (z. B. 800 oder 1200 W).
- **Regelung und Tarif:** Nulleinspeisung gegen eine feste Grundlast, andere Ladegrenzen, anderer Arbeitspreis.

## Früheren Verlauf übernehmen

Balkonaut zählt ab dem Tag, an dem es läuft. Was die Anlage davor erzeugt hat, soll es nachtragen können, damit
Bericht, Bilanz und Amortisation von Anfang an stimmen. Die Geräte selbst helfen dabei nicht: Der EZHI etwa meldet
lokal nur den aktuellen Stand und Zähler seit der Inbetriebnahme, keinen Verlauf.

- **Home-Assistant-Integration:** Home Assistant hebt für Leistung und Zähler Stundenwerte ohne Ablaufdatum
  auf (Langzeitstatistik). Die Home-Assistant-Integration übernimmt sie, zurück bis zu dem Tag, an dem die Integration des
  Herstellers eingerichtet wurde. Bisher reicht der [Import](integration.md) nur so weit, wie Home Assistant die
  Rohdaten aufhebt, meist 10 Tage.
- **Docker-App:** wahlweise aus der Cloud des Herstellers, zuerst APsystems. Das ist eine Option, die man
  ausdrücklich einschaltet; ohne sie liest die Docker-App weiter nur im Heimnetz. Die
  [APsystems-Cloud](einstellungen.md#apsystems-cloud-optional) liefert bisher Einstellungen und Szenario, aber
  keinen Verlauf.

## Installation über die HACS-Standardliste

Die Home-Assistant-Integration ist zur Aufnahme in die Standardliste von HACS angemeldet. Danach findet HACS sie direkt, ohne dass
du das Repository vorher als benutzerdefiniertes Repository eintragen musst.
