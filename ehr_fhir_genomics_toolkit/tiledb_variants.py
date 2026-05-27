from __future__ import annotations

from typing import Any

import pandas as pd
import tiledb

from .tiledb_utils import (
    DEFAULT_MAX_SAMPLE_IDS,
    assert_query_size,
    open_ctx,
    require_dimensions,
    schema_attribute_names,
)


def fetch_variants_for_samples(
    variants_uri: str,
    sample_ids: list[str],
    attrs: list[str] | None = None,
    tiledb_config: dict[str, Any] | None = None,
    *,
    allow_full_scan: bool = False,
    max_sample_ids: int = DEFAULT_MAX_SAMPLE_IDS,
) -> pd.DataFrame:
    """
    Fetch variants for the requested sample_ids.

    Supports both:
    - minimal mock arrays: GENE, GT, QUAL
    - richer real arrays: GENE, GT, QUAL, CHROM, POS, REF, ALT
    """
    preferred_attrs = attrs or ["GENE", "GT", "QUAL", "CHROM", "POS", "REF", "ALT"]
    sample_ids = [str(s) for s in assert_query_size("sample_ids", sample_ids, max_sample_ids)]

    ctx = open_ctx(tiledb_config or {})
    with tiledb.open(variants_uri, ctx=ctx) as array:
        dims = require_dimensions(array, {"sample_id": ["sample_id"]})
        available_attrs = schema_attribute_names(array)
        selected_attrs = [a for a in preferred_attrs if a in available_attrs]

        if not selected_attrs:
            raise ValueError(
                f"No requested attrs found in TileDB array. "
                f"Requested={preferred_attrs}, available={available_attrs}"
            )

        try:
            df = (
                array.query(attrs=selected_attrs)
                .df[{dims["sample_id"]: sample_ids}]
                .reset_index(drop=False)
            )
        except (tiledb.TileDBError, ValueError) as exc:
            if not allow_full_scan:
                raise RuntimeError(
                    f"TileDB variants query failed for {variants_uri!r}. "
                    "Full-array fallback is disabled for production safety."
                ) from exc
            df = array.query(attrs=selected_attrs).df[:].reset_index()
            df = df[df[dims["sample_id"]].isin(sample_ids)].copy()

    if dims["sample_id"] != "sample_id":
        df = df.rename(columns={dims["sample_id"]: "sample_id"})
    return df


def summarize_mutations_presence(
    variants_df: pd.DataFrame,
    genes: list[str],
) -> pd.DataFrame:
    """
    Build per-sample mutation presence flags like:
    mut_TP53, mut_RB1, mut_MYC
    """
    genes = [str(g).strip() for g in genes if str(g).strip()]
    if variants_df is None or variants_df.empty:
        return pd.DataFrame(columns=["sample_id"] + [f"mut_{g}" for g in genes])

    if "sample_id" not in variants_df.columns or "GENE" not in variants_df.columns:
        raise ValueError("variants_df must contain 'sample_id' and 'GENE' columns.")

    v = variants_df.copy()
    v["sample_id"] = v["sample_id"].astype(str)
    v["GENE"] = v["GENE"].astype(str)

    all_sample_ids = v["sample_id"].dropna().astype(str).unique().tolist()
    v = v[v["GENE"].isin(genes)].copy()

    if v.empty:
        out = pd.DataFrame({"sample_id": all_sample_ids})
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

    flags = pd.DataFrame({"sample_id": all_sample_ids}).merge(flags, on="sample_id", how="left")

    for g in genes:
        if g not in flags.columns:
            flags[g] = 0
        flags[g] = pd.to_numeric(flags[g], errors="coerce").fillna(0).astype(int)
        flags.rename(columns={g: f"mut_{g}"}, inplace=True)

    wanted_cols = ["sample_id"] + [f"mut_{g}" for g in genes]
    for c in wanted_cols:
        if c not in flags.columns:
            flags[c] = 0

    return flags[wanted_cols]
