FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY main.py .
COPY bot/ bot/
COPY data/ data/

RUN useradd --create-home appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

CMD ["uv", "run", "--no-sync", "uvicorn", "bot.main:app", "--host", "0.0.0.0", "--port", "8080"]
