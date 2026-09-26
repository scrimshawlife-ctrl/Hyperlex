"""Release training set: drop share-alike (CC BY-SA) derived rows. No torch. D5(b).

``HYPERLEX_RELEASE_SET=1`` drops every export row whose licence is CC BY-SA
(Wiktionary), and every other row with the same normalized text, so a phrase
first seen on Wiktionary cannot re-enter from another source. Applied by the
train loop and by every eval that compares a release candidate, so train and
eval surfaces match.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections import Counter

RELEASE_ENV = "HYPERLEX_RELEASE_SET"
_CC_SA = re.compile(r"CC[- ]?BY[- ]?SA", re.I)
_TAG = re.compile(r"\b(?:TOKEN|SLOT|MARKER):")


def enabled(raw: str | None = None) -> bool:
    value = (os.environ.get(RELEASE_ENV, "") if raw is None else raw).strip()
    if value not in ("", "0", "1"):
        raise ValueError(f"{RELEASE_ENV} must be 0 or 1")
    return value == "1"


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", _TAG.sub("", text or "").strip().lower())


def is_share_alike(row: dict) -> bool:
    return bool(_CC_SA.search(str(row.get("license") or ""))) or str(row.get("source_license") or "").startswith("CC-BY-SA")


def release_rows(rows: list[dict]) -> tuple[list[dict], dict]:
    sa_texts = {_norm(r.get("text")) for r in rows if is_share_alike(r)}
    kept, by_license, by_text = [], 0, 0
    for r in rows:
        if is_share_alike(r):
            by_license += 1
        elif _norm(r.get("text")) in sa_texts:
            by_text += 1
        else:
            kept.append(r)
    blob = "\n".join(json.dumps({**r, "typology": sorted(r.get("typology") or [])}, sort_keys=True, ensure_ascii=False) for r in kept)
    return kept, {
        "release_set": True,
        "n_input": len(rows),
        "n_kept": len(kept),
        "n_excluded_share_alike": by_license,
        "n_excluded_same_text": by_text,
        "kept_by_task_split": {f"{k[0]}:{k[1]}": v for k, v in Counter((r.get("task"), r.get("split")) for r in kept).items()},
        "release_content_sha256": hashlib.sha256(blob.encode("utf-8")).hexdigest(),
    }


def maybe_release(rows: list[dict]) -> tuple[list[dict], dict]:
    if not enabled():
        return rows, {"release_set": False}
    return release_rows(rows)
