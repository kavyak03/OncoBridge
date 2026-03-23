from __future__ import annotations
from typing import Any, Dict
import tiledb

def open_ctx(config: Dict[str, Any]) -> tiledb.Ctx:
    cfg = tiledb.Config(config or {})
    return tiledb.Ctx(cfg)
