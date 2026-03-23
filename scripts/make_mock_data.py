"""Generate local mock SQL (SQLite) + TileDB arrays (Option 2).

This script overwrites:
  - data/mock_ehr.sqlite
  - data/tiledb/expression_array
  - data/tiledb/variants_array

Usage:
  python scripts/make_mock_data.py
"""
from __future__ import annotations
import os, shutil, sqlite3
from pathlib import Path
import numpy as np
import pandas as pd
import tiledb

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TDB = DATA / "tiledb"

def main():
    DATA.mkdir(exist_ok=True)
    TDB.mkdir(exist_ok=True)

    sqlite_path = DATA / "mock_ehr.sqlite"
    if sqlite_path.exists():
        sqlite_path.unlink()

    conn = sqlite3.connect(sqlite_path)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE clinical_metadata (
      sample_id TEXT PRIMARY KEY,
      patient_id TEXT NOT NULL,
      diagnosis TEXT NOT NULL,
      age_at_collection INTEGER NOT NULL,
      collection_date TEXT NOT NULL
    )""")
    cur.execute("""CREATE TABLE therapy_lines (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      patient_id TEXT NOT NULL,
      regimen TEXT NOT NULL,
      line_of_therapy INTEGER NOT NULL,
      start_date TEXT NOT NULL,
      end_date TEXT
    )""")

    rng = np.random.default_rng(7)
    n_samples = 40
    patient_ids = [f"P{(i//2)+1:03d}" for i in range(n_samples)]
    sample_ids = [f"S{i+1:04d}" for i in range(n_samples)]
    ages = rng.integers(45, 82, size=n_samples)
    dates = pd.date_range("2019-01-15", periods=n_samples, freq="14D").strftime("%Y-%m-%d").tolist()
    diagnosis = ["small cell lung cancer"] * n_samples

    cur.executemany(
        "INSERT INTO clinical_metadata(sample_id, patient_id, diagnosis, age_at_collection, collection_date) VALUES (?,?,?,?,?)",
        list(zip(sample_ids, patient_ids, diagnosis, ages.tolist(), dates))
    )

    regimens_1l = ["carboplatin+etoposide", "cisplatin+etoposide"]
    regimens_1l_io = ["carboplatin+etoposide+atezolizumab", "carboplatin+etoposide+durvalumab"]
    regimens_2l = ["topotecan", "lurbinectedin"]

    patients_unique = sorted(set(patient_ids))
    therapy_rows = []
    for pid in patients_unique:
        reg = rng.choice(regimens_1l) if rng.random() < 0.5 else rng.choice(regimens_1l_io)
        therapy_rows.append((pid, reg, 1, "2019-01-01", "2019-12-31"))
        if rng.random() < 0.35:
            therapy_rows.append((pid, rng.choice(regimens_2l), 2, "2020-01-01", None))

    cur.executemany(
        "INSERT INTO therapy_lines(patient_id, regimen, line_of_therapy, start_date, end_date) VALUES (?,?,?,?,?)",
        therapy_rows
    )
    conn.commit()
    conn.close()

    expr_uri = str(TDB / "expression_array")
    var_uri = str(TDB / "variants_array")
    for uri in [expr_uri, var_uri]:
        if os.path.exists(uri):
            shutil.rmtree(uri)

    genes = sorted(set(["ASCL1","DLL3","CHGA","NEUROD1","INSM1","SYP","POU2F3","TRPM5","GFI1B","YAP1","WWTR1","VIM"]))
    dom = tiledb.Domain(
        tiledb.Dim(name="sample_id", domain=(min(sample_ids), max(sample_ids)), tile=10, dtype="ascii"),
        tiledb.Dim(name="gene", domain=(min(genes), max(genes)), tile=10, dtype="ascii"),
    )
    schema = tiledb.ArraySchema(domain=dom, attrs=[tiledb.Attr(name="expression_value", dtype=np.float32)], sparse=True)
    tiledb.SparseArray.create(expr_uri, schema)

    rows = []
    for sid in sample_ids:
        subtype = rng.choice(["A","N","P","Y"])
        base = rng.normal(0, 0.5)
        for g in genes:
            val = base + rng.normal(0, 1.0)
            if subtype == "A" and g in ["ASCL1","DLL3","CHGA"]:
                val += 2.5
            if subtype == "N" and g in ["NEUROD1","INSM1","SYP"]:
                val += 2.5
            if subtype == "P" and g in ["POU2F3","TRPM5","GFI1B"]:
                val += 2.5
            if subtype == "Y" and g in ["YAP1","WWTR1","VIM"]:
                val += 2.5
            rows.append((sid, g, np.float32(val)))
    df = pd.DataFrame(rows, columns=["sample_id","gene","expression_value"])
    with tiledb.SparseArray(expr_uri, mode="w") as A:
        A[df["sample_id"].tolist(), df["gene"].tolist()] = {"expression_value": df["expression_value"].to_numpy()}

    var_ids = [f"v{i+1:05d}" for i in range(200)]
    dom2 = tiledb.Domain(
        tiledb.Dim(name="sample_id", domain=(min(sample_ids), max(sample_ids)), tile=10, dtype="ascii"),
        tiledb.Dim(name="var_id", domain=(min(var_ids), max(var_ids)), tile=50, dtype="ascii"),
    )
    schema2 = tiledb.ArraySchema(
        domain=dom2,
        attrs=[tiledb.Attr(name="GENE", dtype="ascii"),
               tiledb.Attr(name="GT", dtype=np.int8),
               tiledb.Attr(name="QUAL", dtype=np.float32)],
        sparse=True
    )
    tiledb.SparseArray.create(var_uri, schema2)

    genes2 = ["TP53","RB1","MYC","NOTCH1","CREBBP"]
    rows2 = []
    for sid in sample_ids:
        k = int(rng.integers(1, 6))
        chosen = rng.choice(var_ids, size=k, replace=False)
        for vid in chosen:
            g = rng.choice(genes2, p=[0.35,0.30,0.15,0.10,0.10])
            gt = np.int8(rng.choice([0,1]))
            qual = np.float32(abs(rng.normal(60, 15)))
            rows2.append((sid, vid, g, gt, qual))
    df2 = pd.DataFrame(rows2, columns=["sample_id","var_id","GENE","GT","QUAL"])
    with tiledb.SparseArray(var_uri, mode="w") as A:
        A[df2["sample_id"].tolist(), df2["var_id"].tolist()] = {
            "GENE": df2["GENE"].tolist(),
            "GT": df2["GT"].to_numpy(),
            "QUAL": df2["QUAL"].to_numpy()
        }

    print("Wrote:")
    print(" -", sqlite_path)
    print(" -", expr_uri)
    print(" -", var_uri)

if __name__ == "__main__":
    main()
