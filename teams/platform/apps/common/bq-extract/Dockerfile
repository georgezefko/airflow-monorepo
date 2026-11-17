FROM python:3.12.11-slim
COPY --from=ghcr.io/astral-sh/uv:0.7.19 /uv /bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY main.py ./
USER 1000
ENTRYPOINT ["/app/.venv/bin/python", "main.py"]
