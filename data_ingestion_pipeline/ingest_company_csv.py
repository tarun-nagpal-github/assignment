"""
Read company data from a CSV in chunks and bulk index into the OpenSearch "company" index.
Safe for large files (e.g. 1+ GB). Keeps the repo light: do not commit the CSV.

  - Default CSV: data_ingestion_pipeline/companies_sorted.csv
  - Override: set env COMPANY_CSV_PATH to a full path (e.g. after downloading via
    data_ingestion_pipeline/download_company_dataset.py from Kaggle).

Supports regional employee counts: optional CSV columns
"current employee estimate <suffix>" and "total employee estimate <suffix>"
(e.g. "current employee estimate us", "total employee estimate de") for
each region suffix (us, in, br, de, jp, ar, ...). See backend/regions.py.
"""
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from opensearchpy import OpenSearch

# Allow importing backend.regions
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.regions import COUNTRY_INDEX_SUFFIX

load_dotenv()

REGION_SUFFIXES = set(COUNTRY_INDEX_SUFFIX.values())

OPENSEARCH_HOST = os.getenv("OPENSEARCH_HOST", "https://localhost:9201")
OPENSEARCH_USER = os.getenv("OPENSEARCH_USER", "admin")
OPENSEARCH_PASSWORD = os.getenv(
    "OPENSEARCH_INITIAL_ADMIN_PASSWORD",
    os.getenv("OPENSEARCH_PASSWORD"),
)
if not OPENSEARCH_PASSWORD:
    raise SystemExit(
        "Set OPENSEARCH_INITIAL_ADMIN_PASSWORD in .env or OPENSEARCH_PASSWORD"
    )

# CSV column name -> index field name (first column may be "" or "Unnamed: 0" for id)
COLUMN_MAP = {
    "": "id",
    "Unnamed: 0": "id",
    "name": "name",
    "domain": "domain",
    "year founded": "year_founded",
    "industry": "industry",
    "size range": "size_range",
    "locality": "locality",
    "country": "country",
    "linkedin url": "linkedin_url",
    "current employee estimate": "current_employee_estimate",
    "total employee estimate": "total_employee_estimate",
}

SCRIPT_DIR = Path(__file__).resolve().parent
CSV_PATH = os.getenv("COMPANY_CSV_PATH") or str(SCRIPT_DIR / "companies_sorted.csv")
CSV_PATH = Path(CSV_PATH)
INDEX_NAME = "company"
CHUNK_SIZE = 10_000  # rows per chunk to limit memory use


def _row_to_doc(row: pd.Series, id_col: str) -> dict:
    """Convert a DataFrame row to an index document with native Python types."""
    doc = {}
    for k, v in row.items():
        if pd.isna(v):
            doc[k] = None
        elif isinstance(v, (int, float, str)) and not isinstance(v, bool):
            doc[k] = v
        else:
            try:
                doc[k] = int(v)
            except (TypeError, ValueError):
                try:
                    doc[k] = float(v)
                except (TypeError, ValueError):
                    doc[k] = str(v) if v is not None else None
    # Ensure id is set for _id (might come from first column)
    if "id" not in doc and id_col in row.index:
        val = row[id_col]
        doc["id"] = int(val) if not pd.isna(val) else None
    return doc


def main() -> None:
    client = OpenSearch(
        hosts=[OPENSEARCH_HOST],
        http_compress=True,
        use_ssl=True,
        verify_certs=False,
        ssl_show_warn=False,
        http_auth=(OPENSEARCH_USER, OPENSEARCH_PASSWORD),
    )

    if not CSV_PATH.exists():
        raise SystemExit(f"CSV file not found: {CSV_PATH}")

    total_indexed = 0
    total_errors = 0

    for chunk in pd.read_csv(CSV_PATH, chunksize=CHUNK_SIZE):
        # Normalize column names to index field names
        chunk = chunk.rename(columns=COLUMN_MAP)
        # Keep mapped columns + optional regional employee columns (e.g. "current employee estimate us")
        def is_regional_col(c):
            if not isinstance(c, str):
                return False
            parts = c.split()
            if len(parts) < 4:
                return False
            suffix = parts[-1].lower()
            return (
                (c.startswith("current employee estimate ") and suffix in REGION_SUFFIXES)
                or (c.startswith("total employee estimate ") and suffix in REGION_SUFFIXES)
            )
        valid_cols = [c for c in chunk.columns if c in COLUMN_MAP.values() or is_regional_col(c)]
        chunk = chunk[[c for c in valid_cols if c in chunk.columns]]
        if "id" not in chunk.columns:
            # First column may still be unnamed after rename; use first col as id
            chunk = chunk.rename(columns={chunk.columns[0]: "id"})
        chunk = chunk.dropna(subset=["id"])

        # Types
        chunk["id"] = pd.to_numeric(chunk["id"], errors="coerce").fillna(0).astype("int64")
        for col in ("year_founded", "current_employee_estimate", "total_employee_estimate"):
            if col in chunk.columns:
                chunk[col] = pd.to_numeric(chunk[col], errors="coerce").fillna(0).astype("int64")

        records = chunk.to_dict(orient="records")
        # Clean types for JSON serialization
        for r in records:
            for k, v in list(r.items()):
                if pd.isna(v):
                    r[k] = None
                elif not isinstance(v, (int, float, str)) or isinstance(v, bool):
                    try:
                        r[k] = int(v)
                    except (TypeError, ValueError):
                        try:
                            r[k] = float(v)
                        except (TypeError, ValueError):
                            r[k] = str(v) if v is not None else None

        bulk_body = []
        for doc in records:
            doc_id = doc.get("id")
            if doc_id is None:
                continue
            # Build regional employee fields from optional columns
            current_by_region = {}
            total_by_region = {}
            to_remove = []
            for key, val in doc.items():
                if not isinstance(key, str) or val is None or (isinstance(val, float) and pd.isna(val)):
                    continue
                parts = key.split()
                if len(parts) < 4:
                    continue
                suffix = parts[-1].lower()
                if suffix not in REGION_SUFFIXES:
                    continue
                try:
                    ival = int(val)
                except (TypeError, ValueError):
                    continue
                if key.startswith("current employee estimate "):
                    current_by_region[suffix] = ival
                    to_remove.append(key)
                elif key.startswith("total employee estimate "):
                    total_by_region[suffix] = ival
                    to_remove.append(key)
            for k in to_remove:
                doc.pop(k, None)
            if current_by_region:
                doc["current_employee_estimate_by_region"] = current_by_region
            if total_by_region:
                doc["total_employee_estimate_by_region"] = total_by_region
            bulk_body.append({"index": {"_index": INDEX_NAME, "_id": doc_id}})
            bulk_body.append(doc)

        if not bulk_body:
            continue

        resp = client.bulk(body=bulk_body, refresh=False)
        if resp.get("errors"):
            failed = sum(1 for i in resp.get("items", []) if "error" in i.get("index", {}))
            total_errors += failed
        total_indexed += len(records)
        print(f"  Indexed {total_indexed} rows so far...", end="\r", flush=True)

    # Optional: refresh index once at the end so new docs are searchable
    client.indices.refresh(index=INDEX_NAME)
    print(f"\nDone. Indexed {total_indexed} records into '{INDEX_NAME}'.")
    if total_errors:
        print(f"  ({total_errors} items had errors)")


if __name__ == "__main__":
    main()
