from __future__ import annotations

from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text

from .security import validate_sql_identifier


def query_sql(sqlalchemy_url: str, sql_text: str, params: dict[str, Any]) -> pd.DataFrame:
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

    Security note:
      SQL values are passed as bound parameters. The only interpolated value is
      the table identifier, which is validated by validate_sql_identifier()
      before being inserted into the query string.
    """
    clinical_table = validate_sql_identifier(clinical_table)

    sql = """
SELECT
  sample_id,
  patient_id,
  diagnosis,
  age_at_collection,
  collection_date
FROM __CLINICAL_TABLE__
WHERE diagnosis = :diagnosis
  AND age_at_collection >= :min_age
  AND collection_date BETWEEN :start_date AND :end_date
"""
    return sql.replace("__CLINICAL_TABLE__", clinical_table)


def cohort_with_therapy_sql(clinical_table: str, therapy_table: str) -> str:
    """
    Generic cohort SQL with optional therapy join.

    therapy_table expected columns:
      patient_id, regimen, line_of_therapy, start_date, end_date

    Security note:
      SQL values are passed as bound parameters. The only interpolated values are
      table identifiers, which are validated by validate_sql_identifier()
      before being inserted into the query string.
    """
    clinical_table = validate_sql_identifier(clinical_table)
    therapy_table = validate_sql_identifier(therapy_table)

    sql = """
SELECT
  c.sample_id,
  c.patient_id,
  c.diagnosis,
  c.age_at_collection,
  c.collection_date,
  t.regimen,
  t.line_of_therapy
FROM __CLINICAL_TABLE__ c
LEFT JOIN __THERAPY_TABLE__ t
  ON c.patient_id = t.patient_id
  AND c.collection_date BETWEEN t.start_date AND COALESCE(t.end_date, '2999-12-31')
WHERE c.diagnosis = :diagnosis
  AND c.age_at_collection >= :min_age
  AND c.collection_date BETWEEN :start_date AND :end_date
"""
    return sql.replace("__CLINICAL_TABLE__", clinical_table).replace(
        "__THERAPY_TABLE__",
        therapy_table,
    )


# Backward-compatible aliases
sclc_cohort_sql = generic_cohort_sql
sclc_with_therapy_sql = cohort_with_therapy_sql
