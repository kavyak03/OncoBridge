from __future__ import annotations

import os
from typing import Any, Dict, Optional

import yaml
from pydantic import SecretStr

from .models import AppConfig, ProvenanceConfig, SQLConfig, SQLTables, TileDBConfig


def _read_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _env(name: str) -> Optional[str]:
    v = os.environ.get(name)
    return v if v is not None and str(v).strip() != "" else None


def load_config(path: str) -> AppConfig:
    """Load config.yaml and environment overrides into a validated AppConfig.

    Env overrides:
      - EHR_TOOLKIT_CONFIG
      - SQLALCHEMY_URL
      - TILEDB_EXPRESSION_URI
      - TILEDB_VARIANTS_URI
      - PROVENANCE_LOG_DIR
    """
    cfg_path = _env("EHR_TOOLKIT_CONFIG") or path
    raw = _read_yaml(cfg_path)

    sql_raw = raw.get("sql") or {}
    tiledb_raw = raw.get("tiledb") or {}
    prov_raw = raw.get("provenance") or {}

    if _env("SQLALCHEMY_URL"):
        sql_raw["sqlalchemy_url"] = _env("SQLALCHEMY_URL")
    if _env("TILEDB_EXPRESSION_URI"):
        tiledb_raw["expression_uri"] = _env("TILEDB_EXPRESSION_URI")
    if _env("TILEDB_VARIANTS_URI"):
        tiledb_raw["variants_uri"] = _env("TILEDB_VARIANTS_URI")
    if _env("PROVENANCE_LOG_DIR"):
        prov_raw["log_dir"] = _env("PROVENANCE_LOG_DIR")

    sql_cfg = None
    if sql_raw.get("sqlalchemy_url"):
        tables = SQLTables(**(sql_raw.get("tables") or {}))
        sql_cfg = SQLConfig(sqlalchemy_url=SecretStr(str(sql_raw["sqlalchemy_url"])), tables=tables)

    tiledb_cfg = None
    if tiledb_raw.get("expression_uri") is not None:
        # if expression_uri is provided but empty -> validator will raise (desired)
        tiledb_cfg = TileDBConfig(
            expression_uri=str(tiledb_raw.get("expression_uri") or ""),
            variants_uri=str(tiledb_raw["variants_uri"]) if tiledb_raw.get("variants_uri") else None,
            config=dict(tiledb_raw.get("config") or {}),
        )

    prov_cfg = ProvenanceConfig(**(prov_raw or {}))
    return AppConfig(sql=sql_cfg, tiledb=tiledb_cfg, provenance=prov_cfg)
