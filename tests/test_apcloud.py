"""APsystems-Cloud ohne Netz: Antworten der Cloud nachgebaut, geprüft werden Anmeldung, Schreibregeln und Einstellungen."""
import json

import pytest
import yaml

from balkonaut import apcloud

CONFIG = {"systemMode": "3", "EPS": "0", "ECO": "0", "userSetPower": "200", "socMin": "10", "socMax": "95",
          "dischargeProtection": "12", "powerLimit": "800", "onOff": "0", "noBattery": "0"}


class FakeCloud:
    """Nimmt Anfragen an wie die Cloud; refresh_dead simuliert den abgelaufenen Refresh-Token."""

    def __init__(self):
        self.calls, self.config, self.refresh_dead = [], dict(CONFIG), False

    def __call__(self, url, data, headers, method="POST"):
        path = url.rsplit("9223/", 1)[1]
        self.calls.append((method, path, data))
        if path.endswith("loginEncrypt"):
            return 200, {"code": 0, "data": {"access_token": "A", "refresh_token": "R"}}
        if path.endswith("refreshToken"):
            return (200, {"code": 3001}) if self.refresh_dead else (200, {"code": 0, "data": {"access_token": "A2"}})
        if path.endswith("systemMode") and method == "GET":
            return 200, {"code": 0, "data": dict(self.config)}
        if path.endswith("systemMode"):
            self.config |= json.loads(data["params"])
            return 200, {"code": 0, "data": {"flag": "1"}}
        if path.endswith("socLimit"):
            self.config |= {"socMin": data["socMin"], "socMax": data["socMax"]}
            return 200, {"code": 0, "data": {"flag": True}}
        return 200, {"code": 0, "data": {"flag": 0}}


@pytest.fixture
def fake(monkeypatch):
    f = FakeCloud()
    monkeypatch.setattr(apcloud, "_request", f)
    return f


def test_login_encrypts_credentials():
    p = apcloud.login_params("kay", "geheim", key="0" * 32, iv="1" * 16)
    assert p["app_id"] == apcloud.APP_ID and "geheim" not in json.dumps(p) and "kay" not in json.dumps(p)
    # Nullen auffüllen, bei vollem Block ein ganzer Block mehr (wie die App)
    assert len(p["username"]) == 32 and len(apcloud.login_params("a" * 16, "x", key="0" * 32, iv="1" * 16)["username"]) == 64


def test_read_and_write_rules(fake):
    cloud = apcloud.Cloud("kay", "geheim", "D02000000001")
    assert "geheim" not in repr(cloud)
    v = cloud.read()
    assert v["battery_mode"] == "KI-Modus" and v["battery_soc_min"] == 10 and v["inverter_on"] is True
    cloud.set_mode("1")
    sent = json.loads(fake.calls[-1][2]["params"])
    assert sent["systemMode"] == "1" and sent["dischargeProtection"] == "12" and "powerLimit" not in sent  # nie 1200 W
    with pytest.raises(apcloud.CloudError, match="Ohne Batterie"):
        cloud.set_mode("6")  # Akku gemeldet
    with pytest.raises(apcloud.CloudError, match="2 %"):
        cloud.set_protection(11)
    cloud.set_protection(14)
    with pytest.raises(apcloud.CloudError, match="Minimum"):
        cloud.set_soc(13, 95)  # Entladeschutz 14 läge unter 13 + 2
    with pytest.raises(apcloud.CloudError, match="nicht möglich"):
        cloud.set_soc(90, 80)
    cloud.set_soc(5, 90)
    cloud.set_on(False)
    assert fake.config["socMin"] == "5" and fake.calls[-1][2]["params"] == '{"status": "1"}'
    with pytest.raises(apcloud.CloudError, match="unvollständig"):
        apcloud.mode_params({"systemMode": "1"}, {})


def test_relogin_after_refresh_token_expired(fake):
    cloud = apcloud.Cloud("kay", "geheim", "D02000000001")
    cloud.read()
    fake.refresh_dead, cloud._expires = True, 0.0
    cloud.read()
    assert [c[1].rsplit("/", 1)[1] for c in fake.calls].count("loginEncrypt") == 2


def test_settings_connect_control_disconnect(client, tmp_path, fake):
    assert "Nicht offiziell" in client.get("/einstellungen").text
    r = client.post("/einstellungen", data={"bereich": "cloud", "aktion": "verbinden", "username": "kay",
                                            "password": "geheim", "device_id": ""})
    assert r.status_code == 400 and "Geräte-ID" in r.text  # kein direkt eingetragener EZHI
    r = client.post("/einstellungen", data={"bereich": "cloud", "aktion": "verbinden", "username": "kay",
                                            "password": "geheim", "device_id": "D02000000001"})
    assert r.status_code == 200 and "Verbunden als" in r.text and "geheim" not in r.text
    assert (tmp_path / "config.yaml").stat().st_mode & 0o077 == 0
    assert yaml.safe_load((tmp_path / "config.yaml").read_text())["apsystems_cloud"]["password"] == "geheim"
    r = client.post("/einstellungen", data={"bereich": "cloud", "aktion": "szenario", "mode": "4"})
    assert str(r.url).endswith("gesetzt=szenario#cloud") and 'class="done"' in r.text and ">Umgestellt<" in r.text
    assert fake.config["systemMode"] == "4" and "Lokaler Modus ·" in client.get("/einstellungen").text
    r = client.post("/einstellungen", data={"bereich": "cloud", "aktion": "schutz", "protection": "8"})
    assert r.status_code == 400 and "2 %" in r.text
    client.post("/einstellungen", data={"bereich": "cloud", "aktion": "trennen"})
    assert "apsystems_cloud" not in yaml.safe_load((tmp_path / "config.yaml").read_text())


def test_post_only_from_own_page(client):
    form = {"bereich": "cloud", "aktion": "aus"}
    assert client.post("/einstellungen", data=form, headers={"Origin": "http://boese.example"}).status_code == 403
    assert client.post("/einstellungen", data=form, headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
    assert client.post("/einstellungen", data=form, headers={"Origin": "http://testserver"}).status_code == 400  # nicht verbunden
