from __future__ import annotations

import pandas as pd

from .schema import clinical_schema, merged_schema


def _normalize_nullable_clinical_columns(clinical_df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize optional therapy-enrichment columns so schema validation
    does not fail when left joins introduce missing values.
    """
    df = clinical_df.copy()

    if "line_of_therapy" in df.columns:
        df["line_of_therapy"] = pd.to_numeric(
            df["line_of_therapy"], errors="coerce"
        ).astype("Int64")

    return df


def merge_clinical_expression(
    clinical_df: pd.DataFrame,
    expr_wide_df: pd.DataFrame,
    join_key: str = "sample_id",
) -> pd.DataFrame:
    clinical_df = _normalize_nullable_clinical_columns(clinical_df)
    clinical_schema().validate(clinical_df)

    merged = clinical_df.merge(expr_wide_df, on=join_key, how="inner")

    if "line_of_therapy" in merged.columns:
        merged["line_of_therapy"] = pd.to_numeric(
            merged["line_of_therapy"], errors="coerce"
        ).astype("Int64")

    merged_schema().validate(merged)
    return merged


def attach_features(
    merged_df: pd.DataFrame,
    extra_df: pd.DataFrame,
    join_key: str = "sample_id",
    how: str = "left",
) -> pd.DataFrame:
    if extra_df is None or extra_df.empty:
        return merged_df

    out = merged_df.merge(extra_df, on=join_key, how=how)

    if "line_of_therapy" in out.columns:
        out["line_of_therapy"] = pd.to_numeric(
            out["line_of_therapy"], errors="coerce"
        ).astype("Int64")

    return out