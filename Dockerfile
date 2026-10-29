# Stage 1: Build React Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# Stage 2: Python Backend (FastAPI + Uvicorn)
FROM python:3.11-slim
WORKDIR /app

# Install system runtime libraries (libgomp for LightGBM)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY alertlens/requirements.txt ./alertlens/
RUN pip install --no-cache-dir -r alertlens/requirements.txt

# Copy source tree and data
COPY alertlens/ ./alertlens/
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

ENV PYTHONPATH=/app/alertlens/src
ENV PORT=8000
EXPOSE 8000

WORKDIR /app/alertlens
CMD ["sh", "-c", "uvicorn alertlens.api.main:app --host 0.0.0.0 --port ${PORT} --app-dir src"]
