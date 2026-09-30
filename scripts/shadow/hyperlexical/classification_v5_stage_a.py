"""HYPERLEX_CLASSIFICATION_V5_STAGE_A_TRAIN_V1 — frozen recipe + metrics.

Authorizes one Stage-A train against a READY V5 surface. Does not train by
itself, does not score reserves, and does not move BEST.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

from .classification_v5_stage_a_mixed_remediate import SURFACE_RULE_V1R8
from .classification_v5_stage_a_negative_evidence_surface import (
    BEST_SHA,
    SURFACE_RULE as SURFACE_RULE_V1,
)
from .classification_v5_stage_a_surface_remediate import SURFACE_RULE_V1R7

STAGE_A_RULE = "HYPERLEX_CLASSIFICATION_V5_STAGE_A_TRAIN_V1"
LABEL_PROVENANCE_RULE = "HYPERLEX_V5_STAGE_A_LABEL_PROVENANCE_V1"
AUTHORIZE_RULE = "AUTHORIZE_V5_STAGE_A_NEXT_RUN_ON_REMEDIATED_SURFACE"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V5-STAGE-A-004"
AUTHORIZED_DATASET_SHA = (
    "8d4be8301b89b191841342fe11ef647c838b32e56e6d133b610c232264c5d00a"
)
# Literal pin — avoid circular import with uncertain_surface_remediate.
AUTHORIZED_SURFACE_RULE = "HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1R9"
SURFACE_RULE_V1R9 = AUTHORIZED_SURFACE_RULE
# Parent V1R8 / V1R7 pins retained for historical comparison only.
PARENT_V1R8_DATASET_SHA = (
    "c0fdd82d1734585a7d852318ac5b390cc5e2c50908c0ef9f9eba4b3f7ebedc8b"
)
PARENT_V1R8_SURFACE_RULE = SURFACE_RULE_V1R8
PARENT_V1R8_EXPERIMENT_ID = "HLX-CLASSIFICATION-V5-STAGE-A-002"
PARENT_V1R7_DATASET_SHA = (
    "a81ca68ad3310981c60d2500a83a0989adeb967cbee6ad6dff003ed2c705efa9"
)
PARENT_V1R7_SURFACE_RULE = SURFACE_RULE_V1R7
PARENT_V1R7_EXPERIMENT_ID = "HLX-CLASSIFICATION-V5-STAGE-A-001"

# Frozen class order (index == logit position).
EVIDENCE_LABELS = ("NO_EVIDENCE", "EVIDENCE_PRESENT", "UNCERTAIN")
LABEL_INDEX = {label: index for index, label in enumerate(EVIDENCE_LABELS)}
INDEX_LABEL = {index: label for label, index in LABEL_INDEX.items()}

ACCEPTANCE_GATES = {
    "EVIDENCE_PRESENT_recall_min": 0.70,
    "NO_EVIDENCE_recall_min": 0.90,
    "false_evidence_entry_rate_on_none_max": 0.05,
    "optimize_family_metrics_before_stage_a_pass": False,
}

TRAIN_HYPERPARAMS = {
    "early_stopping_patience": 4,
    "gradient_accumulation": 1,
    "head_init": "xavier_uniform_bias_zeros",
    "last_trainable": 2,
    "learning_rate": 2e-5,
    "max_epochs": 12,
    "max_grad_norm": 1.0,
    "max_len": 64,
    "micro_batch_size": 8,
    "minimum_epochs": 4,
    "mixed_precision": "runtime_supported_deterministic_only",
    "optimizer": "AdamW",
    "padding": "right",
    "pooling": "last_hidden_state[:,0]",
    "seed": 42,
    "truncation": True,
    "warmup_ratio": 0.05,
    "weight_decay": 0.01,
}

PROVENANCE_LOSS_MULTIPLIERS = {
    "OBSERVED": 1.0,
    "INFERRED": 0.5,
}

CLASS_WEIGHT_POLICY = {
    "clip_max": 2.0,
    "clip_min": 0.50,
    "formula": "sqrt(median(effective_count)/effective_count_c); normalize mean=1.0; clip",
    "source_split": "train",
}

THRESHOLD_GRID = {
    "none_thresholds": [round(0.50 + 0.05 * i, 2) for i in range(10)],
    "present_thresholds": [round(0.50 + 0.05 * i, 2) for i in range(10)],
    "require_none_lt_present": True,
}

CHECKPOINT_SELECTION = {
    "metric": "stage_a_macro_f1",
    "strict_improvement": True,
    "tie_break": [
        "lower_false_evidence_entry_rate_on_none",
        "higher_NO_EVIDENCE_recall",
        "earlier_epoch",
    ],
}

THRESHOLD_SELECTION = {
    "acceptance_required": [
        "false_evidence_entry_rate_on_none <= 0.05",
        "EVIDENCE_PRESENT_recall >= 0.70",
        "NO_EVIDENCE_recall >= 0.90",
    ],
    "maximize_in_order": [
        "stage_a_macro_f1",
        "EVIDENCE_PRESENT_recall",
        "NO_EVIDENCE_recall",
        "uncertain_band_width",
    ],
    "fail_if_no_feasible": "SETTLED_FAIL",
    "score": "evidence_score = P(EVIDENCE_PRESENT)",
}

FORBIDDEN_LABEL_AUTHORITIES = (
    "MODEL_PREDICTED",
    "JEV",
    "HEURISTIC_UNVERSIONED",
    "UNKNOWN",
)
ALLOWED_AUTHORITIES = (
    "HUMAN_SETTLED",
    "CANONICAL_RULE",
    "SOURCE_ASSERTED",
    "DERIVED_RULE",
)
ALLOWED_DERIVATIONS = (
    "DIRECT",
    "MAPPED",
    "PAIRWISE_CONTRAST",
    "NEGATIVE_EXCLUSION",
    "AMBIGUITY_SETTLEMENT",
)
ALLOWED_REVIEWER_STATES = ("UNREVIEWED_RULE_DERIVED", "REVIEWED", "SETTLED")
AMBIGUITY_REASONS = (
    "INSUFFICIENT_CONTEXT",
    "CONFLICTING_EVIDENCE",
    "PARTIAL_REQUIRED_CORE",
    "MULTIPLE_PLAUSIBLE_INTERPRETATIONS",
    "UNRESOLVED_SOURCE_MEANING",
)
EVIDENCE_BASIS_TYPES = (
    "TEXT_SPAN",
    "SOURCE_ASSERTION",
    "FAMILY_REQUIRED_CORE",
    "PAIR_CONTRAST",
    "EXCLUSION_RULE",
    "HUMAN_SETTLEMENT",
    "CANONICAL_MAPPING",
)


def canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def label_index(label: str) -> int:
    if label not in LABEL_INDEX:
        raise ValueError(f"unknown_evidence_label:{label}")
    return LABEL_INDEX[label]


def evidence_score_from_probabilities(probabilities: Mapping[str, float]) -> float:
    return float(probabilities["EVIDENCE_PRESENT"])


def softmax_logits(logits: Sequence[float]) -> dict[str, float]:
    peak = max(float(value) for value in logits)
    exps = [math.exp(float(value) - peak) for value in logits]
    total = sum(exps) or 1.0
    probs = [value / total for value in exps]
    return {INDEX_LABEL[index]: probs[index] for index in range(len(EVIDENCE_LABELS))}


def decide_evidence(
    evidence_score: float,
    *,
    none_threshold: float,
    present_threshold: float,
) -> str:
    if not (0.0 <= float(evidence_score) <= 1.0):
        raise ValueError("evidence_score_out_of_range")
    if not (0.0 <= float(none_threshold) < float(present_threshold) <= 1.0):
        raise ValueError("threshold_order_invalid")
    if float(evidence_score) >= float(present_threshold):
        return "EVIDENCE_PRESENT"
    if float(evidence_score) <= float(none_threshold):
        return "NO_EVIDENCE"
    return "UNCERTAIN"


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


def stage_a_macro_f1(golds: Sequence[str], preds: Sequence[str]) -> float:
    scores = [prf(golds, preds, label)["f1"] for label in EVIDENCE_LABELS]
    return sum(scores) / len(scores)


def balanced_accuracy(golds: Sequence[str], preds: Sequence[str]) -> float:
    recalls = [prf(golds, preds, label)["recall"] for label in EVIDENCE_LABELS]
    return sum(recalls) / len(recalls)


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
    macro = stage_a_macro_f1(golds, decisions)
    bal_acc = balanced_accuracy(golds, decisions)
    false_entry = false_evidence_entry_rate_on_none(golds, decisions)
    uncertain_rate = sum(1 for d in decisions if d == "UNCERTAIN") / max(1, len(decisions))
    subtype_metrics: dict[str, Any] = {}
    if subtypes is not None:
        buckets: dict[str, list[int]] = defaultdict(list)
        for index, subtype in enumerate(subtypes):
            buckets[str(subtype)].append(index)
        for subtype, indices in sorted(buckets.items()):
            sub_golds = [golds[i] for i in indices]
            sub_preds = [decisions[i] for i in indices]
            subtype_metrics[subtype] = {
                "n": len(indices),
                "false_evidence_entry_rate_on_none": false_evidence_entry_rate_on_none(
                    sub_golds, sub_preds
                ),
                "by_label": {
                    label: prf(sub_golds, sub_preds, label) for label in EVIDENCE_LABELS
                },
            }
    present_recall = by_label["EVIDENCE_PRESENT"]["recall"]
    none_recall = by_label["NO_EVIDENCE"]["recall"]
    acceptance = {
        "false_evidence_entry_rate_on_none": false_entry
        <= ACCEPTANCE_GATES["false_evidence_entry_rate_on_none_max"],
        "EVIDENCE_PRESENT_recall": present_recall
        >= ACCEPTANCE_GATES["EVIDENCE_PRESENT_recall_min"],
        "NO_EVIDENCE_recall": none_recall >= ACCEPTANCE_GATES["NO_EVIDENCE_recall_min"],
    }
    return {
        "acceptance": acceptance,
        "acceptance_pass": all(acceptance.values()),
        "balanced_accuracy": bal_acc,
        "by_label": by_label,
        "confusion": dict(Counter(f"{g}->{p}" for g, p in zip(golds, decisions))),
        "false_evidence_entry_rate_on_none": false_entry,
        "n": len(golds),
        "stage_a_macro_f1": macro,
        "subtype_metrics": subtype_metrics,
        "uncertain_rate": uncertain_rate,
    }


def compute_class_weights(train_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    effective: dict[str, float] = {label: 0.0 for label in EVIDENCE_LABELS}
    for row in train_rows:
        label = str(row["evidence_label"])
        if label not in effective:
            raise ValueError(f"unknown_train_label:{label}")
        prov = str(row.get("provenance") or "INFERRED")
        effective[label] += float(PROVENANCE_LOSS_MULTIPLIERS.get(prov, 0.5))
    counts = [effective[label] for label in EVIDENCE_LABELS]
    median = statistics.median(counts) if counts else 1.0
    raw = {}
    for label in EVIDENCE_LABELS:
        denom = effective[label] if effective[label] > 0 else 1.0
        raw[label] = math.sqrt(median / denom)
    mean_raw = sum(raw.values()) / len(raw)
    normalized = {label: value / mean_raw for label, value in raw.items()}
    clipped = {
        label: max(
            CLASS_WEIGHT_POLICY["clip_min"],
            min(CLASS_WEIGHT_POLICY["clip_max"], value),
        )
        for label, value in normalized.items()
    }
    return {
        "class_weights": clipped,
        "effective_counts": effective,
        "normalized_weights": normalized,
        "policy": dict(CLASS_WEIGHT_POLICY),
        "provenance_multipliers": dict(PROVENANCE_LOSS_MULTIPLIERS),
        "raw_weights": raw,
    }


def calibrate_thresholds(
    golds: Sequence[str],
    scores: Sequence[float],
    *,
    subtypes: Sequence[str] | None = None,
) -> dict[str, Any]:
    candidates = []
    for none_threshold in THRESHOLD_GRID["none_thresholds"]:
        for present_threshold in THRESHOLD_GRID["present_thresholds"]:
            if not (none_threshold < present_threshold):
                continue
            decisions = [
                decide_evidence(
                    float(score),
                    none_threshold=none_threshold,
                    present_threshold=present_threshold,
                )
                for score in scores
            ]
            metrics = evaluate_decisions(golds, decisions, subtypes=subtypes)
            band = present_threshold - none_threshold
            candidates.append(
                {
                    "metrics": metrics,
                    "none_threshold": none_threshold,
                    "present_threshold": present_threshold,
                    "uncertain_band_width": band,
                    "acceptance_pass": metrics["acceptance_pass"],
                    "stage_a_macro_f1": metrics["stage_a_macro_f1"],
                    "present_recall": metrics["by_label"]["EVIDENCE_PRESENT"]["recall"],
                    "none_recall": metrics["by_label"]["NO_EVIDENCE"]["recall"],
                    "false_entry": metrics["false_evidence_entry_rate_on_none"],
                }
            )
    if not candidates:
        raise RuntimeError("threshold_grid_empty")
    # Compact full-grid witness (preregistered selection evidence; keep permanently).
    grid_results = [
        {
            "acceptance_pass": row["acceptance_pass"],
            "false_evidence_entry_rate_on_none": row["false_entry"],
            "none_recall": row["none_recall"],
            "none_threshold": row["none_threshold"],
            "present_recall": row["present_recall"],
            "present_threshold": row["present_threshold"],
            "stage_a_macro_f1": row["stage_a_macro_f1"],
            "uncertain_band_width": row["uncertain_band_width"],
        }
        for row in candidates
    ]
    passing = [row for row in candidates if row["acceptance_pass"]]
    if not passing:
        return {
            "chosen": None,
            "disposition": "SETTLED_FAIL",
            "feasible": False,
            "grid": THRESHOLD_GRID,
            "grid_results": grid_results,
            "n_candidates": len(candidates),
            "n_passing": 0,
            "selection_rule": THRESHOLD_SELECTION,
        }
    passing.sort(
        key=lambda row: (
            -row["stage_a_macro_f1"],
            -row["present_recall"],
            -row["none_recall"],
            -row["uncertain_band_width"],
            row["none_threshold"],
            row["present_threshold"],
        )
    )
    chosen = passing[0]
    return {
        "chosen": {
            "false_evidence_entry_rate_on_none": chosen["false_entry"],
            "none_threshold": chosen["none_threshold"],
            "present_threshold": chosen["present_threshold"],
            "stage_a_macro_f1": chosen["stage_a_macro_f1"],
            "uncertain_band_width": chosen["uncertain_band_width"],
        },
        "disposition": "SETTLED_PASS",
        "feasible": True,
        "grid": THRESHOLD_GRID,
        "grid_results": grid_results,
        "metrics": chosen["metrics"],
        "n_candidates": len(candidates),
        "n_passing": len(passing),
        "selection_rule": THRESHOLD_SELECTION,
    }


def stratified_label_indices(
    labels: Sequence[str],
    *,
    batch_size: int,
    seed: int,
) -> list[list[int]]:
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


# --- Label provenance -------------------------------------------------------

SUBTYPE_RULE_IDS = {
    "POSITIVE_EVIDENCE": "HYPERLEX_V5_STAGE_A_POSITIVE_MAPPED_V1",
    "ORDINARY_DOMAIN_NONE": "HYPERLEX_V5_STAGE_A_ORDINARY_DOMAIN_NONE_V1",
    "HARD_NONE": "HYPERLEX_V5_STAGE_A_HARD_NONE_V1",
    "NEAR_DOMAIN_NONE": "HYPERLEX_V5_STAGE_A_NEAR_DOMAIN_NONE_V1",
    "GENERIC_NONE": "HYPERLEX_V5_STAGE_A_GENERIC_NONE_V1",
    "LEXICAL_LOOKALIKE_NONE": "HYPERLEX_V5_STAGE_A_LEXICAL_LOOKALIKE_NONE_V1",
    "SHORT_ATOM_NONE": "HYPERLEX_V5_STAGE_A_SHORT_ATOM_NONE_V1",
    "AMBIGUOUS_EVIDENCE": "HYPERLEX_V5_STAGE_A_AMBIGUOUS_V1",
}
PAIRWISE_RULE_ID = "HYPERLEX_V5_STAGE_A_PAIRWISE_CONTRAST_V1"
SOURCE_ASSERTED_POSITIVE_RULE_ID = "HYPERLEX_V5_STAGE_A_POSITIVE_SOURCE_ASSERTED_V1"
RULE_VERSION = "1"


def rule_sha256(rule_id: str) -> str:
    return sha256_text(
        canonical_json(
            {
                "label_provenance_rule": LABEL_PROVENANCE_RULE,
                "rule_id": rule_id,
                "rule_version": RULE_VERSION,
                "stage_a_rule": STAGE_A_RULE,
            }
        )
    )


def _decision_sha(
    *,
    identity: str,
    evidence_label: str,
    evidence_subtype: str,
    authority: str,
    derivation: str,
    evidence_basis: Sequence[Mapping[str, Any]],
    source_labels: Sequence[str],
    rule_id: str,
    rule_version: str,
) -> str:
    return sha256_text(
        canonical_json(
            {
                "authority": authority,
                "derivation": derivation,
                "evidence_basis": list(evidence_basis),
                "evidence_label": evidence_label,
                "evidence_subtype": evidence_subtype,
                "identity": identity,
                "rule_id": rule_id,
                "rule_version": rule_version,
                "source_labels": list(source_labels),
            }
        )
    )


def derive_label_provenance(row: Mapping[str, Any]) -> dict[str, Any]:
    """Deterministic label provenance from sealed surface fields (no model scores)."""
    identity = str(row["identity"])
    label = str(row["evidence_label"])
    subtype = str(row["evidence_subtype"])
    source_prov = str(row.get("provenance") or "INFERRED")
    families = [str(f) for f in (row.get("active_family_support") or [])]
    missing = [str(m) for m in (row.get("missing_required_semantics") or [])]
    paired = bool(row.get("pair_group_id") or row.get("paired_positive_identity"))
    has_url = bool(row.get("source_url"))
    topic = str(row.get("topic_domain") or "")

    if label == "EVIDENCE_PRESENT":
        if not families:
            raise ValueError(f"LABEL_PROVENANCE_INVALID:present_without_family:{identity}")
        if source_prov == "OBSERVED" and has_url:
            authority, derivation = "SOURCE_ASSERTED", "DIRECT"
            rule_id = SOURCE_ASSERTED_POSITIVE_RULE_ID
            reviewer = "REVIEWED"
            basis = [
                {
                    "family": families[0],
                    "reference": f"source-assertion:{families[0]}",
                    "sha256": sha256_text(str(row.get("source_url"))),
                    "type": "SOURCE_ASSERTION",
                },
                {
                    "family": families[0],
                    "reference": f"family-required-core:{families[0]}",
                    "sha256": rule_sha256(rule_id),
                    "type": "FAMILY_REQUIRED_CORE",
                },
            ]
            source_labels = list(families)
        elif paired:
            authority, derivation = "DERIVED_RULE", "PAIRWISE_CONTRAST"
            rule_id = PAIRWISE_RULE_ID
            reviewer = "REVIEWED"
            basis = [
                {
                    "family": families[0],
                    "reference": f"pair-contrast:{row.get('pair_group_id')}",
                    "sha256": sha256_text(str(row.get("pair_group_id") or identity)),
                    "type": "PAIR_CONTRAST",
                }
            ]
            source_labels = list(families)
        else:
            authority, derivation = "CANONICAL_RULE", "MAPPED"
            rule_id = SUBTYPE_RULE_IDS["POSITIVE_EVIDENCE"]
            reviewer = "UNREVIEWED_RULE_DERIVED"
            basis = [
                {
                    "family": families[0],
                    "reference": f"canonical-mapping:lineage->{families[0]}",
                    "sha256": rule_sha256(rule_id),
                    "type": "CANONICAL_MAPPING",
                }
            ]
            source_labels = list(families)
    elif label == "NO_EVIDENCE":
        if paired:
            authority, derivation = "DERIVED_RULE", "PAIRWISE_CONTRAST"
            rule_id = PAIRWISE_RULE_ID
            reviewer = "REVIEWED"
            basis = [
                {
                    "reference": f"pair-contrast:{row.get('pair_group_id')}",
                    "sha256": sha256_text(str(row.get("pair_group_id") or identity)),
                    "type": "PAIR_CONTRAST",
                },
                {
                    "reference": f"v5-stage-a-negative-contract:{subtype}",
                    "sha256": rule_sha256(SUBTYPE_RULE_IDS[subtype]),
                    "type": "EXCLUSION_RULE",
                },
            ]
        elif source_prov == "OBSERVED" and has_url and subtype == "ORDINARY_DOMAIN_NONE":
            authority, derivation = "SOURCE_ASSERTED", "DIRECT"
            rule_id = SUBTYPE_RULE_IDS[subtype]
            reviewer = "REVIEWED"
            basis = [
                {
                    "reference": f"source-assertion:ordinary:{topic or 'domain'}",
                    "sha256": sha256_text(str(row.get("source_url"))),
                    "type": "SOURCE_ASSERTION",
                },
                {
                    "reference": f"v5-stage-a-negative-contract:{subtype}",
                    "sha256": rule_sha256(rule_id),
                    "type": "EXCLUSION_RULE",
                },
            ]
        else:
            authority, derivation = "CANONICAL_RULE", "NEGATIVE_EXCLUSION"
            rule_id = SUBTYPE_RULE_IDS[subtype]
            reviewer = "UNREVIEWED_RULE_DERIVED"
            reason_codes = missing or [f"subtype_exclusion:{subtype}"]
            basis = [
                {
                    "reference": f"v5-stage-a-negative-contract:{subtype}",
                    "sha256": rule_sha256(rule_id),
                    "type": "EXCLUSION_RULE",
                    "exclusion_reason_codes": reason_codes,
                    "evaluated_active_families": families,
                    "failed_required_cores": reason_codes,
                }
            ]
        source_labels = ["NONE", subtype] if subtype else ["NONE"]
    elif label == "UNCERTAIN":
        rule_id = SUBTYPE_RULE_IDS["AMBIGUOUS_EVIDENCE"]
        ambiguity_reason = str(row.get("ambiguity_reason") or "")
        if ambiguity_reason not in AMBIGUITY_REASONS:
            # Fail closed: do not silently default a reason for gold UNCERTAIN.
            # Legacy callers without an explicit reason keep the historical
            # single-reason contract only when no reason field is present.
            if row.get("ambiguity_reason") is None:
                ambiguity_reason = "MULTIPLE_PLAUSIBLE_INTERPRETATIONS"
            else:
                raise ValueError(
                    f"LABEL_PROVENANCE_INVALID:ambiguity_reason:{ambiguity_reason}"
                )
        if (
            str(row.get("provenance") or row.get("source_provenance") or "")
            == "OBSERVED"
            and row.get("source_url")
            and str(row.get("label_authority") or "HUMAN_SETTLED") == "HUMAN_SETTLED"
        ):
            authority, derivation = "HUMAN_SETTLED", "AMBIGUITY_SETTLEMENT"
            reviewer = "SETTLED"
            basis = [
                {
                    "ambiguity_reason": ambiguity_reason,
                    "reference": f"human-settlement:ambiguous:{ambiguity_reason}",
                    "sha256": sha256_text(str(row.get("source_url"))),
                    "type": "HUMAN_SETTLEMENT",
                },
                {
                    "ambiguity_reason": ambiguity_reason,
                    "reference": "v5-stage-a-ambiguous-contract:AMBIGUOUS_EVIDENCE",
                    "sha256": rule_sha256(rule_id),
                    "type": "CANONICAL_MAPPING",
                },
            ]
        else:
            authority, derivation = "CANONICAL_RULE", "AMBIGUITY_SETTLEMENT"
            reviewer = "UNREVIEWED_RULE_DERIVED"
            basis = [
                {
                    "ambiguity_reason": ambiguity_reason,
                    "reference": "v5-stage-a-ambiguous-contract:AMBIGUOUS_EVIDENCE",
                    "sha256": rule_sha256(rule_id),
                    "type": "CANONICAL_MAPPING",
                }
            ]
        source_labels = ["AMBIGUOUS_EVIDENCE"]
    else:
        raise ValueError(f"LABEL_PROVENANCE_INVALID:unknown_label:{label}")

    decision = _decision_sha(
        identity=identity,
        evidence_label=label,
        evidence_subtype=subtype,
        authority=authority,
        derivation=derivation,
        evidence_basis=basis,
        source_labels=source_labels,
        rule_id=rule_id,
        rule_version=RULE_VERSION,
    )
    return {
        "authority": authority,
        "decision_sha256": decision,
        "derivation": derivation,
        "evidence_basis": basis,
        "reviewer_state": reviewer,
        "rule_id": rule_id,
        "rule_sha256": rule_sha256(rule_id),
        "rule_version": RULE_VERSION,
        "source_labels": source_labels,
    }


def validate_label_provenance(
    row: Mapping[str, Any],
    provenance: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    authority = provenance.get("authority")
    derivation = provenance.get("derivation")
    reviewer = provenance.get("reviewer_state")
    basis = provenance.get("evidence_basis") or []
    if authority in FORBIDDEN_LABEL_AUTHORITIES:
        errors.append("forbidden_authority")
    if authority not in ALLOWED_AUTHORITIES:
        errors.append("authority_not_allowed")
    if derivation not in ALLOWED_DERIVATIONS:
        errors.append("derivation_not_allowed")
    if reviewer not in ALLOWED_REVIEWER_STATES:
        errors.append("reviewer_state_not_allowed")
    if not basis:
        errors.append("evidence_basis_empty")
    label = str(row["evidence_label"])
    combo_ok = False
    if label == "EVIDENCE_PRESENT":
        combo_ok = (authority, derivation) in {
            ("HUMAN_SETTLED", "DIRECT"),
            ("SOURCE_ASSERTED", "DIRECT"),
            ("CANONICAL_RULE", "MAPPED"),
            ("DERIVED_RULE", "PAIRWISE_CONTRAST"),
        }
        if not (row.get("active_family_support") or []):
            errors.append("present_requires_family")
        if str(row.get("required_evidence_present")) != "true":
            errors.append("present_requires_required_true")
    elif label == "NO_EVIDENCE":
        combo_ok = (authority, derivation) in {
            ("HUMAN_SETTLED", "DIRECT"),
            ("CANONICAL_RULE", "NEGATIVE_EXCLUSION"),
            ("DERIVED_RULE", "PAIRWISE_CONTRAST"),
            ("SOURCE_ASSERTED", "DIRECT"),
        }
        if str(row.get("required_evidence_present")) != "false":
            errors.append("none_requires_required_false")
        if derivation == "NEGATIVE_EXCLUSION":
            has_reason = False
            for item in basis:
                if item.get("type") == "EXCLUSION_RULE" and (
                    item.get("exclusion_reason_codes") or item.get("reference")
                ):
                    has_reason = True
            if not has_reason:
                errors.append("negative_exclusion_reason_missing")
    elif label == "UNCERTAIN":
        combo_ok = (authority, derivation) in {
            ("HUMAN_SETTLED", "AMBIGUITY_SETTLEMENT"),
            ("CANONICAL_RULE", "AMBIGUITY_SETTLEMENT"),
        }
        has_reason = any(
            item.get("ambiguity_reason") in AMBIGUITY_REASONS for item in basis
        )
        if not has_reason:
            errors.append("ambiguity_reason_missing")
    if not combo_ok:
        errors.append("authority_derivation_combo_invalid")
    if authority == "HUMAN_SETTLED" and reviewer != "SETTLED":
        errors.append("human_settled_requires_settled_reviewer")
    if authority == "SOURCE_ASSERTED" and reviewer not in {"REVIEWED", "SETTLED"}:
        errors.append("source_asserted_reviewer_invalid")
    if authority == "DERIVED_RULE" and reviewer == "UNREVIEWED_RULE_DERIVED":
        errors.append("derived_rule_unreviewed_forbidden")
    if authority != "HUMAN_SETTLED":
        if not provenance.get("rule_id") or not provenance.get("rule_version"):
            errors.append("rule_identity_missing")
        if not provenance.get("rule_sha256"):
            errors.append("rule_sha256_missing")
    expected = _decision_sha(
        identity=str(row["identity"]),
        evidence_label=label,
        evidence_subtype=str(row["evidence_subtype"]),
        authority=str(authority),
        derivation=str(derivation),
        evidence_basis=list(basis),
        source_labels=list(provenance.get("source_labels") or []),
        rule_id=str(provenance.get("rule_id") or ""),
        rule_version=str(provenance.get("rule_version") or ""),
    )
    if provenance.get("decision_sha256") != expected:
        errors.append("decision_sha256_mismatch")
    return errors


def attach_and_validate_label_provenance(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    records = []
    invalid = []
    by_authority: Counter[str] = Counter()
    by_derivation: Counter[str] = Counter()
    by_label: Counter[str] = Counter()
    by_subtype: Counter[str] = Counter()
    by_reviewer: Counter[str] = Counter()
    authority_label: Counter[str] = Counter()
    derivation_subtype: Counter[str] = Counter()
    by_rule: Counter[str] = Counter()
    label_rule_share: dict[str, Counter[str]] = defaultdict(Counter)

    for row in rows:
        try:
            prov = derive_label_provenance(row)
            errors = validate_label_provenance(row, prov)
        except ValueError as exc:
            errors = [str(exc)]
            prov = {}
        if errors:
            invalid.append({"identity": row.get("identity"), "errors": errors})
            continue
        records.append(
            {
                "identity": row["identity"],
                "evidence_label": row["evidence_label"],
                "evidence_subtype": row["evidence_subtype"],
                "source_provenance": row.get("provenance"),
                "label_provenance": prov,
            }
        )
        by_authority[str(prov["authority"])] += 1
        by_derivation[str(prov["derivation"])] += 1
        by_label[str(row["evidence_label"])] += 1
        by_subtype[str(row["evidence_subtype"])] += 1
        by_reviewer[str(prov["reviewer_state"])] += 1
        authority_label[f"{prov['authority']}x{row['evidence_label']}"] += 1
        derivation_subtype[f"{prov['derivation']}x{row['evidence_subtype']}"] += 1
        by_rule[str(prov["rule_id"])] += 1
        label_rule_share[str(row["evidence_label"])][str(prov["rule_id"])] += 1

    dominance_warnings = []
    for label, counter in label_rule_share.items():
        total = sum(counter.values()) or 1
        for rule_id, count in counter.items():
            share = count / total
            if share > 0.75:
                dominance_warnings.append(
                    {
                        "label": label,
                        "rule_id": rule_id,
                        "share": share,
                        "warning": "single_rule_dominance_gt_0_75",
                    }
                )

    return {
        "invalid_provenance_rows": len(invalid),
        "invalid_samples": invalid[:20],
        "n_valid": len(records),
        "pass": len(invalid) == 0,
        "records": records,
        "rule": LABEL_PROVENANCE_RULE,
        "statistics": {
            "authority_x_label": dict(authority_label),
            "counts_by_authority": dict(by_authority),
            "counts_by_derivation": dict(by_derivation),
            "counts_by_gate_label": dict(by_label),
            "counts_by_reviewer_state": dict(by_reviewer),
            "counts_by_rule_id": dict(by_rule),
            "counts_by_subtype": dict(by_subtype),
            "derivation_x_subtype": dict(derivation_subtype),
            "single_rule_dominance_warnings": dominance_warnings,
        },
    }


def build_resolved_training_config(
    *,
    dataset_sha256: str,
    class_weight_report: Mapping[str, Any],
    code_revision: str,
    tokenizer_identity: str,
    surface_rule: str,
) -> dict[str, Any]:
    config = {
        "acceptance_gates": dict(ACCEPTANCE_GATES),
        "architecture": {
            "encoder": "ModernBERT-base",
            "head": "linear_hidden_to_3_logits",
            "head_init": TRAIN_HYPERPARAMS["head_init"],
            "pooling": TRAIN_HYPERPARAMS["pooling"],
        },
        "best_encoder_sha256": BEST_SHA,
        "checkpoint_selection": dict(CHECKPOINT_SELECTION),
        "class_order": list(EVIDENCE_LABELS),
        "class_weight_report": dict(class_weight_report),
        "code_revision": code_revision,
        "dataset_sha256": dataset_sha256,
        "experiment_id": EXPERIMENT_ID,
        "label_provenance_rule": LABEL_PROVENANCE_RULE,
        "loss": {
            "name": "weighted_cross_entropy",
            "provenance_multipliers": dict(PROVENANCE_LOSS_MULTIPLIERS),
            "forbidden": [
                "focal",
                "contrastive",
                "family",
                "prototype",
                "reserve_derived_weighting",
            ],
        },
        "optimization": {
            "early_stopping_patience": TRAIN_HYPERPARAMS["early_stopping_patience"],
            "gradient_accumulation": TRAIN_HYPERPARAMS["gradient_accumulation"],
            "learning_rate": TRAIN_HYPERPARAMS["learning_rate"],
            "max_epochs": TRAIN_HYPERPARAMS["max_epochs"],
            "max_grad_norm": TRAIN_HYPERPARAMS["max_grad_norm"],
            "micro_batch_size": TRAIN_HYPERPARAMS["micro_batch_size"],
            "minimum_epochs": TRAIN_HYPERPARAMS["minimum_epochs"],
            "mixed_precision": TRAIN_HYPERPARAMS["mixed_precision"],
            "optimizer": TRAIN_HYPERPARAMS["optimizer"],
            "warmup_ratio": TRAIN_HYPERPARAMS["warmup_ratio"],
            "weight_decay": TRAIN_HYPERPARAMS["weight_decay"],
        },
        "rule": STAGE_A_RULE,
        "schema": "hyperlex.classification.v5.stage_a_resolved_config.v1",
        "seed": TRAIN_HYPERPARAMS["seed"],
        "surface_rule": surface_rule,
        "threshold_grid": dict(THRESHOLD_GRID),
        "threshold_selection": dict(THRESHOLD_SELECTION),
        "tokenization": {
            "max_length": TRAIN_HYPERPARAMS["max_len"],
            "padding": TRAIN_HYPERPARAMS["padding"],
            "tokenizer_identity": tokenizer_identity,
            "truncation": TRAIN_HYPERPARAMS["truncation"],
        },
        "trainable": {
            "evidence_head": True,
            "last_trainable_encoder_layers": TRAIN_HYPERPARAMS["last_trainable"],
            "mutate_best": False,
        },
        "train_run_limit": 1,
    }
    config["training_config_sha256"] = sha256_text(
        canonical_json({k: v for k, v in config.items() if k != "training_config_sha256"})
    )
    return config


def stage_a_authorization_contract(
    *,
    dataset_sha256: str,
    training_config_sha256: str,
    code_revision: str,
) -> dict[str, Any]:
    return {
        "BEST": "UNCHANGED",
        "BEST_MUTATED": False,
        "CURRENT_BEST": BEST_SHA,
        "DATASET_SHA256": dataset_sha256,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "RESERVE_CONSUMED": False,
        "SCIENTIFIC_RESULT": "NOT_COMPUTABLE",
        "TRAINING_CONFIG_SHA256": training_config_sha256,
        "TRAINING_RUN_LIMIT": 1,
        "TRAINING_STATUS": "AUTHORIZED_NOT_STARTED",
        "TRAIN_AUTHORIZED": True,
        "acceptance_gates": dict(ACCEPTANCE_GATES),
        "authorize_rule": AUTHORIZE_RULE,
        "authorized_dataset_sha256": AUTHORIZED_DATASET_SHA,
        "code_revision": code_revision,
        "label_provenance_rule": LABEL_PROVENANCE_RULE,
        "parent_surface_dataset_sha256": PARENT_V1R8_DATASET_SHA,
        "parent_surface_rule": PARENT_V1R8_SURFACE_RULE,
        "parent_surface_rule_v1": SURFACE_RULE_V1,
        "rule": STAGE_A_RULE,
        "schema": "hyperlex.classification.v5.stage_a_train_authorization.v1",
        "surface_rule": AUTHORIZED_SURFACE_RULE,
        "train": False,
        "train_authorized": True,
    }


def authorization_gate_checks(
    *,
    train_authorized: bool,
    dataset_sha256: str,
    surface_readiness: str,
    resolved_config_sha256: str,
    authorized_config_sha256: str,
    current_best: str,
    reserve_consumed: bool,
) -> dict[str, Any]:
    checks = {
        "train_authorized": train_authorized is True,
        "dataset_sha256": dataset_sha256 == AUTHORIZED_DATASET_SHA,
        "surface_readiness": surface_readiness == "PASS",
        "resolved_config_sha256": resolved_config_sha256 == authorized_config_sha256,
        "CURRENT_BEST": current_best == BEST_SHA,
        "reserve_consumed": reserve_consumed is False,
    }
    return {"checks": checks, "pass": all(checks.values())}
