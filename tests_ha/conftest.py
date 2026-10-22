import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(recorder_mock, enable_custom_integrations, hass, tmp_path):
    """Recorder vor hass einrichten (Verlaufsimport im eigenständigen Betrieb), eigene Integrationen erlauben und
    je Test ein eigener Konfigurationsordner, damit balkonaut/balkonaut.db nicht zwischen Tests geteilt wird."""
    hass.config.config_dir = str(tmp_path)
    yield
