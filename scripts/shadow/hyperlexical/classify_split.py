"""Opt-in classify train/val override (HLX_CLASSIFY_SPLIT_FILE, default off).

The file maps ``selection_surface.row_id`` to ``train``, ``val``, or ``drop``.
It runs before classify admission and the holdout guard. It changes list
membership only: row dicts are not rewritten, so a later holdout ``row_id``
match still sees the original split. Unset returns the same list objects.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from .selection_surface import row_id

SPLIT_FILE_ENV = "HLX_CLASSIFY_SPLIT_FILE"
SCHEMA = "hyperlex.classify_split_override.v0.1"
DESTINATIONS = frozenset({"train", "val", "drop"})


def resolve_split_path(raw: str | None = None) -> str | None:
    if raw is None:
        raw = os.environ.get(SPLIT_FILE_ENV)
    if raw is None:
        return None
    token = str(raw).strip()
    return token or None


def trainval_base_sha256(train: list, val: list) -> str:
    """sha256 of train row ids in order, then val row ids in order."""
    lines = [row_id(row) for row in train] + [row_id(row) for row in val]
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def _refuse(message: str) -> None:
    raise SystemExit(f"REFUSE: {message}")


def _load(path: str) -> tuple[dict[str, Any], str]:
    file = Path(path)
    if not file.is_file():
        _refuse(f"{SPLIT_FILE_ENV} is not a file")
    try:
        payload = json.loads(file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        _refuse(f"{SPLIT_FILE_ENV} is not JSON")
    if not isinstance(payload, dict):
        _refuse(f"{SPLIT_FILE_ENV} must be a JSON object")
    schema = payload.get("schema")
    if schema != SCHEMA:
        _refuse(f"{SPLIT_FILE_ENV} schema must be {SCHEMA}")
    mapping = payload.get("split_by_row_id")
    if not isinstance(mapping, dict) or not mapping:
        _refuse(f"{SPLIT_FILE_ENV} split_by_row_id must be a non-empty object")
    if not all(isinstance(key, str) and isinstance(value, str) for key, value in mapping.items()):
        _refuse(f"{SPLIT_FILE_ENV} split_by_row_id keys and values must be strings")
    bad = sorted({value for value in mapping.values() if value not in DESTINATIONS})
    if bad:
        _refuse(f"{SPLIT_FILE_ENV} has an unknown destination")
    file_sha = hashlib.sha256(file.read_bytes()).hexdigest()
    return payload, file_sha


def apply_classify_split_file(
    train: list,
    val: list,
    *,
    path: str | None = None,
) -> tuple[list, list, dict[str, Any] | None]:
    """Override classify list membership. Unset returns ``train`` and ``val`` unchanged."""
    chosen = resolve_split_path(path)
    if chosen is None:
        return train, val, None
    payload, file_sha = _load(chosen)
    mapping: Mapping[str, str] = payload["split_by_row_id"]
    seen: dict[str, str] = {}
    ordered: list[tuple[str, dict]] = []
    for origin, rows in (("train", train), ("val", val)):
        for row in rows:
            ident = row_id(row)
            if ident in seen:
                _refuse("duplicate classify row_id in train/val")
            seen[ident] = origin
            ordered.append((origin, row))
    missing = len(seen) - sum(1 for ident in seen if ident in mapping)
    extra = len(mapping) - sum(1 for ident in mapping if ident in seen)
    if missing:
        _refuse(f"{SPLIT_FILE_ENV} is missing {missing} classify train/val rows")
    if extra:
        _refuse(f"{SPLIT_FILE_ENV} has {extra} ids that are not classify train/val rows")
    expected = payload.get("base_trainval_sha256")
    if expected is not None:
        if not isinstance(expected, str) or expected != trainval_base_sha256(train, val):
            _refuse(f"{SPLIT_FILE_ENV} base_trainval_sha256 does not match these rows")
    new_train: list = []
    new_val: list = []
    n_train_to_val = n_val_to_train = n_dropped_train = n_dropped_val = 0
    for origin, row in ordered:
        dest = mapping[row_id(row)]
        if dest == "drop":
            if origin == "train":
                n_dropped_train += 1
            else:
                n_dropped_val += 1
            continue
        if origin == "train" and dest == "val":
            n_train_to_val += 1
        elif origin == "val" and dest == "train":
            n_val_to_train += 1
        if dest == "train":
            new_train.append(row)
        else:
            new_val.append(row)
    receipt = {
        "enabled": True,
        "file_sha256": file_sha,
        "n_train_to_val": n_train_to_val,
        "n_val_to_train": n_val_to_train,
        "n_dropped_train": n_dropped_train,
        "n_dropped_val": n_dropped_val,
        "n_train": len(new_train),
        "n_val": len(new_val),
    }
    return new_train, new_val, receipt
