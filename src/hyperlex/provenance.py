"""Enhanced provenance fingerprints for Hyperlex.

Source fingerprints bind ingest signals to stable hashes without requiring
network re-fetch. Analysis provenance attaches fingerprints when available.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from . import PKG_VERSION

ADAPTER_VERSION = "ingest-v1.7"


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def content_fingerprint(raw_signal: str) -> str:
    """Stable content hash of the raw signal body."""
    return _sha256_hex(raw_signal or "")


def source_fingerprint(
    *,
    source: str,
    query: str,
    raw_signal: str,
    source_locator: Optional[str] = None,
    fetched_at: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a source fingerprint block.

    fingerprint_id = sha256(source|query|content_hash|locator)[:24]
    """
    content_hash = content_fingerprint(raw_signal)
    fetched_at = fetched_at or datetime.now(timezone.utc).isoformat()
    locator = source_locator or f"hyperlex://{source}"
    preimage = f"{source}|{query.strip().lower()}|{content_hash}|{locator}|{ADAPTER_VERSION}"
    fingerprint_id = _sha256_hex(preimage)[:24]
    return {
        "fingerprint_id": fingerprint_id,
        "content_hash": content_hash,
        "content_hash_short": content_hash[:16],
        "source": source,
        "query": query,
        "source_locator": locator,
        "fetched_at": fetched_at,
        "adapter_version": ADAPTER_VERSION,
        "package_version": PKG_VERSION,
    }


def analysis_canonical_hash(
    *,
    query: str,
    observed: str,
    neo_terms: list,
    source_fingerprint_id: Optional[str] = None,
) -> str:
    """Canonical analysis hash including optional source fingerprint anchor."""
    payload = {
        "q": query,
        "obs": (observed or "")[:100],
        "neos": neo_terms,
        "src_fp": source_fingerprint_id,
    }
    return _sha256_hex(json.dumps(payload, sort_keys=True, separators=(",", ":")))[:16]


def merge_ingest_provenance(
    base: Dict[str, Any],
    fingerprint: Dict[str, Any],
) -> Dict[str, Any]:
    out = dict(base)
    out["source_fingerprint"] = fingerprint
    out["content_hash"] = fingerprint.get("content_hash")
    out["adapter_version"] = fingerprint.get("adapter_version")
    return out
