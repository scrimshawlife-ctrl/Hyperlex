"""Stage A evidence-gate training contracts and metrics.

Trains a 3-way evidence head on HYPERLEX_V3_EVIDENCE_SURFACE_V1. Does not
create a v3 reserve, does not score the spent v2 reserve, and does not move BEST.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from typing import Any, Mapping, Sequence

from .classification_v3_evidence_gate import (
    EVIDENCE_LABELS,
    FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX,
    FAMILY_EMISSION_PRECISION_MIN_AFTER_GATE,
    RULE,
    decide_evidence,
)
from .classification_v3_evidence_surface import SURFACE_RULE

STAGE_A_RULE = "HYPERLEX_CLASSIFICATION_V3_STAGE_A_TRAIN_V1"
LABEL_INDEX = {label: index for index, label in enumerate(EVIDENCE_LABELS)}
INDEX_LABEL = {index: label for label, index in LABEL_INDEX.items()}

# Frozen once. Not a search loop.
TRAIN_HYPERPARAMS = {
    "batch_size": 16,
    "epochs": 4,
    "last_trainable": 2,
    "learning_rate": 2e-5,
    "max_len": 64,
    "seed": 20260930,
    "stratified_label_batches": True,
    "weight_decay": 0.01,
}

# Single validation calibration grid (preregistered, not reserve-derived).
THRESHOLD_GRID = {
    "none_candidates": [round(x * 0.05, 2) for x in range(1, 18)],  # 0.05..0.85
    "present_gap_min": 0.05,
    "present_max": 0.95,
    "present_step": 0.05,
}


def canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def label_index(label: str) -> int:
    if label not in LABEL_INDEX:
        raise ValueError(f"unknown_evidence_label:{label}")
    return LABEL_INDEX[label]


def evidence_score_from_probabilities(probabilities: Mapping[str, float]) -> float:
    """Canonical scalar: P(EVIDENCE_PRESENT)."""
    return float(probabilities["EVIDENCE_PRESENT"])


def softmax_logits(logits: Sequence[float]) -> dict[str, float]:
    peak = max(float(value) for value in logits)
    exps = [math.exp(float(value) - peak) for value in logits]
    total = sum(exps) or 1.0
    probs = [value / total for value in exps]
    return {INDEX_LABEL[index]: probs[index] for index in range(len(EVIDENCE_LABELS))}


def prf(golds: Sequence[str], preds: Sequence[str], label: str) -> dict[str, float]:
    tp = fp = fn = 0
    for gold, pred in zip(golds, preds):
        if pred == label and gold == label:
            tp += 1
        elif pred == label and gold != label:
            fp += 1
        elif pred != label and gold == label:
            fn += 1
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (
        0.0
        if precision + recall == 0.0
        else 2.0 * precision * recall / (precision + recall)
    )
    return {
        "f1": f1,
        "fn": fn,
        "fp": fp,
        "precision": precision,
        "recall": recall,
        "support": tp + fn,
        "tp": tp,
    }


def false_evidence_entry_rate_on_none(
    golds: Sequence[str], decisions: Sequence[str]
) -> float:
    none_idx = [i for i, gold in enumerate(golds) if gold == "NO_EVIDENCE"]
    if not none_idx:
        return 0.0
    false_entries = sum(1 for i in none_idx if decisions[i] == "EVIDENCE_PRESENT")
    return false_entries / len(none_idx)


def evaluate_decisions(
    golds: Sequence[str],
    decisions: Sequence[str],
    *,
    subtypes: Sequence[str] | None = None,
) -> dict[str, Any]:
    by_label = {label: prf(golds, decisions, label) for label in EVIDENCE_LABELS}
    uncertain_rate = sum(1 for decision in decisions if decision == "UNCERTAIN") / max(
        1, len(decisions)
    )
    false_entry = false_evidence_entry_rate_on_none(golds, decisions)
    subtype_false_entry = {}
    if subtypes is not None:
        buckets: dict[str, list[int]] = {}
        for index, subtype in enumerate(subtypes):
            if golds[index] != "NO_EVIDENCE":
                continue
            buckets.setdefault(str(subtype), []).append(index)
        for subtype, indices in sorted(buckets.items()):
            if not indices:
                continue
            hits = sum(1 for i in indices if decisions[i] == "EVIDENCE_PRESENT")
            subtype_false_entry[subtype] = hits / len(indices)
    return {
        "by_label": by_label,
        "confusion": dict(Counter(f"{gold}->{pred}" for gold, pred in zip(golds, decisions))),
        "false_evidence_entry_rate_on_none": false_entry,
        "false_evidence_entry_by_none_subtype": subtype_false_entry,
        "n": len(golds),
        "primary_gate_max": FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX,
        "primary_gate_pass": false_entry <= FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX,
        "uncertain_rate": uncertain_rate,
    }


def calibrate_thresholds(
    golds: Sequence[str],
    scores: Sequence[float],
    *,
    subtypes: Sequence[str] | None = None,
) -> dict[str, Any]:
    """One-shot validation sweep. Prefer gate-pass then PRESENT F1."""
    candidates = []
    none_vals = THRESHOLD_GRID["none_candidates"]
    gap = float(THRESHOLD_GRID["present_gap_min"])
    step = float(THRESHOLD_GRID["present_step"])
    present_max = float(THRESHOLD_GRID["present_max"])
    for none_threshold in none_vals:
        present = none_threshold + gap
        while present <= present_max + 1e-12:
            decisions = [
                decide_evidence(
                    float(score),
                    none_threshold=none_threshold,
                    present_threshold=present,
                )
                for score in scores
            ]
            metrics = evaluate_decisions(golds, decisions, subtypes=subtypes)
            present_f1 = metrics["by_label"]["EVIDENCE_PRESENT"]["f1"]
            candidates.append(
                {
                    "false_evidence_entry_rate_on_none": metrics[
                        "false_evidence_entry_rate_on_none"
                    ],
                    "metrics": metrics,
                    "none_threshold": none_threshold,
                    "present_f1": present_f1,
                    "present_threshold": round(present, 2),
                    "primary_gate_pass": metrics["primary_gate_pass"],
                    "uncertain_rate": metrics["uncertain_rate"],
                }
            )
            present = round(present + step, 2)
    if not candidates:
        raise RuntimeError("threshold grid empty")
    passing = [row for row in candidates if row["primary_gate_pass"]]
    pool = passing or candidates
    pool.sort(
        key=lambda row: (
            0 if row["primary_gate_pass"] else 1,
            -row["present_f1"],
            row["false_evidence_entry_rate_on_none"],
            row["none_threshold"],
            row["present_threshold"],
        )
    )
    chosen = pool[0]
    return {
        "chosen": {
            "false_evidence_entry_rate_on_none": chosen[
                "false_evidence_entry_rate_on_none"
            ],
            "none_threshold": chosen["none_threshold"],
            "present_f1": chosen["present_f1"],
            "present_threshold": chosen["present_threshold"],
            "primary_gate_pass": chosen["primary_gate_pass"],
            "uncertain_rate": chosen["uncertain_rate"],
        },
        "feasible": bool(passing),
        "grid": THRESHOLD_GRID,
        "metrics": chosen["metrics"],
        "n_candidates": len(candidates),
        "n_passing": len(passing),
        "primary_gate_max": FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX,
        "secondary_family_emission_precision_min": FAMILY_EMISSION_PRECISION_MIN_AFTER_GATE,
        "selection_rule": "primary_gate_pass_then_max_present_f1_then_min_false_entry",
    }


def stratified_label_indices(
    labels: Sequence[str],
    *,
    batch_size: int,
    seed: int,
) -> list[list[int]]:
    """One-epoch stratified batches: each index appears once, labels interleaved."""
    import random

    rng = random.Random(seed)
    buckets = {label: [] for label in EVIDENCE_LABELS}
    for index, label in enumerate(labels):
        buckets[label].append(index)
    for label in EVIDENCE_LABELS:
        rng.shuffle(buckets[label])
    per_label = max(1, batch_size // len(EVIDENCE_LABELS))
    pointers = {label: 0 for label in EVIDENCE_LABELS}
    batches: list[list[int]] = []
    while any(pointers[label] < len(buckets[label]) for label in EVIDENCE_LABELS):
        batch: list[int] = []
        for label in EVIDENCE_LABELS:
            bucket = buckets[label]
            for _ in range(per_label):
                if pointers[label] >= len(bucket):
                    break
                batch.append(bucket[pointers[label]])
                pointers[label] += 1
        if not batch:
            break
        rng.shuffle(batch)
        batches.append(batch)
    return batches


def stage_a_contract() -> dict[str, Any]:
    return {
        "best": "UNCHANGED",
        "false_evidence_entry_rate_on_none_max": FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX,
        "hyperparams": dict(TRAIN_HYPERPARAMS),
        "labels": list(EVIDENCE_LABELS),
        "reserve": None,
        "rule": STAGE_A_RULE,
        "parent_rule": RULE,
        "surface_rule": SURFACE_RULE,
        "threshold_grid": dict(THRESHOLD_GRID),
        "train": True,
        "v3_reserve": None,
    }


def assemble_stage_a_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    receipt = {
        "BEST": "UNCHANGED",
        "best_sha256": payload["best_sha256"],
        "calibration": payload["calibration"],
        "checkpoint_sha256": payload["checkpoint_sha256"],
        "config_sha256": payload["config_sha256"],
        "dataset_sha256": payload["dataset_sha256"],
        "hyperparams": TRAIN_HYPERPARAMS,
        "next_action": payload["next_action"],
        "primary_gate_pass": payload["calibration"]["metrics"]["primary_gate_pass"],
        "rule": STAGE_A_RULE,
        "parent_rule": RULE,
        "schema": "hyperlex.classification.v3.stage_a_train.v1",
        "surface_rule": SURFACE_RULE,
        "train": True,
        "train_metrics": payload.get("train_metrics"),
        "validation_metrics": payload["calibration"]["metrics"],
        "v3_reserve": None,
        "weights_dir": payload["weights_dir"],
    }
    receipt["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in receipt.items() if k != "receipt_sha256"})
    )
    return receipt


def next_action_for_stage_a(*, primary_gate_pass: bool) -> str:
    if primary_gate_pass:
        return "WIRE_STAGE_B_RETRIEVAL_ON_EVIDENCE_PRESENT_THEN_VALIDATE"
    return "DIAGNOSE_STAGE_A_FALSE_ENTRY_BEFORE_ANY_RESERVE"
