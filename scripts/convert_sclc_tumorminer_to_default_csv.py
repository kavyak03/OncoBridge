"""Convert SCLC TumorMiner-style attached files to the repo's default CSV ingestion format."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from ehr_fhir_genomics_toolkit.sclc_real_example import DEFAULT_PANEL_GENES, write_converted_bundle

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--input-dir", default="data/real_examples/sclc_tumorminer/raw")
    p.add_argument("--out-dir", default="data/real_examples/sclc_tumorminer/converted")
    p.add_argument("--genes", default=",".join(DEFAULT_PANEL_GENES))
    return p.parse_args()

def main():
    args = parse_args()
    input_dir = Path(args.input_dir)
    genes = [g.strip() for g in args.genes.split(",") if g.strip()]
    outputs = write_converted_bundle(
        annotation_path=input_dir / "Sample_annotation_patient.txt",
        variant_path=input_dir / "sclc_Patient data_var.txt",
        expression_path=input_dir / "sclc_Patient data_xsq.txt",
        out_dir=args.out_dir,
        genes=genes,
    )
    print(json.dumps({"genes": genes, "outputs": outputs}, indent=2))

if __name__ == "__main__":
    main()
