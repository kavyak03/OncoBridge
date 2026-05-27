from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from .io_safety import atomic_write_csv

DEFAULT_PANEL_GENES = [
    "ASCL1",
    "DLL3",
    "CHGA",
    "NEUROD1",
    "INSM1",
    "SYP",
    "POU2F3",
    "TRPM5",
    "GFI1B",
    "YAP1",
    "WWTR1",
    "VIM",
    "TP53",
    "RB1",
    "MYC",
]


def _clean_prefixed_value(x: object) -> str | None:
    if pd.isna(x):
        return None
    s = str(x).strip()
    if not s:
        return None
    return s.split(":", 1)[1].strip() if ":" in s else s


def _parse_date_series(s: pd.Series | None) -> pd.Series:
    if s is None:
        return pd.Series(dtype="object")
    dt = pd.to_datetime(s, errors="coerce")
    return dt.dt.strftime("%Y-%m-%d")


def convert_clinical(annotation_path: str | Path) -> pd.DataFrame:
    ann = pd.read_csv(annotation_path, sep="\t", low_memory=False).copy()
    collection = _parse_date_series(ann.get("sampleDate"))
    first_dx = _parse_date_series(ann.get("dateFirstDiagnosis"))
    last_fu = _parse_date_series(ann.get("dateLastFollowup"))
    collection = collection.fillna(first_dx).fillna(last_fu).fillna("2020-01-01")
    out = pd.DataFrame(
        {
            "sample_id": ann["Name"].astype(str),
            "patient_id": ann.get("patientID", ann["Name"]).astype(str),
            "diagnosis": ann.get("disease", "SCLC")
            .astype(str)
            .replace({"SCLC": "small cell lung cancer"}),
            "age_at_collection": pd.to_numeric(ann.get("age"), errors="coerce"),
            "collection_date": collection,
            "sample_type": ann.get("sampleType").map(_clean_prefixed_value),
            "biopsy_site": ann.get("biopsySite").map(_clean_prefixed_value),
            "tumor_stage": ann.get("tumorStage"),
            "gender": ann.get("gender").map(_clean_prefixed_value),
            "vital_status": ann.get("vitalStatus"),
            "os_months": pd.to_numeric(ann.get("osMonths"), errors="coerce"),
            "event_observed": ann.get("survivalStatus").map(
                lambda x: int(bool(x)) if pd.notna(x) else None
            ),
            "smoking_status": ann.get("smokingStatus"),
            "prior_treatment_label": ann.get("priorTreatment").map(_clean_prefixed_value),
            "data_source": ann.get("dataSource"),
        }
    )
    return out


def convert_coarse_therapy(annotation_path: str | Path) -> pd.DataFrame:
    ann = pd.read_csv(annotation_path, sep="\t", low_memory=False).copy()
    start_date = (
        _parse_date_series(ann.get("dateFirstDiagnosis"))
        .fillna(_parse_date_series(ann.get("sampleDate")))
        .fillna("2020-01-01")
    )
    regimen = ann.get("priorTreatment").map(_clean_prefixed_value).fillna("unknown")
    out = pd.DataFrame(
        {
            "patient_id": ann.get("patientID", ann["Name"]).astype(str),
            "regimen": regimen,
            "line_of_therapy": 1,
            "start_date": start_date,
            "end_date": pd.Series([None] * len(ann)),
        }
    )
    return out[out["regimen"].notna()].copy()


def convert_variants(variant_path: str | Path, annotation_path: str | Path) -> pd.DataFrame:
    ann = pd.read_csv(annotation_path, sep="\t", low_memory=False)
    sample_cols = ann["Name"].astype(str).tolist()
    var = pd.read_csv(variant_path, sep="\t", low_memory=False).copy()
    keep_cols = [
        c
        for c in ["ID", "Chr", "Start", "Ref", "Alt", "Gene.refGene", "CADD_phred"] + sample_cols
        if c in var.columns
    ]
    v = var[keep_cols].copy()
    long_df = v.melt(
        id_vars=[
            c
            for c in ["ID", "Chr", "Start", "Ref", "Alt", "Gene.refGene", "CADD_phred"]
            if c in v.columns
        ],
        value_vars=sample_cols,
        var_name="sample_id",
        value_name="present_value",
    )
    long_df["present_value"] = pd.to_numeric(long_df["present_value"], errors="coerce").fillna(0)
    long_df = long_df[long_df["present_value"] > 0].copy()
    out = pd.DataFrame(
        {
            "sample_id": long_df["sample_id"].astype(str),
            "var_id": long_df["ID"].astype(str),
            "GENE": long_df.get("Gene.refGene", pd.Series(["unknown"] * len(long_df)))
            .astype(str)
            .str.split("[,;]")
            .str[0],
            "GT": 1,
            "QUAL": pd.to_numeric(long_df.get("CADD_phred"), errors="coerce")
            .fillna(0)
            .astype(float),
            "CHROM": long_df.get("Chr"),
            "POS": pd.to_numeric(long_df.get("Start"), errors="coerce"),
            "REF": long_df.get("Ref"),
            "ALT": long_df.get("Alt"),
        }
    )
    return out


def convert_expression_panel(
    expression_path: str | Path, annotation_path: str | Path, genes: Iterable[str] | None = None
) -> pd.DataFrame:
    genes = list(genes or DEFAULT_PANEL_GENES)
    ann = pd.read_csv(annotation_path, sep="\t", low_memory=False)
    sample_cols = ann["Name"].astype(str).tolist()
    expr = pd.read_csv(expression_path, sep="\t", low_memory=False).copy()
    expr = expr[expr["Symbol"].astype(str).isin(genes)].copy()
    long_df = expr.melt(
        id_vars=[c for c in ["ID", "Symbol", "EnsID", "biotype"] if c in expr.columns],
        value_vars=sample_cols,
        var_name="sample_id",
        value_name="expression_value",
    )
    out = pd.DataFrame(
        {
            "sample_id": long_df["sample_id"].astype(str),
            "gene": long_df["Symbol"].astype(str),
            "expression_value": pd.to_numeric(long_df["expression_value"], errors="coerce")
            .fillna(0)
            .astype(float),
            "gene_id": long_df.get("EnsID"),
            "biotype": long_df.get("biotype"),
        }
    )
    return out


def write_converted_bundle(
    annotation_path: str | Path,
    variant_path: str | Path,
    expression_path: str | Path,
    out_dir: str | Path,
    genes: Iterable[str] | None = None,
) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    clinical = convert_clinical(annotation_path)
    therapy = convert_coarse_therapy(annotation_path)
    variants = convert_variants(variant_path, annotation_path)
    expr_panel = convert_expression_panel(expression_path, annotation_path, genes=genes)
    clinical_path = out_dir / "clinical_metadata.csv"
    therapy_path = out_dir / "therapy_lines_coarse.csv"
    variants_path = out_dir / "variants.csv"
    expr_path = out_dir / "expression_panel_long.csv"
    atomic_write_csv(clinical, clinical_path, index=False)
    atomic_write_csv(therapy, therapy_path, index=False)
    atomic_write_csv(variants, variants_path, index=False)
    atomic_write_csv(expr_panel, expr_path, index=False)
    return {
        "clinical_csv": str(clinical_path),
        "therapy_csv": str(therapy_path),
        "variants_csv": str(variants_path),
        "expression_panel_csv": str(expr_path),
    }
