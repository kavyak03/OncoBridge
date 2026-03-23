from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
import tiledb

from .tiledb_utils import open_ctx


def fetch_variants_for_samples(
    variants_uri: str,
    sample_ids: List[str],
    attrs: Optional[List[str]] = None,
    tiledb_config: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    """
    Fetch variants for the requested sample_ids.

    Supports both:
    - minimal mock arrays: GENE, GT, QUAL
    - richer real arrays: GENE, GT, QUAL, CHROM, POS, REF, ALT
    """
    preferred_attrs = attrs or ["GENE", "GT", "QUAL", "CHROM", "POS", "REF", "ALT"]

    ctx = open_ctx(tiledb_config or {})
    with tiledb.open(variants_uri, ctx=ctx) as A:
        available_attrs = [A.schema.attr(i).name for i in range(A.schema.nattr)]
        selected_attrs = [a for a in preferred_attrs if a in available_attrs]

        if not selected_attrs:
            raise ValueError(
                f"No requested attrs found in TileDB array. "
                f"Requested={preferred_attrs}, available={available_attrs}"
            )

        try:
            df = A.query(attrs=selected_attrs).df[dict(sample_id=sample_ids)]
            df = df.reset_index(drop=False)
        except Exception:
            df = A.query(attrs=selected_attrs).df[:].reset_index()
            if "sample_id" in df.columns:
                df = df[df["sample_id"].isin(sample_ids)].copy()

    return df


def summarize_mutations_presence(
    variants_df: pd.DataFrame,
    genes: List[str],
) -> pd.DataFrame:
    """
    Build per-sample mutation presence flags like:
    mut_TP53, mut_RB1, mut_MYC
    """
    if variants_df is None or variants_df.empty:
        return pd.DataFrame(columns=["sample_id"] + [f"mut_{g}" for g in genes])

    if "sample_id" not in variants_df.columns or "GENE" not in variants_df.columns:
        raise ValueError("variants_df must contain 'sample_id' and 'GENE' columns.")

    v = variants_df.copy()
    v["GENE"] = v["GENE"].astype(str)

    v = v[v["GENE"].isin(genes)].copy()
    if v.empty:
        sample_ids = (
            variants_df["sample_id"].dropna().astype(str).unique().tolist()
            if "sample_id" in variants_df.columns
            else []
        )
        out = pd.DataFrame({"sample_id": sample_ids})
        for g in genes:
            out[f"mut_{g}"] = 0
        return out

    flags = (
        v.assign(present=1)
        .pivot_table(
            index="sample_id",
            columns="GENE",
            values="present",
            aggfunc="max",
            fill_value=0,
        )
        .reset_index()
    )

    for g in genes:
        if g not in flags.columns:
            flags[g] = 0
        flags.rename(columns={g: f"mut_{g}"}, inplace=True)

    wanted_cols = ["sample_id"] + [f"mut_{g}" for g in genes]
    for c in wanted_cols:
        if c not in flags.columns:
            flags[c] = 0

    return flags[wanted_cols]