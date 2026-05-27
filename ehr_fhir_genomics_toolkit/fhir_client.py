from __future__ import annotations

from typing import Any

import requests


def fetch_all_pages(
    url: str,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    timeout_seconds: int = 30,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    next_url: str | None = url
    next_params = params
    while next_url:
        r = requests.get(next_url, headers=headers, params=next_params, timeout=timeout_seconds)
        r.raise_for_status()
        bundle = r.json()
        results.extend(bundle.get("entry", []) or [])
        next_url = None
        for link in bundle.get("link", []) or []:
            if link.get("relation") == "next" and link.get("url"):
                next_url = link["url"]
                break
        next_params = None
    return results
