from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import tiledb

DEFAULT_MAX_SAMPLE_IDS = 100_000
DEFAULT_MAX_GENES = 5_000


def open_ctx(config: dict[str, Any]) -> tiledb.Ctx:
    cfg = tiledb.Config(config or {})
    return tiledb.Ctx(cfg)


def assert_query_size(name: str, values: Iterable[object], max_items: int) -> list[object]:
    items = list(values or [])
    if not items:
        raise ValueError(f"TileDB query requires at least one {name}")
    if len(items) > max_items:
        raise ValueError(
            f"TileDB query has too many {name}: {len(items)} > {max_items}; batch the query"
        )
    return items


def schema_dimension_names(array: tiledb.Array) -> list[str]:
    return [array.schema.domain.dim(i).name for i in range(array.schema.domain.ndim)]


def schema_attribute_names(array: tiledb.Array) -> list[str]:
    return [array.schema.attr(i).name for i in range(array.schema.nattr)]


def require_dimensions(array: tiledb.Array, required_any: dict[str, list[str]]) -> dict[str, str]:
    """Require logical dimensions where each logical name can map to aliases.

    Example: {"gene": ["gene", "gene_symbol"]} returns {"gene": "gene_symbol"}
    when that alias is present.
    """
    dims = set(schema_dimension_names(array))
    resolved: dict[str, str] = {}
    for logical_name, aliases in required_any.items():
        match = next((alias for alias in aliases if alias in dims), None)
        if match is None:
            raise ValueError(
                f"TileDB array missing required dimension for {logical_name!r}; "
                f"expected one of {aliases}, available={sorted(dims)}"
            )
        resolved[logical_name] = match
    return resolved


def require_attributes(array: tiledb.Array, required: list[str]) -> None:
    attrs = set(schema_attribute_names(array))
    missing = [a for a in required if a not in attrs]
    if missing:
        raise ValueError(
            f"TileDB array missing required attrs {missing}; available={sorted(attrs)}"
        )
