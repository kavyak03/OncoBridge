from __future__ import annotations

from pathlib import Path

import pandas as pd
import pandera.errors as pa_errors
import pytest

from ehr_fhir_genomics_toolkit.data_contracts import validate_clinical_csv, validate_therapy_csv
from ehr_fhir_genomics_toolkit.io_safety import safe_rmtree, safe_unlink
from ehr_fhir_genomics_toolkit.merger import attach_features, merge_clinical_expression
from ehr_fhir_genomics_toolkit.provenance import ProvenanceLogger
from ehr_fhir_genomics_toolkit.sql_connector import generic_cohort_sql


def _clinical_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "sample_id": ["S1", "S2"],
            "patient_id": ["P1", "P2"],
            "diagnosis": ["small cell lung cancer", "small cell lung cancer"],
            "age_at_collection": [64, 70],
            "collection_date": pd.to_datetime(["2020-01-01", "2020-01-02"]),
        }
    )


def _expr_df() -> pd.DataFrame:
    return pd.DataFrame({"sample_id": ["S1", "S2"], "ASCL1": [1.0, 2.0]})


def test_sql_identifier_validation_rejects_injection():
    with pytest.raises(ValueError):
        generic_cohort_sql("clinical_metadata; DROP TABLE patients")


def test_merge_rejects_duplicate_clinical_sample_ids():
    clinical = pd.concat([_clinical_df(), _clinical_df().iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        merge_clinical_expression(clinical, _expr_df())


def test_merge_rejects_row_loss_by_default():
    expr = pd.DataFrame({"sample_id": ["S1"], "ASCL1": [1.0]})
    with pytest.raises(ValueError, match="dropped"):
        merge_clinical_expression(_clinical_df(), expr)


def test_attach_features_fills_missing_mutation_flags():
    extra = pd.DataFrame({"sample_id": ["S1"], "mut_TP53": [1]})
    out = attach_features(_clinical_df(), extra)
    s2 = out[out["sample_id"] == "S2"].iloc[0]
    assert s2["mut_TP53"] == 0


def test_clinical_validation_rejects_negative_age():
    df = pd.DataFrame(
        {
            "sample_id": ["S1"],
            "patient_id": ["P1"],
            "diagnosis": ["small cell lung cancer"],
            "age_at_collection": [-1],
            "collection_date": ["2020-01-01"],
        }
    )
    with pytest.raises(pa_errors.SchemaError):
        validate_clinical_csv(df)


def test_therapy_validation_rejects_end_before_start():
    df = pd.DataFrame(
        {
            "patient_id": ["P1"],
            "regimen": ["carboplatin"],
            "line_of_therapy": [1],
            "start_date": ["2020-02-01"],
            "end_date": ["2020-01-01"],
        }
    )
    with pytest.raises(ValueError, match="end_date"):
        validate_therapy_csv(df)


def test_safe_delete_refuses_outside_allowed_root(tmp_path: Path):
    root = tmp_path / "allowed"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError):
        safe_unlink(outside, allowed_roots=[root])


def test_safe_rmtree_refuses_outside_allowed_root(tmp_path: Path):
    root = tmp_path / "allowed"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(ValueError):
        safe_rmtree(outside, allowed_roots=[root])


def test_provenance_hashes_sql_by_default(tmp_path: Path):
    logger = ProvenanceLogger(str(tmp_path))

    sql_url = "".join(
        [
            "mysql+pymysql://",
            "user",
            ":",
            "pass",
            "@example/db",
        ]
    )

    logger.log_sql(sql_url, "SELECT * FROM clinical_metadata", {"min_age": 18})

    text = (tmp_path / "provenance.jsonl").read_text(encoding="utf-8")
    assert "SELECT * FROM" not in text
    assert "user:***@example" in text
    assert "sql_text_hash" in text
