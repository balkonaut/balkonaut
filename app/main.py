import asyncio
import json
import logging
import math
import time
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import config
from balkonaut import analytics, collector, pvgis
from balkonaut.storage import Storage

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def de(value, digits=1):
    """Zahl im deutschen Format, fehlende Werte als Strich."""
    if not isinstance(value, (int, float)):
        return "–"
    return f"{value:,.{digits}f}".replace(",", " ").replace(".", ",").replace(" ", ".")


templates.env.filters.update(
    de=de,
    abs_de=lambda v, d=1: de(abs(v) if isinstance(v, (int, float)) else None, d),
    pct=lambda v: "–" if v is None else de(v * 100, 0) + " %",
    ago=lambda s: f"{s} s" if s < 120 else f"{s // 60} min" if s < 7200 else f"{s // 3600} h",
)
PERIODS = [("tag", "Heute"), ("monat", "Monat"), ("jahr", "Jahr"), ("gesamt", "Gesamt")]
VIEWS = [("tag", "Tag"), ("woche", "Woche"), ("monat", "Monat"), ("jahr", "Jahr")]


def parse_day(text, today):
    """Datum aus der Adresszeile, bei leerer oder ungültiger Angabe heute."""
    try:
        return date.fromisoformat(text) if text else today
    except ValueError:
        return today


def chart(bars):
    """Balken, Maßstab (Höhe 140 Einheiten) und Beschriftung der y-Achse in kWh für das SVG-Diagramm."""
    peak = max((max(b["own"] + b["grid"], b["gen"]) for b in bars), default=0)
    ticks = []
    if peak:
        raw = peak / 4  # etwa vier Hilfslinien mit runden Werten (1, 2, 5 × 10^n)
        mag = 10 ** math.floor(math.log10(raw))
        step = next(m * mag for m in (1, 2, 5, 10) if m * mag >= raw)
        digits = max(0, -math.floor(math.log10(step)))
        ticks = [(i * step, de(i * step, digits)) for i in range(1, int(peak / step + 1e-9) + 1)]
    return {"bars": bars, "scale": 140 / peak if peak else 0, "ticks": ticks}


log = logging.getLogger(__name__)


async def load_profile(app, adapter, cache):
    """Ertragsprofil (kWh je Monat) aus Forecast.Solar-Flächen und PVGIS, zwischengespeichert in cache."""
    old = json.loads(cache.read_text()) if cache.exists() else None
    try:
        lat, lon, planes = await asyncio.to_thread(adapter.solar_planes)
        key = {"lat": round(lat, 2), "lon": round(lon, 2), "planes": [list(p) for p in planes]}  # ~1 km genau
        if not planes or (old and old["key"] == key):
            app.state.profile = old["profile"] if old and planes else None
            return
        profile = await asyncio.to_thread(pvgis.monthly, key["lat"], key["lon"], planes)
        cache.write_text(json.dumps({"key": key, "profile": profile}))
        app.state.profile = profile
    except Exception as e:  # HA oder PVGIS nicht erreichbar: letztes bekanntes Profil nutzen
        log.warning("Ertragsprofil nicht aktualisiert: %s", e)
        app.state.profile = old["profile"] if old else None


@asynccontextmanager
async def lifespan(app):
    data = config.data_dir()
    data.mkdir(parents=True, exist_ok=True)
    app.state.config_path = data / "config.yaml"
    cfg = config.load(app.state.config_path)
    app.state.storage = Storage(data / "balkonaut.db")
    app.state.profile = None
    tasks = []
    if ha := cfg.get("home_assistant"):
        adapter = config.adapter(ha)
        tasks = [asyncio.create_task(collector.run(adapter, app.state.storage)),
                 asyncio.create_task(load_profile(app, adapter, data / "ertragsprofil.json"))]
    yield
    for task in tasks:
        task.cancel()


app = FastAPI(title="Balkonaut", lifespan=lifespan)
# Gebautes Handbuch (MkDocs), im Container unter /srv/handbuch
app.mount("/handbuch", StaticFiles(directory=Path(__file__).parent.parent / "handbuch", html=True, check_dir=False))


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/v1/status")
def api_status(request: Request):
    """Aktuelle Messwerte, Bilanz und Akku für heute, Monat, Jahr und gesamt sowie Amortisation.
    Felder: siehe Handbuch, Schnittstelle."""
    cfg = config.load(request.app.state.config_path)
    storage = request.app.state.storage
    now = time.time()
    rows = storage.hourly(int(now))
    latest = storage.latest()
    starts = analytics.periods(now)
    watch = analytics.yield_watch(rows, now)
    warnings = watch["warnungen"]
    if latest and now - max(ts for ts, _ in latest.values()) > 120:
        warnings = [{"code": "keine_messwerte", "text": "Seit über 2 Minuten keine Messwerte, Verbindung zu Home Assistant prüfen"}] + warnings
    return {
        "warnungen": warnings,
        "ertrag": watch["wechselrichter"],
        "stand": datetime.fromtimestamp(max(ts for ts, _ in latest.values()), analytics.TZ) if latest else None,
        "live": {k: v for k, (_, v) in latest.items()},
        "bilanz": {name: analytics.balance(rows, start, cfg["prices"]) for name, start in starts.items()},
        "akku": {name: analytics.battery(rows, start, cfg["prices"], config.commissioned(cfg))
                 for name, start in starts.items()},
        "amortisation": analytics.amortization(rows, cfg["prices"], cfg["system"]["cost"], config.commissioned(cfg),
                                               request.app.state.profile),
    }


@app.get("/api/v1/verlauf")
def api_history(request: Request, ansicht: str = "tag", datum: str = ""):
    """Balken einer Verlaufsansicht (tag, woche, monat, jahr) und Bilanz des Zeitraums."""
    return history_data(request, ansicht, datum)


def report_data(request, monat):
    cfg = config.load(request.app.state.config_path)
    today = datetime.now(analytics.TZ).date()
    day = parse_day(monat + "-01" if monat else "", today)
    rows = request.app.state.storage.hourly(int(time.time()))
    r = analytics.month_report(rows, day, cfg["prices"], time.time(), request.app.state.profile, config.commissioned(cfg))
    if r["weiter"] > today:
        r["weiter"] = None
    return r


@app.get("/api/v1/bericht")
def api_report(request: Request, monat: str = ""):
    """Monatsbericht (monat=JJJJ-MM, Standard: aktueller Monat)."""
    return report_data(request, monat)


@app.get("/bericht", include_in_schema=False)
def report(request: Request, monat: str = ""):
    r = report_data(request, monat)
    return templates.TemplateResponse(request, "report.html", {"r": r, "chart": chart(r["tage"])})


@app.get("/api/v1/nulleinspeisung")
def api_regulation(request: Request):
    """Regelgüte der Nulleinspeisung der letzten 7 Tage, null ohne Messwerte."""
    return regulation_data(request)


@app.get("/", include_in_schema=False)
def dashboard(request: Request, zeitraum: str = "tag"):
    cfg = config.load(request.app.state.config_path)
    st = api_status(request)
    period = zeitraum if zeitraum in st["bilanz"] else "tag"
    live = st["live"]
    live["pv"] = (live.get("pv_power") or 0) + (live.get("pv_ac_power") or 0) if live else None
    today = datetime.now(analytics.TZ).date()
    bars = analytics.history(request.app.state.storage.hourly(int(time.time())),
                             analytics.buckets("tag", today)[1], cfg["prices"])
    a = st["amortisation"]
    return templates.TemplateResponse(request, "dashboard.html", {
        "periods": PERIODS, "period": period, "b": st["bilanz"][period], "akku": st["akku"][period],
        "live": live, "live_age": int(time.time() - st["stand"].timestamp()) if st["stand"] else None,
        "chart": chart(bars), "a": a, "warnings": st["warnungen"],
        "progress": min(a["bisher_gespart"] / a["kosten"] * 100, 100) if a["kosten"] else 0,
        "prices_set": cfg["prices"]["energy"] > 0 and cfg["system"]["cost"] > 0,
    })


def history_data(request, ansicht, datum):
    cfg = config.load(request.app.state.config_path)
    today = datetime.now(analytics.TZ).date()
    day = parse_day(datum, today)
    view = ansicht if ansicht in dict(VIEWS) else "tag"
    title, buckets, prev, nxt = analytics.buckets(view, day)
    rows = request.app.state.storage.hourly(int(time.time()))
    bars = analytics.history(rows, buckets, cfg["prices"])
    total = analytics.balance([r for r in rows if r[1] < buckets[-1][2]], buckets[0][1], cfg["prices"])
    return {"ansicht": view, "titel": title, "zurueck": prev, "weiter": nxt if nxt <= today else None,
            "balken": bars, "bilanz": total}


@app.get("/verlauf", include_in_schema=False)
def history(request: Request, ansicht: str = "tag", datum: str = ""):
    d = history_data(request, ansicht, datum)
    return templates.TemplateResponse(request, "history.html", {
        "views": VIEWS, "view": d["ansicht"], "title": d["titel"], "prev": d["zurueck"], "next": d["weiter"],
        "chart": chart(d["balken"]), "b": d["bilanz"],
    })


def regulation_data(request):
    cfg = config.load(request.app.state.config_path)
    storage = request.app.state.storage
    latest = {k: v for k, (_, v) in storage.latest().items()}
    since = int(time.time()) - 7 * 86400
    series = storage.series(since, ["grid_power", "output_power", "pv_ac_power", "battery_soc"])
    return analytics.regulation(series, cfg["prices"], soc_min=latest.get("battery_soc_min") or 10,
                                limit=latest.get("output_power_limit") or 800)


@app.get("/nulleinspeisung", include_in_schema=False)
def zero_feed_in(request: Request):
    return templates.TemplateResponse(request, "regulation.html", {"r": regulation_data(request)})


@app.get("/einstellungen", include_in_schema=False)
def settings(request: Request):
    cfg = config.load(request.app.state.config_path)
    return templates.TemplateResponse(request, "settings.html", {"cfg": cfg})


@app.post("/einstellungen", include_in_schema=False)
async def save_settings(request: Request):
    form = {k: v[0] for k, v in parse_qs((await request.body()).decode()).items()}
    cfg = config.load(request.app.state.config_path)
    try:
        values = {k: float(form[k].replace(",", ".")) for k in ("energy", "feed_in", "cost")}
        day = date.fromisoformat(form["commissioned"]) if form.get("commissioned") else None
        if min(values.values()) < 0 or (day and day > date.today()):
            raise ValueError
    except (KeyError, ValueError):
        return templates.TemplateResponse(request, "settings.html", {"cfg": cfg, "error": True}, status_code=400)
    cfg["prices"].update(energy=values["energy"], feed_in=values["feed_in"])
    cfg["system"].update(cost=values["cost"], commissioned=day)
    config.save(request.app.state.config_path, cfg)
    return RedirectResponse("/einstellungen?gespeichert=1", status_code=303)
