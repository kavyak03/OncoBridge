from __future__ import annotations

import argparse
import logging
import os
from datetime import date

import pandas as pd
from pydantic import ValidationError

from .cohort_dsl import apply_dsl_to_cohortspec, dsl_examples
from .config import load_config
from .demo_data import (
    generate_demo_clinical_cohort,
    generate_demo_expression_long,
    generate_demo_variants,
)
from .io_safety import atomic_write_csv
from .merger import assert_unique_key, attach_features, merge_clinical_expression
from .models import CohortSpec, ExpressionSpec, RunSpec, VariantSpec
from .provenance import ProvenanceLogger
from .signatures import (
    compute_signature_scores,
    default_gene_list,
    load_signature_definitions,
)
from .sql_connector import cohort_with_therapy_sql, generic_cohort_sql, query_sql
from .therapy_buckets import (
    apply_regimen_bucket_filter,
    list_bucket_names,
    load_regimen_bucket_definitions,
)
from .tiledb_expression import fetch_expression_long, pivot_expression_wide
from .tiledb_variants import fetch_variants_for_samples, summarize_mutations_presence

DEFAULT_MUTATION_GENES = ["TP53", "RB1", "MYC"]
LOGGER = logging.getLogger(__name__)


def _parse_date(s: str) -> date:
    try:
        y, m, d = s.split("-")
        return date(int(y), int(m), int(d))
    except Exception as exc:  # noqa: BLE001 - user-facing date parse boundary
        raise ValueError(f"Invalid date {s!r}; expected YYYY-MM-DD") from exc


def parse_args(argv: list[str] | None = None):
    p = argparse.ArgumentParser(
        prog="ehr_fhir_genomics_toolkit",
        description=(
            "Build an analysis-ready cohort DataFrame from SQL + TileDB "
            "(expression + optional variants), with reproducible provenance. "
            "The SDK is disease-agnostic and ships with an SCLC example profile."
        ),
    )

    p.add_argument("--demo-mode", action="store_true")
    p.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config.yaml (or set EHR_TOOLKIT_CONFIG). Not required if --demo-mode is set.",
    )

    p.add_argument(
        "--cohort-dsl",
        default="",
        help=f"Optional cohort DSL. Example: {dsl_examples()}",
    )

    p.add_argument("--diagnosis", default="small cell lung cancer")
    p.add_argument("--min-age", type=int, default=18)
    p.add_argument("--start-date", default="2018-01-01")
    p.add_argument("--end-date", default="2020-12-31")

    p.add_argument("--therapy-mode", choices=["none", "join_table"], default="none")

    p.add_argument("--regimen-bucket", default="any")
    p.add_argument("--regimen-profile", default="generic_oncology")
    p.add_argument("--regimen-config", default="")

    p.add_argument("--signature-profile", default="generic_oncology")
    p.add_argument("--signature-config", default="")

    p.add_argument(
        "--genes",
        default="",
        help="Comma-separated gene list to query. If omitted, genes are inferred from the active signature definition.",
    )

    p.add_argument("--compute-signatures", action="store_true")
    p.add_argument("--include-variants", action="store_true")
    p.add_argument("--output", default="merged_dataset.csv")
    p.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return p.parse_args(argv)


def _build_runspec(args, genes: list[str]) -> RunSpec:
    cohort = CohortSpec(
        diagnosis=args.diagnosis,
        min_age=args.min_age,
        start_date=_parse_date(args.start_date),
        end_date=_parse_date(args.end_date),
        therapy_mode=args.therapy_mode,
        regimen_bucket=args.regimen_bucket,
    )
    cohort = apply_dsl_to_cohortspec(cohort, args.cohort_dsl)

    expr = ExpressionSpec(genes=genes)
    variants = VariantSpec(
        enabled=bool(args.include_variants),
        mutation_genes=DEFAULT_MUTATION_GENES,
    )

    mode = (
        "demo"
        if args.demo_mode
        else ("mock_infra" if os.path.basename(args.config) == "config.mock.yaml" else "real_infra")
    )

    return RunSpec(
        mode=mode,
        cohort=cohort,
        expression=expr,
        variants=variants,
        compute_signatures=bool(args.compute_signatures),
        output=args.output,
    )


def _build_logger(args, spec: RunSpec) -> ProvenanceLogger:
    if spec.mode == "demo":
        log_dir = os.environ.get("PROVENANCE_LOG_DIR", "run_logs")
        return ProvenanceLogger(log_dir)

    cfg_tmp = load_config(args.config)
    log_dir = os.environ.get("PROVENANCE_LOG_DIR", cfg_tmp.provenance.log_dir)
    return ProvenanceLogger(
        log_dir,
        include_raw_sql=cfg_tmp.provenance.include_raw_sql,
        include_raw_tiledb_uri=cfg_tmp.provenance.include_raw_tiledb_uri,
        include_raw_paths=cfg_tmp.provenance.include_raw_paths,
    )


def _log_profiles(prov: ProvenanceLogger, args, signature_defs, bucket_defs) -> None:
    prov.log_event(
        "signature_profile",
        {
            "signature_profile": args.signature_profile,
            "signature_config": args.signature_config or None,
            "signature_names": list(signature_defs.keys()),
        },
    )
    prov.log_event(
        "regimen_profile",
        {
            "regimen_profile": args.regimen_profile,
            "regimen_config": args.regimen_config or None,
            "available_buckets": list_bucket_names(bucket_defs),
        },
    )


def _attach_optional_features(
    merged: pd.DataFrame,
    expr_wide: pd.DataFrame,
    clinical_df: pd.DataFrame,
    spec: RunSpec,
    prov: ProvenanceLogger,
    signature_defs,
) -> pd.DataFrame:
    if spec.compute_signatures:
        sig_scores = compute_signature_scores(expr_wide, signature_definitions=signature_defs)
        prov.log_dataframe("signature_scores", sig_scores)
        merged = attach_features(merged, sig_scores, join_key="sample_id", how="left")
        prov.log_dataframe("merged_with_signatures", merged)

    if spec.variants.enabled:
        variants = generate_demo_variants(clinical_df["sample_id"].astype(str).tolist(), seed=7)
        prov.log_dataframe("variants_raw", variants)
        mut_flags = summarize_mutations_presence(variants, spec.variants.mutation_genes)
        prov.log_dataframe("mutation_flags", mut_flags)
        merged = attach_features(merged, mut_flags, join_key="sample_id", how="left")
        prov.log_dataframe("merged_with_mutations", merged)

    return merged


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level), format="%(levelname)s:%(name)s:%(message)s"
    )

    signature_defs = load_signature_definitions(
        signature_config=args.signature_config or None,
        profile=args.signature_profile,
    )

    if args.genes.strip():
        genes = [g.strip() for g in args.genes.split(",") if g.strip()]
    else:
        genes = default_gene_list(signature_defs)

    bucket_defs = load_regimen_bucket_definitions(
        regimen_config=args.regimen_config or None,
        profile=args.regimen_profile,
    )

    try:
        spec = _build_runspec(args, genes)
    except (ValidationError, ValueError) as exc:
        raise SystemExit(f"Invalid run specification: {exc}") from exc

    prov = _build_logger(args, spec)
    prov.log_event("run_spec", spec.model_dump())
    _log_profiles(prov, args, signature_defs, bucket_defs)

    # ------------------------------------------------------------------
    # DEMO MODE
    # ------------------------------------------------------------------
    if spec.mode == "demo":
        prov.log_event("mode", {"demo_mode": True})

        clinical_df = generate_demo_clinical_cohort(
            n_samples=50,
            seed=7,
            diagnosis=spec.cohort.diagnosis,
            include_therapy=(spec.cohort.therapy_mode == "join_table"),
        )

        if spec.cohort.therapy_mode == "join_table" and spec.cohort.regimen_bucket != "any":
            clinical_df = apply_regimen_bucket_filter(
                clinical_df=clinical_df,
                bucket_name=spec.cohort.regimen_bucket,
                bucket_defs=bucket_defs,
            )

        prov.log_dataframe("clinical_df", clinical_df)
        if clinical_df.empty:
            raise SystemExit(
                "No demo cohort rows remain after applying therapy / regimen filters. "
                "Try a different regimen bucket or use --regimen-bucket any."
            )

        expr_long = generate_demo_expression_long(clinical_df["sample_id"].tolist(), genes, seed=7)
        prov.log_dataframe("expr_long", expr_long)

        expr_wide = pivot_expression_wide(expr_long)
        prov.log_dataframe("expr_wide", expr_wide)

        merged = merge_clinical_expression(clinical_df, expr_wide, join_key="sample_id")
        prov.log_dataframe("merged_clinical_expr", merged)
        merged = _attach_optional_features(
            merged, expr_wide, clinical_df, spec, prov, signature_defs
        )

        atomic_write_csv(merged, spec.output, index=False)
        prov.log_output(spec.output)
        LOGGER.info(
            "[DEMO MODE] Wrote %s (rows=%s, cols=%s)", spec.output, len(merged), merged.shape[1]
        )
        LOGGER.info("Provenance log: %s", os.path.join(prov.log_dir, "provenance.jsonl"))
        return

    # ------------------------------------------------------------------
    # MOCK / REAL INFRA MODE
    # ------------------------------------------------------------------
    cfg = load_config(args.config)
    if cfg.sql is None or cfg.tiledb is None:
        raise SystemExit(
            "config.yaml must define both `sql.sqlalchemy_url` and `tiledb.expression_uri` for non-demo runs. "
            "For real credentials, prefer SQLALCHEMY_URL/TILEDB_* environment variables."
        )

    clinical_table = cfg.sql.tables.clinical_metadata
    therapy_table = cfg.sql.tables.therapies

    sql_text = (
        cohort_with_therapy_sql(clinical_table, therapy_table)
        if spec.cohort.therapy_mode == "join_table"
        else generic_cohort_sql(clinical_table)
    )

    params = {
        "diagnosis": spec.cohort.diagnosis,
        "min_age": spec.cohort.min_age,
        "start_date": spec.cohort.start_date.isoformat(),
        "end_date": spec.cohort.end_date.isoformat(),
    }

    prov.log_sql(cfg.sql.sqlalchemy_url_plain, sql_text, params)
    clinical_df = query_sql(cfg.sql.sqlalchemy_url_plain, sql_text, params)
    if "collection_date" in clinical_df.columns:
        clinical_df["collection_date"] = pd.to_datetime(
            clinical_df["collection_date"], errors="coerce"
        )
    prov.log_dataframe("clinical_df", clinical_df)

    if spec.cohort.therapy_mode == "join_table" and spec.cohort.regimen_bucket != "any":
        clinical_df = apply_regimen_bucket_filter(
            clinical_df=clinical_df,
            bucket_name=spec.cohort.regimen_bucket,
            bucket_defs=bucket_defs,
        )
        prov.log_dataframe("clinical_df_regimen_filtered", clinical_df)

    if clinical_df.empty:
        raise SystemExit(
            "No cohort rows returned from SQL after applying filters. "
            "Check diagnosis, date range, therapy mode, and regimen bucket."
        )
    assert_unique_key(clinical_df, "sample_id", "clinical_df after SQL/therapy filtering")

    sample_ids = clinical_df["sample_id"].astype(str).tolist()

    prov.log_tiledb(
        cfg.tiledb.expression_uri,
        {
            "dims": {"sample_id": f"{len(sample_ids)} ids", "gene": genes},
            "attrs": ["expression_value"],
        },
    )
    expr_long = fetch_expression_long(
        cfg.tiledb.expression_uri,
        sample_ids=sample_ids,
        genes=genes,
        tiledb_config=cfg.tiledb.config,
        # Local mock TileDB arrays may require full-scan fallback depending on
        # TileDB/Python indexing behavior. Keep production real-infra strict.
        allow_full_scan=(spec.mode == "mock_infra"),
    )
    prov.log_dataframe("expr_long", expr_long)

    expr_wide = pivot_expression_wide(expr_long)
    prov.log_dataframe("expr_wide", expr_wide)

    merged = merge_clinical_expression(clinical_df, expr_wide, join_key="sample_id")
    prov.log_dataframe("merged_clinical_expr", merged)

    if spec.compute_signatures:
        sig_scores = compute_signature_scores(expr_wide, signature_definitions=signature_defs)
        prov.log_dataframe("signature_scores", sig_scores)
        merged = attach_features(merged, sig_scores, join_key="sample_id", how="left")
        prov.log_dataframe("merged_with_signatures", merged)

    if spec.variants.enabled:
        if not cfg.tiledb.variants_uri:
            raise SystemExit("tiledb.variants_uri must be set when --include-variants is used.")

        prov.log_tiledb(
            cfg.tiledb.variants_uri,
            {"dims": {"sample_id": f"{len(sample_ids)} ids"}, "attrs": ["GENE", "GT", "QUAL"]},
        )
        variants = fetch_variants_for_samples(
            cfg.tiledb.variants_uri,
            sample_ids=sample_ids,
            tiledb_config=cfg.tiledb.config,
            # Local mock TileDB arrays may require full-scan fallback depending on
            # TileDB/Python indexing behavior. Keep production real-infra strict.
            allow_full_scan=(spec.mode == "mock_infra"),
        )
        prov.log_dataframe("variants_raw", variants)

        mut_flags = summarize_mutations_presence(variants, spec.variants.mutation_genes)
        prov.log_dataframe("mutation_flags", mut_flags)
        merged = attach_features(merged, mut_flags, join_key="sample_id", how="left")
        prov.log_dataframe("merged_with_mutations", merged)

    atomic_write_csv(merged, spec.output, index=False)
    prov.log_output(spec.output)
    LOGGER.info("Wrote %s (rows=%s, cols=%s)", spec.output, len(merged), merged.shape[1])
    LOGGER.info("Provenance log: %s", os.path.join(prov.log_dir, "provenance.jsonl"))


if __name__ == "__main__":
    main()
