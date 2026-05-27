from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import pandas as pd

from .models import (
    DataFrameProvenance,
    EventProvenance,
    OutputProvenance,
    ProvenanceRecord,
    SQLProvenance,
    TileDBProvenance,
)
from .security import redact_mapping


def _hash_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _hash_payload(payload: Any) -> str:
    return _hash_text(json.dumps(payload, sort_keys=True, default=str))


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


def _redact_path_or_uri(value: str, *, include_raw: bool = False) -> str:
    if include_raw:
        return value
    if not value:
        return value

    split = urlsplit(value)
    if split.scheme and split.scheme not in {"file"}:
        # Preserve backend/scheme and final path element, hide host and full prefix.
        basename = Path(split.path).name or "<root>"
        return urlunsplit((split.scheme, "***", f"/.../{basename}", "", ""))

    path = Path(value)
    if path.is_absolute():
        return f"<local_path>/{path.name}"
    # Relative repo paths are acceptable in public provenance.
    return value


class ProvenanceLogger:
    """Append-only provenance logger writing validated JSONL records."""

    def __init__(
        self,
        log_dir: str = "run_logs",
        *,
        include_raw_sql: bool = False,
        include_raw_tiledb_uri: bool = False,
        include_raw_paths: bool = False,
    ):
        self.log_dir = log_dir
        self.include_raw_sql = include_raw_sql
        self.include_raw_tiledb_uri = include_raw_tiledb_uri
        self.include_raw_paths = include_raw_paths
        os.makedirs(self.log_dir, exist_ok=True)
        self.path = os.path.join(self.log_dir, "provenance.jsonl")

    def _write(self, record: ProvenanceRecord) -> None:
        payload = record.model_dump()
        payload["_ts"] = datetime.now(timezone.utc).isoformat()
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, default=str) + "\n")

    def log_event(self, name: str, payload: dict[str, Any] | None = None) -> None:
        self._write(EventProvenance(name=name, payload=redact_mapping(payload or {})))

    def log_sql(self, sqlalchemy_url: str, sql_text: str, params: dict[str, Any]) -> None:
        redacted_params = redact_mapping(params)
        sql_hash = _hash_text(sql_text)
        params_hash = _hash_payload(redacted_params)
        qh = _hash_text(sql_hash + params_hash)
        self._write(
            SQLProvenance(
                sqlalchemy_url_redacted=_redact_sqlalchemy_url(sqlalchemy_url),
                sql_text=sql_text if self.include_raw_sql else None,
                params=redacted_params if self.include_raw_sql else None,
                sql_text_hash=sql_hash,
                params_hash=params_hash,
                query_hash=qh,
            )
        )

    def log_tiledb(self, uri: str, query_spec: dict[str, Any]) -> None:
        redacted_uri = _redact_path_or_uri(uri, include_raw=self.include_raw_tiledb_uri)
        redacted_spec = redact_mapping(query_spec)
        qh = _hash_text(redacted_uri + json.dumps(redacted_spec, sort_keys=True, default=str))
        self._write(TileDBProvenance(uri=redacted_uri, query_spec=redacted_spec, query_hash=qh))

    def log_dataframe(self, name: str, df: pd.DataFrame) -> None:
        self._write(
            DataFrameProvenance(
                name=name,
                n_rows=int(df.shape[0]),
                n_cols=int(df.shape[1]),
                columns=[str(c) for c in df.columns.tolist()],
                content_hash=_hash_df(df),
            )
        )

    def log_output(self, path: str) -> None:
        self._write(
            OutputProvenance(path=_redact_path_or_uri(path, include_raw=self.include_raw_paths))
        )
