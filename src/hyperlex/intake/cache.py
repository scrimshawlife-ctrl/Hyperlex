"""Persistent ingest cache + simple per-source rate limiting.

Disk root: ~/.hyperlex/cache/  (override HYPERLEX_CACHE_DIR)
Rate state: ~/.hyperlex/rate_limit.json

Fail-open: cache/rate errors never block ingest — they degrade to live fetch.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Default TTLs (seconds)
DEFAULT_TTL = 300
SOURCE_TTL: Dict[str, int] = {
    "glossary": 600,
    "real": 600,
    "web": 600,
    "reddit": 180,
    "urban": 600,
    "wikipedia": 1800,
    "firecrawl": 900,
    "crawl4ai": 900,
    "x_search": 120,
    "combined": 180,
    "mock": 0,  # never disk-cache mock (deterministic, cheap)
}

# Minimum seconds between live network fetches per source
SOURCE_MIN_INTERVAL: Dict[str, float] = {
    "glossary": 2.0,
    "real": 2.0,
    "web": 2.0,
    "reddit": 3.0,
    "urban": 1.5,
    "wikipedia": 1.0,
    "firecrawl": 5.0,
    "crawl4ai": 5.0,
    "x_search": 2.0,
    "combined": 5.0,
}

_MEM: Dict[str, Tuple[float, str]] = {}  # key -> (expires_at, value)


def cache_dir() -> Path:
    env = os.environ.get("HYPERLEX_CACHE_DIR", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return (Path.home() / ".hyperlex" / "cache").resolve()


def rate_state_path() -> Path:
    env = os.environ.get("HYPERLEX_RATE_LIMIT_PATH", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return (Path.home() / ".hyperlex" / "rate_limit.json").resolve()


def cache_key(query: str, source: str) -> str:
    return f"{source}:{query.lower().strip()}"


def _disk_path(key: str) -> Path:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
    return cache_dir() / f"{digest}.json"


def ttl_for(source: str) -> int:
    return int(SOURCE_TTL.get(source, DEFAULT_TTL))


def get_cached(key: str, source: str = "") -> Optional[str]:
    """L1 memory then L2 disk. Returns value or None if miss/expired."""
    now = time.time()
    # L1
    if key in _MEM:
        exp, val = _MEM[key]
        if now < exp:
            return val
        del _MEM[key]

    ttl = ttl_for(source or key.split(":", 1)[0])
    if ttl <= 0:
        return None

    path = _disk_path(key)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        exp = float(data.get("expires_at", 0))
        val = data.get("value")
        if not isinstance(val, str) or now >= exp:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
            return None
        _MEM[key] = (exp, val)
        return val
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None


def set_cached(key: str, val: str, source: str = "") -> None:
    ttl = ttl_for(source or key.split(":", 1)[0])
    if ttl <= 0:
        return
    now = time.time()
    exp = now + ttl
    _MEM[key] = (exp, val)
    path = _disk_path(key)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "key": key,
            "source": source or key.split(":", 1)[0],
            "cached_at": now,
            "expires_at": exp,
            "ttl": ttl,
            "value": val,
        }
        path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    except OSError:
        pass  # fail-open


def is_cached(key: str) -> bool:
    return get_cached(key) is not None


def clear_memory_cache() -> None:
    _MEM.clear()


def _load_rate_state() -> Dict[str, float]:
    path = rate_state_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {str(k): float(v) for k, v in data.items() if isinstance(v, (int, float))}
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    return {}


def _save_rate_state(state: Dict[str, float]) -> None:
    path = rate_state_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, sort_keys=True, indent=2), encoding="utf-8")
    except OSError:
        pass


def wait_for_rate_limit(source: str) -> Dict[str, Any]:
    """
    Block until min interval for source has elapsed (sleep).
    Returns diagnostic dict. Env HYPERLEX_NO_RATE_LIMIT=1 disables.
    """
    flag = str(os.environ.get("HYPERLEX_NO_RATE_LIMIT", "")).strip().lower()
    if flag in {"1", "true", "yes", "on"}:
        return {"source": source, "waited": 0.0, "skipped": True}

    min_iv = float(SOURCE_MIN_INTERVAL.get(source, 1.0))
    if min_iv <= 0:
        return {"source": source, "waited": 0.0, "skipped": True}

    state = _load_rate_state()
    last = float(state.get(source, 0.0))
    now = time.time()
    remaining = min_iv - (now - last)
    waited = 0.0
    if remaining > 0:
        time.sleep(remaining)
        waited = remaining
        now = time.time()
    state[source] = now
    _save_rate_state(state)
    return {"source": source, "waited": waited, "min_interval": min_iv, "skipped": False}


def cache_stats() -> Dict[str, Any]:
    d = cache_dir()
    n_files = 0
    if d.exists():
        n_files = sum(1 for p in d.glob("*.json") if p.is_file())
    return {
        "cache_dir": str(d),
        "memory_entries": len(_MEM),
        "disk_entries": n_files,
        "rate_state_path": str(rate_state_path()),
    }
