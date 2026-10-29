FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY alertlens/requirements.txt /app/alertlens/requirements.txt
RUN pip install --no-cache-dir -r /app/alertlens/requirements.txt

# Copy source code, models, and built frontend
COPY alertlens /app/alertlens
COPY README.md /app/README.md

WORKDIR /app/alertlens

EXPOSE 8000

ENV PORT=8000
ENV ALERTLENS_DB_PATH=data/alertlens.db

CMD ["sh", "-c", "uvicorn alertlens.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
