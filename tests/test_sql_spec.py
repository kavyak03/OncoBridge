from ehr_fhir_genomics_toolkit.sql_connector import sclc_cohort_sql

def test_sclc_sql_contains_params():
    sql = sclc_cohort_sql("clinical_metadata")
    assert ":diagnosis" in sql and ":min_age" in sql and ":start_date" in sql and ":end_date" in sql
