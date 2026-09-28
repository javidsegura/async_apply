FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# Chromium backs both the PDF rendering and the JD-extraction browser fallback.
RUN uv run playwright install --with-deps chromium

COPY . .

EXPOSE 8000

CMD ["./entrypoint.sh"]
