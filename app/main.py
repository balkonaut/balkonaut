import asyncio
import json
import logging
import math
import socket
import time
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import config
from balkonaut import analytics, collector, pvgis
from balkonaut.storage import RAW_DAYS, Storage

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
# Adresse, unter der die Integration das Add-on erreicht (Hostname des Add-on-Containers im HA-Netz)
templates.env.globals["integration_url"] = lambda: f"http://{socket.gethostname()}:8000" if config.addon() else None
PERIODS = [("tag", "Heute"), ("monat", "Monat"), ("jahr", "Jahr"), ("gesamt", "Gesamt")]
SUPERVISOR_IP = "172.30.32.2"  # Absender von Ingress-Anfragen im Add-on
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


def soc_gauge(live):
    """Akku-Ring: Ladestand, Farbton von 0 (rot, Untergrenze) bis 130 (grün, Obergrenze) und Grenzmarken
    als Striche im Ring (viewBox 100, Radius 34 bis 50). None ohne Ladestand."""
    soc = live.get("battery_soc")
    if soc is None:
        return None
    lo, hi = live.get("battery_soc_min") or 0, live.get("battery_soc_max") or 100
    marks = []
    for key, name, value in (("lo", "Minimum", live.get("battery_soc_min")),
                             ("prot", "Entladeschutz", live.get("battery_discharge_protection")),
                             ("hi", "Maximum", live.get("battery_soc_max"))):
        if value is not None:
            c, s = math.cos(value / 100 * 2 * math.pi), math.sin(value / 100 * 2 * math.pi)
            marks.append({"key": key, "name": name, "value": value,
                          "x1": round(50 + 34 * c, 2), "y1": round(50 + 34 * s, 2),
                          "x2": round(50 + 50 * c, 2), "y2": round(50 + 50 * s, 2)})
    share = (soc - lo) / (hi - lo) if hi > lo else 1
    # Restzeit bis zur Obergrenze (laden) bzw. Minimum oder Entladeschutz (entladen)
    # ponytail: ohne Wandlungsverluste und bei gleichbleibender Leistung, Verlauf glätten falls es springt
    power, cap, rest = live.get("battery_power") or 0, live.get("battery_capacity"), None
    target = hi if power > 0 else max(lo, live.get("battery_discharge_protection") or 0)
    if cap and abs(power) >= 20 and (target - soc) * power > 0:
        minutes = round((target - soc) / 100 * cap * 60000 / power)
        rest = {"target": target, "minutes": minutes} if minutes <= 48 * 60 else None
    return {"soc": soc, "lo": lo, "hi": hi, "hue": round(min(max(share, 0), 1) * 130), "marks": marks, "rest": rest}


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
                 asyncio.create_task(load_profile(app, adapter, data / "ertragsprofil.json")),
                 asyncio.create_task(regulation_job(app))]
    yield
    for task in tasks:
        task.cancel()


app = FastAPI(title="Balkonaut", lifespan=lifespan)


@app.middleware("http")
async def addon_writes_via_ingress(request: Request, call_next):
    """Im Add-on ändern nur Anfragen über Ingress (vom Supervisor) die Einstellungen; lesen dürfen auch
    andere Container im HA-Netz, z. B. die Integration."""
    sender = request.client and request.client.host
    if config.addon() and request.method not in ("GET", "HEAD") and sender != SUPERVISOR_IP:
        return PlainTextResponse("Einstellungen nur über Home Assistant änderbar", status_code=403)
    return await call_next(request)
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
    first = day.replace(day=1)
    last = (first + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    stored = request.app.state.storage.regulation_days(first.isoformat(), last.isoformat())
    r["nulleinspeisung"] = analytics.combine_regulation(stored.values())
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
        "heute": st["bilanz"]["tag"], "live": live, "gauge": soc_gauge(live),
        "live_age": int(time.time() - st["stand"].timestamp()) if st["stand"] else None,
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


REGULATION_KEYS = ["grid_power", "output_power", "pv_ac_power", "battery_soc"]


def regulation_between(storage, prices, start, end):
    latest = {k: v for k, (_, v) in storage.latest().items()}
    series = storage.series(start, REGULATION_KEYS, end)
    return analytics.regulation(series, prices, soc_min=latest.get("battery_soc_min") or 10,
                                limit=latest.get("output_power_limit") or 800)


def store_regulation_days(storage, cfg):
    """Regelgüte für jeden abgeschlossenen Tag mit Rohwerten berechnen, der noch nicht gespeichert ist."""
    today = datetime.now(analytics.TZ).date()
    days = [today - timedelta(days=i) for i in range(RAW_DAYS - 1, 0, -1)]
    stored = storage.regulation_days(days[0].isoformat(), days[-1].isoformat())
    for day in days:
        if day.isoformat() not in stored:
            start = datetime.combine(day, datetime.min.time(), analytics.TZ).timestamp()
            r = regulation_between(storage, cfg["prices"], start, start + 86400)
            if r:
                storage.save_regulation_day(day.isoformat(), r)


async def regulation_job(app):
    while True:  # stündlich; neue Tage kommen nach Mitternacht dazu
        try:
            await asyncio.to_thread(store_regulation_days, app.state.storage, config.load(app.state.config_path))
        except Exception:
            log.exception("Tageswerte der Regelgüte nicht gespeichert")
        await asyncio.sleep(3600)


def regulation_data(request):
    cfg = config.load(request.app.state.config_path)
    return regulation_between(request.app.state.storage, cfg["prices"], int(time.time()) - 7 * 86400, time.time())


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
    return RedirectResponse("einstellungen?gespeichert=1", status_code=303)  # relativ wegen Ingress
