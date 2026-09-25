"""Classify scores for checkpoint selection and the eval harness. No torch.

Macro-F1 is the unweighted mean of per-class F1 over gold labels other than
``none`` that have support (n > 0). ``none`` stays in the per-class table and
in the false-positive / false-negative rates. It does not enter the macro.
"""

from __future__ import annotations

import math
import os
from typing import Mapping, Sequence

NONE_LABEL = "none"
SELECT_METRIC_ENV = "HLX_SELECT_METRIC"
SELECT_METRIC_UNBIND = "unbind_exact"
SELECT_METRIC_CLASSIFY = "classify_macro_f1_nonnone"
_SELECT_METRICS = frozenset({SELECT_METRIC_UNBIND, SELECT_METRIC_CLASSIFY})


def resolve_select_metric(raw: str | None = None) -> str:
    """Checkpoint score name. Unset keeps ``unbind_exact`` (historical selection)."""
    if raw is None:
        raw = os.environ.get(SELECT_METRIC_ENV)
    value = "" if raw is None else str(raw).strip()
    if not value:
        return SELECT_METRIC_UNBIND
    if value not in _SELECT_METRICS:
        raise ValueError(
            f"{SELECT_METRIC_ENV} must be unset or {SELECT_METRIC_CLASSIFY!r}, got {value!r}"
        )
    return value


def checkpoint_score(metrics: Mapping[str, object], metric_name: str) -> float:
    """Scalar used to keep a best checkpoint. Missing classify F1 does not win."""
    if metric_name == SELECT_METRIC_CLASSIFY:
        raw = metrics.get("classify_macro_f1_nonnone")
        if raw is None:
            return float("-inf")
        return float(raw)  # type: ignore[arg-type]
    return float(metrics.get("unbind_exact") or 0.0)  # type: ignore[arg-type]


def accuracy(gold: Sequence[str], pred: Sequence[str]) -> float | None:
    _same_len(gold, pred)
    if not gold:
        return None
    hit = sum(int(g == p) for g, p in zip(gold, pred))
    return hit / len(gold)


def class_prf(gold: Sequence[str], pred: Sequence[str], label: str) -> dict[str, float | int]:
    """Precision, recall, F1, and gold support for one label."""
    _same_len(gold, pred)
    tp = fp = fn = n = 0
    for g, p in zip(gold, pred):
        if g == label:
            n += 1
        if p == label and g == label:
            tp += 1
        elif p == label:
            fp += 1
        elif g == label:
            fn += 1
    precision = 0.0 if tp + fp == 0 else tp / (tp + fp)
    recall = 0.0 if tp + fn == 0 else tp / (tp + fn)
    f1 = 0.0 if precision + recall == 0.0 else (2.0 * precision * recall) / (precision + recall)
    return {"precision": precision, "recall": recall, "f1": f1, "n": n}


def per_class_table(
    gold: Sequence[str],
    pred: Sequence[str],
    *,
    labels: Sequence[str] | None = None,
) -> dict[str, dict[str, float | int]]:
    """P/R/F1/n for every label in gold or pred, unless ``labels`` is passed."""
    _same_len(gold, pred)
    if labels is None:
        seen = sorted(set(gold) | set(pred))
    else:
        seen = list(labels)
    return {label: class_prf(gold, pred, label) for label in seen}


def macro_f1_nonnone(
    gold: Sequence[str],
    pred: Sequence[str],
    *,
    none_label: str = NONE_LABEL,
) -> float | None:
    """Mean F1 over non-none gold labels with n > 0. ``None`` when none qualify."""
    _same_len(gold, pred)
    labels = sorted({g for g in gold if g != none_label})
    if not labels:
        return None
    scores = [float(class_prf(gold, pred, label)["f1"]) for label in labels]
    return sum(scores) / len(scores)


def none_rates(
    gold: Sequence[str],
    pred: Sequence[str],
    *,
    none_label: str = NONE_LABEL,
) -> dict[str, float | int | None]:
    """Binary rates with positive class = ``none``.

    False-positive rate: predicted ``none`` among gold that is not ``none``.
    False-negative rate: predicted something else among gold ``none``.
    A zero denominator is ``None`` (not a zero rate).
    """
    _same_len(gold, pred)
    n_not_none = 0
    n_none = 0
    fp = 0
    fn = 0
    for g, p in zip(gold, pred):
        if g == none_label:
            n_none += 1
            if p != none_label:
                fn += 1
        else:
            n_not_none += 1
            if p == none_label:
                fp += 1
    return {
        "none_fpr": None if n_not_none == 0 else fp / n_not_none,
        "none_fnr": None if n_none == 0 else fn / n_none,
        "n_none": n_none,
        "n_not_none": n_not_none,
    }


def none_false_positive_rate(
    gold: Sequence[str],
    pred: Sequence[str],
    *,
    none_label: str = NONE_LABEL,
) -> float | None:
    rate = none_rates(gold, pred, none_label=none_label)["none_fpr"]
    return None if rate is None else float(rate)


def mcnemar_exact_p(n_model_only_correct: int, n_baseline_only_correct: int) -> float:
    """Two-sided exact McNemar p on discordant pairs.

    Under the null, the model-only count is Binomial(n, 1/2) with
    n = b + c. The p-value is min(1, 2 * P(X <= min(b, c))).
    No discordant pairs → 1.
    """
    b = int(n_model_only_correct)
    c = int(n_baseline_only_correct)
    if b < 0 or c < 0:
        raise ValueError("discordant counts must be >= 0")
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    log_choose = 0.0
    log_two_n = n * math.log(2.0)
    logs = []
    for i in range(0, k + 1):
        if i:
            log_choose += math.log(n - i + 1) - math.log(i)
        logs.append(log_choose - log_two_n)
    pivot = max(logs)
    acc = sum(math.exp(item - pivot) for item in logs)
    p = 2.0 * math.exp(pivot) * acc
    if p > 1.0:
        return 1.0
    if p < 0.0:
        return 0.0
    return p


def mcnemar_paired(
    gold: Sequence[str],
    model: Sequence[str],
    baseline: Sequence[str],
) -> dict[str, float | int]:
    """Exact two-sided McNemar of ``model`` vs ``baseline`` on the same gold."""
    if not (len(gold) == len(model) == len(baseline)):
        raise ValueError("gold, model, and baseline lengths differ")
    model_only = 0
    baseline_only = 0
    for g, m, b in zip(gold, model, baseline):
        m_ok = m == g
        b_ok = b == g
        if m_ok and not b_ok:
            model_only += 1
        elif b_ok and not m_ok:
            baseline_only += 1
    return {
        "n_discordant": model_only + baseline_only,
        "n_model_only_correct": model_only,
        "n_baseline_only_correct": baseline_only,
        "p_two_sided": mcnemar_exact_p(model_only, baseline_only),
    }


def _same_len(gold: Sequence[str], pred: Sequence[str]) -> None:
    if len(gold) != len(pred):
        raise ValueError(f"gold/pred length mismatch: {len(gold)} vs {len(pred)}")
