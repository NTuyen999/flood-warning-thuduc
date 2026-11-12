# Build from the repo root: docker compose up -d --build   (or: docker build -f backend/Dockerfile .)
FROM python:3.13-slim

# libgomp1: OpenMP runtime needed by xgboost/lightgbm wheels.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ml/src ml/src
COPY ml/saved_models ml/saved_models
COPY backend/app backend/app
COPY backend/db backend/db

RUN useradd --create-home app && mkdir -p backend/uploads ml/outputs \
    && chown -R app backend/uploads ml/outputs
USER app

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
