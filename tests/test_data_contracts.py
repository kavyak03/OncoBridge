import pandas as pd
import pytest

from ehr_fhir_genomics_toolkit.data_contracts import (
    validate_clinical_csv,
    validate_expression_csv,
    validate_therapy_csv,
    validate_variant_csv,
)


def test_validate_clinical_csv_ok():
    df = pd.DataFrame({
        "sample_id": ["S1"],
        "patient_id": ["P1"],
        "diagnosis": ["small cell lung cancer"],
        "age_at_collection": [64],
        "collection_date": ["2020-01-01"],
    })
    out = validate_clinical_csv(df)
    assert list(out.columns) == list(df.columns)


def test_validate_clinical_csv_missing_column():
    df = pd.DataFrame({
        "sample_id": ["S1"],
        "patient_id": ["P1"],
        "diagnosis": ["small cell lung cancer"],
        "age_at_collection": [64],
    })
    with pytest.raises(Exception):
        validate_clinical_csv(df)


def test_validate_expression_csv_ok():
    df = pd.DataFrame({
        "sample_id": ["S1"],
        "gene": ["ASCL1"],
        "expression_value": [1.2],
    })
    out = validate_expression_csv(df)
    assert len(out) == 1


def test_validate_variant_csv_ok():
    df = pd.DataFrame({
        "sample_id": ["S1"],
        "var_id": ["v1"],
        "GENE": ["TP53"],
        "GT": [1],
        "QUAL": [12.4],
    })
    out = validate_variant_csv(df)
    assert len(out) == 1


def test_validate_therapy_csv_ok():
    df = pd.DataFrame({
        "patient_id": ["P1"],
        "regimen": ["chemotherapy"],
        "line_of_therapy": [1],
        "start_date": ["2020-01-01"],
        "end_date": [None],
    })
    out = validate_therapy_csv(df)
    assert len(out) == 1
