from __future__ import annotations

import re
from typing import Any

_SQL_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$")


SENSITIVE_KEYS = {"password", "passwd", "pwd", "token", "secret", "key", "api_key"}


def validate_sql_identifier(name: str) -> str:
    """Validate a SQL identifier that cannot be bound as a SQL parameter.

    SQLAlchemy parameters protect values, not table/column names. This helper
    keeps configurable table names to a conservative ``schema.table`` shape.
    """
    if not isinstance(name, str) or not _SQL_IDENTIFIER_RE.fullmatch(name.strip()):
        raise ValueError(f"Unsafe SQL identifier: {name!r}")
    return name.strip()


def redact_mapping(value: Any) -> Any:
    """Recursively redact likely secret values in dict/list payloads."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            key = str(k)
            if any(s in key.lower() for s in SENSITIVE_KEYS):
                out[key] = "***"
            else:
                out[key] = redact_mapping(v)
        return out
    if isinstance(value, list):
        return [redact_mapping(v) for v in value]
    if isinstance(value, tuple):
        return tuple(redact_mapping(v) for v in value)
    return value
