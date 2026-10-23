// Balkonaut-Panel in der Seitenleiste: Übersicht, Verlauf, Nulleinspeisung und Monatsbericht wie in der Docker-App.
// Daten über die WebSocket-Befehle balkonaut/status, /verlauf, /bericht, /nulleinspeisung; die Übersicht nutzt die
// Karte balkonaut-card, die die Integration global lädt. Keine Abhängigkeiten, kein Build-Schritt.

const TABS = [["start", "Übersicht"], ["verlauf", "Verlauf"], ["nulleinspeisung", "Nulleinspeisung"], ["bericht", "Bericht"]];
const PERIODS = [["tag", "Heute"], ["monat", "Monat"], ["jahr", "Jahr"], ["gesamt", "Gesamt"]];
const VIEWS = [["tag", "Tag"], ["woche", "Woche"], ["monat", "Monat"], ["jahr", "Jahr"]];
const HANDBUCH = "https://balkonaut.github.io/balkonaut/";

const PANEL_STYLE = `
  :host { display: block; min-height: 100%; background: var(--primary-background-color);
    --bk-sun: #f2b733; --bk-leaf: #3fa66b; --bk-sky: #4a8fd0; --bk-warn: #d9682f;
    --bk-line: var(--divider-color, #c4cfdd); --bk-ink: var(--primary-text-color); --bk-muted: var(--secondary-text-color);
    --bk-card: var(--ha-card-background, var(--card-background-color, #fff));
    --bk-mono: ui-monospace, "SF Mono", "JetBrains Mono", Menlo, Consolas, monospace; color: var(--bk-ink); }
  .toolbar { display: flex; align-items: center; gap: 8px; height: 56px; padding: 0 12px; font-size: 20px;
    background: var(--app-header-background-color, var(--primary-color)); color: var(--app-header-text-color, #fff); }
  .toolbar .brand { font: 700 18px var(--bk-mono); letter-spacing: .04em; text-transform: uppercase; }
  main { max-width: 72rem; margin: 0 auto; padding: 16px 16px 48px; }
  nav { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 16px; }
  nav button, nav a, .tabs button { min-height: 40px; padding: 0 14px; border: 1px solid var(--bk-line); border-radius: 6px;
    background: var(--bk-card); color: var(--bk-muted); font: 600 13px var(--bk-mono); text-transform: uppercase;
    letter-spacing: .06em; cursor: pointer; text-decoration: none; display: inline-flex; align-items: center; }
  nav button.on, .tabs button.on { background: var(--bk-ink); color: var(--bk-card); border-color: var(--bk-ink); }
  nav .spacer { flex: 1; }
  h2 { font: 600 13px var(--bk-mono); text-transform: uppercase; letter-spacing: .08em; color: var(--bk-muted); margin: 28px 0 12px; }
  .grid { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr)); }
  .card { background: var(--bk-card); border: 1px solid var(--bk-line); border-radius: 6px; padding: 16px 20px; min-width: 0; }
  .label { color: var(--bk-muted); font-size: 14px; }
  .card > .label:first-child { font: 600 12px var(--bk-mono); text-transform: uppercase; letter-spacing: .08em; }
  .value { font: 600 26px var(--bk-mono); letter-spacing: -.04em; margin: 4px 0; font-variant-numeric: tabular-nums; }
  .note { padding: 12px 16px; border-radius: 6px; background: color-mix(in srgb, var(--bk-warn) 15%, var(--bk-card));
    border-left: 4px solid var(--bk-warn); margin-bottom: 12px; }
  .tabs { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 12px; }
  .pager { display: flex; align-items: baseline; gap: 16px; margin: 12px 0; }
  .pager b { flex: 1; text-align: center; }
  .pager button { background: none; border: 0; color: var(--primary-color); font: inherit; cursor: pointer; padding: 8px; }
  .pager button:disabled { color: var(--bk-muted); cursor: default; }
  svg.chart { width: 100%; height: auto; display: block; }
  .legend { display: flex; flex-wrap: wrap; gap: 16px; font-size: 14px; color: var(--bk-muted); margin-top: 8px; }
  .legend i { display: inline-block; width: 12px; height: 12px; border-radius: 1px; margin-right: 6px; vertical-align: -1px; }
  .bar { height: 10px; background: var(--bk-line); border-radius: 2px; overflow: hidden; margin: 8px 0 16px; }
  .bar span { display: block; height: 100%; background: var(--bk-leaf); }
  table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
  th, td { padding: 6px 8px; border-bottom: 1px solid var(--bk-line); text-align: right; }
  th:first-child, td:first-child { text-align: left; }
  balkonaut-card { display: block; }
  @media print { .toolbar, nav, .noprint { display: none; } }
`;

class BalkonautPanel extends HTMLElement {
  constructor() {
    super();
    this._tab = "start";
    this._period = "tag";
    this._view = "tag";
    this._datum = "";
    this._monat = "";
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (this._card) this._card.hass = hass;
    if (this._menu) this._menu.hass = hass;
    if (first) this._show(this._tab);
  }

  set narrow(narrow) {
    this._narrow = narrow;
    if (this._menu) this._menu.narrow = narrow;
  }

  _fmt(v, digits = 1) {
    if (typeof v !== "number" || Number.isNaN(v)) return "–";
    const n = Number(v.toFixed(digits)) + 0; // kein „-0,0“
    return n.toLocaleString(this._hass.locale?.language || "de", { minimumFractionDigits: digits, maximumFractionDigits: digits });
  }

  _pct(v) {
    return v === null || v === undefined ? "–" : `${this._fmt(v * 100, 0)} %`;
  }

  _box(label, value, sub = "") {
    return `<div class="card"><div class="label">${label}</div><div class="value">${value}</div>${sub ? `<div class="label">${sub}</div>` : ""}</div>`;
  }

  async _ws(type, extra = {}) {
    return this._hass.callWS({ type: `balkonaut/${type}`, ...extra });
  }

  async _show(tab) {
    this._tab = tab;
    let body;
    try {
      if (tab === "start") body = this._start(await this._ws("status"), await this._ws("verlauf", { ansicht: "tag" }));
      else if (tab === "verlauf") body = this._history(await this._ws("verlauf", { ansicht: this._view, datum: this._datum }));
      else if (tab === "nulleinspeisung") body = this._regulation(await this._ws("nulleinspeisung"));
      else body = this._report(await this._ws("bericht", { monat: this._monat }));
    } catch (err) {
      body = `<p class="note">Balkonaut ist nicht verfügbar: ${err.message || err}</p>`;
    }
    this._render(body);
  }

  _render(body) {
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const nav = TABS.map(([k, name]) => `<button data-tab="${k}" class="${k === this._tab ? "on" : ""}">${name}</button>`).join("")
      + `<span class="spacer"></span><a href="/config/integrations/integration/balkonaut">Einstellungen</a>`
      + `<a href="${HANDBUCH}" target="_blank" rel="noreferrer">Handbuch</a>`;
    this.shadowRoot.innerHTML = `<style>${PANEL_STYLE}</style>
      <div class="toolbar"><ha-menu-button></ha-menu-button><span class="brand">Balkonaut</span></div>
      <main><nav>${nav}</nav>${body}</main>`;
    this._menu = this.shadowRoot.querySelector("ha-menu-button");
    Object.assign(this._menu, { hass: this._hass, narrow: this._narrow });
    this._card = this.shadowRoot.querySelector("balkonaut-card");
    if (this._card) {
      this._card.setConfig({});
      this._card.hass = this._hass;
    }
    this.shadowRoot.querySelectorAll("[data-tab]").forEach((b) => b.addEventListener("click", () => this._show(b.dataset.tab)));
    this.shadowRoot.querySelectorAll("[data-set]").forEach((b) => b.addEventListener("click", () => {
      const [key, value] = b.dataset.set.split("=");
      this[key] = value;
      if (key === "_view") this._datum = "";
      this._show(this._tab);
    }));
  }

  // Balkendiagramm wie app/templates/_chart.html: Eigenverbrauch grün, Netzbezug blau, Erzeugung gelber Strich
  _chart(bars) {
    const n = bars.length, left = 36, w = (480 - left) / Math.max(n, 1), every = Math.ceil(n / 12);
    const peak = Math.max(0, ...bars.map((b) => Math.max(b.own + b.grid, b.gen)));
    let ticks = [], scale = 0;
    if (peak) {
      const raw = peak / 4, mag = 10 ** Math.floor(Math.log10(raw));
      const step = [1, 2, 5, 10].map((m) => m * mag).find((s) => s >= raw);
      const digits = Math.max(0, -Math.floor(Math.log10(step)));
      for (let i = 1; i * step <= peak + 1e-9; i++) ticks.push([i * step, this._fmt(i * step, digits)]);
      scale = 140 / peak;
    }
    const grid = ticks.map(([v, l]) => `<line x1="${left}" x2="480" y1="${150 - v * scale}" y2="${150 - v * scale}" stroke="var(--bk-line)"/>
      <text x="${left - 4}" y="${153 - v * scale}" font-size="9" text-anchor="end" fill="var(--bk-muted)">${l}</text>`).join("");
    const cols = bars.map((h, i) => {
      const x = left + i * w + w * 0.1, bw = w * 0.8;
      return `<rect x="${x}" y="${150 - h.own * scale}" width="${bw}" height="${h.own * scale}" fill="var(--bk-leaf)"><title>${h.label}: ${this._fmt(h.own, 2)} kWh vom Balkonkraftwerk</title></rect>
        <rect x="${x}" y="${150 - (h.own + h.grid) * scale}" width="${bw}" height="${h.grid * scale}" fill="var(--bk-sky)"><title>${h.label}: ${this._fmt(h.grid, 2)} kWh aus dem Netz</title></rect>
        ${h.gen ? `<rect x="${x}" y="${149 - h.gen * scale}" width="${bw}" height="3" fill="var(--bk-sun)"><title>${h.label}: ${this._fmt(h.gen, 2)} kWh erzeugt</title></rect>` : ""}
        ${i % every === 0 ? `<text x="${x + w * 0.4}" y="166" font-size="10" text-anchor="middle" fill="var(--bk-muted)">${h.label}</text>` : ""}`;
    }).join("");
    return `<svg class="chart" viewBox="0 0 480 170" role="img" aria-label="Hausverbrauch je Zeitabschnitt, aufgeteilt in Balkonkraftwerk und Netzbezug, mit Erzeugung">
      <text x="0" y="8" font-size="9" fill="var(--bk-muted)">kWh</text>${grid}
      <line x1="${left}" x2="480" y1="150" y2="150" stroke="var(--bk-muted)"/>${cols}</svg>
      <div class="legend"><span><i style="background:var(--bk-leaf)"></i>Balkonkraftwerk</span><span><i style="background:var(--bk-sky)"></i>Netz</span>
      <span><i style="background:var(--bk-sun);height:4px;vertical-align:3px"></i>Erzeugung</span></div>`;
  }

  _balance(b) {
    return `<div class="grid">${this._box("Ersparnis", `${this._fmt(b.ersparnis, 2)} €`)}${this._box("Eigenverbrauch", `${this._fmt(b.eigenverbrauch)} kWh`)}
      ${this._box("Autarkiegrad", this._pct(b.autarkiegrad))}${this._box("Eigenverbrauchsquote", this._pct(b.eigenverbrauchsquote))}
      ${this._box("Erzeugung", `${this._fmt(b.erzeugung)} kWh`)}${this._box("Hausverbrauch", `${this._fmt(b.hausverbrauch)} kWh`)}
      ${this._box("Netzbezug", `${this._fmt(b.netzbezug)} kWh`)}${this._box("Einspeisung", `${this._fmt(b.einspeisung)} kWh`)}</div>`;
  }

  _start(data, today) {
    const st = data.status, b = st.bilanz[this._period], k = st.akku[this._period], a = st.amortisation;
    const tabs = PERIODS.map(([key, name]) => `<button data-set="_period=${key}" class="${key === this._period ? "on" : ""}">${name}</button>`).join("");
    const progress = a.kosten ? Math.min((a.bisher_gespart / a.kosten) * 100, 100) : 0;
    const date = (iso) => iso ? new Date(iso).toLocaleDateString(this._hass.locale?.language || "de", { month: "2-digit", year: "numeric" }) : "–";
    return `${st.warnungen.map((w) => `<p class="note">${w.text}</p>`).join("")}
      <balkonaut-card></balkonaut-card>
      <h2>Bilanz</h2><div class="tabs">${tabs}</div>${this._balance(b)}
      <h2>Akku</h2><div class="grid">
        ${this._box("Vollzyklen im Zeitraum", this._fmt(k.zyklen), `gesamt ${this._fmt(k.zyklen_gesamt, 0)}${k.zyklen_pro_jahr ? `, ${this._fmt(k.zyklen_pro_jahr, 0)} pro Jahr` : ""}`)}
        ${this._box("Gesundheit (SoH)", `${this._fmt(k.gesundheit, 0)} %`, `Kapazität ${this._fmt(k.kapazitaet, 2)} kWh`)}
        ${this._box("Wirkungsgrad Akku", this._pct(k.wirkungsgrad))}
        ${this._box("Verluste Speicher-Wechselrichter", this._pct(k.verluste_wechselrichter))}
        ${this._box("Stunden mit vollem Akku", k.stunden_voll ?? "–", `dabei eingespeist ${this._fmt(k.einspeisung_bei_vollem_akku)} kWh`)}
        ${this._box("Stunden mit leerem Akku", k.stunden_leer ?? "–", `dabei Netzbezug ${this._fmt(k.netzbezug_bei_leerem_akku)} kWh (${this._fmt(k.kosten_bei_leerem_akku, 2)} €)`)}</div>
      <h2>Woher kommt dein Strom heute?</h2><div class="card">${this._chart(today.balken)}</div>
      <h2>Amortisation</h2><div class="card">
        <div class="label">Bisher gespart ${this._fmt(a.bisher_gespart, 0)} € von ${this._fmt(a.kosten, 0)} €</div>
        <div class="bar"><span style="width:${progress}%"></span></div>
        <div class="grid">
          <div><div class="label">Noch offen</div><div class="value">${this._fmt(a.rest, 0)} €</div></div>
          <div><div class="label">Ersparnis pro Jahr</div><div class="value">${this._fmt(a.ersparnis_pro_jahr, 0)} €</div></div>
          <div><div class="label">Amortisiert</div><div class="value">${a.jahre_bis_amortisation === null ? "–" : a.rest === 0 ? "bereits" : date(a.amortisiert_am)}</div>
            ${a.jahre_bis_amortisation ? `<div class="label">in ${this._fmt(a.jahre_bis_amortisation)} Jahren</div>` : ""}</div>
        </div></div>`;
  }

  _history(d) {
    const tabs = VIEWS.map(([key, name]) => `<button data-set="_view=${key}" class="${key === d.ansicht ? "on" : ""}">${name}</button>`).join("");
    return `<div class="tabs">${tabs}</div>
      <div class="pager"><button data-set="_datum=${d.zurueck}">← zurück</button><b>${d.titel}</b>
        <button ${d.weiter ? `data-set="_datum=${d.weiter}"` : "disabled"}>weiter →</button></div>
      <div class="card">${this._chart(d.balken)}</div><h2>Bilanz</h2>${this._balance(d.bilanz)}`;
  }

  _regulation(r) {
    if (!r) return `<p class="note">Noch keine Messwerte.</p>`;
    return `<p class="label">Wie gut regelt der Speicher den Netzanschluss auf 0 W? Grundlage sind die Messwerte der letzten 7 Tage.
      Die Ergebnisse hängen an einer korrekten Netzmessung.</p>
      ${r.regelbereit_stunden < 1 ? `<p class="note">Der Speicher konnte im Zeitraum kaum nachregeln (Akku leer oder Abgabe am Limit). Die Werte sind deshalb wenig aussagekräftig.</p>` : ""}
      <div class="grid">
        ${this._box("Regelbereit", `${this._fmt(r.regelbereit_stunden)} h`, `von ${this._fmt(r.zeitraum_stunden, 0)} h`)}
        ${this._box("Davon nahe 0 W (±50 W)", this._pct(r.anteil_nahe_null))}
        ${this._box("Typische Netzleistung dabei", `${this._fmt(r.median_netz, 0)} W`, "Median, + Bezug")}
        ${this._box("Vermeidbarer Netzbezug", `${this._fmt(r.vermeidbarer_netzbezug, 2)} kWh`, `${this._fmt(r.vermeidbare_kosten, 2)} €`)}
        ${this._box("Einspeisung", `${this._fmt(r.einspeisung, 2)} kWh`, `Wert bei Eigenverbrauch ${this._fmt(r.einspeisung_wert, 2)} €`)}
        ${this._box("Lastsprünge über 300 W", r.lastspruenge, `nicht ausgeregelt in 5 min: ${r.nicht_ausgeregelt}`)}
        ${this._box("Reaktionszeit", `${this._fmt(r.reaktionszeit_median, 0)} s`, "Median bis zurück auf ±50 W")}
        ${this._box(`Abgabe über Limit (${this._fmt(r.limit, 0)} W)`, this._pct(r.anteil_ueber_limit), `höchster Wert ${this._fmt(r.max_abgabe, 0)} W`)}
      </div>`;
  }

  _report(r) {
    const month = (iso) => iso.slice(0, 7);
    const rows = [["erzeugung", "Erzeugung", "kWh", 1], ["abgabe", "Abgabe ins Haus", "kWh", 1], ["hausverbrauch", "Hausverbrauch", "kWh", 1],
      ["eigenverbrauch", "Eigenverbrauch", "kWh", 1], ["netzbezug", "Netzbezug", "kWh", 1], ["einspeisung", "Einspeisung", "kWh", 2], ["ersparnis", "Ersparnis", "€", 2]];
    const cols = [r.bilanz, r.vormonat, r.vorjahr];
    const table = rows.map(([key, name, unit, digits]) => `<tr><td>${name}</td>${cols.map((b) =>
      `<td>${b.hausverbrauch ? `${this._fmt(b[key], digits)} ${unit}` : "–"}</td>`).join("")}</tr>`).join("")
      + `<tr><td>Autarkiegrad</td>${cols.map((b) => `<td>${this._pct(b.autarkiegrad)}</td>`).join("")}</tr>`
      + `<tr><td>Eigenverbrauchsquote</td>${cols.map((b) => `<td>${this._pct(b.eigenverbrauchsquote)}</td>`).join("")}</tr>`;
    const n = r.nulleinspeisung;
    return `<div class="pager noprint"><button data-set="_monat=${month(r.zurueck)}">← zurück</button><b>Monatsbericht ${r.monat}</b>
        <button ${r.weiter ? `data-set="_monat=${month(r.weiter)}"` : "disabled"}>weiter →</button>
        <button onclick="window.print()">Drucken</button></div>
      <h2>Bilanz</h2><div class="card"><table><tr><th></th><th>${r.monat}</th><th>Vormonat</th><th>Vorjahresmonat</th></tr>${table}</table>
        ${r.erwartet ? `<p class="label">Erwartete Erzeugung laut PVGIS: ${this._fmt(r.erwartet)} kWh, erreicht: ${this._pct(r.bilanz.erzeugung / r.erwartet)}.</p>` : ""}</div>
      <h2>Tageswerte</h2><div class="card">${this._chart(r.tage)}</div>
      <h2>Akku</h2><div class="grid">
        ${this._box("Vollzyklen", this._fmt(r.akku.zyklen))}${this._box("Wirkungsgrad", this._pct(r.akku.wirkungsgrad))}
        ${this._box("Stunden voll / leer", `${r.akku.stunden_voll} / ${r.akku.stunden_leer}`)}${this._box("Gesundheit (SoH)", `${this._fmt(r.akku.gesundheit, 0)} %`)}</div>
      ${n ? `<h2>Nulleinspeisung</h2><div class="grid">
        ${this._box("Regelbereit", `${this._fmt(n.regelbereit_stunden, 0)} h`, `an ${n.tage} Tagen`)}${this._box("Davon nahe 0 W", this._pct(n.anteil_nahe_null))}
        ${this._box("Vermeidbarer Netzbezug", `${this._fmt(n.vermeidbarer_netzbezug)} kWh`, `${this._fmt(n.vermeidbare_kosten, 2)} €`)}
        ${this._box("Abgabe über Limit", this._pct(n.anteil_ueber_limit), `höchster Wert ${this._fmt(n.max_abgabe, 0)} W`)}</div>` : ""}`;
  }
}

if (!customElements.get("balkonaut-panel")) customElements.define("balkonaut-panel", BalkonautPanel);
