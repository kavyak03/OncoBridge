from pathlib import Path

import pandas as pd
import pytest

from ehr_fhir_genomics_toolkit.cli import main as cli_main


def _tiledb_available() -> bool:
    try:
        import tiledb  # noqa: F401

        return True
    except Exception:
        return False


def _mock_arrays_exist(repo_root: Path) -> bool:
    expr = repo_root / "data" / "tiledb" / "expression_array"
    var = repo_root / "data" / "tiledb" / "variants_array"
    return expr.exists() and var.exists()


@pytest.mark.skipif(not _tiledb_available(), reason="TileDB Python package not available")
def test_cli_mock_infra_runs_if_arrays_exist(tmp_path: Path, monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]
    if not _mock_arrays_exist(repo_root):
        pytest.skip(
            "Mock TileDB arrays not found. Run `python scripts/make_mock_data.py` to generate them."
        )

    out_csv = tmp_path / "mockinfra_out.csv"
    monkeypatch.chdir(repo_root)
    monkeypatch.setenv("PROVENANCE_LOG_DIR", str(tmp_path / "run_logs"))

    cli_main(
        [
            "--config",
            "config.mock.yaml",
            "--therapy-mode",
            "join_table",
            "--signature-profile",
            "sclc",
            "--regimen-profile",
            "sclc",
            "--regimen-bucket",
            "first_line_platinum_etoposide_io",
            "--compute-signatures",
            "--include-variants",
            "--output",
            str(out_csv),
        ]
    )

    assert out_csv.exists(), "Expected mock infra output CSV to be created"
    df = pd.read_csv(out_csv)
    assert "sample_id" in df.columns
    assert "patient_id" in df.columns
    assert any(c.startswith("SCLC_") for c in df.columns)
    assert any(c.startswith("mut_") for c in df.columns)
