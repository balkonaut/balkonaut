# Tests der Home-Assistant-Integration gegen die Version aus pytest-homeassistant-custom-component
FROM python:3.14-slim AS ha-test
WORKDIR /build
RUN pip install --no-cache-dir pytest-homeassistant-custom-component==0.13.373
COPY core core
COPY custom_components custom_components
COPY tests_ha tests_ha
RUN python -m pytest tests_ha -q -p no:cacheprovider -o asyncio_mode=auto -o pythonpath=. -o testpaths=tests_ha

# Prüfung der Integration mit hassfest (wie die GitHub-Action home-assistant/actions/hassfest)
FROM ghcr.io/home-assistant/hassfest AS hassfest
COPY core core
COPY custom_components custom_components
RUN /usr/src/homeassistant/script/hassfest/docker/entrypoint.sh

FROM python:3.12-slim AS docs

WORKDIR /build
COPY pyproject.toml LICENSE mkdocs.yml ./
COPY core core
RUN pip install --no-cache-dir ".[docs]"
COPY docs docs
RUN mkdocs build --strict -d /site

# Tests des Kerns; die Docker-App liegt in github.com/balkonaut/balkonaut-docker und testet dort gegen diesen Kern
FROM python:3.12-slim AS test

WORKDIR /build
COPY pyproject.toml LICENSE ./
COPY core core
RUN pip install --no-cache-dir ".[dev]"
COPY tests tests
RUN python -m pytest -q
