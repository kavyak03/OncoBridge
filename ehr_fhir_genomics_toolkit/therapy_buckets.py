from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

BUILTIN_REGIMEN_BUCKET_PROFILES: dict[str, dict[str, dict]] = {
    "generic_oncology": {
        "any": {},
        "first_line_folfox": {
            "include_any": ["folfox", "oxaliplatin", "5-fu", "fluorouracil", "leucovorin"],
            "line_of_therapy": 1,
        },
        "first_line_pembrolizumab": {
            "include_any": ["pembrolizumab", "keytruda"],
            "line_of_therapy": 1,
        },
        "any_immunotherapy": {
            "include_any": ["pembrolizumab", "nivolumab", "atezolizumab", "durvalumab"],
        },
    },
    "sclc": {
        "any": {},
        "first_line_platinum_etoposide": {
            "include_any": ["cisplatin+etoposide", "carboplatin+etoposide"],
            "line_of_therapy": 1,
        },
        "first_line_platinum_etoposide_io": {
            "include_any": [
                "carboplatin+etoposide+atezolizumab",
                "carboplatin+etoposide+durvalumab",
            ],
            "line_of_therapy": 1,
        },
        "second_line": {
            "include_any": ["topotecan", "lurbinectedin"],
            "line_of_therapy": 2,
        },
    },
}


def load_regimen_bucket_definitions(
    regimen_config: str | None = None,
    profile: str = "generic_oncology",
) -> dict[str, dict]:
    if regimen_config:
        path = Path(regimen_config)
        if not path.exists():
            raise FileNotFoundError(f"Regimen config not found: {regimen_config}")
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise ValueError("Regimen config must be a mapping: bucket_name -> rules")
        return raw

    if profile not in BUILTIN_REGIMEN_BUCKET_PROFILES:
        raise ValueError(
            f"Unknown regimen profile '{profile}'. "
            f"Available built-ins: {sorted(BUILTIN_REGIMEN_BUCKET_PROFILES)}"
        )
    return BUILTIN_REGIMEN_BUCKET_PROFILES[profile]


def list_bucket_names(bucket_defs: dict[str, dict]) -> list[str]:
    return sorted(bucket_defs.keys())


def apply_regimen_bucket_filter(
    clinical_df: pd.DataFrame,
    bucket_name: str,
    bucket_defs: dict[str, dict],
) -> pd.DataFrame:
    if bucket_name == "any":
        return clinical_df

    if bucket_name not in bucket_defs:
        raise ValueError(
            f"Unknown regimen bucket '{bucket_name}'. "
            f"Available buckets: {sorted(bucket_defs.keys())}"
        )

    if "regimen" not in clinical_df.columns:
        raise ValueError("Cannot apply regimen bucket filtering: 'regimen' column not found.")

    rules = bucket_defs[bucket_name] or {}
    out = clinical_df.copy()
    regimen_series = out["regimen"].fillna("").astype(str).str.lower()

    include_any = [s.lower() for s in rules.get("include_any", [])]
    include_all = [s.lower() for s in rules.get("include_all", [])]
    exclude_any = [s.lower() for s in rules.get("exclude_any", [])]
    line_of_therapy = rules.get("line_of_therapy", None)

    mask = pd.Series(True, index=out.index)

    if include_any:
        mask &= regimen_series.apply(lambda x: any(term in x for term in include_any))

    if include_all:
        mask &= regimen_series.apply(lambda x: all(term in x for term in include_all))

    if exclude_any:
        mask &= ~regimen_series.apply(lambda x: any(term in x for term in exclude_any))

    if line_of_therapy is not None and "line_of_therapy" in out.columns:
        lot = pd.to_numeric(out["line_of_therapy"], errors="coerce")
        mask &= lot == int(line_of_therapy)

    return out.loc[mask].copy()
