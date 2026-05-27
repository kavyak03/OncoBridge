"""Load user-supplied expression/variant CSV files into local TileDB arrays."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import tiledb

from ehr_fhir_genomics_toolkit.data_contracts import validate_expression_csv, validate_variant_csv
from ehr_fhir_genomics_toolkit.io_safety import safe_rmtree


def build_expression_array(df: pd.DataFrame, uri: str):
    df = validate_expression_csv(df)

    path = Path(uri)
    if path.exists():
        safe_rmtree(path, allowed_roots=[Path("data").resolve()])

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
    tiledb.SparseArray.create(str(path), schema)

    with tiledb.SparseArray(str(path), mode="w") as array:
        array[df["sample_id"].astype(str).tolist(), df["gene"].astype(str).tolist()] = {
            "expression_value": df["expression_value"].astype("float32").to_numpy()
        }


def build_variants_array(df: pd.DataFrame, uri: str):
    df = validate_variant_csv(df)

    path = Path(uri)
    if path.exists():
        safe_rmtree(path, allowed_roots=[Path("data").resolve()])

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
        ],
        sparse=True,
    )
    tiledb.SparseArray.create(str(path), schema)

    with tiledb.SparseArray(str(path), mode="w") as array:
        array[df["sample_id"].astype(str).tolist(), df["var_id"].astype(str).tolist()] = {
            "GENE": df["GENE"].astype(str).tolist(),
            "GT": df["GT"].astype("int8").to_numpy(),
            "QUAL": df["QUAL"].astype("float32").to_numpy(),
        }


def parse_args(argv: list[str] | None = None):
    p = argparse.ArgumentParser()
    p.add_argument("--expression-csv", default=None)
    p.add_argument("--expression-uri", default="data/real_tiledb/expression_array")
    p.add_argument("--variants-csv", default=None)
    p.add_argument("--variants-uri", default="data/real_tiledb/variants_array")
    return p.parse_args(argv)


def main(argv: list[str] | None = None):
    args = parse_args(argv)
    if not args.expression_csv and not args.variants_csv:
        raise SystemExit("Provide at least one of --expression-csv or --variants-csv")

    if args.expression_csv:
        expr = pd.read_csv(args.expression_csv)
        build_expression_array(expr, args.expression_uri)
        print(f"Wrote expression TileDB array: {args.expression_uri}")

    if args.variants_csv:
        var = pd.read_csv(args.variants_csv)
        build_variants_array(var, args.variants_uri)
        print(f"Wrote variants TileDB array: {args.variants_uri}")


if __name__ == "__main__":
    main()
