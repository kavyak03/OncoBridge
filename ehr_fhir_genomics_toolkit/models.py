from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator

from .security import validate_sql_identifier

# -------------------------
# Config models
# -------------------------


class SQLTables(BaseModel):
    clinical_metadata: str = "clinical_metadata"
    therapies: str = "therapy_lines"

    @field_validator("clinical_metadata", "therapies")
    @classmethod
    def _safe_identifier(cls, v: str) -> str:
        return validate_sql_identifier(v)


class SQLConfig(BaseModel):
    sqlalchemy_url: SecretStr = Field(
        ...,
        description="SQLAlchemy connection string. Prefer SQLALCHEMY_URL env var for real credentials.",
    )
    tables: SQLTables = Field(default_factory=SQLTables)

    @property
    def sqlalchemy_url_plain(self) -> str:
        return self.sqlalchemy_url.get_secret_value()


class TileDBConfig(BaseModel):
    expression_uri: str = Field(..., description="TileDB URI/path for expression array")
    variants_uri: str | None = Field(default=None, description="TileDB URI/path for variants array")
    config: dict[str, Any] = Field(default_factory=dict, description="Extra TileDB config dict")

    @field_validator("expression_uri")
    @classmethod
    def _non_empty_expr(cls, v: str) -> str:
        if not v or not str(v).strip():
            raise ValueError("tiledb.expression_uri must be set")
        return v


class ProvenanceConfig(BaseModel):
    log_dir: str = "run_logs"
    include_raw_sql: bool = False
    include_raw_tiledb_uri: bool = False
    include_raw_paths: bool = False


class AppConfig(BaseModel):
    sql: SQLConfig | None = None
    tiledb: TileDBConfig | None = None
    provenance: ProvenanceConfig = Field(default_factory=ProvenanceConfig)


# -------------------------
# Run spec models
# -------------------------


class CohortSpec(BaseModel):
    diagnosis: str = "small cell lung cancer"
    min_age: int = 18
    start_date: date = date(2018, 1, 1)
    end_date: date = date(2020, 12, 31)
    therapy_mode: Literal["none", "join_table"] = "none"
    regimen_bucket: str = "any"

    @model_validator(mode="after")
    def _check_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be >= start_date")
        if self.min_age < 0:
            raise ValueError("min_age must be >= 0")
        return self


class ExpressionSpec(BaseModel):
    genes: list[str] = Field(..., min_length=1)
    unit: str = "arbitrary"
    transform: str | None = None

    @field_validator("genes")
    @classmethod
    def _reasonable_gene_list(cls, v: list[str]) -> list[str]:
        genes = [str(g).strip() for g in v if str(g).strip()]
        if not genes:
            raise ValueError("At least one gene must be provided")
        if len(genes) > 5000:
            raise ValueError("Gene list is too large for a single query; batch the request")
        return genes


class VariantSpec(BaseModel):
    enabled: bool = False
    mutation_genes: list[str] = Field(default_factory=lambda: ["TP53", "RB1", "MYC"])


class RunSpec(BaseModel):
    mode: Literal["demo", "mock_infra", "real_infra"] = "demo"
    cohort: CohortSpec = Field(default_factory=CohortSpec)
    expression: ExpressionSpec
    variants: VariantSpec = Field(default_factory=VariantSpec)
    compute_signatures: bool = False
    output: str = "sclc_merged_dataset.csv"


# -------------------------
# Provenance models
# -------------------------


class SQLProvenance(BaseModel):
    kind: Literal["sql"] = "sql"
    sqlalchemy_url_redacted: str
    sql_text: str | None = None
    params: dict[str, Any] | None = None
    sql_text_hash: str
    params_hash: str
    query_hash: str


class TileDBProvenance(BaseModel):
    kind: Literal["tiledb"] = "tiledb"
    uri: str
    query_spec: dict[str, Any]
    query_hash: str


class DataFrameProvenance(BaseModel):
    kind: Literal["dataframe"] = "dataframe"
    name: str
    n_rows: int
    n_cols: int
    columns: list[str]
    content_hash: str


class OutputProvenance(BaseModel):
    kind: Literal["output"] = "output"
    path: str


class EventProvenance(BaseModel):
    kind: Literal["event"] = "event"
    name: str
    payload: dict[str, Any] = Field(default_factory=dict)


ProvenanceRecord = (
    SQLProvenance | TileDBProvenance | DataFrameProvenance | OutputProvenance | EventProvenance
)
