"""Load user-supplied real clinical CSV files into a local SQLite database.

Expected clinical CSV columns:
  sample_id, patient_id, diagnosis, age_at_collection, collection_date

Optional therapy CSV columns:
  patient_id, regimen, line_of_therapy, start_date, end_date
"""
from __future__ import annotations
import argparse
import sqlite3
from pathlib import Path

import pandas as pd

from ehr_fhir_genomics_toolkit.data_contracts import validate_clinical_csv, validate_therapy_csv


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--clinical-csv", required=True)
    p.add_argument("--therapy-csv", default=None)
    p.add_argument("--sqlite-path", default="data/real_ehr.sqlite")
    return p.parse_args()


def main():
    args = parse_args()
    clinical = pd.read_csv(args.clinical_csv)
    clinical = validate_clinical_csv(clinical)

    out = Path(args.sqlite_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()

    conn = sqlite3.connect(out)
    clinical.to_sql("clinical_metadata", conn, index=False, if_exists="replace")

    if args.therapy_csv:
        therapy = pd.read_csv(args.therapy_csv)
        therapy = validate_therapy_csv(therapy)
        therapy.to_sql("therapy_lines", conn, index=False, if_exists="replace")

    conn.close()
    print(f"Wrote SQLite database: {out}")


if __name__ == "__main__":
    main()
