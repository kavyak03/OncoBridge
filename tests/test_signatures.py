import pandas as pd

from ehr_fhir_genomics_toolkit.signatures import compute_signature_scores


def test_signature_scores_mean():
    df = pd.DataFrame(
        {
            "sample_id": ["S1"],
            "ASCL1": [2.0],
            "DLL3": [4.0],
            "CHGA": [6.0],
        }
    )
    scores = compute_signature_scores(df, profile="sclc")
    assert abs(scores.loc[0, "SCLC_A_ASCL1"] - 4.0) < 1e-6
