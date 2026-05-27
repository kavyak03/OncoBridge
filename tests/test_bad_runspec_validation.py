from datetime import date

import pytest
from pydantic import ValidationError

from ehr_fhir_genomics_toolkit.models import CohortSpec, ExpressionSpec, RunSpec


def test_runspec_rejects_end_before_start():
    with pytest.raises(ValidationError):
        CohortSpec(start_date=date(2020, 1, 2), end_date=date(2020, 1, 1))


def test_runspec_rejects_empty_gene_list():
    with pytest.raises(ValidationError):
        RunSpec(mode="demo", cohort=CohortSpec(), expression=ExpressionSpec(genes=[]))
