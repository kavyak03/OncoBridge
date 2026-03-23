from __future__ import annotations

import json
import statistics
import time
from pathlib import Path
from typing import Callable, Dict, List, Tuple

import pandas as pd

from .config import load_config
from .demo_data import generate_demo_clinical_cohort, generate_demo_expression_long, generate_demo_variants
from .merger import attach_features, merge_clinical_expression
from .run_manifest import build_run_manifest, make_run_id, write_run_manifest
from .signatures import compute_signature_scores, default_gene_list, load_signature_definitions
from .sql_connector import cohort_with_therapy_sql, query_sql
from .therapy_buckets import apply_regimen_bucket_filter, load_regimen_bucket_definitions
from .tiledb_expression import fetch_expression_long, pivot_expression_wide
from .tiledb_variants import fetch_variants_for_samples, summarize_mutations_presence

DEFAULT_MUTATION_GENES = ["TP53", "RB1", "MYC"]


def timed_call(fn: Callable[[], object]) -> Tuple[object, float]:
    start = time.perf_counter()
    result = fn()
    elapsed = time.perf_counter() - start
    return result, elapsed


def _safe_mean(records: List[Dict[str, float]], key: str) -> float:
    vals = [r.get(key, 0.0) for r in records]
    return statistics.mean(vals) if vals else 0.0


def _safe_std(records: List[Dict[str, float]], key: str) -> float:
    vals = [r.get(key, 0.0) for r in records]
    return statistics.stdev(vals) if len(vals) > 1 else 0.0


def _collect_stats(records: List[Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    keys = sorted({k for rec in records for k in rec.keys()})
    return {
        k: {
            "mean": _safe_mean(records, k),
            "std": _safe_std(records, k),
        }
        for k in keys
    }


def _improvement_percent(base: float, new: float) -> float:
    if base == 0:
        return 0.0
    return ((base - new) / base) * 100.0


def naive_pipeline(
    n_samples: int = 200,
    include_variants: bool = True,
    compute_signatures_flag: bool = True,
    signature_profile: str = "generic_oncology",
    signature_config: str | None = None,
):
    metrics: Dict[str, float] = {}

    signature_defs = load_signature_definitions(signature_config=signature_config, profile=signature_profile)
    genes = default_gene_list(signature_defs)

    clinical_df, t = timed_call(lambda: generate_demo_clinical_cohort(n_samples=n_samples, seed=7))
    metrics["sql_query_s"] = t

    expr_long, t = timed_call(lambda: generate_demo_expression_long(clinical_df["sample_id"].tolist(), genes, seed=7))
    metrics["tiledb_expression_query_s"] = t

    expr_wide_1, t = timed_call(lambda: pivot_expression_wide(expr_long))
    metrics["expression_pivot_for_merge_s"] = t

    merged, t = timed_call(lambda: merge_clinical_expression(clinical_df, expr_wide_1, join_key="sample_id"))
    metrics["merge_clinical_expression_s"] = t

    if compute_signatures_flag:
        expr_wide_2, t = timed_call(lambda: pivot_expression_wide(expr_long))
        metrics["expression_pivot_for_signatures_s"] = t

        sig_scores, t = timed_call(lambda: compute_signature_scores(expr_wide_2, signature_definitions=signature_defs))
        metrics["signature_compute_s"] = t

        merged, t = timed_call(lambda: attach_features(merged, sig_scores, join_key="sample_id", how="left"))
        metrics["attach_signatures_s"] = t

    if include_variants:
        variants_df, t = timed_call(lambda: generate_demo_variants(clinical_df["sample_id"].tolist(), seed=7))
        metrics["tiledb_variants_query_s"] = t

        mut_flags, t = timed_call(lambda: summarize_mutations_presence(variants_df, DEFAULT_MUTATION_GENES))
        metrics["mutation_flag_summarize_s"] = t

        merged, t = timed_call(lambda: attach_features(merged, mut_flags, join_key="sample_id", how="left"))
        metrics["attach_mutations_s"] = t

    metrics["feature_engineering_s"] = (
        metrics.get("expression_pivot_for_merge_s", 0.0)
        + metrics.get("merge_clinical_expression_s", 0.0)
        + metrics.get("expression_pivot_for_signatures_s", 0.0)
        + metrics.get("signature_compute_s", 0.0)
        + metrics.get("attach_signatures_s", 0.0)
        + metrics.get("mutation_flag_summarize_s", 0.0)
        + metrics.get("attach_mutations_s", 0.0)
    )

    metrics["pipeline_total_s"] = (
        metrics.get("sql_query_s", 0.0)
        + metrics.get("tiledb_expression_query_s", 0.0)
        + metrics.get("tiledb_variants_query_s", 0.0)
        + metrics.get("feature_engineering_s", 0.0)
    )
    return merged, metrics


def semi_naive_pipeline(
    n_samples: int = 200,
    include_variants: bool = True,
    compute_signatures_flag: bool = True,
    signature_profile: str = "generic_oncology",
    signature_config: str | None = None,
):
    metrics: Dict[str, float] = {}

    signature_defs = load_signature_definitions(signature_config=signature_config, profile=signature_profile)
    genes = default_gene_list(signature_defs)

    clinical_df, t = timed_call(lambda: generate_demo_clinical_cohort(n_samples=n_samples, seed=7))
    metrics["sql_query_s"] = t

    expr_long, t = timed_call(lambda: generate_demo_expression_long(clinical_df["sample_id"].tolist(), genes, seed=7))
    metrics["tiledb_expression_query_s"] = t

    expr_wide, t = timed_call(lambda: pivot_expression_wide(expr_long))
    metrics["expression_pivot_once_s"] = t

    merged, t = timed_call(lambda: merge_clinical_expression(clinical_df, expr_wide, join_key="sample_id"))
    metrics["merge_clinical_expression_s"] = t

    if compute_signatures_flag:
        sig_scores, t = timed_call(lambda: compute_signature_scores(expr_wide, signature_definitions=signature_defs))
        metrics["signature_compute_s"] = t

        merged, t = timed_call(lambda: attach_features(merged, sig_scores, join_key="sample_id", how="left"))
        metrics["attach_signatures_s"] = t

    if include_variants:
        variants_df, t = timed_call(lambda: generate_demo_variants(clinical_df["sample_id"].tolist(), seed=7))
        metrics["tiledb_variants_query_s"] = t

        mut_flags, t = timed_call(lambda: summarize_mutations_presence(variants_df, DEFAULT_MUTATION_GENES))
        metrics["mutation_flag_summarize_s"] = t

        merged, t = timed_call(lambda: attach_features(merged, mut_flags, join_key="sample_id", how="left"))
        metrics["attach_mutations_s"] = t

    metrics["feature_engineering_s"] = (
        metrics.get("expression_pivot_once_s", 0.0)
        + metrics.get("merge_clinical_expression_s", 0.0)
        + metrics.get("signature_compute_s", 0.0)
        + metrics.get("attach_signatures_s", 0.0)
        + metrics.get("mutation_flag_summarize_s", 0.0)
        + metrics.get("attach_mutations_s", 0.0)
    )

    metrics["pipeline_total_s"] = (
        metrics.get("sql_query_s", 0.0)
        + metrics.get("tiledb_expression_query_s", 0.0)
        + metrics.get("tiledb_variants_query_s", 0.0)
        + metrics.get("feature_engineering_s", 0.0)
    )
    return merged, metrics


def sdk_pipeline(
    n_samples: int = 200,
    include_variants: bool = True,
    compute_signatures_flag: bool = True,
    signature_profile: str = "generic_oncology",
    signature_config: str | None = None,
):
    metrics: Dict[str, float] = {}

    signature_defs = load_signature_definitions(signature_config=signature_config, profile=signature_profile)
    genes = default_gene_list(signature_defs)

    clinical_df, t = timed_call(lambda: generate_demo_clinical_cohort(n_samples=n_samples, seed=7))
    metrics["sql_query_s"] = t

    expr_long, t = timed_call(lambda: generate_demo_expression_long(clinical_df["sample_id"].tolist(), genes, seed=7))
    metrics["tiledb_expression_query_s"] = t

    expr_wide, t = timed_call(lambda: pivot_expression_wide(expr_long))
    metrics["expression_pivot_once_s"] = t

    merged, t = timed_call(lambda: merge_clinical_expression(clinical_df, expr_wide, join_key="sample_id"))
    metrics["merge_clinical_expression_s"] = t

    if compute_signatures_flag:
        sig_scores, t = timed_call(lambda: compute_signature_scores(expr_wide, signature_definitions=signature_defs))
        metrics["signature_compute_s"] = t

        merged, t = timed_call(lambda: attach_features(merged, sig_scores, join_key="sample_id", how="left"))
        metrics["attach_signatures_s"] = t

    if include_variants:
        variants_df, t = timed_call(lambda: generate_demo_variants(clinical_df["sample_id"].tolist(), seed=7))
        metrics["tiledb_variants_query_s"] = t

        mut_flags, t = timed_call(lambda: summarize_mutations_presence(variants_df, DEFAULT_MUTATION_GENES))
        metrics["mutation_flag_summarize_s"] = t

        merged, t = timed_call(lambda: attach_features(merged, mut_flags, join_key="sample_id", how="left"))
        metrics["attach_mutations_s"] = t

    metrics["feature_engineering_s"] = (
        metrics.get("expression_pivot_once_s", 0.0)
        + metrics.get("merge_clinical_expression_s", 0.0)
        + metrics.get("signature_compute_s", 0.0)
        + metrics.get("attach_signatures_s", 0.0)
        + metrics.get("mutation_flag_summarize_s", 0.0)
        + metrics.get("attach_mutations_s", 0.0)
    )

    metrics["pipeline_total_s"] = (
        metrics.get("sql_query_s", 0.0)
        + metrics.get("tiledb_expression_query_s", 0.0)
        + metrics.get("tiledb_variants_query_s", 0.0)
        + metrics.get("feature_engineering_s", 0.0)
    )
    return merged, metrics


def mock_infra_pipeline(
    config_path: str = "config.mock.yaml",
    include_variants: bool = True,
    compute_signatures_flag: bool = True,
    signature_profile: str = "generic_oncology",
    signature_config: str | None = None,
    regimen_profile: str = "generic_oncology",
    regimen_config: str | None = None,
    diagnosis: str = "small cell lung cancer",
    therapy_mode: str = "join_table",
    regimen_bucket: str = "any",
):
    cfg = load_config(config_path)
    if cfg.sql is None or cfg.tiledb is None:
        raise ValueError("Mock infra benchmark requires sql + tiledb config")

    metrics: Dict[str, float] = {}
    signature_defs = load_signature_definitions(signature_config=signature_config, profile=signature_profile)
    genes = default_gene_list(signature_defs)
    bucket_defs = load_regimen_bucket_definitions(regimen_config=regimen_config, profile=regimen_profile)

    sql_text = (
        cohort_with_therapy_sql(cfg.sql.tables.clinical_metadata, cfg.sql.tables.therapies)
        if therapy_mode == "join_table"
        else cohort_with_therapy_sql(cfg.sql.tables.clinical_metadata, cfg.sql.tables.therapies)
    )
    params = {
        "diagnosis": diagnosis,
        "min_age": 18,
        "start_date": "2018-01-01",
        "end_date": "2020-12-31",
    }

    clinical_df, t = timed_call(lambda: query_sql(cfg.sql.sqlalchemy_url_plain, sql_text, params))
    metrics["sql_query_s"] = t

    if "collection_date" in clinical_df.columns:
        clinical_df["collection_date"] = pd.to_datetime(clinical_df["collection_date"], errors="coerce")

    if therapy_mode == "join_table" and regimen_bucket != "any":
        clinical_df = apply_regimen_bucket_filter(clinical_df, regimen_bucket, bucket_defs)

    sample_ids = clinical_df["sample_id"].astype(str).tolist()

    expr_long, t = timed_call(lambda: fetch_expression_long(cfg.tiledb.expression_uri, sample_ids, genes, tiledb_config=cfg.tiledb.config))
    metrics["tiledb_expression_query_s"] = t

    expr_wide, t = timed_call(lambda: pivot_expression_wide(expr_long))
    metrics["expression_pivot_once_s"] = t

    merged, t = timed_call(lambda: merge_clinical_expression(clinical_df, expr_wide, join_key="sample_id"))
    metrics["merge_clinical_expression_s"] = t

    if compute_signatures_flag:
        sig_scores, t = timed_call(lambda: compute_signature_scores(expr_wide, signature_definitions=signature_defs))
        metrics["signature_compute_s"] = t

        merged, t = timed_call(lambda: attach_features(merged, sig_scores, join_key="sample_id", how="left"))
        metrics["attach_signatures_s"] = t

    if include_variants and cfg.tiledb.variants_uri:
        variants_df, t = timed_call(lambda: fetch_variants_for_samples(cfg.tiledb.variants_uri, sample_ids, tiledb_config=cfg.tiledb.config))
        metrics["tiledb_variants_query_s"] = t

        mut_flags, t = timed_call(lambda: summarize_mutations_presence(variants_df, DEFAULT_MUTATION_GENES))
        metrics["mutation_flag_summarize_s"] = t

        merged, t = timed_call(lambda: attach_features(merged, mut_flags, join_key="sample_id", how="left"))
        metrics["attach_mutations_s"] = t

    metrics["feature_engineering_s"] = (
        metrics.get("expression_pivot_once_s", 0.0)
        + metrics.get("merge_clinical_expression_s", 0.0)
        + metrics.get("signature_compute_s", 0.0)
        + metrics.get("attach_signatures_s", 0.0)
        + metrics.get("mutation_flag_summarize_s", 0.0)
        + metrics.get("attach_mutations_s", 0.0)
    )

    metrics["pipeline_total_s"] = (
        metrics.get("sql_query_s", 0.0)
        + metrics.get("tiledb_expression_query_s", 0.0)
        + metrics.get("tiledb_variants_query_s", 0.0)
        + metrics.get("feature_engineering_s", 0.0)
    )
    return merged, metrics


def run_benchmark(
    mode: str = "demo",
    n_samples: int = 500,
    repeats: int = 5,
    include_variants: bool = True,
    compute_signatures_flag: bool = True,
    out_dir: str = "benchmark_results",
    config_path: str = "config.mock.yaml",
    signature_profile: str = "generic_oncology",
    signature_config: str | None = None,
    regimen_profile: str = "generic_oncology",
    regimen_config: str | None = None,
):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, object]] = []

    if mode == "demo":
        naive_records: List[Dict[str, float]] = []
        semi_naive_records: List[Dict[str, float]] = []
        sdk_records: List[Dict[str, float]] = []

        for i in range(repeats):
            _, naive_m = naive_pipeline(
                n_samples=n_samples,
                include_variants=include_variants,
                compute_signatures_flag=compute_signatures_flag,
                signature_profile=signature_profile,
                signature_config=signature_config,
            )
            _, semi_m = semi_naive_pipeline(
                n_samples=n_samples,
                include_variants=include_variants,
                compute_signatures_flag=compute_signatures_flag,
                signature_profile=signature_profile,
                signature_config=signature_config,
            )
            _, sdk_m = sdk_pipeline(
                n_samples=n_samples,
                include_variants=include_variants,
                compute_signatures_flag=compute_signatures_flag,
                signature_profile=signature_profile,
                signature_config=signature_config,
            )

            naive_records.append(naive_m)
            semi_naive_records.append(semi_m)
            sdk_records.append(sdk_m)

            rows.append({"run": i + 1, "pipeline": "naive", "mode": "demo", **naive_m})
            rows.append({"run": i + 1, "pipeline": "semi_naive", "mode": "demo", **semi_m})
            rows.append({"run": i + 1, "pipeline": "sdk", "mode": "demo", **sdk_m})

        pd.DataFrame(rows).to_csv(out / "benchmark_runs.csv", index=False)

        naive_stats = _collect_stats(naive_records)
        semi_naive_stats = _collect_stats(semi_naive_records)
        sdk_stats = _collect_stats(sdk_records)

        summary = {
            "mode": "demo",
            "n_samples": n_samples,
            "repeats": repeats,
            "naive_stats": naive_stats,
            "semi_naive_stats": semi_naive_stats,
            "sdk_stats": sdk_stats,
            "naive_vs_sdk": {
                "pipeline_total_improvement_percent": _improvement_percent(
                    naive_stats["pipeline_total_s"]["mean"],
                    sdk_stats["pipeline_total_s"]["mean"],
                ),
                "feature_engineering_improvement_percent": _improvement_percent(
                    naive_stats["feature_engineering_s"]["mean"],
                    sdk_stats["feature_engineering_s"]["mean"],
                ),
            },
            "semi_naive_vs_sdk": {
                "pipeline_total_improvement_percent": _improvement_percent(
                    semi_naive_stats["pipeline_total_s"]["mean"],
                    sdk_stats["pipeline_total_s"]["mean"],
                ),
                "feature_engineering_improvement_percent": _improvement_percent(
                    semi_naive_stats["feature_engineering_s"]["mean"],
                    sdk_stats["feature_engineering_s"]["mean"],
                ),
            },
            "claim_50_percent_supported": _improvement_percent(
                naive_stats["pipeline_total_s"]["mean"],
                sdk_stats["pipeline_total_s"]["mean"],
            ) >= 50.0,
            "notes": [
                "Demo benchmarks are disease-agnostic and use whichever signature profile/config is provided.",
                "The benchmark isolates pipeline-structure differences rather than real database/network latency.",
            ],
        }

    elif mode == "mock":
        mock_records: List[Dict[str, float]] = []
        for i in range(repeats):
            _, mock_m = mock_infra_pipeline(
                config_path=config_path,
                include_variants=include_variants,
                compute_signatures_flag=compute_signatures_flag,
                signature_profile=signature_profile,
                signature_config=signature_config,
                regimen_profile=regimen_profile,
                regimen_config=regimen_config,
            )
            mock_records.append(mock_m)
            rows.append({"run": i + 1, "pipeline": "mock_infra_sdk", "mode": "mock", **mock_m})

        pd.DataFrame(rows).to_csv(out / "benchmark_runs.csv", index=False)

        mock_stats = _collect_stats(mock_records)
        summary = {
            "mode": "mock",
            "repeats": repeats,
            "mock_stats": mock_stats,
            "notes": [
                "Mock mode validates the structured SDK path against local SQLite + local TileDB.",
                "Mock mode is useful for infrastructure validation, not for the main architecture-efficiency claim.",
            ],
        }

    else:
        raise ValueError("mode must be 'demo' or 'mock'")

    (out / "benchmark_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    manifest = build_run_manifest(
        run_id=make_run_id(prefix=f"benchmark_{mode}"),
        mode=mode,
        config_path=config_path if mode == "mock" else None,
        cohort={"n_samples": n_samples if mode == "demo" else None},
        features={
            "include_variants": include_variants,
            "compute_signatures": compute_signatures_flag,
            "signature_profile": signature_profile,
            "signature_config": signature_config,
            "regimen_profile": regimen_profile,
            "regimen_config": regimen_config,
            "benchmark_repeats": repeats,
        },
        inputs={"mode": mode},
        outputs={
            "benchmark_runs_csv": str(out / "benchmark_runs.csv"),
            "benchmark_summary_json": str(out / "benchmark_summary.json"),
        },
        benchmark=summary,
    )
    manifest_path = write_run_manifest(manifest)
    summary["run_manifest"] = manifest_path
    (out / "benchmark_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return summary