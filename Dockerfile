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

FROM python:3.12-slim AS test

WORKDIR /build
COPY pyproject.toml LICENSE ./
COPY core core
RUN pip install --no-cache-dir ".[app,dev]"
COPY app app
COPY tests tests
RUN python -m pytest -q

FROM python:3.12-slim

WORKDIR /srv
COPY pyproject.toml LICENSE ./
COPY core core
RUN pip install --no-cache-dir ".[app]"
COPY app app
COPY --from=docs /site handbuch

ENV BALKONAUT_DATA=/data
VOLUME /data

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
