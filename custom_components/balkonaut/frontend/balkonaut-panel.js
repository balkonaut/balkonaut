// Balkonaut-Panel in der Seitenleiste: Übersicht, Verlauf, Nulleinspeisung und Monatsbericht wie in der Docker-App.
// Daten über die WebSocket-Befehle balkonaut/status, /verlauf, /bericht, /nulleinspeisung; die Übersicht nutzt die
// Karte balkonaut-card, die die Integration global lädt. Keine Abhängigkeiten, kein Build-Schritt.

const TABS = [["start", "Übersicht"], ["verlauf", "Verlauf"], ["nulleinspeisung", "Nulleinspeisung"], ["bericht", "Bericht"]];
const PERIODS = [["tag", "Heute"], ["monat", "Monat"], ["jahr", "Jahr"], ["gesamt", "Gesamt"]];
const VIEWS = [["tag", "Tag"], ["woche", "Woche"], ["monat", "Monat"], ["jahr", "Jahr"]];
const HANDBUCH = "https://balkonaut.github.io/balkonaut/";
// Texte aus Antworten (auch der konfigurierten App) nie als HTML einsetzen
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

const PANEL_STYLE = `
  :host { display: block; min-height: 100%; background: var(--primary-background-color);
    --bk-sun: #f2b733; --bk-leaf: #3fa66b; --bk-batt: #0b84a5; --bk-sky: #4a8fd0; --bk-warn: #d9682f;
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
  .day .hit { fill: var(--bk-ink); opacity: 0; } .day:hover .hit, .day:focus-visible .hit { opacity: .08; }
  .legend { display: flex; flex-wrap: wrap; gap: 16px; font-size: 14px; color: var(--bk-muted); margin-top: 8px; }
  .legend i { display: inline-block; width: 12px; height: 12px; border-radius: 1px; margin-right: 6px; vertical-align: -1px; }
  .bar { height: 10px; background: var(--bk-line); border-radius: 2px; overflow: hidden; margin: 8px 0 16px; }
  .bar span { display: block; height: 100%; background: var(--bk-leaf); }
  table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
  th, td { padding: 6px 8px; border-bottom: 1px solid var(--bk-line); text-align: right; }
  th:first-child, td:first-child { text-align: left; }
  .ways { display: grid; gap: 24px; grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr)); }
  .ways .head { display: flex; align-items: baseline; font-weight: 600; margin-bottom: 6px; }
  .ways .head b, .ways .row b { margin-left: auto; font: 600 18px var(--bk-mono); font-variant-numeric: tabular-nums; }
  .ways .head b { font-size: 26px; letter-spacing: -.04em; }
  .ways .row { display: grid; grid-template-columns: 1fr auto; gap: 2px 12px; align-items: baseline; padding: 6px 0 6px 16px; border-top: 1px solid var(--bk-line); }
  .ways .row i { grid-column: 1 / -1; height: 6px; border-radius: 3px; background: var(--bk-line); overflow: hidden; display: block; }
  .ways .row i span { display: block; height: 100%; }
  .setup { margin-bottom: 16px; }
  .setup .head { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 16px; }
  .setup .head b { font-size: 1.1rem; }
  .setup .bar { height: 6px; border-radius: 3px; }
  .setup .bar span { background: var(--bk-sun); }
  .setup ol { list-style: none; margin: 0; padding: 0; display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr)); }
  .setup li { display: flex; flex-direction: column; align-items: flex-start; gap: 10px; padding: 14px;
    border: 1px solid var(--bk-line); border-radius: 6px; }
  .setup li.next { border: 2px solid var(--bk-sun); }
  .setup .mark { width: 32px; height: 32px; border-radius: 50%; display: grid; place-items: center;
    font: 600 14px var(--bk-mono); border: 2px solid var(--bk-line); color: var(--bk-muted); }
  .setup .done .mark { background: var(--bk-leaf); border-color: var(--bk-leaf); color: var(--bk-card); }
  .setup .next .mark { border-color: var(--bk-sun); color: var(--bk-ink); }
  .setup .done b { color: var(--bk-muted); }
  .setup li span { color: var(--bk-muted); font-size: 14px; }
  .setup a { display: inline-flex; align-items: center; min-height: 44px; padding: 0 18px; border-radius: 6px; text-decoration: none;
    font-weight: 600; border: 1px solid var(--bk-line); color: var(--bk-ink); margin-top: auto; }
  .setup .next a { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: var(--primary-color); }
  .card:has(> .info) { position: relative; } .card:has(> .info) > .label:first-child { padding-right: 40px; overflow-wrap: anywhere; }
  .info { position: absolute; top: 12px; right: 12px; width: 32px; height: 32px; border-radius: 50%; border: 1px solid var(--bk-line);
    background: var(--bk-card); color: var(--bk-muted); font: 600 14px/1 var(--bk-mono); cursor: pointer;
    display: grid; place-items: center; padding: 0; }
  .info[aria-expanded="true"] { background: var(--bk-ink); color: var(--bk-card); }
  .hilfe { font-size: 14px; color: var(--bk-muted); margin: 8px 0 0; line-height: 1.4; }
  .grid > .card:has(> .info) { display: grid; grid-row: span 2; grid-template-rows: subgrid; row-gap: 4px; align-content: start; }
  .grid > .card:has(> .info) > .label:first-child { align-self: end; }
  .k-body { display: flex; flex-direction: column; } .q-wrap { margin-top: auto; }  /* Skala unten: in einer Reihe auf einer Linie */
  .q-badge { display: inline-block; vertical-align: middle; font: 600 11px var(--bk-mono); letter-spacing: .06em; text-transform: uppercase;
    padding: 2px 8px; border-radius: 999px; background: var(--q); color: #fff; }
  .q-scale { position: relative; height: 8px; border-radius: 4px; margin: 8px 0 4px;
    background: linear-gradient(90deg, hsl(0 60% 45%), hsl(45 75% 45%), hsl(130 55% 42%)); }
  .q-scale i { position: absolute; top: -4px; width: 4px; height: 16px; border-radius: 2px; background: var(--bk-ink); transform: translateX(-2px); }
  .q-ends { display: flex; justify-content: space-between; gap: 8px; font-size: 12px; color: var(--bk-muted); line-height: 1.3; } .q-ends span:last-child { text-align: right; }
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

  // Kachel mit Erklärung (Knopf i) und, wo es eine Bewertung gibt, Skala von rot (links) bis grün, wie app/templates/_kachel.html
  _kachel(bereich, key, label, value, raw = null, sub = "") {
    const [text, good, bad, goodText, badText] = this._kacheln?.[bereich]?.[key] || [""];
    const s = good === undefined || typeof raw !== "number" ? null : Math.min(Math.max((raw - bad) / (good - bad), 0), 1);
    const id = `hilfe-${bereich}-${key}`, nb = (t) => esc(t).replaceAll(" ", "&nbsp;");
    const badge = s === null ? "" : `<div><span class="q-badge" style="--q:hsl(${Math.round(s * 130)} 60% 42%)">${
      s >= 0.67 ? "gut" : s >= 0.34 ? "mittel" : "schwach"}</span></div>`;
    const scale = s === null ? "" : `<div class="q-wrap" aria-hidden="true"><div class="q-scale"><i style="left:${(s * 100).toFixed(1)}%"></i></div>
      <div class="q-ends"><span>schlecht<br>${nb(badText)}</span><span>gut<br>${nb(goodText)}</span></div></div>`;
    return `<div class="card"><div class="label">${esc(label)}</div>${text ? `<button class="info" type="button" aria-expanded="false"
      aria-controls="${id}" aria-label="Erklärung zu ${esc(label)}">i</button>` : ""}<div class="k-body"><div class="value">${esc(value)}</div>${badge}
      ${sub ? `<div class="label">${esc(sub)}</div>` : ""}${scale}${text ? `<p class="hilfe" id="${id}" hidden>${esc(text)}</p>` : ""}</div></div>`;
  }

  async _ws(type, extra = {}) {
    return this._hass.callWS({ type: `balkonaut/${type}`, ...extra });
  }

  async _show(tab) {
    this._tab = tab;
    const seq = this._seq = (this._seq || 0) + 1; // nur die Antwort des letzten Klicks zeigen
    let body;
    try {
      this._kacheln ??= await this._ws("kacheln");
      if (tab === "start") body = this._start(await this._ws("status"), await this._ws("verlauf", { ansicht: "tag" }));
      else if (tab === "verlauf") body = this._history(await this._ws("verlauf", { ansicht: this._view, datum: this._datum }));
      else if (tab === "nulleinspeisung") body = this._regulation(await this._ws("nulleinspeisung"));
      else body = this._report(await this._ws("bericht", { monat: this._monat }));
    } catch (err) {
      body = `<p class="note">Balkonaut ist nicht verfügbar: ${esc(err.message || err)}</p>`;
    }
    if (seq === this._seq) this._render(body);
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
    this.shadowRoot.querySelectorAll(".info").forEach((b) => b.addEventListener("click", () => {
      const open = b.getAttribute("aria-expanded") !== "true";
      b.setAttribute("aria-expanded", open);
      this.shadowRoot.getElementById(b.getAttribute("aria-controls")).hidden = !open;
    }));
    this.shadowRoot.querySelectorAll("[data-tab]").forEach((b) => b.addEventListener("click", () => this._show(b.dataset.tab)));
    this.shadowRoot.querySelectorAll("[data-day]").forEach((a) => a.addEventListener("click", (e) => {
      e.preventDefault();
      [this._view, this._datum] = ["tag", a.dataset.day];
      this._show("verlauf");
    }));
    this.shadowRoot.querySelectorAll("[data-set]").forEach((b) => b.addEventListener("click", () => {
      const [key, value] = b.dataset.set.split("=");
      this[key] = value;
      if (key === "_view") this._datum = "";
      this._show(this._tab);
    }));
  }

  // Balkendiagramm wie app/templates/_chart.html: Eigenverbrauch grün, Netzbezug blau, Erzeugung gelber Strich
  _chart(bars, dayLink = false) {  // dayLink: jeder Balken öffnet den Tag im Verlauf
    const n = bars.length, left = 36, w = (480 - left) / Math.max(n, 1), every = Math.ceil(n / 12);
    const peak = Math.max(0, ...bars.map((b) => Math.max(b.own, b.grid, b.gen, b.fc || 0)));
    let ticks = [], scale = 0;
    if (peak) {
      const raw = peak / 12, mag = 10 ** Math.floor(Math.log10(raw));  // höchstens 12 beschriftete Hilfslinien
      const step = [1, 2, 5, 10].map((m) => m * mag).find((s) => s >= raw);
      const digits = Math.max(0, -Math.floor(Math.log10(step)));
      // dazwischen je eine blasse Linie ohne Zahl, z. B. Zahlen alle 0,2, Linien alle 0,1
      for (let i = 1; i * step / 2 <= peak + 1e-9; i++) ticks.push([i * step / 2, i % 2 ? "" : this._fmt(i * step / 2, digits)]);
      scale = 140 / peak;
    }
    const grid = ticks.map(([v, l]) => `<line x1="${left}" x2="480" y1="${150 - v * scale}" y2="${150 - v * scale}" stroke="var(--bk-line)"${l ? "" : ` stroke-opacity=".45"`}/>
      ${l ? `<text x="${left - 4}" y="${153 - v * scale}" font-size="9" text-anchor="end" fill="var(--bk-muted)">${l}</text>` : ""}`).join("");
    // je Abschnitt Balkonkraftwerk und Netz nebeneinander, Erzeugung als gelber Strich darüber, wie app/templates/_chart.html
    const cols = bars.map((h, i) => {
      const x = left + i * w;
      return `${dayLink ? `<a class="day" href="#" data-day="${esc(h.datum)}" aria-label="${esc(h.datum)} im Verlauf öffnen"><rect class="hit" x="${x}" y="0" width="${w}" height="150"/>` : ""}<rect x="${x + w * 0.1}" y="${150 - h.own * scale}" width="${w * 0.38}" height="${h.own * scale}" fill="var(--bk-leaf)"><title>${esc(h.label)}: ${this._fmt(h.own, 2)} kWh vom Balkonkraftwerk</title></rect>
        <rect x="${x + w * 0.52}" y="${150 - h.grid * scale}" width="${w * 0.38}" height="${h.grid * scale}" fill="var(--bk-sky)"><title>${esc(h.label)}: ${this._fmt(h.grid, 2)} kWh aus dem Netz</title></rect>
        ${h.gen ? `<rect x="${x + w * 0.1}" y="${149 - h.gen * scale}" width="${w * 0.8}" height="3" fill="var(--bk-sun)"><title>${esc(h.label)}: ${this._fmt(h.gen, 2)} kWh erzeugt</title></rect>` : ""}
        ${dayLink ? "</a>" : ""}${i % every === 0 ? `<text x="${x + w * 0.5}" y="166" font-size="10" text-anchor="middle" fill="var(--bk-muted)">${esc(h.label)}</text>` : ""}`;
    }).join("");
    const fc = bars.some((b) => typeof b.fc === "number" && b.fc > 0);
    const line = fc ? `<polyline points="${bars.map((b, i) => `${(left + (i + 0.5) * w).toFixed(1)},${(150 - (Number(b.fc) || 0) * scale).toFixed(1)}`).join(" ")}"
      fill="none" stroke="var(--bk-sun)" stroke-width="1.5" stroke-dasharray="4 3"><title>Erwartete Erzeugung laut Forecast.Solar</title></polyline>` : "";
    const help = this._kacheln?.diagramm?.herkunft?.[0];
    return `${help ? `<button class="info" type="button" aria-expanded="false" aria-controls="hilfe-diagramm" aria-label="Erklärung zum Diagramm">i</button>` : ""}
      <svg class="chart" viewBox="0 0 480 170" role="img" aria-label="Hausverbrauch je Zeitabschnitt: Balkonkraftwerk und Netz, mit Erzeugung${fc ? " und Prognose" : ""}">
      <text x="0" y="8" font-size="9" fill="var(--bk-muted)">kWh</text>${grid}
      <line x1="${left}" x2="480" y1="150" y2="150" stroke="var(--bk-muted)"/>${cols}${line}</svg>
      <div class="legend"><span><i style="background:var(--bk-leaf)"></i>Balkonkraftwerk</span><span><i style="background:var(--bk-sky)"></i>Netz</span>
      <span><i style="background:var(--bk-sun);height:4px;vertical-align:3px"></i>Erzeugung</span>${fc ? `<span><i style="background:none;height:0;border-top:2px dashed var(--bk-sun);vertical-align:3px"></i>Prognose</span>` : ""}</div>
      ${help ? `<p class="hilfe" id="hilfe-diagramm" hidden>${esc(help)}</p>` : ""}`;
  }

  _balance(b) {
    const k = (key, label, value, raw) => this._kachel("bilanz", key, label, value, raw);
    return `<div class="grid">${k("ersparnis", "Ersparnis", `${this._fmt(b.ersparnis, 2)} €`)}${k("eigenverbrauch", "Eigenverbrauch", `${this._fmt(b.eigenverbrauch)} kWh`)}
      ${k("autarkiegrad", "Autarkiegrad", this._pct(b.autarkiegrad))}${k("eigenverbrauchsquote", "Eigenverbrauchsquote", this._pct(b.eigenverbrauchsquote), b.eigenverbrauchsquote)}
      ${k("erzeugung", "Erzeugung", `${this._fmt(b.erzeugung)} kWh`)}${k("hausverbrauch", "Hausverbrauch", `${this._fmt(b.hausverbrauch)} kWh`)}
      ${k("netzbezug", "Netzbezug", `${this._fmt(b.netzbezug)} kWh`)}${k("einspeisung", "Einspeisung", `${this._fmt(b.einspeisung)} kWh`)}</div>`;
  }

  _ways(b, k) {
    const row = (name, v, total, color) => `<div class="row"><span>${name}</span><b>${this._fmt(v)} kWh</b><i><span style="width:${
      v && total ? Math.round((v / total) * 100) : 0}%;background:var(--bk-${color})"></span></i></div>`;
    const lost = k.entladen_ins_haus == null ? null : k.entladen - k.entladen_ins_haus;
    return `<div class="card ways"><div><div class="head">Sonne erzeugt<b>${this._fmt(b.erzeugung)} kWh</b></div>
      ${row("direkt ins Haus", k.direkt_ins_haus, b.erzeugung, "leaf")}${row("in den Akku geladen", k.geladen, b.erzeugung, "batt")}
      ${row("eingespeist", b.einspeisung, b.erzeugung, "sky")}</div>
      <div><div class="head">Akku entladen<b>${this._fmt(k.entladen)} kWh</b></div>
      ${row("davon im Haus angekommen", k.entladen_ins_haus, k.entladen, "leaf")}${row("Verluste und Netz", lost, k.entladen, "muted")}</div></div>`;
  }

  // Kachel Einrichtung wie in der Docker-App, solange ein Pflichtschritt fehlt; die Inbetriebnahme ist nur empfohlen
  _setup(setup) {
    if (!setup) return "";
    const steps = [
      ["messgroessen", "Messgrößen zuordnen", "Netz, Abgabe, Erzeugung und Ladestand, sonst bleibt die Bilanz leer. Unter ⋮ → Neu konfigurieren."],
      ["prognose", "Prognose", "Forecast.Solar-Entität zuordnen oder eine Fläche eintragen, für den Ertragswächter. Unter Konfigurieren."],
      ["preise", "Preise und Anlage", "Ohne Arbeitspreis und Anlagekosten stehen Ersparnis und Amortisation auf 0&nbsp;€. Unter Konfigurieren."],
      ["inbetriebnahme", "Datum der Inbetriebnahme", "Empfohlen: macht die Ersparnis pro Jahr genauer. Unter Konfigurieren.", true],
    ];
    const required = steps.filter(([, , , optional]) => !optional);
    const done = required.filter(([key]) => setup[key]).length;
    if (done === required.length) return "";
    const next = steps.find(([key]) => !setup[key])[0];
    const items = steps.map(([key, title, hint], i) => {
      const cls = setup[key] ? "done" : key === next ? "next" : "";
      return `<li class="${cls}"><span class="mark" aria-hidden="true">${setup[key] ? "✓" : i + 1}</span>
        <div><b>${title}</b><br><span>${setup[key] ? "Erledigt." : hint}</span></div>
        <a href="/config/integrations/integration/balkonaut">${setup[key] ? "Ändern" : key === next ? "Jetzt eintragen" : "Eintragen"}</a></li>`;
    }).join("");
    return `<section class="card setup"><div class="head"><b>Einrichtung</b><span class="label">${done} von ${required.length} erledigt</span></div>
      <div class="bar" role="progressbar" aria-valuemin="0" aria-valuemax="${required.length}" aria-valuenow="${done}" aria-label="Einrichtung">
      <span style="width:${Math.round((done / required.length) * 100)}%"></span></div><ol>${items}</ol></section>`;
  }

  _start(data, today) {
    const st = data.status, b = st.bilanz[this._period], k = st.akku[this._period], a = st.amortisation;
    const tabs = PERIODS.map(([key, name]) => `<button data-set="_period=${key}" class="${key === this._period ? "on" : ""}">${name}</button>`).join("");
    const progress = a.kosten ? Math.min((a.bisher_gespart / a.kosten) * 100, 100) : 0;
    const date = (iso) => iso ? new Date(iso).toLocaleDateString(this._hass.locale?.language || "de", { month: "2-digit", year: "numeric" }) : "–";
    return `${this._setup(data.setup)}${st.warnungen.map((w) => `<p class="note">${esc(w.text)}</p>`).join("")}
      <balkonaut-card></balkonaut-card>
      <h2>Bilanz</h2><div class="tabs">${tabs}</div>${this._balance(b)}
      <h2>Energiewege</h2>${this._ways(b, k)}
      <h2>Akku</h2><div class="grid">
        ${this._kachel("akku", "zyklen", "Vollzyklen im Zeitraum", this._fmt(k.zyklen), null, `gesamt ${this._fmt(k.zyklen_gesamt, 0)}${k.zyklen_pro_jahr ? `, ${this._fmt(k.zyklen_pro_jahr, 0)} pro Jahr` : ""}`)}
        ${this._kachel("akku", "gesundheit", "Gesundheit (SoH)", `${this._fmt(k.gesundheit, 0)} %`, null, `Kapazität ${this._fmt(k.kapazitaet, 2)} kWh`)}
        ${this._kachel("akku", "wirkungsgrad", "Wirkungsgrad Akku", this._pct(k.wirkungsgrad), k.wirkungsgrad)}
        ${this._kachel("akku", "verluste_wechselrichter", "Verluste Speicher-Wechselrichter", this._pct(k.verluste_wechselrichter), k.verluste_wechselrichter)}
        ${this._kachel("akku", "stunden_voll", "Stunden mit vollem Akku", k.stunden_voll ?? "–", null, `dabei eingespeist ${this._fmt(k.einspeisung_bei_vollem_akku)} kWh`)}
        ${this._kachel("akku", "stunden_leer", "Stunden mit leerem Akku", k.stunden_leer ?? "–", null, `dabei Netzbezug ${this._fmt(k.netzbezug_bei_leerem_akku)} kWh (${this._fmt(k.kosten_bei_leerem_akku, 2)} €)`)}</div>
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
      <div class="pager"><button data-set="_datum=${esc(d.zurueck)}">← zurück</button><b>${esc(d.titel)}</b>
        <button ${d.weiter ? `data-set="_datum=${esc(d.weiter)}"` : "disabled"}>weiter →</button></div>
      <div class="card">${this._chart(d.balken)}</div><h2>Bilanz</h2>${this._balance(d.bilanz)}`;
  }

  _regulation(r) {
    if (!r) return `<p class="note">Noch keine Messwerte.</p>`;
    return `<p class="label">Wie gut regelt der Speicher den Netzanschluss auf 0 W? Grundlage sind die Messwerte der letzten 7 Tage.
      Die Ergebnisse hängen an einer korrekten Netzmessung.</p>
      ${r.regelbereit_stunden < 1 ? `<p class="note">Der Speicher konnte im Zeitraum kaum nachregeln (Akku leer oder Abgabe am Limit). Die Werte sind deshalb wenig aussagekräftig.</p>` : ""}
      <div class="grid">
        ${this._kachel("nulleinspeisung", "regelbereit_stunden", "Regelbereit", `${this._fmt(r.regelbereit_stunden)} h`, null, `von ${this._fmt(r.zeitraum_stunden, 0)} h`)}
        ${this._kachel("nulleinspeisung", "anteil_nahe_null", "Davon nahe 0 W (±50 W)", this._pct(r.anteil_nahe_null), r.anteil_nahe_null)}
        ${this._kachel("nulleinspeisung", "median_netz", "Typische Netzleistung dabei", `${this._fmt(r.median_netz, 0)} W`,
          typeof r.median_netz === "number" ? Math.abs(r.median_netz) : null, "Median, + Bezug")}
        ${this._kachel("nulleinspeisung", "vermeidbarer_netzbezug", "Vermeidbarer Netzbezug", `${this._fmt(r.vermeidbarer_netzbezug, 2)} kWh`, r.vermeidbarer_netzbezug, `${this._fmt(r.vermeidbare_kosten, 2)} €`)}
        ${this._kachel("nulleinspeisung", "einspeisung", "Einspeisung", `${this._fmt(r.einspeisung, 2)} kWh`, r.einspeisung, `Wert bei Eigenverbrauch ${this._fmt(r.einspeisung_wert, 2)} €`)}
        ${this._kachel("nulleinspeisung", "lastspruenge", "Lastsprünge über 300 W", r.lastspruenge, null, `nicht ausgeregelt in 5 min: ${r.nicht_ausgeregelt}`)}
        ${this._kachel("nulleinspeisung", "reaktionszeit_median", "Reaktionszeit", `${this._fmt(r.reaktionszeit_median, 0)} s`, r.reaktionszeit_median, "Median bis zurück auf ±50 W")}
        ${this._kachel("nulleinspeisung", "anteil_ueber_limit", `Abgabe über Limit (${this._fmt(r.limit, 0)} W)`, this._pct(r.anteil_ueber_limit), r.anteil_ueber_limit, `höchster Wert ${this._fmt(r.max_abgabe, 0)} W`)}
      </div>${r.stunden ? `<div class="card" style="margin-top:.75rem">${this._hours(r.stunden)}</div>` : ""}`;
  }

  // Regelgüte nach Uhrzeit wie app/templates/_stunden.html: oben Anteil nahe 0 W als Farbfeld, unten vermeidbarer Netzbezug
  _hours(hours) {
    const left = 36, w = (480 - left) / 24, peak = Math.max(0, ...hours.map((h) => h.vermeidbarer_netzbezug));
    const [, good, bad] = this._kacheln?.nulleinspeisung?.anteil_nahe_null || [];
    const two = (n) => String(n).padStart(2, "0");
    const cols = hours.map((h, i) => {
      const x = left + i * w, a = h.anteil_nahe_null, s = a === null || good === undefined ? null : Math.min(Math.max((a - bad) / (good - bad), 0), 1);
      const tip = `<title>${two(h.stunde)}–${two((h.stunde + 1) % 24)} Uhr: ${s === null ? "nicht regelbereit"
        : `${this._fmt(h.regelbereit_stunden)} h regelbereit, davon ${this._pct(a)} nahe 0 W, vermeidbar ${this._fmt(h.vermeidbarer_netzbezug, 2)} kWh`}</title>`;
      const bh = peak ? h.vermeidbarer_netzbezug * 50 / peak : 0;
      return `<rect x="${x + 1}" y="6" width="${w - 2}" height="30" rx="3" ${s === null ? `fill="var(--bk-line)" fill-opacity=".4"` : `fill="hsl(${Math.round(s * 130)} 60% 42%)"`}>${tip}</rect>
        ${s === null ? "" : `<text x="${x + w * 0.5}" y="25" font-size="8" text-anchor="middle" fill="var(--bk-card)" font-family="var(--bk-mono)">${Math.round(a * 100)}</text>`}
        <rect x="${x + w * 0.2}" y="${100 - bh}" width="${w * 0.6}" height="${bh}" fill="var(--bk-sky)">${tip}</rect>
        ${i % 3 === 0 ? `<text x="${x + w * 0.5}" y="115" font-size="10" text-anchor="middle" fill="var(--bk-muted)">${h.stunde}</text>` : ""}`;
    }).join("");
    const help = this._kacheln?.diagramm?.uhrzeit?.[0];
    return `<div class="label">Nach Uhrzeit</div>${help ? `<button class="info" type="button" aria-expanded="false" aria-controls="hilfe-uhrzeit" aria-label="Erklärung zu Nach Uhrzeit">i</button>` : ""}
      <svg class="chart" viewBox="0 0 480 120" role="img" aria-label="Anteil nahe 0 W und vermeidbarer Netzbezug je Uhrzeit">
      <text x="0" y="24" font-size="9" fill="var(--bk-muted)" font-family="var(--bk-mono)">±50 W</text>
      <text x="0" y="84" font-size="9" fill="var(--bk-muted)" font-family="var(--bk-mono)">kWh</text>${cols}
      <line x1="${left}" x2="480" y1="100" y2="100" stroke="var(--bk-muted)"/></svg>
      <div class="legend"><span>oben: Anteil nahe 0 W in % (blass: nicht regelbereit)</span><span><i style="background:var(--bk-sky)"></i>vermeidbarer Netzbezug</span></div>
      ${help ? `<p class="hilfe" id="hilfe-uhrzeit" hidden>${esc(help)}</p>` : ""}`;
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
    return `<div class="pager noprint"><button data-set="_monat=${esc(month(r.zurueck))}">← zurück</button><b>Monatsbericht ${esc(r.monat)}</b>
        <button ${r.weiter ? `data-set="_monat=${esc(month(r.weiter))}"` : "disabled"}>weiter →</button>
        <button onclick="window.print()">Drucken</button></div>
      <h2>Bilanz</h2><div class="card"><table><tr><th></th><th>${esc(r.monat)}</th><th>Vormonat</th><th>Vorjahresmonat</th></tr>${table}</table></div>
      <h2>Tageswerte</h2><div class="card">${this._chart(r.tage, true)}<p class="label noprint">Ein Klick auf einen Tag öffnet ihn im Verlauf.</p></div>
      <h2>Akku</h2><div class="grid">
        ${this._kachel("akku", "zyklen", "Vollzyklen", this._fmt(r.akku.zyklen))}${this._kachel("akku", "wirkungsgrad", "Wirkungsgrad", this._pct(r.akku.wirkungsgrad), r.akku.wirkungsgrad)}
        ${this._kachel("akku", "stunden_voll", "Stunden mit vollem Akku", r.akku.stunden_voll ?? "–")}${this._kachel("akku", "stunden_leer", "Stunden mit leerem Akku", r.akku.stunden_leer ?? "–")}
        ${this._kachel("akku", "gesundheit", "Gesundheit (SoH)", `${this._fmt(r.akku.gesundheit, 0)} %`)}</div>
      ${n ? `<h2>Nulleinspeisung</h2><div class="grid">
        ${this._kachel("nulleinspeisung", "regelbereit_stunden", "Regelbereit", `${this._fmt(n.regelbereit_stunden, 0)} h`, null, `an ${n.tage} Tagen`)}
        ${this._kachel("nulleinspeisung", "anteil_nahe_null", "Davon nahe 0 W", this._pct(n.anteil_nahe_null), n.anteil_nahe_null)}
        ${this._kachel("nulleinspeisung", "vermeidbarer_netzbezug", "Vermeidbarer Netzbezug", `${this._fmt(n.vermeidbarer_netzbezug)} kWh`, null, `${this._fmt(n.vermeidbare_kosten, 2)} €`)}
        ${this._kachel("nulleinspeisung", "anteil_ueber_limit", "Abgabe über Limit", this._pct(n.anteil_ueber_limit), n.anteil_ueber_limit, `höchster Wert ${this._fmt(n.max_abgabe, 0)} W`)}</div>` : ""}`;
  }
}

if (!customElements.get("balkonaut-panel")) customElements.define("balkonaut-panel", BalkonautPanel);
