"""Run a survival modeling example from an existing merged cohort CSV.

This example is educational. If the input CSV does not already contain:
  - survival_time_months
  - event_observed

the script can add synthetic demo survival outcomes.

Examples:
  python scripts/run_survival_example.py --input-csv demo_sclc_dataset.csv --out-dir survival_results
  python scripts/run_survival_example.py --input-csv real_dataset.csv --feature-cols SCLC_Y_YAP1,mut_TP53
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import pandas as pd

from ehr_fhir_genomics_toolkit.survival import add_demo_survival_outcomes, fit_cox_example, save_survival_outputs


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--input-csv", required=True)
    p.add_argument("--out-dir", default="survival_results")
    p.add_argument("--feature-cols", default="")
    p.add_argument("--add-demo-outcomes", action="store_true", help="Add synthetic survival_time_months/event_observed if not present.")
    return p.parse_args()


def main():
    args = parse_args()
    df = pd.read_csv(args.input_csv)

    if {"survival_time_months", "event_observed"} - set(df.columns):
        if args.add_demo_outcomes:
            df = add_demo_survival_outcomes(df, seed=7)
        else:
            raise SystemExit("Input CSV missing survival_time_months/event_observed. Use --add-demo-outcomes for an educational demo.")

    feature_cols = [c.strip() for c in args.feature_cols.split(",") if c.strip()]
    cph = fit_cox_example(df, feature_cols=feature_cols or None)
    outputs = save_survival_outputs(df, cph, out_dir=args.out_dir)

    summary = {
        "n_rows": len(df),
        "feature_cols_used": feature_cols or "default signature/mutation columns",
        "outputs": outputs,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
