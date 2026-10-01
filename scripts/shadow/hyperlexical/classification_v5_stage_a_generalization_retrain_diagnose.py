"""DIAGNOSE_V5_STAGE_A_GENERALIZATION_RETRAIN_SETTLED_FAIL — read-only.

Diagnoses Gate-1 failure on V1R1 after SETTLED_FAIL of
HLX-CLASSIFICATION-V5-STAGE-A-TWO-STAGE-GENERALIZATION-001.
Does not train, create V1R2, retune, use spent reserve, or move BEST.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

from .classification_v2_surface import surface_form, word_count
from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_generalization_surface import length_band
from .classification_v5_stage_a_two_stage_generalization import (
    AUTHORIZED_AUTH_RECEIPT_SHA256,
    AUTHORIZED_DATASET_SHA,
    AUTHORIZED_READINESS_SHA,
    AUTHORIZED_SURFACE_RECEIPT_SHA,
    AUTHORIZED_TRAINING_CONFIG_SHA256,
    EXPERIMENT_ID,
    PARENT_STAGE_A_BEST_SHA,
    SPENT_RESERVE,
    SPENT_RESERVE_OVERLAP,
    SPENT_RESERVE_STATUS,
)

DIAGNOSE_RULE = "DIAGNOSE_V5_STAGE_A_GENERALIZATION_RETRAIN_SETTLED_FAIL"
FAILED_CHECKPOINT_SHA256 = (
    "26841d5f3a8b9cd4237f79203b80697f2da186e7d4b30ab6c08d528adba56e76"
)
FAILED_RUN_RECEIPT_SHA256 = (
    "35d9a70675dc320116d68e52dda52bc6118140ae401d709ed104b5ae290d8025"
)

# Frozen observed outcome — no reinterpretation.
FROZEN_OBSERVED_OUTCOME = {
    "E2E_NONE_recall": 0.7845,
    "E2E_PRESENT_recall": 0.8907,
    "E2E_false_entry": 0.2014,
    "Gate1_NONE_recall": 0.7845,
    "Gate1_POSSIBLE_recall": 0.9037,
    "Gate1_false_entry": 0.2155,
    "Gate1_macro_F1": 0.8397,
    "SHORT_ATOM_NONE_false_entry": 0.546,
    "SHORT_ATOM_PRESENT_recall": 0.750,
    "n_threshold_passing": 0,
    "scientific_disposition": "SETTLED_FAIL",
}

GATE1_THRESHOLDS = [
    0.50,
    0.55,
    0.60,
    0.65,
    0.70,
    0.75,
    0.80,
    0.85,
    0.90,
    0.95,
]

PRIMARY_DIAGNOSES = (
    "GATE1_HEAD_OPTIMIZATION_FAILURE",
    "GATE1_NONLINEAR_BOUNDARY_FAILURE",
    "GATE1_REPRESENTATION_FAILURE",
    "GATE1_SEMANTIC_TARGET_MISMATCH",
    "GATE1_DATA_COVERAGE_FAILURE",
    "MIXED_GATE1_FAILURE",
)

NEXT_ACTIONS = (
    "NEW_STAGE_A_SURFACE",
    "GATE1_OBJECTIVE_REDESIGN",
    "GATE1_ARCHITECTURE_REDESIGN",
    "STAGE_A_SEMANTIC_DECOMPOSITION",
    "STOP_AND_ARCHIVE_V5",
)

REPRESENTATION_STATES = (
    "SHORT_ATOM_REPRESENTATION_SEPARABLE",
    "SHORT_ATOM_REPRESENTATION_PARTIAL",
    "SHORT_ATOM_REPRESENTATION_COLLAPSED",
)

SEMANTIC_CORE_CLASSES = (
    "LEXEME_ONLY",
    "LEXEME_PLUS_RELATION",
    "LEXEME_PLUS_CONTEXT",
    "EXPLICIT_EVIDENCE_CORE",
    "NEGATED_OR_NONASSERTED",
    "CATEGORY_MENTION_ONLY",
    "OTHER",
)


def gate1_gold_possible(evidence_label: str) -> bool:
    return str(evidence_label) in {"EVIDENCE_PRESENT", "UNCERTAIN"}


def classify_gate1_error(
    *,
    evidence_label: str,
    p_possible: float,
    gate1_threshold: float = 0.50,
) -> str:
    gold_possible = gate1_gold_possible(evidence_label)
    pred_possible = float(p_possible) >= float(gate1_threshold)
    if not gold_possible and not pred_possible:
        return "TRUE_NONE"
    if not gold_possible and pred_possible:
        return "FALSE_POSSIBLE"
    if gold_possible and pred_possible:
        return "TRUE_POSSIBLE"
    return "FALSE_NONE"


def label_authority(row: Mapping[str, Any]) -> str:
    prov = str(row.get("provenance") or "UNKNOWN")
    if prov == "OBSERVED":
        return "OBSERVED_AUTHORITY"
    if prov == "INFERRED":
        return "INFERRED_AUTHORITY"
    return "UNKNOWN_AUTHORITY"


def label_derivation(row: Mapping[str, Any]) -> str:
    notes = str(row.get("notes") or "")
    subtype = str(row.get("evidence_subtype") or "")
    if "v5_gen_wikt" in notes or "wik" in notes:
        return "WIKTIONARY_DERIVED"
    if "v5_gen_short" in notes or "SHORT_ATOM" in subtype:
        return "MATCHED_SHORT_ATOM_FILL"
    if "lookalike" in notes.lower() or "LOOKALIKE" in subtype:
        return "LEXICAL_LOOKALIKE"
    if row.get("paired_positive_identity") or row.get("pair_group_id"):
        return "MATCHED_CONTRAST"
    if prov := str(row.get("provenance") or ""):
        return f"PROVENANCE_{prov}"
    return "OTHER_DERIVATION"


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:12]


def simple_tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[A-Za-z0-9_'-]+", str(text).lower()) if t]


def percentile(sorted_vals: Sequence[float], p: float) -> float | None:
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    rank = (len(sorted_vals) - 1) * (p / 100.0)
    lo = int(math.floor(rank))
    hi = int(math.ceil(rank))
    if lo == hi:
        return float(sorted_vals[lo])
    weight = rank - lo
    return float(sorted_vals[lo] * (1.0 - weight) + sorted_vals[hi] * weight)


def dist_stats(values: Sequence[float]) -> dict[str, float | None]:
    vals = sorted(float(v) for v in values)
    if not vals:
        return {
            "mean": None,
            "median": None,
            "n": 0,
            "p10": None,
            "p25": None,
            "p50": None,
            "p75": None,
            "p90": None,
        }
    mean = sum(vals) / len(vals)
    return {
        "mean": mean,
        "median": percentile(vals, 50),
        "n": len(vals),
        "p10": percentile(vals, 10),
        "p25": percentile(vals, 25),
        "p50": percentile(vals, 50),
        "p75": percentile(vals, 75),
        "p90": percentile(vals, 90),
    }


def distribution_overlap(
    a: Sequence[float], b: Sequence[float]
) -> dict[str, float | None]:
    """Histogram intersection overlap on [0,1] with 20 bins + median gap."""
    if not a or not b:
        return {"histogram_intersection": None, "median_gap": None, "n_a": len(a), "n_b": len(b)}
    bins = 20
    ha = [0] * bins
    hb = [0] * bins
    for x in a:
        idx = min(bins - 1, max(0, int(float(x) * bins)))
        ha[idx] += 1
    for x in b:
        idx = min(bins - 1, max(0, int(float(x) * bins)))
        hb[idx] += 1
    na, nb = float(len(a)), float(len(b))
    inter = sum(min(ha[i] / na, hb[i] / nb) for i in range(bins))
    med_a = percentile(sorted(float(x) for x in a), 50) or 0.0
    med_b = percentile(sorted(float(x) for x in b), 50) or 0.0
    return {
        "histogram_intersection": inter,
        "median_gap": med_b - med_a,
        "n_a": len(a),
        "n_b": len(b),
    }


def cosine(u: Sequence[float], v: Sequence[float]) -> float:
    num = sum(float(a) * float(b) for a, b in zip(u, v))
    du = math.sqrt(sum(float(a) * float(a) for a in u))
    dv = math.sqrt(sum(float(b) * float(b) for b in v))
    if du <= 0.0 or dv <= 0.0:
        return 0.0
    return num / (du * dv)


def centroid(vectors: Sequence[Sequence[float]]) -> list[float] | None:
    if not vectors:
        return None
    dim = len(vectors[0])
    out = [0.0] * dim
    for vec in vectors:
        for i, val in enumerate(vec):
            out[i] += float(val)
    n = float(len(vectors))
    return [x / n for x in out]


def classify_representation_state(
    *,
    none_present_cosine: float | None,
    mean_none_margin: float | None,
    mean_present_margin: float | None,
) -> str:
    if none_present_cosine is None or mean_none_margin is None or mean_present_margin is None:
        return "SHORT_ATOM_REPRESENTATION_COLLAPSED"
    # High centroid cosine + non-positive margins → collapsed
    if none_present_cosine >= 0.95 and mean_none_margin <= 0.02 and mean_present_margin <= 0.02:
        return "SHORT_ATOM_REPRESENTATION_COLLAPSED"
    if none_present_cosine <= 0.85 and mean_none_margin >= 0.05 and mean_present_margin >= 0.05:
        return "SHORT_ATOM_REPRESENTATION_SEPARABLE"
    return "SHORT_ATOM_REPRESENTATION_PARTIAL"


def semantic_core_class(row: Mapping[str, Any]) -> str:
    """Classify using existing gold fields only — no new gold inference."""
    label = str(row.get("evidence_label") or "")
    subtype = str(row.get("evidence_subtype") or "")
    missing = [str(x) for x in (row.get("missing_required_semantics") or [])]
    notes = str(row.get("notes") or "")
    required = str(row.get("required_evidence_present") or "").lower()
    text = str(row.get("text") or "")
    lowered = text.lower()

    if any(tok in lowered for tok in (" not ", "n't", "never", "no ")):
        if label == "NO_EVIDENCE":
            return "NEGATED_OR_NONASSERTED"

    if label == "EVIDENCE_PRESENT" and required == "true":
        if word_count(text) <= 2 and "POSITIVE" in subtype:
            # Short positive atom: often lexeme carrying relation/core
            if row.get("pair_group_id"):
                return "LEXEME_PLUS_RELATION"
            return "EXPLICIT_EVIDENCE_CORE"
        return "EXPLICIT_EVIDENCE_CORE"

    if label == "NO_EVIDENCE":
        if "paired_against_positive_lacks_family_evidence" in missing:
            return "LEXEME_PLUS_RELATION"
        if "LOOKALIKE" in subtype or "lookalike" in notes.lower():
            return "LEXEME_ONLY"
        if "SHORT_ATOM_NONE" in subtype or "HARD_NONE" in subtype:
            if any("domain" in m for m in missing) or "CATEGORY" in subtype:
                return "CATEGORY_MENTION_ONLY"
            return "LEXEME_ONLY"
        if word_count(text) >= 5:
            return "LEXEME_PLUS_CONTEXT"
        return "LEXEME_ONLY"

    if label == "UNCERTAIN":
        return "LEXEME_PLUS_CONTEXT"
    return "OTHER"


def architecture_semantic_comparison() -> dict[str, Any]:
    return {
        "A_current_NO_vs_POSSIBLE": {
            "additional_supervision": "none (current gold)",
            "addresses": "binary Stage-A entry",
            "implementation_complexity": "already implemented",
            "risk_of_shortcut": "high on SHORT_ATOM lexical membership",
            "v1r1_labels_support": True,
            "what_error_addresses": (
                "status quo; observed SHORT_ATOM NONE/PRESENT collapse under this target"
            ),
        },
        "B_assertion_gate": {
            "additional_supervision": (
                "SEMANTIC_ASSERTION_PRESENT vs NO_SEMANTIC_ASSERTION "
                "(not currently labeled on SHORT_ATOM NONE/PRESENT)"
            ),
            "addresses": "lexeme membership vs asserted evidence",
            "implementation_complexity": "medium (new Gate1 target + remap)",
            "risk_of_shortcut": "medium if assertion label collapses to length",
            "v1r1_labels_support": (
                "partial: required_evidence_present / missing_required_semantics "
                "exist but are not a trained assertion target"
            ),
            "what_error_addresses": (
                "SHORT_ATOM FALSE_POSSIBLE where domain lexemes enter without assertion"
            ),
        },
        "C_domain_then_relation": {
            "additional_supervision": (
                "DOMAIN_RELEVANT vs IRRELEVANT + EVIDENCE_RELATION vs NONE"
            ),
            "addresses": "separates domain membership from evidence relation",
            "implementation_complexity": "high (two supervised stages)",
            "risk_of_shortcut": "medium; domain head may absorb family leakage",
            "v1r1_labels_support": (
                "partial: topic_domain + missing_required_semantics / pair contrasts"
            ),
            "what_error_addresses": (
                "wiktionary/domain SHORT_ATOM NONE treated as POSSIBLE"
            ),
        },
        "D_factorized_evidence_core": {
            "additional_supervision": (
                "independent heads: domain relevance, assertion/relation, uncertainty"
            ),
            "addresses": "factorizes the hidden intermediate concepts Gate1 currently blends",
            "implementation_complexity": "high (multi-head + deterministic glue)",
            "risk_of_shortcut": (
                "lower if factors are supervised; higher if factors are unsupervised proxies"
            ),
            "v1r1_labels_support": (
                "partial: can derive weak factors from subtype/missing_semantics/"
                "required_evidence_present but not full factor gold"
            ),
            "what_error_addresses": (
                "semantic-target mismatch: one binary head asked to do three jobs"
            ),
        },
    }


def decide_primary_diagnosis(payload: Mapping[str, Any]) -> dict[str, Any]:
    probes = payload.get("probe_results") or {}
    rep_state = str(payload.get("representation_state") or "")
    lexical = payload.get("lexical_association") or {}
    semantic = payload.get("semantic_core") or {}
    threshold = payload.get("threshold_impossibility") or {}
    coverage_signal = bool(payload.get("data_coverage_dominant", False))

    a_ba = float((probes.get("A_existing_head") or {}).get("short_atom_ba") or 0.0)
    b_ba = float((probes.get("B_logistic") or {}).get("short_atom_ba") or 0.0)
    c_ba = float((probes.get("C_nonlinear") or {}).get("short_atom_ba") or 0.0)
    b_beats_a = (b_ba - a_ba) >= 0.05
    c_beats_b = (c_ba - b_ba) >= 0.05
    neither_separates = max(b_ba, c_ba) < 0.60

    fp_high = float(lexical.get("false_possible_high_assoc_fraction") or 0.0)
    tn_high = float(lexical.get("true_none_high_assoc_fraction") or 0.0)
    lexical_signal = fp_high >= 0.55 and (fp_high - tn_high) >= 0.15

    sem_counts = dict((semantic.get("short_atom_counts") or {}))
    lexeme_only = int(sem_counts.get("LEXEME_ONLY") or 0)
    explicit = int(sem_counts.get("EXPLICIT_EVIDENCE_CORE") or 0)
    relation = int(sem_counts.get("LEXEME_PLUS_RELATION") or 0)
    semantic_mismatch = (
        lexeme_only + relation >= 0.5 * max(1, sum(sem_counts.values()))
        and explicit > 0
    )

    class_tag = str(threshold.get("class") or "")
    reasons = []

    if b_beats_a and not c_beats_b and not neither_separates:
        diagnosis = "GATE1_HEAD_OPTIMIZATION_FAILURE"
        reasons.append("fresh logistic probe substantially beats existing Gate1 head")
    elif c_beats_b:
        diagnosis = "GATE1_NONLINEAR_BOUNDARY_FAILURE"
        reasons.append("nonlinear probe substantially beats linear probe")
    elif rep_state == "SHORT_ATOM_REPRESENTATION_COLLAPSED" and neither_separates:
        diagnosis = "GATE1_REPRESENTATION_FAILURE"
        reasons.append("SHORT_ATOM embeddings collapsed and probes cannot separate")
    elif coverage_signal and not semantic_mismatch:
        diagnosis = "GATE1_DATA_COVERAGE_FAILURE"
        reasons.append("coverage/cohort gaps dominate without semantic-target evidence")
    elif (lexical_signal or semantic_mismatch) and class_tag in {
        "STRUCTURAL_CLASS_OVERLAP",
        "OPERATING_POINT_CONFLICT",
    }:
        diagnosis = "GATE1_SEMANTIC_TARGET_MISMATCH"
        reasons.append(
            "SHORT_ATOM NONE vs PRESENT is largely lexeme/domain membership vs "
            "asserted evidence; binary NO_EVIDENCE/POSSIBLE hides that intermediate"
        )
        if lexical_signal:
            reasons.append(
                f"FALSE_POSSIBLE high-assoc token fraction={fp_high:.3f} vs "
                f"TRUE_NONE={tn_high:.3f}"
            )
        if semantic_mismatch:
            reasons.append(
                f"semantic-core mass LEXEME_ONLY+RELATION={lexeme_only + relation} "
                f"with EXPLICIT_EVIDENCE_CORE={explicit}"
            )
        if neither_separates:
            reasons.append("linear/nonlinear probes fail to separate SHORT_ATOM Gate1")
        if rep_state != "SHORT_ATOM_REPRESENTATION_COLLAPSED":
            reasons.append(
                f"representation state={rep_state} (not fully collapsed; target mismatch)"
            )
    elif neither_separates and lexical_signal:
        diagnosis = "GATE1_SEMANTIC_TARGET_MISMATCH"
        reasons.append("probes cannot separate; lexical association explains FALSE_POSSIBLE")
    else:
        diagnosis = "MIXED_GATE1_FAILURE"
        reasons.append("multiple Gate1 failure modes without a single dominant cause")

    if diagnosis not in PRIMARY_DIAGNOSES:
        raise ValueError(f"invalid_primary_diagnosis:{diagnosis}")
    return {
        "probe_deltas": {
            "B_minus_A_short_atom_ba": b_ba - a_ba,
            "C_minus_B_short_atom_ba": c_ba - b_ba,
            "max_probe_short_atom_ba": max(b_ba, c_ba),
        },
        "primary_diagnosis": diagnosis,
        "reasons": reasons,
        "representation_state": rep_state,
    }


def decide_next_action(primary_diagnosis: str) -> str:
    mapping = {
        "GATE1_HEAD_OPTIMIZATION_FAILURE": "GATE1_ARCHITECTURE_REDESIGN",
        "GATE1_NONLINEAR_BOUNDARY_FAILURE": "GATE1_ARCHITECTURE_REDESIGN",
        "GATE1_REPRESENTATION_FAILURE": "GATE1_ARCHITECTURE_REDESIGN",
        "GATE1_SEMANTIC_TARGET_MISMATCH": "STAGE_A_SEMANTIC_DECOMPOSITION",
        "GATE1_DATA_COVERAGE_FAILURE": "NEW_STAGE_A_SURFACE",
        "MIXED_GATE1_FAILURE": "STAGE_A_SEMANTIC_DECOMPOSITION",
    }
    action = mapping[primary_diagnosis]
    if action not in NEXT_ACTIONS:
        raise ValueError(action)
    return action


def justified_changes(primary_diagnosis: str) -> dict[str, bool]:
    return {
        "architecture_change_justified": primary_diagnosis
        in {
            "GATE1_HEAD_OPTIMIZATION_FAILURE",
            "GATE1_NONLINEAR_BOUNDARY_FAILURE",
            "GATE1_REPRESENTATION_FAILURE",
        },
        "dataset_change_justified": primary_diagnosis == "GATE1_DATA_COVERAGE_FAILURE",
        "objective_change_justified": primary_diagnosis
        in {
            "GATE1_SEMANTIC_TARGET_MISMATCH",
            "MIXED_GATE1_FAILURE",
        },
        "semantic_decomposition_justified": primary_diagnosis
        in {
            "GATE1_SEMANTIC_TARGET_MISMATCH",
            "MIXED_GATE1_FAILURE",
        },
    }


def assemble_diagnosis_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    primary = payload["primary"]
    next_action = payload["next_action"]
    justified = justified_changes(primary["primary_diagnosis"])
    receipt = {
        "DIAGNOSE_RULE": DIAGNOSE_RULE,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "FAILED_CHECKPOINT_SHA256": FAILED_CHECKPOINT_SHA256,
        "FAILED_RUN_RECEIPT_SHA256": FAILED_RUN_RECEIPT_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "PARENT_STAGE_A_BEST": PARENT_STAGE_A_BEST_SHA,
        "SCIENTIFIC_DISPOSITION_PARENT": "SETTLED_FAIL",
        "SPENT_RESERVE": SPENT_RESERVE,
        "SPENT_RESERVE_OVERLAP": SPENT_RESERVE_OVERLAP,
        "SPENT_RESERVE_STATUS": SPENT_RESERVE_STATUS,
        "STAGE_A_BEST_MUTATED": False,
        "TRAIN": False,
        "V1R1_MUTATED": False,
        "V1R2_CREATED": False,
        "architecture_semantic_comparison": architecture_semantic_comparison(),
        "authorized_auth_receipt_sha256": AUTHORIZED_AUTH_RECEIPT_SHA256,
        "authorized_dataset_sha256": AUTHORIZED_DATASET_SHA,
        "authorized_readiness_sha256": AUTHORIZED_READINESS_SHA,
        "authorized_surface_receipt_sha256": AUTHORIZED_SURFACE_RECEIPT_SHA,
        "authorized_training_config_sha256": AUTHORIZED_TRAINING_CONFIG_SHA256,
        "frozen_observed_outcome": dict(FROZEN_OBSERVED_OUTCOME),
        "justified": justified,
        "next_action": next_action,
        "primary_diagnosis": primary["primary_diagnosis"],
        "primary_reasons": list(primary["reasons"]),
        "read_only": True,
        "schema": (
            "hyperlex.classification.v5."
            "stage_a_generalization_retrain_diagnose.v1"
        ),
        "sections": {
            "gate1_error_decomposition": payload.get("gate1_error_decomposition"),
            "lexical_association": payload.get("lexical_association"),
            "old_vs_new_stage_a": payload.get("old_vs_new_stage_a"),
            "probe_results": payload.get("probe_results"),
            "provenance_controlled": payload.get("provenance_controlled"),
            "representation_separability": payload.get("representation_separability"),
            "semantic_core": payload.get("semantic_core"),
            "short_atom_distributions": payload.get("short_atom_distributions"),
            "threshold_impossibility": payload.get("threshold_impossibility"),
            "wiktionary_source_effect": payload.get("wiktionary_source_effect"),
        },
    }
    receipt["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in receipt.items() if k != "receipt_sha256"})
    )
    return receipt
