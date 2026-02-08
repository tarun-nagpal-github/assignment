"""
Download the company dataset from Kaggle into this folder (no need to commit the CSV).

Requires Kaggle API credentials:
  - Option A: Place kaggle.json in ~/.kaggle/ (from Kaggle Account → API).
  - Option B: Set env KAGGLE_USERNAME and KAGGLE_KEY.

Usage (from project root):
  .venv/bin/pip install kaggle
  .venv/bin/python data_ingestion_pipeline/download_company_dataset.py

Then run ingest as usual; the CSV will be at data_ingestion_pipeline/companies_sorted.csv.
"""
import os
import shutil
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DATASET = "peopledatalabssf/free-7-million-company-dataset"
OUTPUT_CSV = SCRIPT_DIR / "companies_sorted.csv"


def main() -> None:
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
    except ImportError:
        raise SystemExit(
            "Install the Kaggle API: pip install kaggle\n"
            "Then add credentials: ~/.kaggle/kaggle.json or set KAGGLE_USERNAME and KAGGLE_KEY."
        )

    api = KaggleApi()
    api.authenticate()

    print(f"Downloading {DATASET} ...")
    api.dataset_download_files(DATASET, path=str(SCRIPT_DIR), unzip=False)

    # Find the downloaded zip (Kaggle may name it <slug>.zip)
    slug = DATASET.split("/")[-1]
    zip_path = SCRIPT_DIR / f"{slug}.zip"
    if not zip_path.exists():
        zips = list(SCRIPT_DIR.glob("*.zip"))
        if not zips:
            raise SystemExit("Downloaded zip not found.")
        zip_path = max(zips, key=lambda p: p.stat().st_mtime)

    print("Extracting CSV ...")
    with zipfile.ZipFile(zip_path, "r") as z:
        names = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if not names:
            raise SystemExit("No CSV found in the zip.")
        # Use largest CSV if multiple
        csv_name = max(names, key=lambda n: z.getinfo(n).file_size)
        with z.open(csv_name) as src:
            with open(OUTPUT_CSV, "wb") as dst:
                shutil.copyfileobj(src, dst)

    zip_path.unlink()
    print(f"Done. CSV saved to {OUTPUT_CSV}")
    print("Run: .venv/bin/python data_ingestion_pipeline/ingest_company_csv.py")


if __name__ == "__main__":
    main()
