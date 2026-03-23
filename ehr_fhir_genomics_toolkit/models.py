from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator


# -------------------------
# Config models
# -------------------------

class SQLTables(BaseModel):
    clinical_metadata: str = "clinical_metadata"
    therapies: str = "therapy_lines"


class SQLConfig(BaseModel):
    sqlalchemy_url: SecretStr = Field(..., description="SQLAlchemy connection string (e.g., mysql+pymysql://user:pass@host/db)")
    tables: SQLTables = Field(default_factory=SQLTables)

    @property
    def sqlalchemy_url_plain(self) -> str:
        return self.sqlalchemy_url.get_secret_value()


class TileDBConfig(BaseModel):
    expression_uri: str = Field(..., description="TileDB URI/path for expression array")
    variants_uri: Optional[str] = Field(default=None, description="TileDB URI/path for variants array (optional)")
    config: Dict[str, Any] = Field(default_factory=dict, description="Extra TileDB config dict")

    @field_validator("expression_uri")
    @classmethod
    def _non_empty_expr(cls, v: str) -> str:
        if not v or not str(v).strip():
            raise ValueError("tiledb.expression_uri must be set")
        return v


class ProvenanceConfig(BaseModel):
    log_dir: str = "run_logs"


class AppConfig(BaseModel):
    sql: Optional[SQLConfig] = None
    tiledb: Optional[TileDBConfig] = None
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
    genes: List[str] = Field(..., min_length=1)
    unit: str = "arbitrary"
    transform: Optional[str] = None


class VariantSpec(BaseModel):
    enabled: bool = False
    mutation_genes: List[str] = Field(default_factory=lambda: ["TP53", "RB1", "MYC"])


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
    sql_text: str
    params: Dict[str, Any]
    query_hash: str


class TileDBProvenance(BaseModel):
    kind: Literal["tiledb"] = "tiledb"
    uri: str
    query_spec: Dict[str, Any]
    query_hash: str


class DataFrameProvenance(BaseModel):
    kind: Literal["dataframe"] = "dataframe"
    name: str
    n_rows: int
    n_cols: int
    columns: List[str]
    content_hash: str


class OutputProvenance(BaseModel):
    kind: Literal["output"] = "output"
    path: str


class EventProvenance(BaseModel):
    kind: Literal["event"] = "event"
    name: str
    payload: Dict[str, Any] = Field(default_factory=dict)


ProvenanceRecord = SQLProvenance | TileDBProvenance | DataFrameProvenance | OutputProvenance | EventProvenance
