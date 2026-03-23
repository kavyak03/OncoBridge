from __future__ import annotations

from typing import List

import numpy as np
import pandas as pd


def generate_demo_clinical_cohort(
    n_samples: int = 50,
    seed: int = 7,
    diagnosis: str = "small cell lung cancer",
    include_therapy: bool = False,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    patient_ids = [f"P{(i // 2) + 1:04d}" for i in range(n_samples)]
    sample_ids = [f"S{i + 1:05d}" for i in range(n_samples)]
    ages = rng.integers(45, 82, size=n_samples)

    # Avoid pandas datetime overflow for large synthetic cohorts
    freq = "14D" if n_samples <= 1000 else "D"
    dates = pd.date_range("2019-01-15", periods=n_samples, freq=freq)

    df = pd.DataFrame(
        {
            "sample_id": sample_ids,
            "patient_id": patient_ids,
            "diagnosis": [diagnosis] * n_samples,
            "age_at_collection": ages,
            "collection_date": dates.strftime("%Y-%m-%d"),
        }
    )

    if include_therapy:
        regimen_options = [
            "carboplatin+etoposide",
            "cisplatin+etoposide",
            "carboplatin+etoposide+atezolizumab",
            "carboplatin+etoposide+durvalumab",
            "topotecan",
            "lurbinectedin",
        ]
        regimen_probs = [0.22, 0.18, 0.20, 0.15, 0.13, 0.12]

        regimens = rng.choice(regimen_options, size=n_samples, p=regimen_probs)

        line_of_therapy = []
        for r in regimens:
            if r in {
                "carboplatin+etoposide",
                "cisplatin+etoposide",
                "carboplatin+etoposide+atezolizumab",
                "carboplatin+etoposide+durvalumab",
            }:
                line_of_therapy.append(1)
            else:
                line_of_therapy.append(2)

        df["regimen"] = regimens
        df["line_of_therapy"] = line_of_therapy

    return df


def generate_demo_expression_long(sample_ids: List[str], genes: List[str], seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []

    for sid in sample_ids:
        subtype = rng.choice(["A", "N", "P", "Y"])
        base = rng.normal(0, 0.5)

        for g in genes:
            val = base + rng.normal(0, 1.0)

            if subtype == "A" and g in ["ASCL1", "DLL3", "CHGA"]:
                val += 2.5
            if subtype == "N" and g in ["NEUROD1", "INSM1", "SYP"]:
                val += 2.5
            if subtype == "P" and g in ["POU2F3", "TRPM5", "GFI1B"]:
                val += 2.5
            if subtype == "Y" and g in ["YAP1", "WWTR1", "VIM"]:
                val += 2.5

            rows.append((sid, g, float(val)))

    return pd.DataFrame(rows, columns=["sample_id", "gene", "expression_value"])


def generate_demo_variants(sample_ids: List[str], seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    var_ids = [f"v{i+1:05d}" for i in range(200)]
    genes = ["TP53", "RB1", "MYC", "NOTCH1", "CREBBP"]

    rows = []
    for sid in sample_ids:
        k = int(rng.integers(1, 6))
        chosen = rng.choice(var_ids, size=k, replace=False)
        for vid in chosen:
            g = rng.choice(genes, p=[0.35, 0.30, 0.15, 0.10, 0.10])
            gt = int(rng.choice([0, 1]))
            qual = float(abs(rng.normal(60, 15)))
            rows.append((sid, vid, g, gt, qual))

    return pd.DataFrame(rows, columns=["sample_id", "var_id", "GENE", "GT", "QUAL"])