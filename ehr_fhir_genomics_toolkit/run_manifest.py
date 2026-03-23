from __future__ import annotations

import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def make_run_id(prefix: str = "run") -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    return f"{ts}_{prefix}"


def build_run_manifest(
    *,
    run_id: str,
    mode: str,
    config_path: Optional[str],
    cohort: Dict[str, Any],
    features: Dict[str, Any],
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
    benchmark: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    manifest = {
        "run_id": run_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "config_path": config_path,
        "cohort": cohort,
        "features": features,
        "inputs": inputs,
        "outputs": outputs,
        "environment": {
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "cwd": os.getcwd(),
        },
    }
    if benchmark is not None:
        manifest["benchmark"] = benchmark
    if extra:
        manifest["extra"] = extra
    return manifest


def write_run_manifest(manifest: Dict[str, Any], log_dir: str = "run_logs/manifests") -> str:
    out_dir = Path(log_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{manifest['run_id']}.json"
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return str(out_path)