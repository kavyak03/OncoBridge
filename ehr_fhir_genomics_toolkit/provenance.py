from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import pandas as pd

from .models import (
    DataFrameProvenance,
    EventProvenance,
    OutputProvenance,
    ProvenanceRecord,
    SQLProvenance,
    TileDBProvenance,
)


def _hash_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _hash_df(df: pd.DataFrame) -> str:
    h = pd.util.hash_pandas_object(df, index=True).values
    return hashlib.sha256(h.tobytes()).hexdigest()


def _redact_sqlalchemy_url(url: str) -> str:
    if "://" not in url:
        return "***"
    prefix, rest = url.split("://", 1)
    if "@" not in rest:
        return f"{prefix}://***"
    creds, tail = rest.split("@", 1)
    if ":" in creds:
        user = creds.split(":", 1)[0]
        return f"{prefix}://{user}:***@{tail}"
    return f"{prefix}://***@{tail}"


class ProvenanceLogger:
    """Append-only provenance logger writing validated JSONL records."""

    def __init__(self, log_dir: str = "run_logs"):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.path = os.path.join(self.log_dir, "provenance.jsonl")

    def _write(self, record: ProvenanceRecord) -> None:
        payload = record.model_dump()
        payload["_ts"] = datetime.now(timezone.utc).isoformat()
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, default=str) + "\n")

    def log_event(self, name: str, payload: Optional[Dict[str, Any]] = None) -> None:
        self._write(EventProvenance(name=name, payload=payload or {}))

    def log_sql(self, sqlalchemy_url: str, sql_text: str, params: Dict[str, Any]) -> None:
        qh = _hash_text(sql_text + json.dumps(params, sort_keys=True, default=str))
        self._write(SQLProvenance(
            sqlalchemy_url_redacted=_redact_sqlalchemy_url(sqlalchemy_url),
            sql_text=sql_text,
            params=params,
            query_hash=qh,
        ))

    def log_tiledb(self, uri: str, query_spec: Dict[str, Any]) -> None:
        qh = _hash_text(uri + json.dumps(query_spec, sort_keys=True, default=str))
        self._write(TileDBProvenance(uri=uri, query_spec=query_spec, query_hash=qh))

    def log_dataframe(self, name: str, df: pd.DataFrame) -> None:
        self._write(DataFrameProvenance(
            name=name,
            n_rows=int(df.shape[0]),
            n_cols=int(df.shape[1]),
            columns=[str(c) for c in df.columns.tolist()],
            content_hash=_hash_df(df),
        ))

    def log_output(self, path: str) -> None:
        self._write(OutputProvenance(path=path))
