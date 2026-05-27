from __future__ import annotations

from collections.abc import Iterable

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series


class ClinicalCSVSchema(pa.DataFrameModel):
    sample_id: Series[str]
    patient_id: Series[str]
    diagnosis: Series[str]
    age_at_collection: Series[float] = pa.Field(ge=0, le=120, nullable=True)
    collection_date: Series[str]

    class Config:
        strict = False
        coerce = True


class TherapyCSVSchema(pa.DataFrameModel):
    patient_id: Series[str]
    regimen: Series[str]
    line_of_therapy: Series[int] = pa.Field(ge=0)
    start_date: Series[str]
    end_date: Series[str] | None = pa.Field(nullable=True)

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


def _parse_required_date_column(df: pd.DataFrame, column: str, name: str) -> pd.DataFrame:
    out = df.copy()
    parsed = pd.to_datetime(out[column], errors="coerce")
    bad = out[column].notna() & parsed.isna()
    if bad.any():
        examples = out.loc[bad, column].astype(str).head(10).tolist()
        raise ValueError(f"{name} validation failed: invalid {column} dates: {examples}")
    if parsed.isna().any():
        raise ValueError(f"{name} validation failed: {column} cannot contain null dates")
    out[column] = parsed.dt.strftime("%Y-%m-%d")
    return out


def _parse_optional_date_column(df: pd.DataFrame, column: str, name: str) -> pd.DataFrame:
    out = df.copy()
    if column not in out.columns:
        out[column] = None
        return out
    parsed = pd.to_datetime(out[column], errors="coerce")
    bad = out[column].notna() & parsed.isna()
    if bad.any():
        examples = out.loc[bad, column].astype(str).head(10).tolist()
        raise ValueError(f"{name} validation failed: invalid {column} dates: {examples}")
    out[column] = parsed.dt.strftime("%Y-%m-%d").where(parsed.notna(), None)
    return out


def _assert_unique(df: pd.DataFrame, columns: list[str], name: str) -> None:
    dupes = df[df.duplicated(columns, keep=False)]
    if not dupes.empty:
        examples = dupes[columns].astype(str).head(10).to_dict(orient="records")
        raise ValueError(f"{name} validation failed: duplicate keys for {columns}: {examples}")


def validate_clinical_csv(df: pd.DataFrame) -> pd.DataFrame:
    df = _assert_columns_present(
        df,
        ["sample_id", "patient_id", "diagnosis", "age_at_collection", "collection_date"],
        "clinical CSV",
    )
    df = _parse_required_date_column(df, "collection_date", "clinical CSV")
    validated = ClinicalCSVSchema.validate(df)
    validated = _assert_non_empty(validated, "clinical CSV")
    _assert_unique(validated, ["sample_id"], "clinical CSV")
    return validated


def validate_therapy_csv(df: pd.DataFrame) -> pd.DataFrame:
    df = _assert_columns_present(
        df,
        ["patient_id", "regimen", "line_of_therapy", "start_date"],
        "therapy CSV",
    )
    df = _parse_required_date_column(df, "start_date", "therapy CSV")
    df = _parse_optional_date_column(df, "end_date", "therapy CSV")
    validated = TherapyCSVSchema.validate(df)
    validated = _assert_non_empty(validated, "therapy CSV")

    start = pd.to_datetime(validated["start_date"], errors="coerce")
    end = pd.to_datetime(validated["end_date"], errors="coerce")
    bad_order = end.notna() & (end < start)
    if bad_order.any():
        examples = (
            validated.loc[bad_order, ["patient_id", "start_date", "end_date"]]
            .head(10)
            .to_dict(orient="records")
        )
        raise ValueError(f"therapy CSV validation failed: end_date before start_date: {examples}")
    return validated


def validate_expression_csv(df: pd.DataFrame) -> pd.DataFrame:
    df = _assert_columns_present(
        df,
        ["sample_id", "gene", "expression_value"],
        "expression CSV",
    )
    validated = ExpressionCSVSchema.validate(df)
    validated = _assert_non_empty(validated, "expression CSV")
    _assert_unique(validated, ["sample_id", "gene"], "expression CSV")
    return validated


def validate_variant_csv(df: pd.DataFrame) -> pd.DataFrame:
    df = _assert_columns_present(
        df,
        ["sample_id", "var_id", "GENE", "GT", "QUAL"],
        "variant CSV",
    )
    validated = VariantCSVSchema.validate(df)
    validated = _assert_non_empty(validated, "variant CSV")
    _assert_unique(validated, ["sample_id", "var_id"], "variant CSV")
    return validated
