# CompanySearch API – production image (Kubernetes / cloud / docker-compose)
# OpenSearch runs via docker-compose using the official opensearchproject/opensearch image.
FROM python:3.11-slim

WORKDIR /app

# Install deps (backend only for smaller image)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY backend/ ./backend/
WORKDIR /app/backend
ENV PYTHONUNBUFFERED=1

# One process per container; scale via replicas (e.g. Kubernetes HPA) for 60 RPS
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
