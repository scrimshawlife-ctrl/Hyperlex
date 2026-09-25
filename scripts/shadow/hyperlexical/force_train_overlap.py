"""Count force-train rows that still sit in val or in the selection set.

The historical move (`apply_unbind_force_train`) takes OBSERVED
``(text, role_scheme)`` keys out of val. A row can still share an id or a
normalized-text sha with val or with the checkpoint-selection rows. This
module counts those rows on every run. ``HLX_FORCE_TRAIN_DISJOINT=1`` drops
the overlapping rows from val and refuses when that drop is more than half
of a val split.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from .heldout_census import normalize_group_text
from .holdout_guard import normalized_text_sha256
from .selection_surface import row_id
from .unbind_recipe import UNBIND_FORCE_TRAIN_PATH_ENV, resolve_unbind_force_train_path

FORCE_TRAIN_DISJOINT_ENV = "HLX_FORCE_TRAIN_DISJOINT"
_ID_FIELDS = ("id", "row_id")


def resolve_force_train_disjoint(raw: str | None = None) -> bool:
    """Drop overlapping val rows. Default off: count and log only."""
    if raw is None:
        raw = os.environ.get(FORCE_TRAIN_DISJOINT_ENV)
    return raw == "1"


def load_force_train_rows(path: str | Path | None = None) -> list[dict[str, Any]]:
    """JSONL objects from the force-train path. Empty path → no rows.

    Same fail-closed file rules as ``load_force_train_keys`` (path must exist,
    each line a JSON object with non-empty string ``text``). Extra fields are
    kept so id matching can see them.
    """
    raw = resolve_unbind_force_train_path(path)
    if not raw:
        return []
    file = Path(raw)
    if not file.is_file():
        raise ValueError(f"{UNBIND_FORCE_TRAIN_PATH_ENV} is not a file: {file}")
    try:
        body = file.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"{UNBIND_FORCE_TRAIN_PATH_ENV} is unreadable: {file}") from exc
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(body.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{UNBIND_FORCE_TRAIN_PATH_ENV} line {index} is not valid JSON") from exc
        if not isinstance(obj, dict):
            raise ValueError(f"{UNBIND_FORCE_TRAIN_PATH_ENV} line {index} must be a JSON object")
        text = obj.get("text")
        scheme = obj.get("role_scheme")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"{UNBIND_FORCE_TRAIN_PATH_ENV} line {index} needs non-empty string text")
        if scheme not in {"positional", "type_slot"}:
            raise ValueError(
                f"{UNBIND_FORCE_TRAIN_PATH_ENV} line {index} role_scheme must be "
                f"positional|type_slot, got {scheme!r}"
            )
        rows.append(obj)
    return rows


def _explicit_ids(row: Mapping[str, Any]) -> set[str]:
    found: set[str] = set()
    for key in _ID_FIELDS:
        token = row.get(key)
        if isinstance(token, str) and token.strip():
            found.add(token.strip())
    return found


def _text_sha(row: Mapping[str, Any]) -> str | None:
    text = str(row.get("text") or "")
    if not normalize_group_text(text):
        return None
    return normalized_text_sha256(text)


def _index(rows: Sequence[Mapping[str, Any]]) -> tuple[set[str], set[str]]:
    ids: set[str] = set()
    shas: set[str] = set()
    for row in rows:
        ids.add(row_id(row))
        ids.update(_explicit_ids(row))
        sha = _text_sha(row)
        if sha:
            shas.add(sha)
    return ids, shas


def _hits(row: Mapping[str, Any], ids: set[str], shas: set[str]) -> bool:
    if row_id(row) in ids or (_explicit_ids(row) & ids):
        return True
    sha = _text_sha(row)
    return bool(sha and sha in shas)


def overlap_counts(
    force_rows: Sequence[Mapping[str, Any]],
    val_rows: Sequence[Mapping[str, Any]],
    selection_rows: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    """How many force-train rows match val, selection, or either, by id or text sha."""
    val_ids, val_shas = _index(val_rows)
    sel_ids, sel_shas = _index(selection_rows)
    in_val = 0
    in_selection = 0
    union = 0
    for row in force_rows:
        hit_val = _hits(row, val_ids, val_shas)
        hit_sel = _hits(row, sel_ids, sel_shas)
        if hit_val:
            in_val += 1
        if hit_sel:
            in_selection += 1
        if hit_val or hit_sel:
            union += 1
    return {
        "n_force_rows": len(force_rows),
        "n_overlap": union,
        "n_in_val": in_val,
        "n_in_selection": in_selection,
    }


def _drop(rows: list, force_ids: set[str], force_shas: set[str]) -> tuple[list, int]:
    kept = []
    dropped = 0
    for row in rows:
        if _hits(row, force_ids, force_shas):
            dropped += 1
        else:
            kept.append(row)
    return kept, dropped


def _over_half(dropped: int, total: int) -> bool:
    """True when ``dropped / total > 1/2``. Empty val is not over half."""
    return total > 0 and dropped * 2 > total


def enforce_force_train_disjoint(
    classify_val: list,
    unbind_val: list,
    selection_rows: Sequence[Mapping[str, Any]],
    *,
    force_rows: Sequence[Mapping[str, Any]] | None = None,
    disjoint: bool | None = None,
) -> tuple[list, list, dict[str, Any]]:
    """Log force-train overlap. Optionally drop overlapping val rows.

    Returns the same list objects when nothing is dropped. Prints the overlap
    count even when the disjoint flag is off. Refuses when a drop would remove
    more than half of classify val or more than half of unbind val.
    """
    rows = list(load_force_train_rows() if force_rows is None else force_rows)
    do_drop = resolve_force_train_disjoint() if disjoint is None else bool(disjoint)
    val_rows = list(classify_val) + list(unbind_val)
    counts = overlap_counts(rows, val_rows, selection_rows)
    print(
        "[force-train] overlap "
        f"n={counts['n_overlap']} in_val={counts['n_in_val']} "
        f"in_selection={counts['n_in_selection']} force_rows={counts['n_force_rows']}",
        flush=True,
    )
    report: dict[str, Any] = {
        **counts,
        "disjoint": do_drop,
        "n_dropped_classify_val": 0,
        "n_dropped_unbind_val": 0,
        "n_classify_val": len(classify_val),
        "n_unbind_val": len(unbind_val),
    }
    if not do_drop:
        return classify_val, unbind_val, report
    force_ids, force_shas = _index(rows)
    new_classify, dropped_c = _drop(classify_val, force_ids, force_shas)
    new_unbind, dropped_u = _drop(unbind_val, force_ids, force_shas)
    report["n_dropped_classify_val"] = dropped_c
    report["n_dropped_unbind_val"] = dropped_u
    print(
        "[force-train] disjoint dropped "
        f"classify_val={dropped_c}/{len(classify_val)} "
        f"unbind_val={dropped_u}/{len(unbind_val)}",
        flush=True,
    )
    if _over_half(dropped_c, len(classify_val)) or _over_half(dropped_u, len(unbind_val)):
        raise SystemExit(
            "REFUSE: HLX_FORCE_TRAIN_DISJOINT dropped share of val is over 50%: "
            f"classify_val={dropped_c}/{len(classify_val)} "
            f"unbind_val={dropped_u}/{len(unbind_val)}"
        )
    if dropped_c == 0 and dropped_u == 0:
        return classify_val, unbind_val, report
    return new_classify, new_unbind, report
