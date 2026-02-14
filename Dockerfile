FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY main.py .
COPY bot/ bot/

CMD ["uv", "run", "functions-framework", "--target=handle_webhook", "--port=8080"]
