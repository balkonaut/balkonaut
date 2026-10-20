import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Laufende App mit leerem Datenverzeichnis."""
    monkeypatch.setenv("BALKONAUT_DATA", str(tmp_path))
    with TestClient(app) as c:
        yield c
