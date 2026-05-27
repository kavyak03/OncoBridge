from __future__ import annotations

from typing import Any

import pandas as pd
import tiledb

from .tiledb_utils import (
    DEFAULT_MAX_GENES,
    DEFAULT_MAX_SAMPLE_IDS,
    assert_query_size,
    open_ctx,
    require_attributes,
    require_dimensions,
)


def fetch_expression_long(
    expression_uri: str,
    sample_ids: list[str],
    genes: list[str],
    attrs: list[str] | None = None,
    tiledb_config: dict[str, Any] | None = None,
    *,
    allow_full_scan: bool = False,
    max_sample_ids: int = DEFAULT_MAX_SAMPLE_IDS,
    max_genes: int = DEFAULT_MAX_GENES,
) -> pd.DataFrame:
    """
    Fetch expression in long format for multiple genes.

    The production default is to fail fast on schema/indexing errors rather than
    silently scanning the full array. ``allow_full_scan=True`` is available for
    exploratory local debugging only.
    """
    attrs = attrs or ["expression_value"]
    sample_ids = [str(s) for s in assert_query_size("sample_ids", sample_ids, max_sample_ids)]
    genes = [str(g) for g in assert_query_size("genes", genes, max_genes)]

    ctx = open_ctx(tiledb_config or {})
    with tiledb.open(expression_uri, ctx=ctx) as array:
        dims = require_dimensions(
            array,
            {
                "sample_id": ["sample_id"],
                "gene": ["gene", "gene_symbol"],
            },
        )
        require_attributes(array, attrs)
        query_index = {dims["sample_id"]: sample_ids, dims["gene"]: genes}

        try:
            df = array.query(attrs=attrs).df[query_index].reset_index(drop=False)
        except (tiledb.TileDBError, ValueError) as exc:
            if not allow_full_scan:
                raise RuntimeError(
                    f"TileDB expression query failed for {expression_uri!r}. "
                    "Full-array fallback is disabled for production safety."
                ) from exc
            df = array.query(attrs=attrs).df[:].reset_index()
            df = df[df[dims["sample_id"]].isin(sample_ids) & df[dims["gene"]].isin(genes)].copy()

    if dims["gene"] != "gene":
        df = df.rename(columns={dims["gene"]: "gene"})
    if dims["sample_id"] != "sample_id":
        df = df.rename(columns={dims["sample_id"]: "sample_id"})

    if "expression_value" not in df.columns:
        raise ValueError("Expected attribute 'expression_value' not found in expression array.")
    return df[["sample_id", "gene", "expression_value"]]


def pivot_expression_wide(expr_long: pd.DataFrame) -> pd.DataFrame:
    """
    Convert (sample_id, gene, expression_value) -> wide columns per gene.
    """
    required = {"sample_id", "gene", "expression_value"}
    missing = required - set(expr_long.columns)
    if missing:
        raise ValueError(f"Expression dataframe missing required columns: {sorted(missing)}")

    wide = expr_long.pivot_table(
        index="sample_id",
        columns="gene",
        values="expression_value",
        aggfunc="mean",
    )
    wide = wide.reset_index()
    wide.columns = [str(c) for c in wide.columns]
    return wide
