FROM python:3.11-slim

WORKDIR /app

RUN pip install uv --no-cache-dir

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --no-dev --frozen --no-install-project

COPY src/ src/
RUN uv sync --no-dev --frozen

RUN mkdir -p /app/data

ENV NOTES_STORE_PATH=/app/data/notes.json

ENTRYPOINT ["/app/.venv/bin/mcp-business-workflows"]
