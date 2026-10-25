// Balkonaut-Karte für Lovelace: Energiefluss und Akku-Ring im Leitwarten-Design.
// Live-Werte kommen im eigenständigen Betrieb direkt aus den zugeordneten Entitäten, alles Berechnete
// (Bilanz von heute) über den WebSocket-Befehl balkonaut/status. Keine Abhängigkeiten, kein Build-Schritt.

const ICONS = {
  panel: '<rect x="2" y="4" width="20" height="12" rx="1"/><path d="M2 10h20M8.7 4v12M15.3 4v12M12 16v4M8 20h8"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>',
  batt: '<path d="M15 7h1a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2h-2"/><path d="M6 7H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h1"/><path d="m11 7-3 5h4l-3 5"/><path d="M22 11v2"/>',
  home: '<path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/><path d="M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  pole: '<path d="M12 2v20M2 5h20M3 3v2M7 3v2M17 3v2M21 3v2"/><path d="m19 5-7 7-7-7"/>',
};
const UNITS = { kW: 1000, Wh: 0.001 }; // wie core/homeassistant.py
// Texte aus Optionen und Geräteregister kommen ins HTML, daher maskieren
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

const STYLE = `
  :host { --bk-sun: #f2b733; --bk-leaf: #3fa66b; --bk-sky: #4a8fd0; --bk-batt: #14b8a6;
    --bk-lo: #e5484d; --bk-prot: #f59e0b; --bk-line: var(--divider-color, #c4cfdd);
    --bk-ink: var(--primary-text-color, #0f1d30); --bk-muted: var(--secondary-text-color, #4f5e73);
    --bk-bg: var(--ha-card-background, var(--card-background-color, #fff));
    --bk-mono: ui-monospace, "SF Mono", "JetBrains Mono", Menlo, Consolas, monospace; }
  ha-card { padding: 16px; }
  .head { display: flex; justify-content: space-between; align-items: center; font: 600 12px var(--bk-mono);
    text-transform: uppercase; letter-spacing: .08em; color: var(--bk-muted); }
  .flow { display: block; width: 100%; max-width: 520px; height: auto; margin: 8px auto; }  /* breit nicht riesig */
  .lane { fill: none; stroke: color-mix(in srgb, var(--bk-muted) 30%, transparent); }  /* ruhend, in hell und dunkel sichtbar */
  .pulse { fill: none; stroke: currentColor; stroke-dasharray: 8 16; animation: run 2s linear infinite;
    filter: drop-shadow(0 0 4px currentColor); }
  .pulse.rev { animation-direction: reverse; }
  @keyframes run { to { stroke-dashoffset: -24; } }
  .node > rect:first-child { fill: var(--bk-bg); stroke-width: 1.5; }
  .node .ico { fill: none; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
  .lbl { font: 600 11px var(--bk-mono); fill: var(--bk-muted); text-transform: uppercase; letter-spacing: .03em; }
  .w { font: 700 19px var(--bk-mono); fill: var(--bk-ink); }
  .hub rect { fill: color-mix(in srgb, var(--bk-sun) 18%, var(--bk-bg)); stroke: var(--bk-sun); stroke-width: 1.5; }
  .hub text { font: 700 11px var(--bk-mono); fill: var(--bk-ink); text-anchor: middle; letter-spacing: .06em; }
  .row { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
  .ring { flex: none; width: 96px; height: 96px; transform: rotate(-90deg); }
  .ring circle { fill: none; stroke-width: 10; }
  .val { font: 600 28px var(--bk-mono); letter-spacing: -.04em; color: var(--bk-ink); }
  .unit { font-size: .55em; color: var(--bk-muted); margin-left: 4px; }
  .sub { font-size: 14px; color: var(--bk-muted); }
  .key { display: flex; flex-wrap: wrap; gap: 4px 12px; margin-top: 8px; font-size: 12px; color: var(--bk-muted); }
  .key i { display: inline-block; width: 3px; height: 12px; margin-right: 5px; vertical-align: -2px; }
  .stats { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 16px; padding-top: 12px;
    border-top: 1px solid var(--bk-line); }
  .stats .lab { font: 600 11px var(--bk-mono); text-transform: uppercase; letter-spacing: .08em; color: var(--bk-muted); }
  @media (prefers-reduced-motion: reduce) { .pulse { animation: none; } }
`;

class BalkonautCard extends HTMLElement {
  setConfig(config) {
    this._config = config || {};
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._data && !this._loading) this._load();
    this._render();
  }

  connectedCallback() {
    this._timer = setInterval(() => this._load(), 10000); // wie die Messung
  }

  disconnectedCallback() {
    clearInterval(this._timer);
  }

  getCardSize() {
    return 7;
  }

  // Abschnittsansicht: volle Breite, damit der Energiefluss lesbar bleibt; mindestens eine halbe Spalte
  getGridOptions() {
    return { columns: 12, min_columns: 6 };
  }

  static getStubConfig() {
    return {};
  }

  async _load() {
    if (!this._hass) return;
    this._loading = true;
    try {
      const msg = { type: "balkonaut/status" };
      if (this._config.entry_id) msg.entry_id = this._config.entry_id;
      this._data = await this._hass.callWS(msg);
      this._error = null;
    } catch (err) {
      this._error = err.message || String(err);
    }
    this._loading = false;
    this._last = null;
    this._render();
  }

  // Messgröße in W bzw. %: im eigenständigen Betrieb live aus der Entität, sonst aus dem letzten Status
  _value(key) {
    const d = this._data;
    if (!d.entities) { // App: nur echte Zahlen, die Werte landen auch in SVG-Attributen
      const v = Number(d.status?.live?.[key] ?? NaN);
      return Number.isFinite(v) ? v : null;
    }
    const state = d.entities[key] && this._hass.states[d.entities[key]];
    const v = state ? parseFloat(state.state) : NaN;
    if (Number.isNaN(v)) return null;
    return v * (UNITS[state.attributes.unit_of_measurement] || 1) * (d.invert.includes(key) ? -1 : 1);
  }

  _fmt(v, digits = 0) {
    if (v === null || v === undefined || Number.isNaN(v)) return "–";
    return esc(v.toLocaleString(this._hass.locale?.language || "de", { minimumFractionDigits: digits, maximumFractionDigits: digits }));
  }

  _render() {
    if (!this._hass) return;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    if (!this._data) {
      this.shadowRoot.innerHTML = `<style>${STYLE}</style><ha-card><div class="sub">${
        this._error ? `Balkonaut nicht verfügbar: ${esc(this._error)}` : "Balkonaut lädt …"}</div></ha-card>`;
      return;
    }
    const keys = ["pv_power", "pv_ac_power", "battery_power", "battery_soc", "output_power", "grid_power",
      "battery_soc_min", "battery_soc_max", "battery_discharge_protection", "battery_capacity"];
    const v = Object.fromEntries(keys.map((k) => [k, this._value(k)]));
    const sig = JSON.stringify(v);
    if (sig === this._last) return; // nur neu zeichnen, wenn sich ein Wert geändert hat
    this._last = sig;
    this.shadowRoot.innerHTML = `<style>${STYLE}</style><ha-card>${this._flow(v)}${this._battery(v)}${this._stats()}</ha-card>`;
  }

  _line(d, watts, color, reverse = false) {
    const a = Math.abs(watts || 0);
    const width = (2 + Math.min(8, a / 80)).toFixed(1);
    const dur = Math.max(0.5, 2.4 - a / 400).toFixed(2);
    return `<path class="lane" d="${d}" stroke-width="${width}"/>` + (a >= 5
      ? `<path class="pulse${reverse ? " rev" : ""}" d="${d}" stroke-width="${width}" style="color:${color};animation-duration:${dur}s"/>`
      : "");
  }

  _node(x, y, color, label, watts, icon, extra = "") {
    return `<g class="node" transform="translate(${x} ${y})"><rect width="120" height="56" rx="6" stroke="${color}"/>
      <text class="lbl" x="10" y="19">${label}</text>
      <svg x="100" y="7" width="16" height="16" viewBox="0 0 24 24" class="ico" stroke="${color}">${ICONS[icon]}</svg>
      <text class="w" x="10" y="41">${this._fmt(watts === null ? null : Math.abs(watts))} W</text>${extra}</g>`;
  }

  _gauge(v) {
    const soc = v.battery_soc;
    if (soc === null) return null;
    const lo = v.battery_soc_min ?? 0, hi = v.battery_soc_max ?? 100;
    const share = hi > lo ? (soc - lo) / (hi - lo) : 1;
    const marks = [["lo", v.battery_soc_min, "Minimum"], ["prot", v.battery_discharge_protection, "Entladeschutz"],
      ["hi", v.battery_soc_max, "Maximum"]].filter(([, p]) => p !== null);
    // Restzeit bis zur Ober- bzw. Untergrenze bei gleichbleibender Leistung, ohne Wandlungsverluste
    const power = v.battery_power || 0, cap = v.battery_capacity;
    const target = power > 0 ? hi : Math.max(lo, v.battery_discharge_protection ?? 0);
    let rest = null;
    if (cap && Math.abs(power) >= 20 && (target - soc) * power > 0) {
      const minutes = Math.round(((target - soc) / 100) * cap * 60000 / power);
      if (minutes <= 48 * 60) rest = { target, minutes };
    }
    return { soc, lo, hi, marks, rest, hue: Math.round(Math.min(Math.max(share, 0), 1) * 130) };
  }

  _flow(v) {
    const pvAc = v.pv_ac_power, batt = v.battery_power, grid = v.grid_power;
    const pv = (v.pv_power ?? 0) + (pvAc ?? 0);
    const house = v.output_power !== null && grid !== null ? v.output_power + grid : null;
    const g = this._gauge(v);
    const color = (k) => ({ lo: "var(--bk-lo)", prot: "var(--bk-prot)", hi: "var(--bk-leaf)" })[k];
    const meter = g ? `<rect x="10" y="47" width="100" height="3" fill="var(--bk-line)"/>
      <rect x="10" y="47" width="${g.lo}" height="3" fill="var(--bk-muted)" fill-opacity=".45"/>
      <rect x="${10 + g.hi}" y="47" width="${100 - g.hi}" height="3" fill="var(--bk-muted)" fill-opacity=".45"/>
      <rect x="10" y="47" width="${Math.min(g.soc, 100)}" height="3" fill="hsl(${g.hue} 70% 48%)"/>
      ${g.marks.map(([k, p]) => `<rect x="${9 + p}" y="43" width="2" height="11" fill="${color(k)}"/>`).join("")}` : "";
    const names = this._data.names || {};
    const battName = esc((names.battery || "Akku").slice(0, 10)), hubName = esc((names.hub || "Wechselrichter").slice(0, 14));
    const extraName = esc((names.extra || "Zusatz-WR").slice(0, 14));
    const modules = (k) => esc((names.modules?.[k] || "Module").slice(0, 14));
    const battLabel = (batt || 0) > 5 ? `${battName} lädt` : (batt || 0) < -5 ? `${battName} entlädt` : battName;
    // Module oben, je Wechselrichter ein Feld mit gemeinsamer Leistung (Werte je Modul liefern die Geräte nicht)
    const pvPart = pvAc === null
      ? this._line("M200 66 V222", pv, "var(--bk-sun)") + this._node(140, 10, "var(--bk-sun)", modules("storage"), pv, "panel")
      : this._line("M100 66 V182 H190 V222", v.pv_power, "var(--bk-sun)") + this._line("M300 66 V88", pvAc, "var(--bk-sun)")
        + this._line("M300 144 V182 H210 V222", pvAc, "var(--bk-sun)")
        + this._node(40, 10, "var(--bk-sun)", modules("storage"), v.pv_power, "panel") + this._node(240, 10, "var(--bk-sun)", modules("extra"), pvAc, "panel")
        + this._node(240, 88, "var(--bk-sun)", extraName, pvAc, "sun");
    return `<div class="head"><span>${esc(this._config.title ?? "Energiefluss jetzt")}</span></div>
      <svg class="flow" viewBox="0 0 400 407" role="img"
        aria-label="Sonne ${this._fmt(pv)} W, Akku ${this._fmt(batt)} W, Haus ${this._fmt(house)} W, Netz ${this._fmt(grid)} W">
        ${this._line("M150 242 H124", batt, "var(--bk-batt)", (batt || 0) < 0)}
        ${this._line("M250 242 H276", house, "var(--bk-leaf)")}
        ${this._line("M200 262 V341", grid, "var(--bk-sky)", (grid || 0) > 0)}
        ${pvPart}
        <g class="hub"><rect x="150" y="222" width="100" height="40" rx="4"/><text x="200" y="246">${hubName}</text></g>
        ${this._node(4, 214, "var(--bk-batt)", battLabel, batt, "batt", meter)}
        ${this._node(276, 214, "var(--bk-leaf)", "Haus", house, "home")}
        ${this._node(140, 341, "var(--bk-sky)", (grid || 0) < -5 ? "Einspeisung" : "Netzbezug", grid, "pole")}
      </svg>`;
  }

  _battery(v) {
    const g = this._gauge(v);
    if (!g) return "";
    const C = 2.639, batt = v.battery_power || 0;
    const color = (k) => ({ lo: "var(--bk-lo)", prot: "var(--bk-prot)", hi: "var(--bk-leaf)" })[k];
    const ticks = g.marks.map(([k, p]) => {
      const a = (p / 100) * 2 * Math.PI, c = Math.cos(a), s = Math.sin(a);
      return `<line x1="${50 + 34 * c}" y1="${50 + 34 * s}" x2="${50 + 50 * c}" y2="${50 + 50 * s}" stroke="${color(k)}" stroke-width="3"/>`;
    }).join("");
    const state = batt > 5 ? "lädt" : batt < -5 ? "entlädt" : "ruht";
    const m = g.rest?.minutes;
    return `<div class="row">
      <svg class="ring" viewBox="0 0 100 100" role="img" aria-label="Ladestand ${this._fmt(g.soc)} %">
        <circle cx="50" cy="50" r="42" stroke="var(--bk-line)"/>
        <circle cx="50" cy="50" r="42" stroke="var(--bk-muted)" stroke-opacity=".4" stroke-dasharray="${g.lo * C} 264"/>
        <circle cx="50" cy="50" r="42" stroke="var(--bk-muted)" stroke-opacity=".4" stroke-dasharray="0 ${g.hi * C} ${(100 - g.hi) * C} 264"/>
        <circle cx="50" cy="50" r="42" stroke="hsl(${g.hue} 70% 48%)" stroke-dasharray="${Math.min(g.soc, 100) * C} 264"/>
        <circle cx="50" cy="50" r="42" stroke="var(--bk-bg)" stroke-width="12" stroke-dasharray="2 11.2"/>${ticks}
      </svg>
      <div><div class="val">${this._fmt(g.soc)}<span class="unit">%</span></div>
        <div class="sub">${state}${Math.abs(batt) > 5 ? ` mit ${this._fmt(Math.abs(batt))} W` : ""}</div>
        ${g.rest ? `<div class="sub">${this._fmt(g.rest.target)} % in ca. ${m >= 60 ? `${Math.floor(m / 60)} h ` : ""}${m % 60} min</div>` : ""}</div>
    </div>
    ${g.marks.length ? `<div class="key">${g.marks.map(([k, p, name]) =>
      `<span><i style="background:${color(k)}"></i>${name} ${this._fmt(p)} %</span>`).join("")}</div>` : ""}`;
  }

  _stats() {
    const today = this._data.status?.bilanz?.tag;
    if (!today) return "";
    const pct = today.autarkiegrad === null ? null : today.autarkiegrad * 100;
    return `<div class="stats">
      <div><div class="lab">Heute gespart</div><div class="val">${this._fmt(today.ersparnis, 2)}<span class="unit">€</span></div></div>
      <div><div class="lab">Autarkie heute</div><div class="val">${this._fmt(pct)}<span class="unit">%</span></div></div>
    </div>`;
  }
}

if (!customElements.get("balkonaut-card")) {
  customElements.define("balkonaut-card", BalkonautCard);
  window.customCards = window.customCards || [];
  window.customCards.push({ type: "balkonaut-card", name: "Balkonaut", description: "Energiefluss und Akku-Ring", preview: true });
}
