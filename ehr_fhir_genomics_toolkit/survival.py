from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pandas as pd
from lifelines import CoxPHFitter

from .io_safety import atomic_write_csv

SIGNATURE_COLUMNS = ["SCLC_A_ASCL1", "SCLC_N_NEUROD1", "SCLC_P_POU2F3", "SCLC_Y_YAP1"]
MUTATION_COLUMNS = ["mut_TP53", "mut_RB1", "mut_MYC"]


def add_demo_survival_outcomes(df: pd.DataFrame, seed: int = 7) -> pd.DataFrame:
    """Add synthetic survival time/event columns for educational examples.

    This is NOT real clinical survival data.
    It creates a plausible toy relationship:
      - higher SCLC_Y score slightly worse hazard
      - RB1/TP53 mutation flags slightly worse hazard
    """
    rng = np.random.default_rng(seed)
    out = df.copy()
    risk = np.zeros(len(out), dtype=float)

    for c in SIGNATURE_COLUMNS:
        if c in out.columns:
            scale = 0.15 if "YAP1" in c else 0.05
            risk += scale * pd.to_numeric(out[c], errors="coerce").fillna(0).to_numpy()

    for c in MUTATION_COLUMNS:
        if c in out.columns:
            weight = 0.35 if c in {"mut_TP53", "mut_RB1"} else 0.15
            risk += weight * pd.to_numeric(out[c], errors="coerce").fillna(0).to_numpy()

    base_time = rng.exponential(scale=18.0, size=len(out))  # months
    adjusted = base_time / np.exp(np.clip(risk, -2, 2))
    censor = rng.uniform(6, 30, size=len(out))
    observed = adjusted <= censor
    duration = np.where(observed, adjusted, censor)

    out["survival_time_months"] = np.round(duration, 2)
    out["event_observed"] = observed.astype(int)
    return out


def prepare_survival_features(
    df: pd.DataFrame, feature_cols: Sequence[str] | None = None
) -> pd.DataFrame:
    feature_cols = list(feature_cols or [])
    if not feature_cols:
        feature_cols = [c for c in SIGNATURE_COLUMNS + MUTATION_COLUMNS if c in df.columns]
    cols = ["survival_time_months", "event_observed"] + feature_cols
    model_df = df[cols].copy()
    for c in feature_cols:
        model_df[c] = pd.to_numeric(model_df[c], errors="coerce").fillna(0.0)
    return model_df


def fit_cox_example(df: pd.DataFrame, feature_cols: Sequence[str] | None = None) -> CoxPHFitter:
    model_df = prepare_survival_features(df, feature_cols)
    cph = CoxPHFitter()
    cph.fit(model_df, duration_col="survival_time_months", event_col="event_observed")
    return cph


def km_risk_groups(df: pd.DataFrame, score_col: str) -> pd.DataFrame:
    out = df.copy()
    out[score_col] = pd.to_numeric(out[score_col], errors="coerce")
    cutoff = out[score_col].median()
    out["risk_group"] = np.where(out[score_col] >= cutoff, "high", "low")
    return out


def save_survival_outputs(
    df: pd.DataFrame, cph: CoxPHFitter, out_dir: str = "survival_results"
) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    cox_path = out / "cox_summary.csv"
    atomic_write_csv(cph.summary, cox_path)

    dataset_path = out / "survival_dataset.csv"
    atomic_write_csv(df, dataset_path, index=False)

    return {
        "cox_summary_csv": str(cox_path),
        "survival_dataset_csv": str(dataset_path),
    }
