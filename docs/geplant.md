# Geplant

Was als Nächstes kommt, ohne feste Termine. Erledigte Punkte verschwinden von dieser Seite und stehen dann im
jeweiligen Kapitel des Handbuchs.

## Simulator: Was wäre, wenn …?

Balkonaut rechnet dein echtes Jahr Stunde für Stunde mit geänderter Anlage nach und zeigt, was sich an Netzbezug,
Einspeisung und Ersparnis ändert:

- **Mehr Akku:** Wie viel brächte ein weiterer Akku, und nach wie vielen Jahren hätte er sich bezahlt gemacht?
  Lohnt er sich, erscheint ein Hinweis bei den [Warnungen](auswertung.md#warnungen), etwa „Ein weiterer Akku würde
  etwa X € im Jahr sparen“. Bis dahin hilft die Kachel *Weiteres Akku-Modul*, siehe
  [Lohnt sich ein größerer Akku?](auswertung.md#lohnt-sich-ein-groerer-akku)
- **Module und Abgabelimit:** mehr oder weniger Module, anderes Limit (z. B. 800 oder 1200 W).
- **Regelung und Tarif:** Nulleinspeisung gegen eine feste Grundlast, andere Ladegrenzen, anderer Arbeitspreis.

Der Simulator braucht eine verlässliche Messung am Netzanschluss, weil sich der Hausverbrauch daraus ergibt.

## Früheren Verlauf übernehmen

Balkonaut zählt ab dem Tag, an dem es läuft. Was die Anlage davor erzeugt hat, soll es nachtragen können, damit
Bericht, Bilanz und Amortisation von Anfang an stimmen. Die Geräte selbst helfen dabei nicht: Der EZHI etwa meldet
lokal nur den aktuellen Stand und Zähler seit der Inbetriebnahme, keinen Verlauf.

- **Integration für Home Assistant:** Home Assistant hebt für Leistung und Zähler Stundenwerte ohne Ablaufdatum
  auf (Langzeitstatistik). Die Integration übernimmt sie, zurück bis zu dem Tag, an dem die Integration des
  Herstellers eingerichtet wurde. Bisher reicht der [Import](integration.md) nur so weit, wie Home Assistant die
  Rohdaten aufhebt, meist 10 Tage.
- **Docker-App:** wahlweise aus der Cloud des Herstellers, zuerst APsystems. Das ist eine Option, die man
  ausdrücklich einschaltet; ohne sie liest die Docker-App weiter nur im Heimnetz.

## Installation über die HACS-Standardliste

Die Integration ist zur Aufnahme in die Standardliste von HACS angemeldet. Danach findet HACS sie direkt, ohne dass
du das Repository vorher als benutzerdefiniertes Repository eintragen musst.
