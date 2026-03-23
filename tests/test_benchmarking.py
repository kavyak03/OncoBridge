from pathlib import Path

from ehr_fhir_genomics_toolkit.benchmarking import run_benchmark


def test_benchmark_writes_outputs(tmp_path: Path):
    summary = run_benchmark(
        mode="demo",
        n_samples=50,
        repeats=2,
        out_dir=str(tmp_path),
        signature_profile="generic_oncology",
    )

    assert "naive_vs_sdk" in summary
    assert "semi_naive_vs_sdk" in summary
    assert (tmp_path / "benchmark_runs.csv").exists()
    assert (tmp_path / "benchmark_summary.json").exists()