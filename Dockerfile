FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY main.py .
COPY bot/ bot/

RUN useradd --create-home appuser
USER appuser

EXPOSE 8080

CMD ["uv", "run", "functions-framework", "--target=handle_webhook", "--port=8080"]
