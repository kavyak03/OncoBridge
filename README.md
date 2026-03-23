# OncoBridge --- Clinical ↔ Genomics Cohort Integration SDK

OncoBridge is a modular Python toolkit for building analysis-ready biomedical datasets by integrating:

- Clinical cohort metadata (SQL)
- Gene expression matrices (TileDB)
- Variant calls (TileDB)

The project demonstrates how translational bioinformatics pipelines can be engineered as reproducible data platforms rather than one-off analysis scripts.

The core SDK is disease-agnostic.
This repository includes small cell lung cancer (SCLC) as a fully worked example, but the same pipeline can be adapted to other diseases by providing custom gene-signature definitions, regimen bucket definitions, and cohort filters

## Core pipeline workflow

The SDK builds an analysis-ready dataset through the following stages:

1. Clinical cohort extraction (SQL)
2. Gene expression retrieval (TileDB)
3. Variant retrieval (TileDB)
4. Feature engineering and mutation summarization
5. Gene-signature scoring
6. Construction of a final integrated dataset

Pipeline concept:

User Intent
  │
  ▼
Run Specification (Pydantic contracts)
  │
  ▼
Data Extraction Layer
  ├── SQL clinical cohort queries
  ├── TileDB gene expression retrieval
  └── TileDB variant retrieval
  │
  ▼
Feature Engineering Layer
  ├── expression reshaping
  ├── cohort + genomic merges
  ├── mutation summarization
  └── gene-signature scoring
  │
  ▼
Output + Provenance
  ├── analysis-ready dataset
  └── reproducible provenance log

## Key features

### Infrastructure-agnostic design

The SDK supports three execution modes:

Demo Mode — synthetic data — zero-setup onboarding
Mock Infra — SQLite + local TileDB — realistic local development
Real Infra — MariaDB + TileDB clusters — enterprise deployment

This allows anyone to run the repository locally without external credentials.

### Contract-driven configuration

Pydantic models validate:

configuration files
CLI run specifications
provenance log records

This prevents silent errors and makes pipeline behavior deterministic.

### Deterministic provenance logging

Each pipeline run records:

SQL query text and parameters
TileDB query specifications
dataframe schemas and hashes
output dataset location

Logs are stored in:

`run_logs/provenance.jsonl`

### Modular architecture

CLI orchestration — `cli.py`
Config loading — `config.py`
SQL extraction — `sql_connector.py`
Expression retrieval — `tiledb_expression.py`
Variant retrieval — `tiledb_variants.py`
Dataset assembly — `merger.py`
Biological features — `signatures.py`
Therapy logic — `therapy_buckets.py`
Provenance logging — `provenance.py`

### Benchmark-Driven Engineering

The repository includes a benchmark harness comparing:

a naive analysis pipeline
a semi-naive pipeline
the structured SDK pipeline

This allows performance claims to be measured instead of assumed.

The benchmark itself is disease-agnostic and focuses on pipeline structure rather than SCLC-specific biology.

## Module schematic (how the repo is wired)

This is the execution path for any patient cohort with clinical, gene expression, and variant data.

                           ┌───────────────────────────────┐
                           │  ehr_fhir_genomics_toolkit/   │
                           │            cli.py             │
                           │  (argparse → RunSpec validate)│
                           └───────────────┬───────────────┘
                                           │
                                           ▼
                           ┌───────────────────────────────┐
                           │           models.py           │
                           │  AppConfig / RunSpec contracts│
                           └───────────────┬───────────────┘
                                           │
                    loads config           │ logs run_spec + steps
                                           ▼
        ┌──────────────────────┐    ┌───────────────────────────────┐
        │      config.py       │    │         provenance.py        │
        │ YAML + env overrides │    │ JSONL audit trail (hashes)   │
        │    → AppConfig       │    └───────────────┬───────────────┘
        └──────────┬───────────┘                    │
                   │                                │
                   ▼                                ▼
     ┌────────────────────────┐         ┌─────────────────────────────┐
     │     sql_connector.py   │         │     tiledb_expression.py   │
     │ - generic cohort SQL   │         │ - fetch_expression_long()  │
     │ - query_sql() → cohort │         │ - pivot_expression_wide()  │
     └──────────┬─────────────┘         └───────────┬─────────────────┘
                │                                   │
                │                                   ▼
                │                       ┌─────────────────────────────┐
                │                       │      tiledb_variants.py    │
                │                       │ - fetch_variants_for_samples│
                │                       │ - summarize_mutations_*    │
                │                       └───────────┬─────────────────┘
                │                                   │
                └───────────────────────┬───────────┘
                                        ▼
                           ┌───────────────────────────────┐
                           │            merger.py          │
                           │ - merge_clinical_expression   │
                           │ - attach_features             │
                           └───────────────┬───────────────┘
                                           │
                                           ▼
                           ┌───────────────────────────────┐
                           │          signatures.py        │
                           │ compute_signature_scores()    │
                           │ generic loader + scorer       │
                           └───────────────┬───────────────┘
                                           │
                                           ▼
                           ┌───────────────────────────────┐
                           │       therapy_buckets.py      │
                           │ bucket loader + filtering     │
                           └───────────────┬───────────────┘
                                           │
                                           ▼
                           ┌───────────────────────────────┐
                           │          Output CSV           │
                           │  + run_logs/provenance.jsonl  │
                           └───────────────────────────────┘

## Disease-agnostic core + included SCLC example

The repository is organized so that the pipeline engine is generic, while SCLC is included as a concrete example profile.

Disease-specific content is externalized into configuration files wherever possible:

- `configs/signatures/`
- `configs/regimen_buckets/`

This means users can reuse the same SDK for other use cases by providing:

- a different signature definition YAML
- a different regimen bucket YAML
- a different diagnosis / cohort filter

without changing the source code.

## Tutorial

### Create environment

conda env create -f environment.yml
conda activate ehr_genomics_env

### Install the ehr_fhir_genomics_toolkit in the conda env

python -m pip install -e .

### Demo mode

Generic demo run:

  python -m ehr_fhir_genomics_toolkit.cli \
    --demo-mode \
    --compute-signatures \
    --include-variants \
    --output demo_dataset.csv

SCLC-specific demo run using the included example signature and regimen profiles:

  python -m ehr_fhir_genomics_toolkit.cli \
    --demo-mode \
    --diagnosis "small cell lung cancer" \
    --signature-profile sclc \
    --regimen-profile sclc \
    --compute-signatures \
    --include-variants \
    --output demo_sclc_dataset.csv

Outputs:

- `demo_dataset.csv` or `demo_sclc_dataset.csv`
- `run_logs/provenance.jsonl`

#### Mock infrastructure in demo mode

This repo includes `data/mock_ehr.sqlite` (SQLite DB you can query immediately)

To also run TileDB-backed queries locally:

  python scripts/make_mock_data.py

That creates:

- `data/tiledb/expression_array`
- `data/tiledb/variants_array`

Generic run:

  python -m ehr_fhir_genomics_toolkit.cli \
    --config config.mock.yaml \
    --therapy-mode join_table \
    --compute-signatures \
    --include-variants \
    --output mockinfra_dataset.csv

SCLC example run:

  python -m ehr_fhir_genomics_toolkit.cli \
    --config config.mock.yaml \
    --diagnosis "small cell lung cancer" \
    --therapy-mode join_table \
    --signature-profile sclc \
    --regimen-profile sclc \
    --regimen-bucket first_line_platinum_etoposide_io \
    --compute-signatures \
    --include-variants \
    --output mockinfra_sclc_dataset.csv

### Real Infrastructure Mode (local Python environment)

Validation Note:

The real infrastructure execution path (MariaDB / SQL + TileDB arrays) shares the same pipeline logic as the demo and mock-infrastructure modes included in this repository.

The SDK and CLI have been validated locally using the demo and mock infrastructure pipelines. The real infrastructure configuration documented below reflects the expected execution pattern for environments where a MariaDB database and TileDB arrays are available.

However, a full end-to-end execution against external database infrastructure has not been performed within this public repository environment.

Because the same SDK and CLI execution paths are used for both mock and real infrastructure modes, the real deployment behavior is expected to match the validated mock-infrastructure pipeline when equivalent data sources are provided.

Generic run:

  cp config.yaml.example config.yaml

  python -m ehr_fhir_genomics_toolkit.cli \
    --config config.yaml \
    --diagnosis "disease of interest" \
    --min-age 18 \
    --start-date 2018-01-01 \
    --end-date 2020-12-31 \
    --compute-signatures \
    --include-variants \
    --output merged_dataset.csv

SCLC example run:

  python -m ehr_fhir_genomics_toolkit.cli \
    --config config.yaml \
    --diagnosis "small cell lung cancer" \
    --therapy-mode join_table \
    --signature-profile sclc \
    --regimen-profile sclc \
    --regimen-bucket first_line_platinum_etoposide_io \
    --compute-signatures \
    --include-variants \
    --output sclc_dataset.csv

### Therapy Filtering and Regimen Buckets

The SDK optionally supports therapy-aware cohort construction, allowing users to restrict cohorts based on treatment categories (e.g., first-line platinum chemotherapy).

This behavior is controlled by three parameters:

- --therapy-mode
- --regimen-profile / --regimen-config
- --regimen-bucket

Understanding how these interact is important when building therapy-specific cohorts.

1. therapy_mode

This controls whether therapy data is used in the cohort selection logic.

- therapy_mode=none -> Therapy data is ignored.
  The cohort is filtered only by: diagnosis, age, collection date, and DSL conditions

  Example:

  python -m ehr_fhir_genomics_toolkit.cli \
    --demo-mode \
    --therapy-mode none \
    --compute-signatures

  Use this when:
  - therapy information is not available
  - therapy-based cohort restriction is not required

- therapy_mode=join_table -> Therapy data is included in the cohort construction logic.
  
  This enables: therapy-aware filtering and regimen bucket filtering

  Example:

    python -m ehr_fhir_genomics_toolkit.cli \
    --demo-mode \
    --therapy-mode join_table \
    --compute-signatures

  In real or mock infrastructure mode, this joins the therapy table in SQL. In demo mode, synthetic therapy data is generated and used in the same way.

2. Regimen Buckets: A regimen bucket is a logical grouping of therapies.

  Example buckets might include:

    - first_line_platinum_etoposide
    - first_line_platinum_etoposide_io
    - second_line
    - any

  These buckets allow users to define clinically meaningful treatment groups.

  The bucket used for filtering is specified with: --regimen-bucket

  Example:

  --regimen-bucket first_line_platinum_etoposide_io

  If you do not want therapy-based filtering, use: --regimen-bucket any

3. Regimen Definitions

Regimen buckets must be defined in the following ways:

- Built-in regimen profiles

  - --regimen-profile generic_oncology
  - --regimen-profile sclc

  These profiles ship with the SDK and require no additional configuration.

  Example:

  --therapy-mode join_table \
  --regimen-profile sclc \
  --regimen-bucket first_line_platinum_etoposide_io

- Custom regimen bucket YAML

  Users can define their own therapy categories via a YAML file.

  Example:

  --regimen-config configs/regimen_buckets/my_disease.yaml

  Example YAML structure:

  first_line_targeted:
    include:
      - osimertinib
      - erlotinib

  second_line_chemo:
    include:
      - docetaxel
      - gemcitabine

  Example CLI usage:

  --therapy-mode join_table \
  --regimen-config configs/regimen_buckets/my_disease.yaml \
  --regimen-bucket first_line_targeted

4. Typical Usage Patterns

- No therapy filtering
  --therapy-mode none

- Use therapy data but do not filter
  --therapy-mode join_table
  --regimen-bucket any

- Filter by built-in therapy category
  --therapy-mode join_table \
  --regimen-profile sclc \
  --regimen-bucket first_line_platinum_etoposide

- Filter by custom therapy definition
  --therapy-mode join_table \
  --regimen-config configs/regimen_buckets/custom.yaml \
  --regimen-bucket my_bucket

5. Demo Mode Behavior

In --demo-mode, the toolkit generates synthetic therapy data, allowing therapy mode and regimen filtering to behave exactly as it would in a real environment. This makes it possible to experiment with therapy-aware cohort construction without requiring a live database.

### Cohort Query DSL

The SDK supports a lightweight disease-agnostic DSL so users can define a cohort without touching Python code.

Example:

- generic: `diagnosis=breast cancer; min_age=18; start_date=2019-01-01; end_date=2021-12-31`
- SCLC: `diagnosis=small cell lung cancer; min_age=18; start_date=2018-01-01; end_date=2020-12-31; therapy_mode=join_table; regimen_bucket=first_line_platinum_etoposide_io`

Example run

  python -m ehr_fhir_genomics_toolkit.cli \
    --config config.mock.yaml \
    --cohort-dsl "diagnosis=small cell lung cancer; min_age=18; start_date=2018-01-01; end_date=2020-12-31; therapy_mode=join_table; regimen_bucket=first_line_platinum_etoposide_io" \
    --signature-profile sclc \
    --regimen-profile sclc \
    --compute-signatures \
    --include-variants \
    --output dsl_dataset.csv

The DSL overrides the regular cohort CLI flags.

### Reproducibility and provenance

Every run appends to:
`run_logs/provenance.jsonl`

It records:

- SQL query text + parameters (password scrubbed)
- TileDB URIs + slice specs
- DataFrame hashes and column lists
- run UUID + git SHA (when available)
- output path

### Downstream analysis notebook

On bash, run: jupyter notebook

Open `notebooks/01_downstream_analysis_example.ipynb`

Default `DATA_PATH` points to `../demo_sclc_dataset.csv`. Change it to your output file as needed.

### Survival modeling example

This repo includes a survival modeling example to complete the story from:

cohort extraction

- genomic integration
- feature engineering
- time-to-event modeling

Script

  python scripts/run_survival_example.py \
    --input-csv demo_sclc_dataset.csv \
    --add-demo-outcomes \
    --out-dir survival_results

Outputs:
  `survival_results/survival_dataset.csv`
  `survival_results/cox_summary.csv`

#### Notebook

Open:
  `notebooks/02_survival_modeling_example.ipynb`

IMPORTANT NOTE: If your dataset does not have real survival columns:

- survival_time_months
- event_observed

the example can add synthetic demo outcomes for educational purposes using the '-add-demo-outcomes' CLI argument.

### Bring-your-own real data integration

This repository is designed so that the core SDK remains disease-agnostic.

Users can load their own clinical / expression / variant datasets locally as long as they conform to the default ingestion schemas. The included SCLC example demonstrates one concrete use case, but the same pipeline can support other diseases by changing:

- diagnosis filters
- signature definitions
- regimen bucket definitions

#### Load clinical / therapy CSVs into SQLite

Expected clinical CSV columns:

- sample_id
- patient_id
- diagnosis
- age_at_collection
- collection_date

Expected therapy CSV columns:

- patient_id
- regimen
- line_of_therapy
- start_date
- end_date

Example:

  python scripts/load_real_sqlite_from_csv.py \
    --clinical-csv data/real/clinical_metadata.csv \
    --therapy-csv data/real/therapy_lines.csv \
    --sqlite-path data/real_ehr.sqlite

#### Load expression / variant CSVs into local TileDB

Expected expression CSV columns:

- sample_id
- gene
- expression_value

Expected variant CSV columns:

- sample_id
- var_id
- GENE
- GT
- QUAL

Example:

  python scripts/load_real_tiledb_from_csv.py \
    --expression-csv data/real/expression_long.csv \
    --expression-uri data/real_tiledb/expression_array

  python scripts/load_real_tiledb_from_csv.py \
    --variants-csv data/real/variants.csv \
    --variants-uri data/real_tiledb/variants_array

#### Create a real-data config

Example config.realdata.template.yaml:

  sql:
    sqlalchemy_url: "sqlite:///data/real_ehr.sqlite"
    tables:
      clinical_metadata: "clinical_metadata"
      therapies: "therapy_lines"

  tiledb:
    expression_uri: "data/real_tiledb/expression_array"
    variants_uri: "data/real_tiledb/variants_array"
    config: {}

  provenance:
    log_dir: "run_logs"

Then run:

  python -m ehr_fhir_genomics_toolkit.cli \
    --config config.realdata.template.yaml \
    --therapy-mode join_table \
    --compute-signatures \
    --include-variants \
    --output real_local_dataset.csv

#### Custom signatures and regimen buckets

Users can provide their own disease-specific logic without editing source code.

Custom signature definitions:

Use `--signature-config configs/signatures/my_disease.yaml`

YAML format:

```yaml

SIGNATURE_1:
  - GENE_A
  - GENE_B
  - GENE_C

SIGNATURE_2:
  - GENE_D
  - GENE_E
```

Custom regimen buckets:
Use `--regimen-config configs/regimen_buckets/my_disease.yaml`

YAML format:

```yaml

any: {}

first_line_custom:
  include_any:
    - drug_a
    - drug_b
  line_of_therapy: 1
```

This keeps the SDK generic while allowing disease-specific definitions to live outside `src/`.

#### SCLC example profile (included)

The repository includes a fully worked small cell lung cancer (SCLC) example profile under:

`configs/signatures/sclc.yaml`
`configs/regimen_buckets/sclc.yaml`

and a real-patient example under:

  `data/real_examples/sclc_tumorminer/`

This section demonstrates how a specific disease profile can be layered on top of the generic SDK.

##### What is included

Raw attached files:

- data/real_examples/sclc_tumorminer/raw/
  - Sample_annotation_patient.txt
  - sclc_Patient data_var.txt
  - sclc_Patient data_xsq.txt

Converted default CSV inputs:

- data/real_examples/sclc_tumorminer/converted/
  - clinical_metadata.csv
  - therapy_lines_coarse.csv
  - variants.csv
  - expression_panel_long.csv

These converted files match the default CSV ingestion pattern used by the repo's local DB/TileDB ingestion scripts: `./scripts/load_real_sqlite_from_csv.py`, and `./scripts/load_real_tiledb_from_csv.py`

Important note about therapy data: The attached SCLC metadata includes only a coarse prior-treatment label, not a regimen-level therapy table.

To keep the pipeline runnable, the repo includes:

therapy_lines_coarse.csv

This file is derived from the metadata's priorTreatment field and is not equivalent to real regimen-level therapy lines.

##### Why the expression file is panel-based

The attached transcriptome matrix is large. To keep the real-patient example lightweight and directly runnable, the repo converts a panel subset of genes used by the SCLC example workflow:

SCLC-A / N / P / Y signature genes

TP53 / RB1 / MYC

##### Conversion scripts for SCLC data

1) Convert raw SCLC TumorMiner-style files to default CSV inputs
python scripts/convert_sclc_tumorminer_to_default_csv.py

2) Build a fully local real-patient example (SQLite + TileDB)
python scripts/prepare_sclc_tumorminer_example.py

This creates:

- local SQLite clinical DB
- local TileDB expression array
- local TileDB variants array
- a ready-to-run config YAML

##### Run the real-patient example locally

Step 1:

Prepare the local DB / TileDB assets:

  python scripts/prepare_sclc_tumorminer_example.py

Step 2:

Run the cohort builder:

  python -m ehr_fhir_genomics_toolkit.cli \
    --config data/real_examples/sclc_tumorminer/config.sclc_tumorminer_panel.yaml \
    --therapy-mode join_table \
    --signature-profile sclc \
    --regimen-profile sclc \
    --compute-signatures \
    --include-variants \
    --output sclc_real_patient_panel_dataset.csv

##### Real-patient example notebook

A dedicated notebook is included:

  `notebooks/03_real_sclc_patient_example.ipynb`

This notebook walks through:

- cohort overview
- real metadata fields
- signature summaries
- mutation summaries
- coarse prior-treatment / therapy exploration
- survival metadata exploration when present

##### Data contracts for ingestion

The ingestion layer now includes data contracts so that external CSV files are validated before they are loaded into SQLite or TileDB.

Implemented in:
  `ehr_fhir_genomics_toolkit/data_contracts.py`

Validated input types:

- clinical CSV
- therapy CSV
- expression CSV
- variant CSV

###### What is checked

Before ingestion, the pipeline checks:

- required columns
- basic data types
- non-empty input frames
- simple value constraints

###### Why this matters

Without data contracts, external data can fail later in the pipeline in confusing ways.

With data contracts, failures happen early and clearly at the ingestion boundary.

### Docker (optional)

Build:

  docker build -t ehr-fhir-genomics:v1 .

#### Demo mode run

  docker run --rm -v "$PWD":/app ehr-fhir-genomics:v1 \
    python -m ehr_fhir_genomics_toolkit.cli \
    --demo-mode \
    --compute-signatures \
    --include-variants \
    --output /app/docker_demo_dataset.csv

#### Mock infra run

  docker run --rm -v "$PWD":/app ehr-fhir-genomics:v1 \
    python -m ehr_fhir_genomics_toolkit.cli \
    --config /app/config.mock.yaml \
    --therapy-mode join_table \
    --compute-signatures \
    --include-variants \
    --output /app/docker_mockinfra_dataset.csv

#### Real Infrastructure Mode via Docker (recommended for reproducibility)

Validation Note:

Containerized local execution has been validated for demo and mock-infrastructure modes. Real MariaDB / Azure deployment instructions are included as reproducible deployment patterns, but public end-to-end cloud validation has not yet been performed in this repository.

##### Running the pipeline in Docker requires providing

- database connectivity
- TileDB array URIs
- a configuration file or environment variables

Step 1 — Build the Docker image
  
  docker build -t ehr-fhir-genomics:v1 .

Step 2 — Create a real configuration file

Create a local config.yaml (do not commit it).

Example:

sql:
  sqlalchemy_url: "mysql+pymysql://USER:PASSWORD@HOST:3306/DBNAME"

tiledb:
  expression_uri: "/data/tiledb/expression_array"
  variants_uri: "/data/tiledb/variants_array"
  config: {}

provenance:
  log_dir: "run_logs"

Step 3 — Run the pipeline using Docker

  docker run --rm \
    -v "$PWD":/app \
    -v "$PWD/config.yaml":/app/config.yaml:ro \
    ehr-fhir-genomics:v1 \
    python -m ehr_fhir_genomics_toolkit.cli \
      --config /app/config.yaml \
      --diagnosis "disease of interest" \
      --min-age 18 \
      --start-date 2018-01-01 \
      --end-date 2020-12-31 \
      --compute-signatures \
      --include-variants \
      --output /app/merged_dataset.csv

Step 4 — Mount TileDB arrays if they are local

  docker run --rm \
    -v "$PWD":/app \
    -v "$PWD/config.yaml":/app/config.yaml:ro \
    -v "/mnt/research/tiledb":/data/tiledb:ro \
    ehr-fhir-genomics:v1 \
    python -m ehr_fhir_genomics_toolkit.cli \
      --config /app/config.yaml \
      --compute-signatures \
      --include-variants \
      --output /app/merged_dataset.csv

Then set in config.yaml:

  tiledb.expression_uri: "/data/tiledb/expression_array"

  tiledb.variants_uri: "/data/tiledb/variants_array"

Step 5 — Alternative: use environment variables

  docker run --rm \
    -v "$PWD":/app \
    -v "/mnt/research/tiledb":/data/tiledb:ro \
    -e SQLALCHEMY_URL="mysql+pymysql://USER:PASSWORD@HOST:3306/DB" \
    -e TILEDB_EXPRESSION_URI="/data/tiledb/expression_array" \
    -e TILEDB_VARIANTS_URI="/data/tiledb/variants_array" \
    ehr-fhir-genomics:v1 \
    python -m ehr_fhir_genomics_toolkit.cli \
      --compute-signatures \
      --include-variants \
      --output /app/merged_dataset.csv

#### Azure (optional): ACR + AKS pattern

Push image to ACR:

```bash

chmod +x scripts/build_and_push_acr.sh
ACR_NAME=myacr IMAGE_NAME=ehr-fhir-genomics TAG=v1 ./scripts/build_and_push_acr.sh

```

This uploads the Docker image to myacr.azurecr.io/ehr-fhir-genomics:v1

##### Run the pipeline in AKS using a Kubernetes Job

Example Kubernetes Job:

```yaml

apiVersion: batch/v1
kind: Job
metadata:
  name: sclc-cohort-build
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: pipeline
        image: myacr.azurecr.io/ehr-fhir-genomics:v1
        env:
        - name: SQLALCHEMY_URL
          valueFrom:
            secretKeyRef:
              name: ehr-secrets
              key: sqlalchemy_url
        - name: TILEDB_EXPRESSION_URI
          value: "/mnt/tiledb/expression_array"
        - name: TILEDB_VARIANTS_URI
          value: "/mnt/tiledb/variants_array"
        - name: PROVENANCE_LOG_DIR
          value: "/mnt/outputs/run_logs"
        command: ["python","-m","ehr_fhir_genomics_toolkit.cli"]
        args:
          ["--compute-signatures","--include-variants","--output","/mnt/outputs/sclc_dataset.csv"]
        volumeMounts:
        - name: outputs
          mountPath: /mnt/outputs
        - name: tiledb
          mountPath: /mnt/tiledb
      volumes:
      - name: outputs
        persistentVolumeClaim:
          claimName: outputs-pvc
      - name: tiledb
        persistentVolumeClaim:
          claimName: tiledb-pvc
```

This job:

- Pulls the container image from ACR
- Injects database credentials via Kubernetes secrets
- Mounts storage for TileDB arrays and outputs
- Runs the cohort extraction pipeline

### Benchmarking the SDK

The benchmark compares three pipeline styles:

1. Naive pipeline

  - repeated expression reshaping
  - repeated merges
  - repeated feature construction

2. Semi-naive pipeline

  - expression reshaped once
  - still fragmented feature attachment

3. SDK pipeline

  - shared intermediate tables
  - bundled feature engineering
  - cleaner transformation path

#### Example run

##### Demo mode

  python scripts/run_benchmark.py --mode demo

Large run example:

  python scripts/run_benchmark.py --mode demo --n-samples 10000 --repeats 10

##### Mock mode

  python scripts/run_benchmark.py --mode mock --config config.mock.yaml

This validates the SDK path against local SQLite + local TileDB.

#### Benchmark reporting style

Benchmarks are reported with:

- replicate runs
- mean runtime
- standard deviation
- percentage improvement

The benchmark writes:

  - benchmark_runs.csv
  - benchmark_summary.json

Important note:

Demo mode is the primary evidence for architecture efficiency because it isolates pipeline-structure differences from backend variability.

Mock mode is useful for infrastructure validation, but not for the main performance claim.

#### Benchmarking overview

To understand how pipeline architecture affects runtime as cohort size increases, scaling experiments were executed at the following sample sizes in the demo mode:

250
500
1000
2500
5000
10000

##### End-to-End Runtime Scaling

![Pipeline runtime scaling](assets/pipeline_runtime_scaling.png)

Runtime increases approximately linearly with cohort size. SDK design preserves scalability while slightly reducing runtime overhead.

##### Feature engineering Runtime Scaling

![Feature engineering runtime scaling](assets/feature_engineering_scaling.png)

Most computational cost in cohort assembly occurs during feature engineering.

This stage includes:

- expression reshaping
- cohort-expression merges
- mutation summarization
- gene-signature scoring

The SDK pipeline reduces runtime in this stage by reusing intermediate expression matrices, consolidating dataframe transformations, and avoiding repeated reshaping operations.

This stage is where the majority of pipeline-structure improvements occur.

##### Runtime breakdown

![Pipeline runtime breakdown](assets/pipeline_runtime_breakdown.png)

- SQL and TileDB queries dominate overall runtime.
- Feature-engineering overhead differs across pipeline designs.
- The SDK consolidates transformations into a smaller number of dataframe operations.

Important note: The benchmarking experiment above uses simulated data to ensure reproducibility and does not measure real database latency.

#### Hardware Environment

Benchmarks were executed on:
CPU: laptop-class CPU
RAM: 16 GB
Python: 3.11
Pandas: 2.x
NumPy: 1.x

#### Run manifests

Each benchmark or pipeline-style execution can write a run manifest to `run_logs/manifests/`

A run manifest is a human-readable JSON summary of:

- run ID and timestamp
- execution mode
- config path
- cohort filters
- feature toggles
- input sources
- output files
- environment metadata

This sits one level above low-level provenance logging. The provenance log is the detailed audit trail, while the run manifest is the concise record of what the run was, what it used, and what it produced.

### Testing

This repo uses Pydantic and Pandera-based validation to enforce:

- config contracts
- run specs
- ingestion schemas
- provenance structure

Run tests:

  pytest -q