import pandas as pd

from ehr_fhir_genomics_toolkit.tiledb_variants import summarize_mutations_presence


def test_mut_flags():
    v = pd.DataFrame({"sample_id": ["S1", "S1", "S2"], "GENE": ["TP53", "RB1", "TP53"]})
    flags = summarize_mutations_presence(v, ["TP53", "RB1", "MYC"])
    s1 = flags[flags["sample_id"] == "S1"].iloc[0]
    assert s1["mut_TP53"] == 1
    assert s1["mut_RB1"] == 1
    assert s1["mut_MYC"] == 0
