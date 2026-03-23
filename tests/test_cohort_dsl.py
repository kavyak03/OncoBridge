from datetime import date

from ehr_fhir_genomics_toolkit.cohort_dsl import apply_dsl_to_cohortspec
from ehr_fhir_genomics_toolkit.models import CohortSpec


def test_cohort_dsl_overrides_fields():
    base = CohortSpec()
    updated = apply_dsl_to_cohortspec(
        base,
        "diagnosis=small cell lung cancer; min_age=21; start_date=2019-01-01; end_date=2020-01-01; therapy_mode=join_table; regimen_bucket=first_line_platinum_etoposide_io",
    )
    assert updated.min_age == 21
    assert updated.start_date == date(2019, 1, 1)
    assert updated.therapy_mode == "join_table"
