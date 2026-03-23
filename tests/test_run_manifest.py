import json
from pathlib import Path

from ehr_fhir_genomics_toolkit.run_manifest import build_run_manifest, make_run_id, write_run_manifest


def test_write_run_manifest(tmp_path: Path):
    manifest = build_run_manifest(
        run_id=make_run_id(prefix="test"),
        mode="demo",
        config_path=None,
        cohort={"diagnosis": "small cell lung cancer"},
        features={"compute_signatures": True},
        inputs={"source": "synthetic"},
        outputs={"dataset_csv": "demo.csv"},
    )
    out = write_run_manifest(manifest, log_dir=str(tmp_path))
    assert Path(out).exists()
    loaded = json.loads(Path(out).read_text(encoding="utf-8"))
    assert loaded["mode"] == "demo"
    assert loaded["outputs"]["dataset_csv"] == "demo.csv"