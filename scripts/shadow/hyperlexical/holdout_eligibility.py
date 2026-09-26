"""Holdout eligibility against a pinned training export.

Construction and the runtime filter both call
``holdout_guard.normalized_text_sha256``. This module does not draw a
manifest, score rows, or train.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from .holdout_guard import _read_manifest, normalized_text_sha256, operational_status
from .selection_surface import row_id

ELIGIBLE = "eligible"
SPLIT_TEST = "split_test"
TRAIN_ROW_ID = "train_row_id"
TRAIN_TEXT_HASH = "train_text_hash"
SPENT_OR_ABANDONED = "spent_or_abandoned"


def text_hash(row: Mapping[str, Any]) -> str:
    return normalized_text_sha256(str(row.get("text") or ""))


def identity_index(rows: Sequence[Mapping[str, Any]]) -> tuple[set[str], set[str]]:
    """Row ids and canonical text hashes present in ``rows``."""
    ids: set[str] = set()
    hashes: set[str] = set()
    for row in rows:
        ids.add(row_id(row))
        hashes.add(text_hash(row))
    return ids, hashes


def manifest_identity(path: str | Path) -> tuple[set[str], set[str], str]:
    """Ids and hashes stored on a manifest, plus its operational status."""
    record, ids, hashes = _read_manifest(str(path))
    return ids, hashes, operational_status(record)


def exclusion_reason(
    row: Mapping[str, Any],
    *,
    train_ids: set[str],
    train_hashes: set[str],
    other_ids: set[str],
    other_hashes: set[str],
) -> str:
    """Waterfall reason. First match wins. ``eligible`` means none matched."""
    if str(row.get("split") or "") == "test":
        return SPLIT_TEST
    ident = row_id(row)
    digest = text_hash(row)
    if ident in train_ids:
        return TRAIN_ROW_ID
    if digest in train_hashes:
        return TRAIN_TEXT_HASH
    if ident in other_ids or digest in other_hashes:
        return SPENT_OR_ABANDONED
    return ELIGIBLE


def multiplicity(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """How many rows share one canonical text hash. No hash values are kept."""
    counts = Counter(text_hash(row) for row in rows)
    histogram = Counter(counts.values())
    return {
        "rows": len(rows),
        "unique_hashes": len(counts),
        "max_rows_per_hash": max(histogram) if histogram else 0,
        "hashes_with_multiple_rows": sum(
            count for size, count in histogram.items() if size > 1
        ),
        "histogram_rows_per_hash": {str(size): histogram[size] for size in sorted(histogram)},
    }


def census(
    source_rows: Sequence[Mapping[str, Any]],
    train_rows: Sequence[Mapping[str, Any]],
    *,
    extra_rows: Sequence[Mapping[str, Any]] = (),
    extra_manifests: Sequence[str | Path] = (),
) -> dict[str, Any]:
    """Eligible universe after row-id and normalized-text exclusion.

    ``extra_rows`` and ``extra_manifests`` are spent or abandoned exclusions.
    ``unbind_clean`` uses ``soft_ceiling.clean_surface`` and is not the
    canonical text hash.
    """
    from .soft_ceiling import clean_surface

    train_ids, train_hashes = identity_index(train_rows)
    other_ids, other_hashes = identity_index(extra_rows)
    manifest_status: list[dict[str, str]] = []
    for path in extra_manifests:
        ids, hashes, status = manifest_identity(path)
        other_ids |= ids
        other_hashes |= hashes
        manifest_status.append({"path": str(path), "operational_status": status})
    reasons: Counter[str] = Counter()
    eligible: list[Mapping[str, Any]] = []
    source_hashes: set[str] = set()
    for row in source_rows:
        source_hashes.add(text_hash(row))
        reason = exclusion_reason(
            row,
            train_ids=train_ids,
            train_hashes=train_hashes,
            other_ids=other_ids,
            other_hashes=other_hashes,
        )
        reasons[reason] += 1
        if reason == ELIGIBLE:
            eligible.append(row)
    eligible_hashes = {text_hash(row) for row in eligible}
    classify = [row for row in eligible if row.get("task") == "classify"]
    unbind = [row for row in eligible if row.get("task") == "unbind"]
    observed = [row for row in classify if str(row.get("class")) == "OBSERVED"]
    non_none = [row for row in classify if str(row.get("lineage")) not in ("", "none")]
    train_for_clean = [row for row in train_rows if row.get("split") == "train"]
    clean, _account = clean_surface(unbind, train_rows=train_for_clean)
    return {
        "source_rows": len(source_rows),
        "source_unique_text_hashes": len(source_hashes),
        "excluded_by_split_test": reasons[SPLIT_TEST],
        "excluded_by_training_row_id": reasons[TRAIN_ROW_ID],
        "excluded_by_training_normalized_text_hash": reasons[TRAIN_TEXT_HASH],
        "excluded_by_spent_or_abandoned": reasons[SPENT_OR_ABANDONED],
        "eligible_rows": len(eligible),
        "eligible_unique_text_hashes": len(eligible_hashes),
        "classify_eligible": len(classify),
        "classify_observed_eligible": len(observed),
        "classify_non_none_eligible": len(non_none),
        "unbind_eligible": len(unbind),
        "unbind_clean_eligible": len(clean),
        "unbind_clean_definition": "soft_ceiling.clean_surface",
        "source_multiplicity": multiplicity(source_rows),
        "train_multiplicity": multiplicity(train_rows),
        "extra_manifests": manifest_status,
        "waterfall_sums_to_source": (
            reasons[SPLIT_TEST]
            + reasons[TRAIN_ROW_ID]
            + reasons[TRAIN_TEXT_HASH]
            + reasons[SPENT_OR_ABANDONED]
            + len(eligible)
            == len(source_rows)
        ),
    }
