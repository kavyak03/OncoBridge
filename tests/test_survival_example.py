from ehr_fhir_genomics_toolkit.demo_data import (
    generate_demo_clinical_cohort,
    generate_demo_expression_long,
    generate_demo_variants,
)
from ehr_fhir_genomics_toolkit.merger import attach_features, merge_clinical_expression
from ehr_fhir_genomics_toolkit.signatures import SIGNATURES, compute_signature_scores
from ehr_fhir_genomics_toolkit.survival import add_demo_survival_outcomes, fit_cox_example
from ehr_fhir_genomics_toolkit.tiledb_expression import pivot_expression_wide
from ehr_fhir_genomics_toolkit.tiledb_variants import summarize_mutations_presence


def test_survival_workflow_runs():
    genes = sorted({g for gs in SIGNATURES.values() for g in gs})
    clinical = generate_demo_clinical_cohort(n_samples=40, seed=7)
    expr_long = generate_demo_expression_long(clinical["sample_id"].tolist(), genes, seed=7)
    expr_wide = pivot_expression_wide(expr_long)
    merged = merge_clinical_expression(clinical, expr_wide)
    merged = attach_features(merged, compute_signature_scores(expr_wide))
    mut_flags = summarize_mutations_presence(
        generate_demo_variants(clinical["sample_id"].tolist(), seed=7), ["TP53", "RB1", "MYC"]
    )
    merged = attach_features(merged, mut_flags)
    surv = add_demo_survival_outcomes(merged)
    cph = fit_cox_example(surv)
    assert "coef" in cph.summary.columns
