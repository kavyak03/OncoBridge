from __future__ import annotations
from typing import Any, Dict, List, Optional
import pandas as pd
import tiledb
from .tiledb_utils import open_ctx

def fetch_expression_long(
    expression_uri: str,
    sample_ids: List[str],
    genes: List[str],
    attrs: Optional[List[str]] = None,
    tiledb_config: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    """
    Fetch expression in long format for multiple genes.
    Assumes TileDB dims include sample_id and gene (or gene_symbol).
    """
    attrs = attrs or ["expression_value"]
    ctx = open_ctx(tiledb_config or {})
    with tiledb.open(expression_uri, ctx=ctx) as A:
        try:
            df = A.query(attrs=attrs).df[dict(sample_id=sample_ids, gene=genes)]
            df = df.reset_index(drop=False)
        except Exception:
            # dev fallback
            df = A.query(attrs=attrs).df[:].reset_index()
            gene_col = "gene" if "gene" in df.columns else ("gene_symbol" if "gene_symbol" in df.columns else None)
            if gene_col:
                df = df[df[gene_col].isin(genes)]
                if gene_col != "gene":
                    df = df.rename(columns={gene_col: "gene"})
            if "sample_id" in df.columns:
                df = df[df["sample_id"].isin(sample_ids)]
    # Ensure expected columns
    if "gene" not in df.columns:
        df["gene"] = None
    if "expression_value" not in df.columns:
        # if attr named differently, user should adapt
        raise ValueError("Expected attribute 'expression_value' not found in expression array.")
    return df[["sample_id", "gene", "expression_value"]]

def pivot_expression_wide(expr_long: pd.DataFrame) -> pd.DataFrame:
    """
    Convert (sample_id, gene, expression_value) → wide columns per gene.
    """
    wide = expr_long.pivot_table(index="sample_id", columns="gene", values="expression_value", aggfunc="mean")
    wide = wide.reset_index()
    wide.columns = [str(c) for c in wide.columns]
    return wide
