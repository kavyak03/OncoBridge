from __future__ import annotations

import pandas as pd

from .schema import clinical_schema, merged_schema

MUTATION_PREFIX = "mut_"


def _normalize_nullable_clinical_columns(clinical_df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize optional therapy-enrichment columns so schema validation
    does not fail when left joins introduce missing values.
    """
    df = clinical_df.copy()

    if "line_of_therapy" in df.columns:
        df["line_of_therapy"] = pd.to_numeric(df["line_of_therapy"], errors="coerce").astype(
            "Int64"
        )

    return df


def assert_unique_key(df: pd.DataFrame, key: str, name: str) -> None:
    if key not in df.columns:
        raise ValueError(f"{name} is missing required join key {key!r}")
    dupes = df[df.duplicated(key, keep=False)]
    if not dupes.empty:
        examples = dupes[key].astype(str).head(10).tolist()
        raise ValueError(f"{name} has duplicate {key!r} values; examples={examples}")


def _fill_mutation_flags(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in [col for col in out.columns if str(col).startswith(MUTATION_PREFIX)]:
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0).astype(int)
    return out


def merge_clinical_expression(
    clinical_df: pd.DataFrame,
    expr_wide_df: pd.DataFrame,
    join_key: str = "sample_id",
    *,
    allow_row_loss: bool = False,
) -> pd.DataFrame:
    clinical_df = _normalize_nullable_clinical_columns(clinical_df)
    clinical_schema().validate(clinical_df)

    assert_unique_key(clinical_df, join_key, "clinical_df")
    assert_unique_key(expr_wide_df, join_key, "expr_wide_df")

    before = len(clinical_df)
    merged = clinical_df.merge(expr_wide_df, on=join_key, how="inner", validate="one_to_one")
    after = len(merged)
    if not allow_row_loss and after != before:
        raise ValueError(
            f"Expression merge dropped {before - after} clinical rows. "
            "Check sample_id coverage or set allow_row_loss=True for exploratory runs."
        )

    if "line_of_therapy" in merged.columns:
        merged["line_of_therapy"] = pd.to_numeric(
            merged["line_of_therapy"], errors="coerce"
        ).astype("Int64")

    merged = _fill_mutation_flags(merged)
    merged_schema().validate(merged)
    return merged


def attach_features(
    merged_df: pd.DataFrame,
    extra_df: pd.DataFrame,
    join_key: str = "sample_id",
    how: str = "left",
    *,
    allow_duplicate_extra_keys: bool = False,
) -> pd.DataFrame:
    if extra_df is None or extra_df.empty:
        return merged_df

    assert_unique_key(merged_df, join_key, "merged_df")
    if not allow_duplicate_extra_keys:
        assert_unique_key(extra_df, join_key, "extra_df")

    validate = "one_to_one" if how in {"left", "inner"} and not allow_duplicate_extra_keys else None
    out = merged_df.merge(extra_df, on=join_key, how=how, validate=validate)

    if "line_of_therapy" in out.columns:
        out["line_of_therapy"] = pd.to_numeric(out["line_of_therapy"], errors="coerce").astype(
            "Int64"
        )

    return _fill_mutation_flags(out)
