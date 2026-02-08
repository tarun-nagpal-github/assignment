# Data ingestion

## Before running `./setup.sh`: add the company CSV

**Manually download the company dataset CSV and place it in this folder** so that `./setup.sh` can ingest it into OpenSearch.

1. **Download** the dataset (e.g. [Kaggle – free-7-million-company-dataset](https://www.kaggle.com/datasets/peopledatalabssf/free-7-million-company-dataset)).
2. **Unzip** the archive and find the main company CSV.
3. **Copy** (or rename) that file to:
   ```text
   data_ingestion_pipeline/companies_sorted.csv
   ```
4. Then run **`./setup.sh`** from the project root. Step 4 will ingest from this file.

If you run `./setup.sh` without the CSV, ingest is skipped. Add the file and run `./setup.sh` again, or run the ingest script manually (see below).

## Scripts

| Script | Purpose |
|--------|--------|
| `ingest_company_csv.py` | Read `companies_sorted.csv` (or `COMPANY_CSV_PATH`) and bulk-index into OpenSearch `company` index. Run from project root: `.venv/bin/python data_ingestion_pipeline/ingest_company_csv.py` |
| `download_company_dataset.py` | Optional: download the dataset from Kaggle via API (requires `~/.kaggle/kaggle.json`). Run from project root: `.venv/bin/python data_ingestion_pipeline/download_company_dataset.py` |

## Using your own CSV path

Set **`COMPANY_CSV_PATH`** in `.env` to the full path of your CSV; the ingest script will use it instead of `data_ingestion_pipeline/companies_sorted.csv`.
