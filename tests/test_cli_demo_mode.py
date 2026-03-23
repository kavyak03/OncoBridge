from pathlib import Path
import os
import subprocess
import sys

import pandas as pd


def test_cli_demo_mode_creates_output(tmp_path: Path):
    out_csv = tmp_path / "demo_out.csv"
    cmd = [
        sys.executable,
        "-m",
        "ehr_fhir_genomics_toolkit.cli",
        "--demo-mode",
        "--signature-profile",
        "sclc",
        "--compute-signatures",
        "--include-variants",
        "--output",
        str(out_csv),
    ]
    env = os.environ.copy()
    env["PROVENANCE_LOG_DIR"] = str(tmp_path / "run_logs")

    proc = subprocess.run(
        cmd,
        cwd=str(Path(__file__).resolve().parents[1]),
        env=env,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, f"CLI failed. stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    assert out_csv.exists(), "Expected demo output CSV to be created"

    df = pd.read_csv(out_csv)
    assert "sample_id" in df.columns
    assert "patient_id" in df.columns

    sig_cols = [c for c in df.columns if c.startswith("SCLC_")]
    assert len(sig_cols) >= 1, "Expected at least one SCLC_* signature column"