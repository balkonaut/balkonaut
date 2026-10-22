import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(recorder_mock, enable_custom_integrations):
    """Recorder vor hass einrichten (Verlaufsimport im eigenständigen Betrieb), dann eigene Integrationen erlauben."""
    yield
