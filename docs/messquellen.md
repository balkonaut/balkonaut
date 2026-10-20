# Messquellen

Ein Balkonkraftwerk mit Speicher wird meist an mehreren Stellen gemessen: am Netzanschluss
(z. B. Shelly Pro 3EM), im Speicher-Wechselrichter und oft zusätzlich am Einspeisepunkt
(z. B. Shelly Plug). Die Werte weichen voneinander ab. Balkonaut nutzt deshalb feste Regeln,
welche Quelle für welche Größe zählt.

## Regeln

| Größe | Maßgebliche Quelle | Warum |
|---|---|---|
| Netzbezug und Einspeisung | Summenleistung des Netzzählers, über alle Phasen saldiert und von Balkonaut aufsummiert | Der Stromzähler des Netzbetreibers saldiert über die Phasen. Die Energiezähler des Shelly Pro 3EM zählen jede Phase einzeln und weisen dadurch zu viel Bezug **und** zu viel Einspeisung aus. |
| Abgabe des Balkonkraftwerks ins Hausnetz | Energiezähler am Einspeisepunkt | Misst genau dort, wo der Strom ins Hausnetz geht. |
| PV-Erzeugung | Energiezähler des Wechselrichters | Zähler erfassen jede Sekunde, gemeldete Leistungswerte nur Stichproben. |
| Akku laden und entladen | Energiezähler des Speichers | Die gemeldete Akkuleistung kann deutlich vom tatsächlichen Energiefluss abweichen. |
| Ladestand (SoC) | Speicher | Einzige Quelle. |
| Momentanwerte im Dashboard | Leistungswerte mit dem schnellsten Takt | Für die Anzeige zählt Aktualität, nicht die Summe. |

Gibt es für eine Größe keinen Energiezähler, summiert Balkonaut die Leistung selbst auf.
Solche Werte sind etwas ungenauer und werden als Näherung gekennzeichnet.

## Beispiel

Über zehn Tage im Oktober 2026 (APsystems EZHI mit EZ1-M, Shelly Pro 3EM, Shelly Plug):

| Messung | kWh |
|---|---|
| Netzbezug, saldiert | 128,0 |
| Netzbezug, Phasenzähler 3EM | 145,0 |
| Einspeisung, saldiert | 0,2 |
| Einspeisung, Phasenzähler 3EM | 17,3 |
| Abgabe ins Hausnetz, Zähler Shelly Plug | 31,9 |
| Abgabe ins Hausnetz, Leistung EZHI aufsummiert | 29,9 |
| Akku entladen, Zähler EZHI | 7,9 |
| Akku entladen, Leistung EZHI aufsummiert | 5,9 |
