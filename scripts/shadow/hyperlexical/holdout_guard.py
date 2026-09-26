"""Drop frozen holdout rows before unbind training and checkpoint selection.

Manifests are id lists plus sha256 hashes of census-normalized text. This
module does not train, score, or read row text out of a manifest.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from .heldout_census import _refuse_embedded_rows, normalize_group_text
from .selection_surface import row_id

HOLDOUT_MANIFESTS_ENV = "HLX_HOLDOUT_MANIFESTS"
ALLOW_NO_HOLDOUT_ENV = "HLX_ALLOW_NO_HOLDOUT"
_ID_KEYS = frozenset({"row_ids", "ids"})
_HASH_KEYS = frozenset({"normalized_text_sha256"})
_REMOVED_KEYS = ("classify_train", "classify_val", "unbind_train", "unbind_val")


class HoldoutSpec:
    """Union of one or more holdout manifests."""

    def __init__(
        self,
        row_ids: frozenset[str],
        text_hashes: frozenset[str],
        manifests: tuple[dict[str, Any], ...],
    ) -> None:
        self.row_ids = row_ids
        self.text_hashes = text_hashes
        self.manifests = manifests

    @property
    def active(self) -> bool:
        return bool(self.row_ids or self.text_hashes)


def _empty_spec() -> HoldoutSpec:
    return HoldoutSpec(frozenset(), frozenset(), ())


def normalized_text_sha256(text: str) -> str:
    """sha256 of ``heldout_census.normalize_group_text`` (UTF-8)."""
    normalized = normalize_group_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def allow_no_holdout(raw: str | None = None) -> bool:
    if raw is None:
        raw = os.environ.get(ALLOW_NO_HOLDOUT_ENV)
    return raw == "1"


def resolve_manifest_paths(raw: str | None = None) -> list[str]:
    """Comma-separated ``HLX_HOLDOUT_MANIFESTS``. Empty segments are ignored."""
    if raw is None:
        raw = os.environ.get(HOLDOUT_MANIFESTS_ENV, "")
    paths: list[str] = []
    seen: set[str] = set()
    for part in str(raw or "").split(","):
        item = part.strip()
        if not item or item in seen:
            continue
        seen.add(item)
        paths.append(item)
    return paths


def merge_manifest_env(extra: Sequence[str]) -> str:
    """Union CLI paths into ``HLX_HOLDOUT_MANIFESTS`` and return the value."""
    paths = resolve_manifest_paths()
    for item in extra:
        token = str(item or "").strip()
        if token and token not in paths:
            paths.append(token)
    joined = ",".join(paths)
    os.environ[HOLDOUT_MANIFESTS_ENV] = joined
    return joined


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _take_token(item: str, *, kind: str) -> str | None:
    token = item.strip()
    if not token:
        return None
    if kind == "hash":
        lowered = token.lower()
        if len(lowered) != 64 or any(ch not in "0123456789abcdef" for ch in lowered):
            raise SystemExit(
                "REFUSE: holdout manifest normalized_text_sha256 entries must be 64-char hex"
            )
        return lowered
    if all(ch in "0123456789abcdefABCDEF" for ch in token):
        return token.lower()
    return token


def _take_strings(value: list[Any], found: set[str], key: str) -> None:
    if not all(isinstance(item, str) for item in value):
        raise SystemExit(f"REFUSE: holdout manifest {key} must be strings")
    kind = "hash" if key in _HASH_KEYS else "id"
    for item in value:
        token = _take_token(item, kind=kind)
        if token:
            found.add(token)


def _collect(obj: Any, ids: set[str], hashes: set[str]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in _ID_KEYS and isinstance(value, list):
                _take_strings(value, ids, key)
            elif key in _HASH_KEYS and isinstance(value, list):
                _take_strings(value, hashes, key)
            elif isinstance(value, (dict, list)):
                _collect(value, ids, hashes)
    elif isinstance(obj, list):
        for value in obj:
            if isinstance(value, (dict, list)):
                _collect(value, ids, hashes)


def _read_manifest(path: str) -> tuple[dict[str, Any], set[str], set[str]]:
    file = Path(path)
    if not file.is_file():
        raise SystemExit(f"REFUSE: holdout manifest is not a file: {file}")
    if "holdout-scores" in file.name:
        raise SystemExit(f"REFUSE: will not read holdout scores {file}")
    try:
        payload = json.loads(file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise SystemExit(f"REFUSE: holdout manifest is not JSON: {file}") from None
    ids: set[str] = set()
    hashes: set[str] = set()
    if isinstance(payload, list) and all(isinstance(item, str) for item in payload):
        _take_strings(payload, ids, "row_ids")
    elif isinstance(payload, (dict, list)):
        _refuse_embedded_rows(payload)
        _collect(payload, ids, hashes)
    else:
        raise SystemExit("REFUSE: holdout manifest must be a JSON object or an ID list")
    if not ids and not hashes:
        raise SystemExit(
            f"REFUSE: holdout manifest has no row_ids or normalized_text_sha256: {file}"
        )
    record = {
        "path": str(file),
        "sha256": _file_sha256(file),
        "n_row_ids": len(ids),
        "n_text_hashes": len(hashes),
    }
    return record, ids, hashes


def load_holdout_spec(raw: str | None = None) -> HoldoutSpec:
    """Load manifests from ``raw`` or ``HLX_HOLDOUT_MANIFESTS``. Empty env → empty spec."""
    paths = resolve_manifest_paths(raw)
    if not paths:
        return _empty_spec()
    manifests: list[dict[str, Any]] = []
    ids: set[str] = set()
    hashes: set[str] = set()
    for item in paths:
        record, file_ids, file_hashes = _read_manifest(item)
        manifests.append(record)
        ids.update(file_ids)
        hashes.update(file_hashes)
    return HoldoutSpec(frozenset(ids), frozenset(hashes), tuple(manifests))


def require_holdout_for_training() -> HoldoutSpec:
    """Fail when training is armed and no manifest or explicit override is set."""
    spec = load_holdout_spec()
    if os.environ.get("HYPERLEX_ALLOW_TRAIN") == "1" and not spec.manifests and not allow_no_holdout():
        raise SystemExit(
            "REFUSE: HYPERLEX_ALLOW_TRAIN=1 but no holdout manifest. "
            f"Set {HOLDOUT_MANIFESTS_ENV} to comma-separated manifest paths, "
            "pass --holdout-manifest, or set "
            f"{ALLOW_NO_HOLDOUT_ENV}=1 to override."
        )
    return spec


def holdout_match(row: Mapping[str, Any], spec: HoldoutSpec) -> str | None:
    """``row_id`` or ``text`` when the row is in the frozen holdout."""
    if not spec.active:
        return None
    if row_id(row) in spec.row_ids:
        return "row_id"
    if normalized_text_sha256(str(row.get("text") or "")) in spec.text_hashes:
        return "text"
    return None


def filter_holdout_rows(rows: list, spec: HoldoutSpec) -> tuple[list, int]:
    """Drop matching rows. Returns the original list when nothing matches."""
    if not spec.active:
        return rows, 0
    kept: list = []
    removed = 0
    for row in rows:
        if holdout_match(row, spec):
            removed += 1
        else:
            kept.append(row)
    if removed == 0:
        return rows, 0
    return kept, removed


def assert_no_holdout(rows: Sequence[Mapping[str, Any]], spec: HoldoutSpec, where: str) -> None:
    """Fail the run if any manifest id or text hash is still in ``rows``."""
    if not spec.active:
        return
    n_id = 0
    n_text = 0
    for row in rows:
        kind = holdout_match(row, spec)
        if kind == "row_id":
            n_id += 1
        elif kind == "text":
            n_text += 1
    if n_id or n_text:
        raise SystemExit(
            f"REFUSE: holdout overlap remains in {where}: "
            f"{n_id} row_id match(es), {n_text} normalized-text match(es)"
        )


def holdout_receipt(spec: HoldoutSpec, removed: Mapping[str, int]) -> dict[str, Any]:
    """Receipt block: file sha256 values and rows removed per split."""
    return {
        "manifests": [dict(item) for item in spec.manifests],
        "manifest_sha256": [str(item["sha256"]) for item in spec.manifests],
        "removed": {key: int(removed.get(key, 0)) for key in _REMOVED_KEYS},
        "allow_no_holdout": allow_no_holdout(),
    }


def log_holdout(spec: HoldoutSpec, removed: Mapping[str, int]) -> None:
    """One stdout line for a training run that loaded a manifest or an override."""
    if not spec.manifests and not allow_no_holdout() and os.environ.get("HYPERLEX_ALLOW_TRAIN") != "1":
        return
    sha = ",".join(str(item["sha256"]) for item in spec.manifests) or "none"
    counts = " ".join(f"{key}={int(removed.get(key, 0))}" for key in _REMOVED_KEYS)
    override = ""
    if allow_no_holdout() and not spec.manifests:
        override = f" {ALLOW_NO_HOLDOUT_ENV}=1"
    print(f"[holdout]{override} manifest_sha256={sha} removed {counts}", flush=True)
