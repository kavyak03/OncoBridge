from __future__ import annotations
from typing import Any, Dict, List, Optional
import requests

def fetch_all_pages(url: str, headers: Optional[Dict[str, str]] = None, params: Optional[Dict[str, Any]] = None, timeout_seconds: int = 30) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    next_url: Optional[str] = url
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
