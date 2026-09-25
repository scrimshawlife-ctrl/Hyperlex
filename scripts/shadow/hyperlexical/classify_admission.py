"""Opt-in classify admission filter (HLX_CLASSIFY_ADMISSION=1, default off).

Drops classify train/val rows whose label cannot be trusted:
  * conflict: the normalized text carries more than one lineage across
    non-test classify rows (after the dump brainrot fold is undone);
  * moltbook_source_constant: moltbook / moltbook-curated-seed lineage is
    hard-coded ai-native (scripts/moltbook_to_hyperlexical.py:55);
  * demoted: gold_demote_reason set, or fallback fillers (general, kdr).
Counts go into the train receipt under "classify_admission".
"""

from __future__ import annotations

import os
from collections import Counter
from typing import Any, Sequence

from .heldout_census import normalize_group_text
from .selection_surface import drop_test_rows

MOLTBOOK_SOURCES = frozenset({"moltbook", "moltbook-curated-seed"})
FALLBACK_FILLERS = frozenset({"general", "kdr"})


def _source(row: dict[str, Any]) -> str:
    prov = row.get("provenance")
    return str(prov.get("source") or "") if isinstance(prov, dict) else ""


def _reason(row: dict[str, Any], labels: dict[str, set[str]]) -> str | None:
    if len(labels.get(normalize_group_text(row.get("text") or ""), ())) > 1:
        return "conflict"
    if _source(row) in MOLTBOOK_SOURCES:
        return "moltbook_source_constant"
    if row.get("gold_demote_reason") or any(
        str(f).lower() in FALLBACK_FILLERS for f in (row.get("fillers") or [])
    ):
        return "demoted"
    return None


def admit_classify_rows(
    all_rows: Sequence[dict[str, Any]],
    classify_tr: list[dict[str, Any]],
    classify_va: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    kept_rows, _ = drop_test_rows(all_rows)
    labels: dict[str, set[str]] = {}
    for r in kept_rows:
        if r.get("task") == "classify":
            key = normalize_group_text(r.get("text") or "")
            if key:
                labels.setdefault(key, set()).add(str(r.get("lineage")))
    receipt: dict[str, Any] = {"enabled": True, "conflict_texts": sum(1 for v in labels.values() if len(v) > 1)}
    out = []
    for name, rows in (("train", classify_tr), ("val", classify_va)):
        dropped: Counter[str] = Counter()
        kept = []
        for r in rows:
            why = _reason(r, labels)
            if why:
                dropped[why] += 1
            else:
                kept.append(r)
        receipt[name] = {"in": len(rows), "kept": len(kept), "dropped": dict(sorted(dropped.items()))}
        out.append(kept)
    return out[0], out[1], receipt


def apply_classify_admission(
    all_rows: Sequence[dict[str, Any]],
    classify_tr: list[dict[str, Any]],
    classify_va: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any] | None]:
    """Filter only when ``HLX_CLASSIFY_ADMISSION`` is ``1``.

    Default off returns the same train and val lists and a null receipt so
    training rows stay byte-identical.
    """
    if os.environ.get("HLX_CLASSIFY_ADMISSION") != "1":
        return classify_tr, classify_va, None
    return admit_classify_rows(all_rows, classify_tr, classify_va)
