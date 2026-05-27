from __future__ import annotations

import json
import shutil
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pandas as pd


def _resolve_roots(allowed_roots: Iterable[str | Path]) -> list[Path]:
    return [Path(root).resolve() for root in allowed_roots]


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def assert_path_under_allowed_root(path: str | Path, allowed_roots: Iterable[str | Path]) -> Path:
    resolved = Path(path).resolve()
    roots = _resolve_roots(allowed_roots)
    if not roots or not any(_is_within(resolved, root) for root in roots):
        joined = ", ".join(str(r) for r in roots) or "<none>"
        raise ValueError(
            f"Refusing to operate on path outside allowed roots: {resolved}; allowed roots: {joined}"
        )
    return resolved


def safe_unlink(path: str | Path, allowed_roots: Iterable[str | Path]) -> None:
    resolved = assert_path_under_allowed_root(path, allowed_roots)
    if resolved.exists():
        if not resolved.is_file():
            raise ValueError(f"Refusing to unlink non-file path: {resolved}")
        resolved.unlink()


def safe_rmtree(path: str | Path, allowed_roots: Iterable[str | Path]) -> None:
    resolved = assert_path_under_allowed_root(path, allowed_roots)
    if resolved.exists():
        if not resolved.is_dir():
            raise ValueError(f"Refusing to recursively delete non-directory path: {resolved}")
        shutil.rmtree(resolved)


def atomic_write_csv(df: pd.DataFrame, path: str | Path, **to_csv_kwargs: Any) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.tmp")
    df.to_csv(tmp, **to_csv_kwargs)
    tmp.replace(target)
    return target


def atomic_write_json(payload: Any, path: str | Path, *, indent: int = 2) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.tmp")
    tmp.write_text(json.dumps(payload, indent=indent, default=str), encoding="utf-8")
    tmp.replace(target)
    return target


def atomic_write_text(text: str, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(target)
    return target
