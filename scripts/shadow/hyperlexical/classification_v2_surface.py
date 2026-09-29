"""Structural applicability surfaces for Classification v2.

Text form is ATOM, PROSE, or AMBIGUOUS. The family label is not an input.
Applicability loss gives each populated label/form cell equal aggregate
authority. The family-head class-weight formula is not applied here.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

SURFACE_ATOM = "ATOM"
SURFACE_PROSE = "PROSE"
SURFACE_AMBIGUOUS = "AMBIGUOUS"
SURFACES = (SURFACE_ATOM, SURFACE_PROSE, SURFACE_AMBIGUOUS)
SURFACE_RULE_ID = "hyperlex.classification.v2.surface.v1"
CELL_LABELS = ("FAMILY_PRESENT", "NONE")
CELL_FORMS = (SURFACE_ATOM, SURFACE_PROSE)
SURFACE_SHORTCUT_ABS_CORRELATION_MAX = 0.30
LENGTH_BUCKETS = ((1, 2), (3, 6), (7, 12), (13, 10**9))

_PROVENANCE_KEYS = {
    ("FAMILY_PRESENT", "OBSERVED"): "observed_non_none_applicability",
    ("FAMILY_PRESENT", "INFERRED"): "inferred_non_none_applicability",
    ("NONE", "OBSERVED"): "observed_none_applicability",
    ("NONE", "INFERRED"): "inferred_none_applicability",
}


def surface_tokens(text: str) -> list[str]:
    """Whitespace tokens. URL and image-markup tokens are not words."""
    tokens = []
    for part in str(text or "").split():
        if part.startswith(("http://", "https://", "![](")):
            continue
        tokens.append(part)
    return tokens


def _sentence_terminator(token: str) -> bool:
    if not token or token[-1] not in ".?!":
        return False
    stem = token[:-1]
    if not any(character.isalpha() for character in stem):
        return False
    if stem.isupper() and len(stem) <= 3:
        return False
    return True


def surface_form(text: str) -> str:
    """Freeze structural form. Callers must not pass a family label."""
    raw = str(text or "")
    tokens = surface_tokens(raw)
    count = len(tokens)
    terminator = any(_sentence_terminator(token) for token in tokens)
    clause = ("," in raw) or (";" in raw)
    if count >= 6 or terminator or clause:
        return SURFACE_PROSE
    if 1 <= count <= 4 and not terminator and not clause:
        return SURFACE_ATOM
    return SURFACE_AMBIGUOUS


def applicability_label(lineage: str) -> str | None:
    if lineage == "none":
        return "NONE"
    if lineage:
        return "FAMILY_PRESENT"
    return None


def cell_name(label: str, form: str) -> str:
    return f"{label}/{form}"


def word_count(text: str) -> int:
    return len(surface_tokens(text))


def _provenance_weight(label: str, klass: str, provenance: Mapping[str, float]) -> float:
    key = _PROVENANCE_KEYS.get((label, klass))
    if key is None or key not in provenance:
        raise ValueError(f"surface provenance missing for {label}/{klass}")
    return float(provenance[key])


def surface_cell_weights(
    rows: Sequence[Mapping[str, Any]],
    provenance: Mapping[str, float],
) -> dict[str, float]:
    """Inverse effective support, then mean 1 across populated training cells."""
    support: dict[str, float] = {}
    for row in rows:
        if row.get("split") not in (None, "train"):
            continue
        if "text" not in row:
            continue
        label = applicability_label(str(row.get("lineage") or ""))
        if label is None:
            continue
        form = surface_form(str(row.get("text") or ""))
        if form == SURFACE_AMBIGUOUS:
            continue
        klass = str(row.get("class") or "")
        name = cell_name(label, form)
        support[name] = support.get(name, 0.0) + _provenance_weight(label, klass, provenance)
    if not support:
        return {}
    raw = {name: 1.0 / value for name, value in support.items() if value > 0.0}
    mean = sum(raw.values()) / len(raw)
    return {name: value / mean for name, value in raw.items()}


def surface_census(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Count train and validation cells. Ambiguous rows stay outside the cells."""
    counts: dict[str, dict[str, int]] = {"train": {}, "val": {}}
    ambiguous = {"train": 0, "val": 0}
    for row in rows:
        split = str(row.get("split") or "")
        if split not in counts or row.get("task") not in (None, "classify"):
            continue
        if "text" not in row:
            continue
        label = applicability_label(str(row.get("lineage") or ""))
        if label is None:
            continue
        form = surface_form(str(row.get("text") or ""))
        if form == SURFACE_AMBIGUOUS:
            ambiguous[split] += 1
            continue
        name = cell_name(label, form)
        counts[split][name] = counts[split].get(name, 0) + 1
    required = [cell_name(label, form) for label in CELL_LABELS for form in CELL_FORMS]
    missing = {
        split: [name for name in required if counts[split].get(name, 0) <= 0]
        for split in ("train", "val")
    }
    return {
        "ambiguous": ambiguous,
        "cells": counts,
        "missing": missing,
        "pass": not missing["train"] and not missing["val"],
        "rule": SURFACE_RULE_ID,
        "shortcut_abs_correlation_max": SURFACE_SHORTCUT_ABS_CORRELATION_MAX,
    }


def representation_leak(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    """A source identity may not supervise both train and validation."""
    splits: dict[str, set[str]] = {}
    for row in rows:
        provenance = row.get("provenance")
        if not isinstance(provenance, dict):
            continue
        source = str(provenance.get("source_text_sha256") or "")
        if not source:
            continue
        splits.setdefault(source, set()).add(str(row.get("split") or ""))
    return sorted(source for source, found in splits.items() if found >= {"train", "val"})


def pearson(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    count = len(xs)
    if count < 2 or count != len(ys):
        return None
    mean_x = sum(xs) / count
    mean_y = sum(ys) / count
    diff_x = [value - mean_x for value in xs]
    diff_y = [value - mean_y for value in ys]
    denom_x = math.sqrt(sum(value * value for value in diff_x))
    denom_y = math.sqrt(sum(value * value for value in diff_y))
    if denom_x == 0.0 or denom_y == 0.0:
        return None
    return sum(left * right for left, right in zip(diff_x, diff_y)) / (denom_x * denom_y)


def calibrated_present_probability(logits: Sequence[float], temperature: float) -> float:
    if len(logits) != 2 or temperature <= 0.0:
        raise ValueError("applicability probability is undefined")
    scaled = [value / temperature for value in logits]
    peak = max(scaled)
    weights = [math.exp(value - peak) for value in scaled]
    total = sum(weights)
    return weights[1] / total


def _f1(gold: int, predicted: int, hit: int) -> float | None:
    if gold <= 0:
        return None
    precision = hit / predicted if predicted else 0.0
    recall = hit / gold
    if precision + recall == 0.0:
        return 0.0
    return 2.0 * precision * recall / (precision + recall)


def applicability_surface_report(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Validation diagnostic. ``probability`` is calibrated P(FAMILY_PRESENT)."""
    lengths: list[float] = []
    probabilities: list[float] = []
    by_form_gold: dict[str, list[str]] = {SURFACE_ATOM: [], SURFACE_PROSE: []}
    by_form_pred: dict[str, list[str]] = {SURFACE_ATOM: [], SURFACE_PROSE: []}
    probability_sums: dict[str, list[float]] = {}
    support: dict[str, int] = {}
    family_by_form: dict[str, list[tuple[str, str]]] = {SURFACE_ATOM: [], SURFACE_PROSE: []}
    buckets = []
    for low, high in LENGTH_BUCKETS:
        buckets.append(
            {
                "bucket": f"{low}-{high if high < 10**9 else 'inf'}",
                "low": low,
                "high": high,
                "gold_none": 0,
                "false_family_present": 0,
                "gold_present": 0,
                "false_none": 0,
            }
        )
    for record in records:
        text = str(record.get("text") or "")
        lineage = str(record.get("lineage") or "")
        label = applicability_label(lineage)
        if label is None:
            continue
        probability = float(record["probability"])
        predicted = str(record.get("prediction") or "")
        if predicted not in CELL_LABELS:
            predicted = "FAMILY_PRESENT" if probability >= 0.5 else "NONE"
        lengths.append(float(word_count(text)))
        probabilities.append(probability)
        form = surface_form(text)
        count = word_count(text)
        for bucket in buckets:
            if bucket["low"] <= count <= bucket["high"]:
                if label == "NONE":
                    bucket["gold_none"] += 1
                    if predicted == "FAMILY_PRESENT":
                        bucket["false_family_present"] += 1
                else:
                    bucket["gold_present"] += 1
                    if predicted == "NONE":
                        bucket["false_none"] += 1
                break
        if form == SURFACE_AMBIGUOUS:
            continue
        name = cell_name(label, form)
        support[name] = support.get(name, 0) + 1
        probability_sums.setdefault(name, []).append(probability)
        by_form_gold[form].append(label)
        by_form_pred[form].append(predicted)
        family_prediction = record.get("family_prediction")
        if lineage != "none" and family_prediction:
            family_by_form[form].append((lineage, str(family_prediction)))
    correlation = pearson(lengths, probabilities)
    form_f1: dict[str, dict[str, float | None]] = {}
    for form in CELL_FORMS:
        form_f1[form] = {}
        for label in CELL_LABELS:
            gold_n = by_form_gold[form].count(label)
            pred_n = by_form_pred[form].count(label)
            hit = sum(
                1
                for gold, pred in zip(by_form_gold[form], by_form_pred[form])
                if gold == label and pred == label
            )
            form_f1[form][label] = _f1(gold_n, pred_n, hit)
    cells = {}
    for label in CELL_LABELS:
        for form in CELL_FORMS:
            name = cell_name(label, form)
            values = probability_sums.get(name) or []
            cells[name] = {
                "applicability_f1": form_f1[form][label],
                "mean_p_family_present": None if not values else sum(values) / len(values),
                "support": support.get(name, 0),
            }
    length_buckets = []
    for bucket in buckets:
        none_n = bucket["gold_none"]
        present_n = bucket["gold_present"]
        length_buckets.append(
            {
                "bucket": bucket["bucket"],
                "false_family_present_rate": None
                if none_n == 0
                else bucket["false_family_present"] / none_n,
                "false_none_rate": None if present_n == 0 else bucket["false_none"] / present_n,
                "gold_none": none_n,
                "gold_present": present_n,
            }
        )
    passed = correlation is not None and abs(correlation) <= SURFACE_SHORTCUT_ABS_CORRELATION_MAX
    return {
        "abs_correlation_max": SURFACE_SHORTCUT_ABS_CORRELATION_MAX,
        "applicability_by_cell": cells,
        "corr_word_count_p_family_present": correlation,
        "family_macro_f1_by_surface": {
            form: _macro_family(pairs) for form, pairs in family_by_form.items()
        },
        "length_buckets": length_buckets,
        "pass": passed,
        "rule": SURFACE_RULE_ID,
        "surface": "validation",
    }




def _macro_family(pairs: Sequence[tuple[str, str]]) -> float | None:
    golds: dict[str, int] = {}
    preds: dict[str, int] = {}
    hits: dict[str, int] = {}
    for gold, predicted in pairs:
        golds[gold] = golds.get(gold, 0) + 1
        preds[predicted] = preds.get(predicted, 0) + 1
        if gold == predicted:
            hits[gold] = hits.get(gold, 0) + 1
    scored = []
    for name, count in golds.items():
        value = _f1(count, preds.get(name, 0), hits.get(name, 0))
        if value is not None:
            scored.append(value)
    if not scored:
        return None
    return sum(scored) / len(scored)
