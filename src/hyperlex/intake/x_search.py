"""X/Twitter ingest adapters.

Priority:
  1. HYPERLEX_X_BEARER_TOKEN → Twitter API v2 recent search (if requests available)
  2. xurl CLI on PATH (optional hermes tooling)
  3. Structured stub with clear provenance (never pretends to be live)

Env:
  HYPERLEX_X_BEARER_TOKEN
  HYPERLEX_X_API_BASE (default https://api.twitter.com/2)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any, Dict, Optional, Tuple

try:
    import requests
except ImportError:
    requests = None


def _offline() -> bool:
    flag = str(os.environ.get("HYPERLEX_OFFLINE", "")).strip().lower()
    return flag in {"1", "true", "yes", "on"}


def _bearer() -> str:
    return (
        os.environ.get("HYPERLEX_X_BEARER_TOKEN", "").strip()
        or os.environ.get("TWITTER_BEARER_TOKEN", "").strip()
        or os.environ.get("X_BEARER_TOKEN", "").strip()
    )


def _api_base() -> str:
    return os.environ.get("HYPERLEX_X_API_BASE", "https://api.twitter.com/2").rstrip("/")


def fetch_x_api(query: str) -> Tuple[str, Dict[str, Any]]:
    """Twitter API v2 recent search. Returns (signal, meta)."""
    token = _bearer()
    locator = f"{_api_base()}/tweets/search/recent"
    meta: Dict[str, Any] = {
        "adapter": "x_api_v2",
        "source_locator": locator,
        "live": False,
    }
    if _offline():
        meta["reason"] = "offline"
        return f"[X_OFFLINE] search disabled for '{query}'", meta
    if not token:
        meta["reason"] = "missing_bearer_token"
        return "", meta
    if requests is None:
        meta["reason"] = "requests_missing"
        return "", meta

    try:
        r = requests.get(
            locator,
            headers={"Authorization": f"Bearer {token}"},
            params={
                "query": query,
                "max_results": 10,
                "tweet.fields": "created_at,public_metrics,lang",
            },
            timeout=10,
        )
        meta["status_code"] = r.status_code
        if r.status_code != 200:
            meta["reason"] = f"http_{r.status_code}"
            return f"[X_API_ERROR] status={r.status_code} for '{query}'", meta
        data = r.json()
        tweets = data.get("data") or []
        if not tweets:
            meta["live"] = True
            meta["n_tweets"] = 0
            return f"[X_API_EMPTY] no recent tweets for '{query}'", meta
        snippets = []
        for t in tweets[:8]:
            text = (t.get("text") or "").replace("\n", " ")[:140]
            snippets.append(text)
        meta["live"] = True
        meta["n_tweets"] = len(tweets)
        signal = (
            f"X/Twitter recent search for '{query}' (n={len(tweets)}): "
            + " | ".join(snippets)
        )
        return signal, meta
    except Exception as exc:
        meta["reason"] = type(exc).__name__
        return f"[X_API_FALLBACK] {type(exc).__name__} for '{query}'", meta


def fetch_x_xurl(query: str) -> Tuple[str, Dict[str, Any]]:
    """Optional xurl CLI bridge."""
    meta: Dict[str, Any] = {"adapter": "xurl", "live": False, "source_locator": "cli://xurl"}
    if _offline():
        meta["reason"] = "offline"
        return "", meta
    xurl = shutil.which("xurl")
    if not xurl:
        meta["reason"] = "xurl_not_on_path"
        return "", meta
    try:
        proc = subprocess.run(
            [xurl, "search", query, "--limit", "8", "--json"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        meta["returncode"] = proc.returncode
        if proc.returncode != 0:
            meta["reason"] = "xurl_nonzero"
            meta["stderr"] = (proc.stderr or "")[:200]
            return "", meta
        raw = (proc.stdout or "").strip()
        if not raw:
            meta["reason"] = "empty_stdout"
            return "", meta
        # Accept JSON array/object or plain lines
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                texts = [str(item.get("text", item))[:140] for item in data[:8] if item]
            elif isinstance(data, dict) and "data" in data:
                texts = [str(t.get("text", ""))[:140] for t in (data.get("data") or [])[:8]]
            else:
                texts = [raw[:400]]
        except json.JSONDecodeError:
            texts = [ln.strip()[:140] for ln in raw.splitlines() if ln.strip()][:8]
        meta["live"] = True
        meta["n_items"] = len(texts)
        return f"X/xurl search for '{query}': " + " | ".join(texts), meta
    except Exception as exc:
        meta["reason"] = type(exc).__name__
        return "", meta


def fetch_x_stub(query: str) -> Tuple[str, Dict[str, Any]]:
    meta = {
        "adapter": "stub",
        "live": False,
        "source_locator": "hyperlex://x_search/stub",
        "reason": "no_live_backend",
        "hint": "Set HYPERLEX_X_BEARER_TOKEN or install xurl for live X ingest",
    }
    signal = (
        f"[X_SEARCH_STUB] Structured placeholder for '{query}': "
        f"velocity markers — sharp money, revenge narrative, memetic spread. "
        f"Not live; do not treat as OBSERVED market chatter."
    )
    return signal, meta


def fetch_x_search(query: str) -> Tuple[str, Dict[str, Any]]:
    """
    Best available X adapter.

    Returns (signal, meta) where meta includes adapter, live, source_locator.
    """
    signal, meta = fetch_x_api(query)
    if signal and meta.get("live"):
        return signal, meta
    # try xurl if API unavailable
    signal2, meta2 = fetch_x_xurl(query)
    if signal2 and meta2.get("live"):
        return signal2, meta2
    # prefer API error message over pure stub if we had a token failure that's informative
    if signal and meta.get("reason") not in (None, "missing_bearer_token", "offline"):
        meta["fallback_chain"] = ["x_api", "stub"]
        return signal, meta
    signal_s, meta_s = fetch_x_stub(query)
    meta_s["fallback_chain"] = ["x_api", "xurl", "stub"]
    meta_s["prior_reasons"] = {
        "x_api": meta.get("reason"),
        "xurl": meta2.get("reason"),
    }
    return signal_s, meta_s
