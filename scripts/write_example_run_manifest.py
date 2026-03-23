from __future__ import annotations

import json

from ehr_fhir_genomics_toolkit.run_manifest import build_run_manifest, make_run_id, write_run_manifest


def main():
    manifest = build_run_manifest(
        run_id=make_run_id(prefix="example_pipeline"),
        mode="demo",
        config_path=None,
        cohort={
            "diagnosis": "small cell lung cancer",
            "min_age": 18,
            "start_date": "2018-01-01",
            "end_date": "2020-12-31",
        },
        features={
            "compute_signatures": True,
            "include_variants": True,
        },
        inputs={
            "sql_table": "clinical_metadata",
            "expression_source": "TileDB expression array",
            "variants_source": "TileDB variants array",
        },
        outputs={
            "dataset_csv": "demo_sclc_dataset.csv",
            "provenance_log": "run_logs/provenance.jsonl",
        },
    )
    path = write_run_manifest(manifest)
    print(json.dumps({"manifest_path": path}, indent=2))


if __name__ == "__main__":
    main()