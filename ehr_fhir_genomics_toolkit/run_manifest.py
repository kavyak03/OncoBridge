from __future__ import annotations

import json
import os
import platform
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def make_run_id(prefix: str = "run") -> str:
    safe_prefix = prefix.strip().replace(" ", "_") or "run"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{safe_prefix}-{timestamp}-{uuid.uuid4().hex[:8]}"


def _read_git_ref(git_dir: Path, ref_name: str) -> str | None:
    """Read a git ref from loose refs or packed-refs without invoking subprocess."""
    ref_path = git_dir / ref_name
    if ref_path.exists():
        value = ref_path.read_text(encoding="utf-8").strip()
        return value or None

    packed_refs = git_dir / "packed-refs"
    if packed_refs.exists():
        for line in packed_refs.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("^"):
                continue
            parts = line.split(" ", maxsplit=1)
            if len(parts) == 2 and parts[1] == ref_name:
                return parts[0]

    return None


def git_commit_sha(repo_root: str | Path = ".") -> str | None:
    """
    Return the current git commit SHA if available.

    This avoids subprocess so run manifests remain safe in packaged zips,
    containers, and restricted production environments.
    """
    root = Path(repo_root).resolve()
    git_path = root / ".git"

    if not git_path.exists():
        return None

    # Worktrees/submodules can store .git as a file: "gitdir: /path/to/gitdir"
    if git_path.is_file():
        text = git_path.read_text(encoding="utf-8").strip()
        prefix = "gitdir:"
        if not text.startswith(prefix):
            return None
        git_dir = Path(text[len(prefix) :].strip())
        if not git_dir.is_absolute():
            git_dir = (root / git_dir).resolve()
    else:
        git_dir = git_path

    head_path = git_dir / "HEAD"
    if not head_path.exists():
        return None

    head = head_path.read_text(encoding="utf-8").strip()
    if not head:
        return None

    if head.startswith("ref:"):
        ref_name = head.removeprefix("ref:").strip()
        return _read_git_ref(git_dir, ref_name)

    # Detached HEAD case.
    return head


def env_snapshot() -> dict[str, Any]:
    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "cwd": str(Path.cwd()),
        "git_commit": git_commit_sha(),
    }


def build_run_manifest(
    run_id: str,
    mode: str,
    config_path: str | None,
    cohort: dict[str, Any],
    features: dict[str, Any],
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    benchmark: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "config_path": config_path,
        "cohort": cohort,
        "features": features,
        "inputs": inputs,
        "outputs": outputs,
        "benchmark": benchmark,
        "environment": env_snapshot(),
    }


def write_run_manifest(manifest: dict[str, Any], log_dir: str = "run_logs/manifests") -> str:
    out_dir = Path(os.environ.get("PROVENANCE_LOG_DIR", log_dir))
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{manifest['run_id']}.json"
    out_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return str(out_path)
