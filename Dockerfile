FROM python:3.12-slim

WORKDIR /srv
COPY pyproject.toml LICENSE ./
COPY core core
RUN pip install --no-cache-dir ".[app]"
COPY app app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
