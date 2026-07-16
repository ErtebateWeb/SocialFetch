FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -e . && \
    rm -rf ~/.cache/pip

ENV PYTHONUNBUFFERED=1

CMD ["python", "run_bot.py"]
