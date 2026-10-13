FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
RUN useradd --create-home --uid 10001 video
USER video
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-10000} --workers 1 --threads 1 --timeout 210 app:app"]
