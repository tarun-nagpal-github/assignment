# Company index

The `company-index.json` includes:

- **Mappings** for company documents (id, name, domain, industry, location, employee estimates, etc.).
- **Regional employee counts** (multi-country): optional `current_employee_estimate_by_region` and `total_employee_estimate_by_region` (object type, keys = region suffix e.g. `us`, `de`). When search is scoped to a region, the API returns the region-specific value when present.
- **Semantic matching**: an `industry_synonym_analyzer` so that free-text search on the industry field expands terms (e.g. "software" → "information technology and services", "computer software"). This is set as the **search_analyzer** on the `industry` field.

**If the `company` index already exists** and you want to enable synonyms, analysis settings cannot be changed in place. Either:

1. Delete the index, recreate it, and re-run the ingest:
   ```bash
   curl -k -u admin:$OPENSEARCH_INITIAL_ADMIN_PASSWORD -X DELETE "https://localhost:9201/company"
   ./create-company-index.sh
   # then run your CSV/Kaggle ingest again
   ```
2. Or create a new index with a different name and the same JSON, then reindex from the old index and switch aliases.

New setups: running `./create-company-index.sh` once creates the index with synonyms enabled.
