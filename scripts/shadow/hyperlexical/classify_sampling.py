"""Deterministic classify-epoch sampling.

``HLX_SEED`` unset returns no seed and does not define an epoch sample.
The rule in this module is the frozen selector. It reads text, lineage,
class, and row order. It does not read a score, a loss, or a reserve.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Mapping, Sequence

from .holdout_guard import normalized_text_sha256

SAMPLING_ENV = "HYPERLEX_CLASSIFY_SAMPLING"
UNCAPPED = "uncapped"
RULE = "inferred_none_circular_sha256_v1"
CAP = 219
EXPECTED_OBSERVED_NONE = 219
EXPECTED_INFERRED_NONE = 1935
OBSERVED = "OBSERVED"
INFERRED = "INFERRED"
NONE = "none"


def canonical_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def parse_sampling_policy(raw: str | None) -> tuple[str, int | None]:
    """Return ``(uncapped, None)`` or ``(rule, 219)``. Any other token fails."""
    if raw is None or not str(raw).strip() or str(raw).strip() == UNCAPPED:
        return UNCAPPED, None
    token = str(raw).strip()
    prefix = RULE + ":"
    if not token.startswith(prefix) or token[len(prefix) :] != str(CAP):
        raise ValueError(
            f"{SAMPLING_ENV} must be {UNCAPPED} or {RULE}:{CAP}, got {raw!r}"
        )
    return RULE, CAP


def _identity(row: Mapping[str, Any]) -> str:
    return normalized_text_sha256(str(row.get("text") or ""))


def _kind(row: Mapping[str, Any]) -> str:
    if row.get("lineage") != NONE:
        return "other"
    evidence = row.get("class")
    if evidence == OBSERVED:
        return "observed_none"
    if evidence == INFERRED:
        return "inferred_none"
    raise ValueError("none classify row is neither OBSERVED nor INFERRED")


def _selection_sha(hashes: Sequence[str]) -> str:
    return hashlib.sha256(canonical_json(list(hashes)).encode("utf-8")).hexdigest()


def apply_inferred_none_cap(
    rows: Sequence[Mapping[str, Any]],
    *,
    epoch_index: int,
    cap: int,
) -> tuple[list[Mapping[str, Any]], dict[str, Any]]:
    """Keep every non-none row and every OBSERVED none row.

    INFERRED none rows are chosen by sorting ``(identity, original index)``
    and taking a circular window. Kept rows stay in their original order.
    ``epoch_index`` is zero-based: epoch 1 starts at offset 0.
    """
    if isinstance(cap, bool) or not isinstance(cap, int) or cap < 1:
        raise ValueError("inferred-none cap must be a positive integer")
    if isinstance(epoch_index, bool) or not isinstance(epoch_index, int) or epoch_index < 0:
        raise ValueError("epoch_index must be a non-negative integer")
    indexed = list(enumerate(rows))
    inferred = [(index, row, _identity(row)) for index, row in indexed if _kind(row) == "inferred_none"]
    observed = sum(1 for _, row in indexed if _kind(row) == "observed_none")
    if len(inferred) < cap:
        raise ValueError("inferred none population is smaller than the cap")
    ordered = sorted(inferred, key=lambda item: (item[2], item[0]))
    start = (epoch_index * cap) % len(ordered)
    chosen = [ordered[(start + offset) % len(ordered)] for offset in range(cap)]
    chosen_indexes = {item[0] for item in chosen}
    if len(chosen_indexes) != cap:
        raise ValueError("inferred none selection collided")
    kept = [
        row
        for index, row in indexed
        if _kind(row) != "inferred_none" or index in chosen_indexes
    ]
    hashes = [item[2] for item in chosen]
    return kept, {
        "classify_rows": len(kept),
        "epoch_index": epoch_index,
        "inferred_none_population": len(inferred),
        "inferred_none_selected": cap,
        "observed_none": observed,
        "rule": RULE,
        "selected_identity_sha256": hashes,
        "selection_sha256": _selection_sha(hashes),
    }


def epoch_classify_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    epoch_index: int,
    policy: str | None = None,
) -> tuple[list[Mapping[str, Any]], dict[str, Any]]:
    """One epoch of classify rows. Unset policy keeps the full list."""
    if policy is None:
        policy = os.environ.get(SAMPLING_ENV)
    rule, cap = parse_sampling_policy(policy)
    indexed = list(enumerate(rows))
    inferred = [(index, row, _identity(row)) for index, row in indexed if _kind(row) == "inferred_none"]
    observed = sum(1 for _, row in indexed if _kind(row) == "observed_none")
    if rule == UNCAPPED:
        hashes = [item[2] for item in inferred]
        return list(rows), {
            "classify_rows": len(rows),
            "epoch_index": epoch_index,
            "inferred_none_population": len(inferred),
            "inferred_none_selected": len(inferred),
            "observed_none": observed,
            "rule": UNCAPPED,
            "selected_identity_sha256": hashes,
            "selection_sha256": _selection_sha(hashes),
        }
    if observed != EXPECTED_OBSERVED_NONE or len(inferred) != EXPECTED_INFERRED_NONE:
        raise ValueError(
            "classify none population does not match the preregistered "
            f"{EXPECTED_OBSERVED_NONE}/{EXPECTED_INFERRED_NONE} pin"
        )
    return apply_inferred_none_cap(rows, epoch_index=epoch_index, cap=cap or CAP)
