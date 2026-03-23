from __future__ import annotations

from datetime import date
from typing import Dict, Optional

from .models import CohortSpec

ALLOWED_KEYS = {
    "diagnosis",
    "min_age",
    "start_date",
    "end_date",
    "therapy_mode",
    "regimen_bucket",
}

def parse_cohort_dsl(dsl: str) -> Dict[str, str]:
    """Parse a tiny cohort DSL.

    Syntax:
      key=value; key=value; ...

    Example:
      diagnosis=small cell lung cancer; min_age=18; start_date=2018-01-01; end_date=2020-12-31; therapy_mode=join_table; regimen_bucket=first_line_platinum_etoposide_io

    This is intentionally small and readable for non-software users.
    """
    if not dsl or not dsl.strip():
        return {}
    out: Dict[str, str] = {}
    for part in dsl.split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ValueError(f"Invalid DSL clause '{part}'. Expected key=value.")
        key, value = part.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key not in ALLOWED_KEYS:
            raise ValueError(f"Unsupported DSL key '{key}'. Allowed keys: {sorted(ALLOWED_KEYS)}")
        out[key] = value
    return out

def apply_dsl_to_cohortspec(base: CohortSpec, dsl: Optional[str]) -> CohortSpec:
    if not dsl:
        return base
    parsed = parse_cohort_dsl(dsl)
    payload = base.model_dump()
    for key, value in parsed.items():
        if key == "min_age":
            payload[key] = int(value)
        elif key in {"start_date", "end_date"}:
            y, m, d = value.split("-")
            payload[key] = date(int(y), int(m), int(d))
        else:
            payload[key] = value
    return CohortSpec(**payload)

def dsl_examples() -> str:
    return (
        "diagnosis=small cell lung cancer; min_age=18; start_date=2018-01-01; "
        "end_date=2020-12-31; therapy_mode=join_table; regimen_bucket=first_line_platinum_etoposide_io"
    )
