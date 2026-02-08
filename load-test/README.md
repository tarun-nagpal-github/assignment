# Load Test – 60 RPS Search + 60 Filter Ops

Validates the scaling requirements: **60 RPS** and **60 search + 60 filter operations in parallel** without degradation.

## Prerequisites

- [k6](https://k6.io/docs/getting-started/installation/) installed
- CompanySearch API running (local or deployed), and OpenSearch with company index

## Run

```bash
# Default: http://localhost:8000, 1 minute
k6 run load-test/k6-search-and-filters.js

# Against deployed API
k6 run -e BASE_URL=https://companysearch.example.com load-test/k6-search-and-filters.js

# Shorter run (e.g. 30s)
k6 run -e BASE_URL=http://localhost:8000 --duration 30s load-test/k6-search-and-filters.js
```

## What it does

- **search_60_rps**: 60 requests/sec to `POST /search` (query + pagination).
- **tags_60_rps**: 60 requests/sec to `GET /tags/{userId}` (filter/list tags).

Both scenarios run **in parallel** for the chosen duration (default 1 min), so the system is driven at **120 RPS** (60 search + 60 tags) to confirm it handles parallel search and filter load.

## Thresholds

- `http_req_failed` &lt; 1%
- `http_req_duration` p95 &lt; 2s
- Custom metrics `search_errors` and `tags_errors` &lt; 1%

If thresholds fail, increase backend replicas or OpenSearch capacity and re-run.
