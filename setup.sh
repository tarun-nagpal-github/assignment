#!/usr/bin/env bash
#
# CompanySearch – One-command setup.
# Run from project root: ./setup.sh
#
# Before running: Manually download the company CSV and place it at
#   data_ingestion_pipeline/companies_sorted.csv
# (e.g. from Kaggle free-7-million-company-dataset). See README.md and data_ingestion_pipeline/README.md.
#
# 1. Ensures .env exists and starts OpenSearch in Docker
# 2. Waits for OpenSearch, then creates the company index
# 3. Ingests data from data_ingestion_pipeline/companies_sorted.csv (or COMPANY_CSV_PATH) if present
# 4. Installs Python and Node dependencies
# 5. Starts backend (port 8000) and frontend (port 5173); Ctrl+C stops both
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> CompanySearch setup (run from: $SCRIPT_DIR)"
echo ""

# --- 1. .env ---
if [ ! -f .env ]; then
  echo "[1/6] Creating .env from .env.example ..."
  cp .env.example .env
  echo "      Edit .env to change OPENSEARCH_INITIAL_ADMIN_PASSWORD (default is fine for local demo)."
else
  echo "[1/6] .env exists."
fi
set -a
# shellcheck source=/dev/null
source .env
set +a
export OPENSEARCH_INITIAL_ADMIN_PASSWORD

if [ -z "$OPENSEARCH_INITIAL_ADMIN_PASSWORD" ]; then
  echo "ERROR: Set OPENSEARCH_INITIAL_ADMIN_PASSWORD in .env"
  exit 1
fi

# --- 2. OpenSearch in Docker ---
echo ""
echo "[2/6] Starting OpenSearch (Docker) ..."
if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: Docker is not installed or not in PATH. Install Docker and Docker Compose first."
  exit 1
fi
docker compose up -d

echo "      Waiting for OpenSearch to be ready (up to ~90s) ..."
for i in $(seq 1 30); do
  if curl -sk -u "admin:${OPENSEARCH_INITIAL_ADMIN_PASSWORD}" "https://localhost:9201" -o /dev/null 2>/dev/null; then
    echo "      OpenSearch is up."
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "ERROR: OpenSearch did not become ready. Check: docker compose logs opensearch-node1"
    exit 1
  fi
  sleep 3
done
echo "      Waiting for OpenSearch security to be ready before creating index ..."

# --- 3. Create index (retry until security is initialized) ---
echo ""
echo "[3/6] Creating company index ..."
if [ ! -f ./opensearch_index/create-company-index.sh ]; then
  echo "ERROR: opensearch_index/create-company-index.sh not found."
  exit 1
fi
for j in $(seq 1 24); do
  bash ./opensearch_index/create-company-index.sh >/dev/null 2>&1 || true
  if curl -sk -u "admin:${OPENSEARCH_INITIAL_ADMIN_PASSWORD}" "https://localhost:9201/company" -o /dev/null -w '%{http_code}' 2>/dev/null | grep -q 200; then
    echo "      Company index ready."
    break
  fi
  if [ "$j" -eq 24 ]; then
    echo "ERROR: Company index could not be created after 2 minutes. Check: docker compose logs opensearch-node1"
    exit 1
  fi
  [ "$j" -eq 1 ] && echo "      (retrying until OpenSearch security is ready ...)"
  sleep 5
done

# --- 4. Ingest ---
echo ""
CSV_FILE="${COMPANY_CSV_PATH:-data_ingestion_pipeline/companies_sorted.csv}"
echo "[4/6] Ingesting data from ${CSV_FILE} (may take a while for large files) ..."
if [ ! -f "$CSV_FILE" ]; then
  echo "      No CSV found at ${CSV_FILE}; skipping ingest."
  echo "      Manually download the company CSV and place it at data_ingestion_pipeline/companies_sorted.csv, then run this script again or run: .venv/bin/python data_ingestion_pipeline/ingest_company_csv.py"
else
  if [ ! -d .venv ]; then
    python3 -m venv .venv
  fi
  .venv/bin/pip install -q --upgrade pip
  .venv/bin/pip install -q -r requirements.txt
  .venv/bin/python data_ingestion_pipeline/ingest_company_csv.py
fi

# --- 5. Python & Node deps ---
echo ""
echo "[5/6] Installing backend and frontend dependencies ..."
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt
if [ ! -d frontend/node_modules ]; then
  (cd frontend && npm install)
else
  (cd frontend && npm install --no-audit --no-fund)
fi

# --- 6. Start backend + frontend ---
echo ""
echo "[6/6] Starting backend and frontend ..."
echo "      Backend: http://localhost:8000"
echo "      Frontend: http://localhost:5173 (open in browser)"
echo "      Press Ctrl+C to stop both."
echo ""

BACKEND_PID=""
cleanup() {
  if [ -n "$BACKEND_PID" ]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  exit 0
}
trap cleanup INT TERM

(
  cd backend
  exec ../.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
) &
BACKEND_PID=$!

# Give backend a moment to bind
sleep 2

cd frontend
exec npm run dev
