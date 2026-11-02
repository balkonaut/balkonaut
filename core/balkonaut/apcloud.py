"""APsystems-Cloud (EMA) für den EZHI: Szenario, Ladegrenzen, Entladeschutz und Abgabelimit lesen und steuern.

Optional und nicht offiziell: Adressen, Anmeldung und Feldnamen stammen aus der Integration „APsystems EZHI Local
API“ (github.com/kamilkosek/EZHI, MIT-Lizenz), die sie aus der APsystems-App abgeleitet hat. APsystems kann das
jederzeit ändern. Zugangsdaten und Token erscheinen nie in Logs oder Fehlermeldungen.
"""
import base64
import json
import os
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request


BASE_URL = "https://app.api.apsystemsema.com:9223"
API_URL = f"{BASE_URL}/aps-api-web/api/v2"
TOKEN_URL = f"{BASE_URL}/api/token/refreshToken"
LOGIN_URL = f"{BASE_URL}/api/token/generateToken/user/loginEncrypt"
# Feste Anmeldedaten der APsystems-App, für alle Nutzer gleich (aus der Vorlage oben)
APP_ID = "4029817264d4821d0164d4821dd80015"
APP_SECRET = "EZAd2023"
PUBLIC_KEY = (
    "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAgdwBhVodMQ84lYZhDSGOUDQAks+NMa7WQ83mR1OyHiIW"
    "tZ1wWAh4H7fclkdNS3lWCmDH9ldF7Kf6JlEvZTc0Textv+YMLXO2gdDIoBvg7vlhY4HxOjXUIFQ+s7cWRrmEIgVV"
    "nTBLZU1GMC8zld7WH9v9EYCAqK7rvGJP0STZ/g6BP8RGJKhdpY6b+ndMXRUBYwkqy8m1SDJHm1FeHSLQWTaWbP5p"
    "z1yrGkkwvx+pib6wli+WE70/uPHp0zXZK5iUwmRQfOkTjDOGJyEE1dqkfHDTqne5ED81M4fCIEFYhyvnr1rifVJK"
    "HCDRGYQpJ0CiffjjH1ZOGSIN4JPG1EEIjQIDAQAB"
)
TIMEOUT = 15  # Sekunden je Anfrage
TOKEN_LIFETIME = 6000  # Zugangs-Token gilt 2 h, vorher erneuern
AUTH_CODES = {3000, 3001, 3002, 3003, 3004}
OFFLINE_CODE = 1001
# systemMode-Werte der APsystems-App; 5 ist die AC-gekoppelte Variante und wird nicht angeboten
MODES = {"1": "Balkon-Energiespeicher", "2": "Tragbare Stromversorgung", "3": "KI-Modus", "4": "Lokaler Modus",
         "5": "Balkon-Energiespeicher (AC)", "6": "Ohne Batterie"}
SELECTABLE = ["1", "2", "3", "4", "6"]
MODE_KEYS = ("systemMode", "EPS", "ECO", "userSetPower")  # Pflichtfelder beim Schreiben, aus der gelesenen Konfiguration
OPTIONAL_KEYS = ("dischargeProtection", "stayOn", "governmentLevies", "area")  # werden mitgeschickt, wenn vorhanden
PROTECTION_MARGIN = 2  # Entladeschutz mindestens 2 % über dem Minimum, wie die APsystems-App


class CloudError(Exception):
    """Abfrage oder Befehl gescheitert; die Meldung ist für den Nutzer gedacht und enthält keine Geheimnisse."""


def wire(value):
    """Wert wie die Cloud ihn schickt: "1" statt True, "4" statt 4.0."""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _int(value, field):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        raise CloudError(f"Cloud meldet für {field} keinen Zahlenwert") from None


def _truthy(value):
    return value.strip().lower() not in ("", "0", "false", "null") if isinstance(value, str) else bool(value)


def _request(url, data, headers, method="POST"):
    """Eine Anfrage, Antwort als (HTTP-Status, JSON); Netzfehler als CloudError ohne Inhalte der Anfrage."""
    query = urllib.parse.urlencode(data)
    req = urllib.request.Request(f"{url}?{query}" if method == "GET" else url,
                                 data=query.encode() if method == "POST" else None, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            status, raw = r.status, r.read(1_000_000)
    except urllib.error.HTTPError as e:
        status, raw = e.code, e.read(1_000_000)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise CloudError(f"APsystems-Cloud nicht erreichbar ({type(getattr(e, 'reason', e)).__name__})") from None
    try:
        return status, json.loads(raw or b"{}")
    except ValueError:
        return status, {}


def _aes_hex(plain, key, iv):
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    raw = plain.encode()
    raw += b"\0" * (16 - len(raw) % 16)  # Nullen wie die App, bei vollem Block ein ganzer Block mehr
    enc = Cipher(algorithms.AES(key.encode()), modes.CBC(iv.encode())).encryptor()
    return (enc.update(raw) + enc.finalize()).hex()


def _rsa_b64(text):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    key = serialization.load_der_public_key(base64.b64decode(PUBLIC_KEY))
    return base64.b64encode(key.encrypt(text.encode(), padding.PKCS1v15())).decode()


def login_params(username, password, key=None, iv=None):
    """Formular für loginEncrypt: Zugangsdaten AES-verschlüsselt, Schlüssel und IV RSA-verschlüsselt."""
    key = key or os.urandom(16).hex()
    iv = iv or f"{secrets.randbelow(10 ** 16):016d}"
    return {"app_id": APP_ID, "app_secret": APP_SECRET, "key": _rsa_b64(key), "version": _rsa_b64(iv),
            "username": _aes_hex(username, key, iv), "password": _aes_hex(password, key, iv), "language": "de"}


def check_soc(soc_min, soc_max):
    if not 0 <= soc_min < soc_max <= 100:
        raise CloudError(f"Ladegrenzen {soc_min} bis {soc_max} % sind nicht möglich (Minimum unter Maximum, 0 bis 100)")


def check_protection(protection, soc_min):
    if protection is not None and soc_min is not None and protection < soc_min + PROTECTION_MARGIN:
        raise CloudError(f"Entladeschutz {protection} % muss mindestens {PROTECTION_MARGIN} % über dem Minimum "
                         f"({soc_min} %) liegen")


def mode_params(config, changes):
    """Ganze Konfiguration für den systemMode-Befehl: gelesene Werte, darüber die Änderungen. Fehlt ein Pflichtfeld,
    lieber abbrechen als raten, denn der Befehl stellt echte Hardware um."""
    params = {k: wire(config[k]) for k in MODE_KEYS + OPTIONAL_KEYS if config.get(k) is not None}
    params |= {k: wire(v) for k, v in changes.items()}
    if missing := [k for k in MODE_KEYS if k not in params]:
        raise CloudError(f"Cloud-Konfiguration unvollständig ({', '.join(missing)}), nichts geändert")
    return params


def values(config):
    """Werte aus der gelesenen Konfiguration; battery_mode als Text, inverter_on als True/False/None."""
    def num(key):
        try:
            return float(config[key])
        except (KeyError, TypeError, ValueError):
            return None
    on = wire(config.get("onOff", ""))
    return {"battery_soc_min": num("socMin"), "battery_soc_max": num("socMax"),
            "battery_discharge_protection": num("dischargeProtection"), "output_power_limit": num("powerLimit"),
            "battery_mode": MODES.get(wire(config.get("systemMode", ""))), "mode": wire(config.get("systemMode", "")),
            "inverter_on": True if on == "0" else False if on == "1" else None}  # 0 = ein, 1 = aus


class Cloud:
    """Angemeldeter Zugang für ein Gerät; Methoden blockieren (im Thread aufrufen)."""

    def __init__(self, username, password, device_id):
        self.username, self.password, self.device_id = username, password, device_id
        self._token = self._refresh = None
        self._expires = 0.0
        self._lock = threading.Lock()  # ein Befehl zur Zeit: lesen, ändern, schreiben

    def __repr__(self):  # nie Zugangsdaten in Logs
        return f"Cloud(device_id={self.device_id!r})"

    def login(self):
        status, body = _request(LOGIN_URL, login_params(self.username, self.password), {"Accept-Language": "de"})
        if status != 200:
            raise CloudError(f"Anmeldung bei der APsystems-Cloud gescheitert (HTTP {status})")
        data = body.get("data") or {}
        if body.get("code") != 0 or not data.get("access_token") or not data.get("refresh_token"):
            raise CloudError("Anmeldung abgelehnt: Benutzername bzw. E-Mail-Adresse und Passwort prüfen")
        self._token, self._refresh = data["access_token"], data["refresh_token"]
        self._expires = time.monotonic() + TOKEN_LIFETIME

    def _ensure_token(self):
        if self._token and time.monotonic() < self._expires:
            return
        if not self._refresh:
            return self.login()
        status, body = _request(TOKEN_URL, {"refresh_token": self._refresh, "language": "de"},
                                {"Authorization": f"Bearer {self._token}", "Accept-Language": "de"})
        token = (body.get("data") or {}).get("access_token")
        if status in (401, 403) or body.get("code") in AUTH_CODES:
            return self.login()  # Refresh-Token nach 7 Tagen abgelaufen: neu anmelden wie die App
        if status != 200 or body.get("code") != 0 or not token:
            raise CloudError(f"Token der APsystems-Cloud nicht erneuert (HTTP {status})")
        self._token, self._expires = token, time.monotonic() + TOKEN_LIFETIME

    def _call(self, method, path, data):
        data = {"deviceId": self.device_id, "type": "EZHI", "language": "de", **data}
        for attempt in (1, 2):
            self._ensure_token()
            status, body = _request(f"{API_URL}/{path}", data,
                                    {"Authorization": f"Bearer {self._token}", "Accept-Language": "de"}, method)
            if status != 401 or attempt == 2:
                break
            self._expires = 0.0  # einmal mit frischem Token wiederholen
        code = body.get("code")
        if status == 401 or code in AUTH_CODES:
            raise CloudError("APsystems-Cloud lehnt die Anmeldung ab")
        if code == OFFLINE_CODE:
            raise CloudError("Der EZHI ist für die Cloud nicht erreichbar (offline)")
        if status != 200 or code != 0:
            raise CloudError(f"APsystems-Cloud: {path} gescheitert (HTTP {status}, Code {code})")
        return body.get("data") or {}

    def _config(self):
        return self._call("GET", "remote/ezInverter/systemMode", {})

    def read(self):
        with self._lock:
            return values(self._config())

    def set_mode(self, mode):
        if mode not in SELECTABLE:
            raise CloudError("Unbekanntes Szenario")
        with self._lock:
            config = self._config()  # vor jedem Schreiben frisch lesen: in der App geänderte Werte zählen
            if mode == "6" and wire(config.get("noBattery", "")) != "1":
                raise CloudError("„Ohne Batterie“ nur ohne angeschlossenen Akku: Der EZHI meldet noch einen Akku "
                                 "oder sagt nichts dazu. Akku erst abklemmen oder in der APsystems-App umstellen.")
            self._write_mode(config, {"systemMode": mode})

    def set_protection(self, protection):
        with self._lock:
            config = self._config()
            check_protection(protection, _int(config.get("socMin"), "socMin"))
            self._write_mode(config, {"dischargeProtection": protection})

    def _write_mode(self, config, changes):
        params = mode_params(config, changes)
        data = self._call("POST", "remote/ezInverter/systemMode",
                          {"identifierType": "1", "maxPowerFlag": "0", "params": json.dumps(params)})
        if not _truthy(data.get("flag")):
            raise CloudError("Der EZHI hat die Änderung abgelehnt")

    def set_soc(self, soc_min, soc_max):
        check_soc(soc_min, soc_max)
        with self._lock:
            config = self._config()
            if config.get("dischargeProtection") is not None:
                check_protection(_int(config["dischargeProtection"], "dischargeProtection"), soc_min)
            data = self._call("POST", "remote/ezInverter/socLimit", {"socMin": str(soc_min), "socMax": str(soc_max)})
        if not _truthy(data.get("flag")):
            raise CloudError("Der EZHI hat die Ladegrenzen abgelehnt")

    def set_on(self, on):
        """Ein- oder ausschalten; einschalten geht nur, solange der EZHI noch mit der Cloud verbunden ist."""
        with self._lock:
            self._call("POST", "remote/common/setRemote",
                       {"identifier": "onOff", "params": json.dumps({"status": "0" if on else "1"})})
