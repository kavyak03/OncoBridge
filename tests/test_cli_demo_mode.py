from pathlib import Path

import pandas as pd

from ehr_fhir_genomics_toolkit.cli import main as cli_main


def test_cli_demo_mode_creates_output(tmp_path: Path, monkeypatch):
    out_csv = tmp_path / "demo_out.csv"
    monkeypatch.setenv("PROVENANCE_LOG_DIR", str(tmp_path / "run_logs"))

    cli_main(
        [
            "--demo-mode",
            "--signature-profile",
            "sclc",
            "--compute-signatures",
            "--include-variants",
            "--output",
            str(out_csv),
        ]
    )

    assert out_csv.exists(), "Expected demo output CSV to be created"

    df = pd.read_csv(out_csv)
    assert "sample_id" in df.columns
    assert "patient_id" in df.columns

    sig_cols = [c for c in df.columns if c.startswith("SCLC_")]
    assert len(sig_cols) >= 1, "Expected at least one SCLC_* signature column"
