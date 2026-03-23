from __future__ import annotations

from typing import Iterable, Optional

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series


class ClinicalCSVSchema(pa.DataFrameModel):
    sample_id: Series[str]
    patient_id: Series[str]
    diagnosis: Series[str]
    age_at_collection: Series[int] = pa.Field(ge=-1, le=120)
    collection_date: Series[str]

    class Config:
        strict = False
        coerce = True


class TherapyCSVSchema(pa.DataFrameModel):
    patient_id: Series[str]
    regimen: Series[str]
    line_of_therapy: Series[int] = pa.Field(ge=0)
    start_date: Series[str]
    end_date: Optional[Series[str]] = pa.Field(nullable=True)

    class Config:
        strict = False
        coerce = True


class ExpressionCSVSchema(pa.DataFrameModel):
    sample_id: Series[str]
    gene: Series[str]
    expression_value: Series[float]

    class Config:
        strict = False
        coerce = True


class VariantCSVSchema(pa.DataFrameModel):
    sample_id: Series[str]
    var_id: Series[str]
    GENE: Series[str]
    GT: Series[int]
    QUAL: Series[float]

    class Config:
        strict = False
        coerce = True


def _assert_non_empty(df: pd.DataFrame, name: str) -> pd.DataFrame:
    if df.empty:
        raise ValueError(f"{name} validation failed: dataframe is empty.")
    return df


def _assert_columns_present(df: pd.DataFrame, required: Iterable[str], name: str) -> pd.DataFrame:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{name} validation failed: missing required columns: {missing}")
    return df


def validate_clinical_csv(df: pd.DataFrame) -> pd.DataFrame:
    df = _assert_columns_present(
        df,
        ["sample_id", "patient_id", "diagnosis", "age_at_collection", "collection_date"],
        "clinical CSV",
    )
    validated = ClinicalCSVSchema.validate(df)
    return _assert_non_empty(validated, "clinical CSV")


def validate_therapy_csv(df: pd.DataFrame) -> pd.DataFrame:
    df = _assert_columns_present(
        df,
        ["patient_id", "regimen", "line_of_therapy", "start_date"],
        "therapy CSV",
    )
    validated = TherapyCSVSchema.validate(df)
    return _assert_non_empty(validated, "therapy CSV")


def validate_expression_csv(df: pd.DataFrame) -> pd.DataFrame:
    df = _assert_columns_present(
        df,
        ["sample_id", "gene", "expression_value"],
        "expression CSV",
    )
    validated = ExpressionCSVSchema.validate(df)
    return _assert_non_empty(validated, "expression CSV")


def validate_variant_csv(df: pd.DataFrame) -> pd.DataFrame:
    df = _assert_columns_present(
        df,
        ["sample_id", "var_id", "GENE", "GT", "QUAL"],
        "variant CSV",
    )
    validated = VariantCSVSchema.validate(df)
    return _assert_non_empty(validated, "variant CSV")