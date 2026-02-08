# CompanySearch – Interview Assignment (Reviewer Guide)

This repo is **standalone and independently runnable**. You can clone it and run the full stack (OpenSearch, API, UI) with a single script, without relying on the candidate’s environment.

---

## What This Is

- **Product**: CompanySearch – a search platform for discovering companies (see [PRD.md](./PRD.md)).
- **Stack**: OpenSearch (search), FastAPI (backend), React + Vite (frontend), Docker.
- **Scope**: Core search API, filters/facets, tags (saved filters), dashboard, **query understanding** (e.g. “tech companies in California”), **semantic industry matching** (synonyms + expansion), **multi-country** (region selector, locale, regional employee counts), and **scaling** (Kubernetes, HPA, 60 RPS load test). See [ASSIGNMENT.md](./ASSIGNMENT.md) for the full checklist.

---

## Prerequisites (on your machine)

Install once:

| Requirement   | Purpose                    | How to check           |
|----------------|----------------------------|------------------------|
| **Docker**     | Run OpenSearch             | `docker --version`     |
| **Docker Compose** | Start OpenSearch stack | `docker compose version` |
| **Python 3.9+**   | Backend + ingest      | `python3 --version`   |
| **Node.js 18+**   | Frontend build         | `node --version`      |
| **npm**        | Frontend deps              | `npm --version`       |

- **Docker Desktop**: set at least **4 GB** memory (Settings → Resources).
- **macOS**: Docker Desktop includes Compose. On Linux, install [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/).

---

## Before running setup: get the company CSV

**Manually download the company dataset CSV and place it in the project before running `./setup.sh`.**

- **Where to put it:** `data_ingestion_pipeline/companies_sorted.csv`
- **Where to get it:** e.g. [Kaggle – free-7-million-company-dataset](https://www.kaggle.com/datasets/peopledatalabssf/free-7-million-company-dataset) (download and unzip; use the main CSV and rename or copy it to `companies_sorted.csv` in `data_ingestion_pipeline/`).

If the CSV is not present, `setup.sh` will skip the ingest step and the search index will be empty until you add the file and run ingest (see [data_ingestion_pipeline/README.md](data_ingestion_pipeline/README.md)).

---

## One-command setup

From the **project root** (where `setup.sh` and `docker-compose.yml` are):

```bash
chmod +x setup.sh
./setup.sh
```

**What the script does:**

1. Creates `.env` from `.env.example` if missing (OpenSearch admin password).
2. Starts OpenSearch (and OpenSearch Dashboards) in Docker.
3. Waits for OpenSearch to be ready, then creates the `company` index.
4. Ingests data from `data_ingestion_pipeline/companies_sorted.csv` **if the file is present** (can take a while for large files). If the file is missing, ingest is skipped—add the CSV and run the script again or run the ingest manually.
5. Installs Python (`.venv`) and Node (frontend) dependencies.
6. Starts the backend on port **8000** and the frontend on port **5173**; the terminal stays on the frontend. **Ctrl+C** stops both.

After the script finishes, open:

- **App**: http://localhost:5173  
- **API**: http://localhost:8000 (e.g. GET /health, GET /regions, POST /search, GET/POST/DELETE /tags/{user_id})  
- **OpenSearch Dashboards** (optional): http://localhost:5601 (user: `admin`, password in `.env`)

**Note:** OpenSearch runs from the **official image** in `docker-compose.yml` (`opensearchproject/opensearch:latest`). The root **Dockerfile** builds the **backend API** image only (for production/Kubernetes).

---

## Manual steps (if you prefer not to use the script)

Same result as above, by hand:

1. **Env and OpenSearch**
   ```bash
   cp .env.example .env   # edit if you want a different password
   docker compose up -d
   ```
2. **Wait** for OpenSearch (~1–2 min), then **create index**:
   ```bash
   ./opensearch_index/create-company-index.sh
   ```
3. **Ingest** (optional; needs `data_ingestion_pipeline/companies_sorted.csv`):
   ```bash
   python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
   .venv/bin/python data_ingestion_pipeline/ingest_company_csv.py
   ```
4. **Backend** (new terminal):
   ```bash
   cd backend && ../.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
   ```
5. **Frontend** (another terminal):
   ```bash
   cd frontend && npm install && npm run dev
   ```
   Then open http://localhost:5173.

---

## What to try in the app

- **Search**: Type a company name or industry (e.g. “tech companies”); click **Search**. Query understanding applies (e.g. location/industry from natural language).
- **Region**: Use the **Region** dropdown (All regions, United States, India, Germany, etc.) to scope results and use region-specific employee counts when available.
- **Filters**: Use the left panel (Industry, Size range, Country, Year founded); click **Search** to apply.
- **Sort**: Use the dropdown (relevance, name, size, year).
- **Tags**: Enter a name and click **Save** to save current filters; use **Apply** to restore them, **Delete** to remove.

---

## Stopping and cleaning up

- **Stop app + API**: In the terminal where you ran `./setup.sh`, press **Ctrl+C** (script stops backend and frontend).
- **Stop OpenSearch**:
  ```bash
  docker compose down
  ```
- **Remove OpenSearch data** (fresh start):
  ```bash
  docker compose down -v
  ```

---

## Repo layout (quick reference)

| Path | Purpose |
|------|--------|
| `PRD.md` | Product requirements. |
| `ASSIGNMENT.md` | Scope, status, and technical quick start. |
| `setup.sh` | One-command setup (Docker, index, ingest, backend, frontend). |
| `.env` / `.env.example` | OpenSearch password (create from example if missing). |
| `docker-compose.yml` | OpenSearch + Dashboards. |
| `opensearch_index/` | Company index mapping and create script. |
| `data_ingestion_pipeline/` | CSV → OpenSearch ingest script. |
| `backend/` | FastAPI search + tags API. |
| `frontend/` | React + Vite UI. |
| `data_ingestion_pipeline/companies_sorted.csv` | **Required for ingest.** Manually download the company dataset (e.g. from Kaggle) and place it here before running `./setup.sh`. |
| `kubernetes/` | K8s manifests (Deployments, HPA, PDB, Ingress). |
| `load-test/` | k6 script for 60 RPS search + 60 RPS filter validation. Run: `k6 run load-test/k6-search-and-filters.js` |
| `Dockerfile` | Backend (API) production image. Build: `docker build -t companysearch-backend:latest .` |
| `docker/` | Frontend Dockerfile + nginx config for production UI. Build: `docker build -f docker/Dockerfile.frontend -t companysearch-frontend:latest .` |
| `kubernetes/INTERVIEW-KUBERNETES.md` | Interview cheat sheet for explaining each K8s file. |

---

## Scaling design

This section describes how the search system meets the **scaling requirements**: 60 RPS target, 60 search + 60 filter operations in parallel without degradation, and a design that accommodates future growth.

### Target capacity: 60 requests per second

| Lever | Implementation |
|-------|----------------|
| **Stateless API** | FastAPI backend has no in-memory session state; any replica can serve any request. Traffic can be spread across pods via the Service. |
| **Baseline replicas** | **3 backend pods** by default. At ~20 RPS per pod (conservative for typical search latency &lt;200 ms), 3 pods support 60 RPS with headroom. |
| **Horizontal Pod Autoscaler (HPA)** | Scales backend from **3 to 20 replicas** on CPU (70%) and memory (80%). Sustained 60 RPS or spikes push CPU up and trigger scale-up; scale-down is stabilized to avoid flapping. |
| **Resource requests/limits** | Backend pods request 100m CPU / 256Mi memory, limit 500m / 512Mi. Ensures scheduler placement and prevents a single pod from starving others. |
| **Readiness & liveness probes** | Only ready pods receive traffic; unhealthy pods are restarted. Keeps effective capacity predictable under load. |

**Capacity math:** With ~50–100 ms OpenSearch latency, a single uvicorn process can handle **20–40 RPS** per pod. 3 pods × ~20 RPS = **60 RPS** at baseline. HPA adds pods to absorb spikes (e.g. 80–100 RPS).

### Parallel operations: 60 search + 60 filter simultaneously

- Each backend pod runs an **async** FastAPI/uvicorn process; many concurrent requests (search and tags) are handled in parallel; I/O wait does not block others.
- **Search** uses OpenSearch connection pooling; **tags** are file-based with short-lived or atomic access. So **60 search + 60 tag** requests run as **120 concurrent operations** across pods without a single bottleneck.
- The **load-test** (k6) runs 60 RPS search and 60 RPS tags in parallel to validate this (see `load-test/`).

### Future growth

| Aspect | Approach |
|--------|----------|
| **Compute** | HPA max 20 replicas can be raised (e.g. 50–100). Cluster autoscaler adds nodes as needed. |
| **OpenSearch** | Scale data/search nodes independently; use a managed OpenSearch service for production. |
| **Ingress** | Ingress controller load-balances; add TLS and WAF as traffic grows. |
| **Observability** | Add metrics (Prometheus), tracing, logging to detect bottlenecks. |
| **Caching** | Optional: Redis in front of search or hot facets. |
| **Rate limiting** | At Ingress or API layer to protect backend and OpenSearch. |

### Kubernetes and cloud layout

- **`kubernetes/`** – Namespace, ConfigMap, Secret, Backend and Frontend Deployments and Services, **HPA** (3–20 replicas), **PDB** (min 2 available), Ingress. See [kubernetes/README.md](./kubernetes/README.md) for deploy order and image build.
- **`Dockerfile`** (root) – Backend image. **`docker/`** – Frontend Dockerfile + nginx config.
- **`load-test/`** – k6 scripts to validate 60 RPS search and 60 RPS filter (tags) in parallel.

---

You can clone this repo on any machine with the prerequisites above and run **`./setup.sh`** to get a full local demo without extra setup from the candidate.
