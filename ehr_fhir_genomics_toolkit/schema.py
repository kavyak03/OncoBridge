from __future__ import annotations

import pandera.pandas as pa
from pandera import Check, Column, DataFrameSchema


def clinical_schema() -> DataFrameSchema:
    # Minimal cohort metadata expected from SQL
    return DataFrameSchema(
        {
            "sample_id": Column(str),
            "patient_id": Column(str),
            "diagnosis": Column(str),
            "age_at_collection": Column(int, Check.ge(0)),
            "collection_date": Column(pa.DateTime, nullable=False),
            # optional therapy fields
            "regimen": Column(str, nullable=True, required=False),
            # IMPORTANT: use pandas nullable integer dtype
            "line_of_therapy": Column("Int64", nullable=True, required=False),
        },
        coerce=True,
        strict=False,
    )


def expression_long_schema() -> DataFrameSchema:
    # Long format: one row per (sample_id, gene)
    return DataFrameSchema(
        {
            "sample_id": Column(str),
            "gene": Column(str),
            "expression_value": Column(float, nullable=True),
        },
        coerce=True,
        strict=False,
    )


def variants_schema() -> DataFrameSchema:
    # Minimal; real arrays vary.
    return DataFrameSchema(
        {
            "sample_id": Column(str),
            "GT": Column(object, nullable=True, required=False),
            "QUAL": Column(float, Check.ge(0), nullable=True, required=False),
            "GENE": Column(
                str, nullable=True, required=False
            ),  # optional gene annotation if present
        },
        coerce=True,
        strict=False,
    )


def merged_schema() -> DataFrameSchema:
    return DataFrameSchema(
        {
            "sample_id": Column(str),
            "patient_id": Column(str),
            "diagnosis": Column(str),
            "age_at_collection": Column(int, Check.ge(0)),
            "collection_date": Column(pa.DateTime),
            # merged dataset may still contain therapy info
            "regimen": Column(str, nullable=True, required=False),
            "line_of_therapy": Column("Int64", nullable=True, required=False),
        },
        coerce=True,
        strict=False,
    )
