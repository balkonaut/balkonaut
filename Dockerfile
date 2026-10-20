FROM python:3.12-slim AS docs

WORKDIR /build
COPY pyproject.toml LICENSE mkdocs.yml ./
COPY core core
RUN pip install --no-cache-dir ".[docs]"
COPY docs docs
RUN mkdocs build --strict -d /site

FROM python:3.12-slim

WORKDIR /srv
COPY pyproject.toml LICENSE ./
COPY core core
RUN pip install --no-cache-dir ".[app]"
COPY app app
COPY --from=docs /site handbuch

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
