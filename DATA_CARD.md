# OncoBridge Data Card

## Intended use

OncoBridge is intended for research, demonstration, portfolio, and engineering workflows involving clinical-genomics cohort assembly. It is not intended for clinical diagnosis, treatment selection, patient management, or regulated clinical decision support.

## Data categories in this repository

### Synthetic/demo data

The demo-mode pipeline generates synthetic clinical metadata, expression values, and variants at runtime. These data are not real patients and are used only to exercise the SDK pipeline.

### Mock infrastructure data

`data/mock_ehr.sqlite` is a local mock SQLite database. TileDB arrays under `data/tiledb/` are generated outputs from `scripts/make_mock_data.py` and should not be committed.

### SCLC real-example raw ZIP

`data/real_examples/sclc_tumorminer/raw/raw.zip` is intentionally retained in the ZIP provided to the user. Extracted raw files, converted CSVs, local SQLite databases, and local TileDB arrays are generated artifacts and are ignored by Git.

Before redistributing this repository publicly, confirm and document the source citation, license/redistribution terms, de-identification status, and permitted use of the raw ZIP contents.

## Generated outputs not meant for Git

Do not commit:

- `run_logs/`
- `survival_results/`
- `benchmark_results/`
- `data/tiledb/`
- `data/real_tiledb/`
- `data/real_examples/**/converted/`
- `data/real_examples/**/db/`
- extracted real-example raw `.txt`, `.tsv`, or `.csv` files

## PHI/PII handling expectation

This public/demo repository should not contain protected health information, private credentials, patient identifiers, client-specific file paths, or private database URLs. Real infrastructure runs should inject secrets through environment variables or deployment secrets.
