FROM python:3.11-slim AS base

WORKDIR /app

RUN addgroup --system --gid 1000 appgroup && \
    adduser --system --uid 1000 --ingroup appgroup appuser

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

USER appuser

EXPOSE 8000

CMD ["python", "-m", "app"]
