"""Civilian unbind residual dump for Spark operators.

Default OFF. When ``HYPERLEX_UNBIND_RESIDUAL_DUMP`` is set to a path, the
train loop writes a JSONL of val rows that miss ``unbind_exact``, plus a
theme summary on the receipt. Does not invent gold. Does not flip
``name_gate``. Ladder metric stays ``unbind_exact``.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .unbind_metrics import slot_counts, token_multiset_counts
from .unbind_recipe import hard_negatives_for

UNBIND_RESIDUAL_DUMP_ENV = "HYPERLEX_UNBIND_RESIDUAL_DUMP"

THEME_EXACT = "exact_hit"
THEME_POS_HEAD = "positional_head_filler_miss"
THEME_TYPE_TOKEN = "type_slot_token_miss"
THEME_MORPH = "morph_bleed"
THEME_ORDER = "token_hit_order_miss"
THEME_LENGTH = "length_mismatch"
THEME_FULL = "full_miss"
THEME_PARTIAL = "partial_slot_miss"


def resolve_unbind_residual_dump_path(raw: str | None = None) -> str:
    """Empty default. Non-empty path is the dump target (parent may be created)."""
    if raw is None:
        raw = os.environ.get(UNBIND_RESIDUAL_DUMP_ENV)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return ""
    return str(raw).strip()


def _scheme(row: Mapping[str, Any] | None) -> str:
    if not row:
        return ""
    return str(row.get("role_scheme") or "").strip()


def _roles(row: Mapping[str, Any] | None, n: int) -> list[str]:
    if not row:
        return [""] * n
    roles = list(row.get("roles") or [])
    if len(roles) >= n:
        return [str(r) for r in roles[:n]]
    return [str(r) for r in roles] + [""] * (n - len(roles))


def classify_residual_themes(
    gold: Sequence[str],
    pred: Sequence[str],
    *,
    role_scheme: str = "",
    roles: Sequence[str] | None = None,
) -> list[str]:
    """Theme tags for one gold/pred filler list. Exact hit → [exact_hit]."""
    g = [str(x) for x in gold]
    p = [str(x) for x in pred]
    if not g:
        return []
    if g == p:
        return [THEME_EXACT]

    themes: list[str] = []
    if len(g) != len(p):
        themes.append(THEME_LENGTH)

    tok_tp, tok_p, tok_g = token_multiset_counts(g, p)
    slot_tp, _, _ = slot_counts(g, p)
    if tok_tp == tok_g == tok_p and tok_g > 0 and slot_tp < len(g):
        themes.append(THEME_ORDER)

    scheme = (role_scheme or "").strip()
    role_list = list(roles or [])
    known = list({*g, *p})
    n = min(len(g), len(p))
    morph_hit = False
    for i in range(n):
        if g[i] == p[i]:
            continue
        sibs = set(hard_negatives_for(g[i], known))
        if p[i] in sibs:
            morph_hit = True
        if i == 0 and scheme == "positional":
            themes.append(THEME_POS_HEAD)
        role_i = str(role_list[i]) if i < len(role_list) else ""
        if scheme == "type_slot" and (
            role_i.upper().startswith("TOKEN") or role_i.upper().startswith("SLOT")
        ):
            if THEME_TYPE_TOKEN not in themes:
                themes.append(THEME_TYPE_TOKEN)
    if morph_hit:
        themes.append(THEME_MORPH)

    if slot_tp == 0 and THEME_ORDER not in themes:
        themes.append(THEME_FULL)
    elif THEME_POS_HEAD not in themes and THEME_ORDER not in themes:
        themes.append(THEME_PARTIAL)

    # De-dupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for t in themes:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def residual_row_record(
    *,
    text: str,
    gold: Sequence[str],
    pred: Sequence[str],
    row: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """One JSONL record for a miss. Exact hits return None."""
    g = [str(x) for x in gold]
    p = [str(x) for x in pred]
    if not g or g == p:
        return None
    scheme = _scheme(row)
    roles = _roles(row, len(g))
    themes = classify_residual_themes(g, p, role_scheme=scheme, roles=roles)
    slot_tp, slot_p, slot_g = slot_counts(g, p)
    tok_tp, tok_p, tok_g = token_multiset_counts(g, p)
    return {
        "text": text,
        "gold": g,
        "pred": p,
        "role_scheme": scheme or None,
        "roles": roles,
        "lineage": (str(row.get("lineage")) if row and row.get("lineage") else None),
        "class": (str(row.get("class")) if row and row.get("class") else None),
        "themes": themes,
        "slot_tp": slot_tp,
        "slot_n_gold": slot_g,
        "token_tp": tok_tp,
        "token_n_gold": tok_g,
        "token_n_pred": tok_p,
    }


def summarize_residual_records(
    records: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Theme + scheme counters for the receipt. Not SoT gold."""
    theme_c: Counter[str] = Counter()
    scheme_c: Counter[str] = Counter()
    class_c: Counter[str] = Counter()
    n = 0
    for rec in records:
        n += 1
        for theme in rec.get("themes") or []:
            theme_c[str(theme)] += 1
        scheme = str(rec.get("role_scheme") or "unknown")
        scheme_c[scheme] += 1
        cls = str(rec.get("class") or "unknown")
        class_c[cls] += 1
    return {
        "n_residual": n,
        "themes": dict(theme_c.most_common()),
        "by_scheme": dict(scheme_c.most_common()),
        "by_class": dict(class_c.most_common()),
    }


def write_residual_dump(
    path: str | Path,
    records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Write JSONL + sibling ``.summary.json``. Returns receipt fields."""
    target = Path(path)
    if not str(target):
        return {
            "unbind_residual_dump": "",
            "n_unbind_residual": 0,
            "unbind_residual_themes": {},
        }
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
    summary = summarize_residual_records(records)
    summary_path = target.with_suffix(target.suffix + ".summary.json")
    if target.suffix == ".jsonl":
        summary_path = target.with_name(target.stem + ".summary.json")
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "unbind_residual_dump": target.name,
        "n_unbind_residual": summary["n_residual"],
        "unbind_residual_themes": summary["themes"],
        "unbind_residual_by_scheme": summary["by_scheme"],
        "unbind_residual_by_class": summary["by_class"],
        "unbind_residual_summary": summary_path.name,
    }
