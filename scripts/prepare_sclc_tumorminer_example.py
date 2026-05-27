"""Prepare a fully local real-patient example from the included SCLC TumorMiner-style files."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import tiledb

from ehr_fhir_genomics_toolkit.data_contracts import (
    validate_clinical_csv,
    validate_expression_csv,
    validate_therapy_csv,
    validate_variant_csv,
)
from ehr_fhir_genomics_toolkit.io_safety import atomic_write_text, safe_rmtree, safe_unlink
from ehr_fhir_genomics_toolkit.sclc_real_example import DEFAULT_PANEL_GENES, write_converted_bundle


def build_sqlite(clinical_csv: Path, therapy_csv: Path, sqlite_path: Path, allowed_root: Path):
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    if sqlite_path.exists():
        safe_unlink(sqlite_path, allowed_roots=[allowed_root])
    with sqlite3.connect(sqlite_path) as conn:
        validate_clinical_csv(pd.read_csv(clinical_csv)).to_sql(
            "clinical_metadata", conn, index=False, if_exists="replace"
        )
        if therapy_csv.exists():
            validate_therapy_csv(pd.read_csv(therapy_csv)).to_sql(
                "therapy_lines", conn, index=False, if_exists="replace"
            )


def build_expression_array(expression_csv: Path, uri: Path, allowed_root: Path):
    df = validate_expression_csv(pd.read_csv(expression_csv))
    if uri.exists():
        safe_rmtree(uri, allowed_roots=[allowed_root])
    samples = sorted(df["sample_id"].astype(str).unique().tolist())
    genes = sorted(df["gene"].astype(str).unique().tolist())
    dom = tiledb.Domain(
        tiledb.Dim(
            name="sample_id",
            domain=(min(samples), max(samples)),
            tile=min(100, len(samples)),
            dtype="ascii",
        ),
        tiledb.Dim(
            name="gene", domain=(min(genes), max(genes)), tile=min(100, len(genes)), dtype="ascii"
        ),
    )
    schema = tiledb.ArraySchema(
        domain=dom, attrs=[tiledb.Attr(name="expression_value", dtype=np.float32)], sparse=True
    )
    tiledb.SparseArray.create(str(uri), schema)
    with tiledb.SparseArray(str(uri), mode="w") as array:
        array[df["sample_id"].astype(str).tolist(), df["gene"].astype(str).tolist()] = {
            "expression_value": df["expression_value"].astype("float32").to_numpy()
        }


def _optional_series(df: pd.DataFrame, column: str, default: object = "") -> pd.Series:
    if column in df.columns:
        return df[column]
    return pd.Series([default] * len(df))


def build_variants_array(variants_csv: Path, uri: Path, allowed_root: Path):
    df = validate_variant_csv(pd.read_csv(variants_csv))
    if uri.exists():
        safe_rmtree(uri, allowed_roots=[allowed_root])
    samples = sorted(df["sample_id"].astype(str).unique().tolist())
    var_ids = sorted(df["var_id"].astype(str).unique().tolist())
    dom = tiledb.Domain(
        tiledb.Dim(
            name="sample_id",
            domain=(min(samples), max(samples)),
            tile=min(100, len(samples)),
            dtype="ascii",
        ),
        tiledb.Dim(
            name="var_id",
            domain=(min(var_ids), max(var_ids)),
            tile=min(500, len(var_ids)),
            dtype="ascii",
        ),
    )
    schema = tiledb.ArraySchema(
        domain=dom,
        attrs=[
            tiledb.Attr(name="GENE", dtype="ascii"),
            tiledb.Attr(name="GT", dtype=np.int8),
            tiledb.Attr(name="QUAL", dtype=np.float32),
            tiledb.Attr(name="CHROM", dtype="ascii"),
            tiledb.Attr(name="POS", dtype=np.int64),
            tiledb.Attr(name="REF", dtype="ascii"),
            tiledb.Attr(name="ALT", dtype="ascii"),
        ],
        sparse=True,
    )
    tiledb.SparseArray.create(str(uri), schema)
    with tiledb.SparseArray(str(uri), mode="w") as array:
        array[df["sample_id"].astype(str).tolist(), df["var_id"].astype(str).tolist()] = {
            "GENE": df["GENE"].astype(str).tolist(),
            "GT": df["GT"].astype("int8").to_numpy(),
            "QUAL": df["QUAL"].astype("float32").to_numpy(),
            "CHROM": _optional_series(df, "CHROM").astype(str).tolist(),
            "POS": pd.to_numeric(_optional_series(df, "POS", 0), errors="coerce")
            .fillna(0)
            .astype("int64")
            .to_numpy(),
            "REF": _optional_series(df, "REF").astype(str).tolist(),
            "ALT": _optional_series(df, "ALT").astype(str).tolist(),
        }


def parse_args(argv: list[str] | None = None):
    p = argparse.ArgumentParser()
    p.add_argument("--input-dir", default="data/real_examples/sclc_tumorminer/raw")
    p.add_argument("--work-dir", default="data/real_examples/sclc_tumorminer")
    p.add_argument("--genes", default=",".join(DEFAULT_PANEL_GENES))
    return p.parse_args(argv)


def main(argv: list[str] | None = None):
    args = parse_args(argv)
    work_dir = Path(args.work_dir)
    raw_dir = Path(args.input_dir)
    conv_dir = work_dir / "converted"
    db_dir = work_dir / "db"
    allowed_root = work_dir.resolve()
    genes = [g.strip() for g in args.genes.split(",") if g.strip()]

    outputs = write_converted_bundle(
        raw_dir / "Sample_annotation_patient.txt",
        raw_dir / "sclc_Patient data_var.txt",
        raw_dir / "sclc_Patient data_xsq.txt",
        conv_dir,
        genes=genes,
    )
    sqlite_path = db_dir / "real_ehr.sqlite"
    expr_uri = db_dir / "expression_array"
    var_uri = db_dir / "variants_array"
    db_dir.mkdir(parents=True, exist_ok=True)
    build_sqlite(
        Path(outputs["clinical_csv"]), Path(outputs["therapy_csv"]), sqlite_path, allowed_root
    )
    build_expression_array(Path(outputs["expression_panel_csv"]), expr_uri, allowed_root)
    build_variants_array(Path(outputs["variants_csv"]), var_uri, allowed_root)

    config_path = work_dir / "config.sclc_tumorminer_panel.yaml"
    atomic_write_text(
        f'''sql:\n  sqlalchemy_url: "sqlite:///{sqlite_path.as_posix()}"\n  tables:\n    clinical_metadata: "clinical_metadata"\n    therapies: "therapy_lines"\n\ntiledb:\n  expression_uri: "{expr_uri.as_posix()}"\n  variants_uri: "{var_uri.as_posix()}"\n  config: {{}}\n\nprovenance:\n  log_dir: "run_logs"\n  include_raw_sql: false\n  include_raw_tiledb_uri: false\n  include_raw_paths: false\n''',
        config_path,
    )
    print(
        json.dumps(
            {
                "genes": genes,
                "converted_outputs": outputs,
                "sqlite_path": str(sqlite_path),
                "expression_uri": str(expr_uri),
                "variants_uri": str(var_uri),
                "config_path": str(config_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
