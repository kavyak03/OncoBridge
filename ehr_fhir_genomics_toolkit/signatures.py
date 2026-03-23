from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import yaml


BUILTIN_SIGNATURE_PROFILES: Dict[str, Dict[str, List[str]]] = {
    "generic_oncology": {
        "PROLIFERATION": ["MKI67", "PCNA", "TOP2A"],
        "EMT": ["VIM", "ZEB1", "SNAI1"],
        "INTERFERON_RESPONSE": ["IFIT1", "ISG15", "OAS1"],
        "APOPTOSIS_STRESS": ["BAX", "CASP3", "DDIT3"],
    },
    "sclc": {
        "SCLC_A_ASCL1": ["ASCL1", "DLL3", "CHGA"],
        "SCLC_N_NEUROD1": ["NEUROD1", "INSM1", "SYP"],
        "SCLC_P_POU2F3": ["POU2F3", "TRPM5", "GFI1B"],
        "SCLC_Y_YAP1": ["YAP1", "WWTR1", "VIM"],
    },
}

# Backward-compatible alias
SIGNATURES: Dict[str, List[str]] = BUILTIN_SIGNATURE_PROFILES["sclc"]


def load_signature_definitions(
    signature_config: Optional[str] = None,
    profile: str = "generic_oncology",
) -> Dict[str, List[str]]:
    """
    Load signature definitions from either:
      1) a YAML file supplied by the user
      2) a built-in profile

    YAML format:
      SIGNATURE_NAME:
        - GENE1
        - GENE2
        - GENE3
    """
    if signature_config:
        path = Path(signature_config)
        if not path.exists():
            raise FileNotFoundError(f"Signature config not found: {signature_config}")
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise ValueError("Signature config must be a mapping: signature_name -> [genes]")
        out: Dict[str, List[str]] = {}
        for sig_name, genes in raw.items():
            if not isinstance(genes, list) or not genes:
                raise ValueError(f"Signature '{sig_name}' must map to a non-empty gene list.")
            out[str(sig_name)] = [str(g).strip() for g in genes if str(g).strip()]
        if not out:
            raise ValueError("No valid signatures found in signature config.")
        return out

    if profile not in BUILTIN_SIGNATURE_PROFILES:
        raise ValueError(
            f"Unknown signature profile '{profile}'. "
            f"Available built-ins: {sorted(BUILTIN_SIGNATURE_PROFILES)}"
        )

    return BUILTIN_SIGNATURE_PROFILES[profile]


def default_gene_list(signature_definitions: Dict[str, List[str]]) -> List[str]:
    """Flatten signature genes into a unique sorted list."""
    return sorted({gene for genes in signature_definitions.values() for gene in genes})


def compute_signature_scores(
    expr_wide: pd.DataFrame,
    signature_definitions: Optional[Dict[str, List[str]]] = None,
    signature_config: Optional[str] = None,
    profile: str = "generic_oncology",
) -> pd.DataFrame:
    """
    Input:
      wide expression DF with columns: sample_id + gene columns

    Output:
      DF with sample_id + signature score columns
      Each signature score is the mean of available genes in that signature.

    Missing genes are ignored. If no genes for a signature are present, score = NaN.
    """
    sig_defs = signature_definitions or load_signature_definitions(
        signature_config=signature_config,
        profile=profile,
    )

    if "sample_id" not in expr_wide.columns:
        raise ValueError("Expression dataframe must contain 'sample_id'.")

    out = expr_wide[["sample_id"]].copy()

    for sig_name, genes in sig_defs.items():
        present = [g for g in genes if g in expr_wide.columns]
        if not present:
            out[sig_name] = np.nan
            continue
        out[sig_name] = expr_wide[present].mean(axis=1, skipna=True)

    return out