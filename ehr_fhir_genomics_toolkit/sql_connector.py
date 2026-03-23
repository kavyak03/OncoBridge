from __future__ import annotations

from typing import Dict, Any
import pandas as pd
from sqlalchemy import create_engine, text


def query_sql(sqlalchemy_url: str, sql_text: str, params: Dict[str, Any]) -> pd.DataFrame:
    engine = create_engine(sqlalchemy_url, pool_pre_ping=True)
    with engine.connect() as conn:
        return pd.read_sql(text(sql_text), conn, params=params)


def generic_cohort_sql(clinical_table: str) -> str:
    """
    Generic cohort SQL:
      - diagnosis = :diagnosis
      - age_at_collection >= :min_age
      - collection_date between :start_date and :end_date

    Required columns in clinical_table:
      sample_id, patient_id, diagnosis, age_at_collection, collection_date
    """
    return f"""
SELECT
  sample_id,
  patient_id,
  diagnosis,
  age_at_collection,
  collection_date
FROM {clinical_table}
WHERE diagnosis = :diagnosis
  AND age_at_collection >= :min_age
  AND collection_date BETWEEN :start_date AND :end_date
"""


def cohort_with_therapy_sql(clinical_table: str, therapy_table: str) -> str:
    """
    Generic cohort SQL with optional therapy join.

    therapy_table expected columns:
      patient_id, regimen, line_of_therapy, start_date, end_date
    """
    return f"""
SELECT
  c.sample_id,
  c.patient_id,
  c.diagnosis,
  c.age_at_collection,
  c.collection_date,
  t.regimen,
  t.line_of_therapy
FROM {clinical_table} c
LEFT JOIN {therapy_table} t
  ON c.patient_id = t.patient_id
  AND c.collection_date BETWEEN t.start_date AND COALESCE(t.end_date, '2999-12-31')
WHERE c.diagnosis = :diagnosis
  AND c.age_at_collection >= :min_age
  AND c.collection_date BETWEEN :start_date AND :end_date
"""


# Backward-compatible aliases
sclc_cohort_sql = generic_cohort_sql
sclc_with_therapy_sql = cohort_with_therapy_sql