"""HYPERLEX_V5_PROMOTION_RESERVE_001 — seal + one-shot score contracts.

Builds a fresh disjoint promotion reserve and scores it exactly once under the
frozen Stage-A two-stage + Stage-B retrieval pipeline. Does not train, rebuild
the Stage-B index, retune floors, or mutate BEST / STAGE_A_BEST.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any, Mapping, Sequence

from .classification_v2 import ACTIVE_FAMILY_VOCABULARY
from .classification_v5_stage_a_gold_label_mapping import (
    NONE_SUBTYPES,
    POSITIVE_SUBTYPE,
    SUBTYPE_TO_GOLD,
    UNCERTAIN_SUBTYPE,
)
from .classification_v5_stage_a_two_stage_promote import (
    CANONICAL_GATE1_THRESHOLD,
    CANONICAL_GATE2_THRESHOLD,
    MODEL_WIDE_BEST_SHA256,
    STAGE_A_BEST_SHA256,
)
from .classification_v5_stage_b import (
    FAMILY_EMISSION_PRECISION_MIN_AFTER_GATE,
    FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX,
    compose_end_to_end,
    may_invoke_stage_b,
)

GATE1_THRESHOLD = CANONICAL_GATE1_THRESHOLD
GATE2_THRESHOLD = CANONICAL_GATE2_THRESHOLD
from .holdout_guard import normalized_text_sha256

RESERVE_ID = "HYPERLEX_V5_PROMOTION_RESERVE_001"
RESERVE_RULE = "HYPERLEX_V5_PROMOTION_RESERVE_SEAL_SCORE_V1"
SCHEMA_SEAL = "hyperlex.classification.v5.promotion_reserve_seal.v1"
SCHEMA_SCORE = "hyperlex.classification.v5.promotion_reserve_score.v1"
AUTHORIZED_SURFACE_RULE = "HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1R9"
AUTHORIZED_DATASET_SHA = (
    "8d4be8301b89b191841342fe11ef647c838b32e56e6d133b610c232264c5d00a"
)
STAGE_B_INDEX_SHA256 = (
    "3fd6c87a5825f3f2a25a81f1a769a77aa69e03ddca5b370f9247672d93aaee21"
)
MINIMUM_FAMILY_SCORE = 0.64
MINIMUM_FAMILY_MARGIN = 0.07

# Preregistered before acquisition. Do not lower after fetch starts.
RESERVE_FLOORS = {
    "min_total": 200,
    "prefer_total": 250,
    "min_no_evidence": 60,
    "min_evidence_present": 120,
    "min_uncertain": 20,
    "min_ordinary_domain_none": 20,
    "min_hard_none": 10,
    "min_near_domain_none": 10,
    "min_distinct_present_families": 12,
    "max_single_family_share_of_present": 0.25,
    "min_observed_overall_share": 0.50,
    "min_observed_none_share": 0.50,
    "min_observed_present_share": 0.40,
}

REQUIRED_NONE_SUBTYPES_NONEMPTY = frozenset(
    {
        "GENERIC_NONE",
        "LEXICAL_LOOKALIKE_NONE",
        "SHORT_ATOM_NONE",
    }
)

INDEXED_SURFACE_FAMILIES: tuple[str, ...] = (
    "betting-sharp",
    "conflict-aggression",
    "crypto-degen",
    "fashion-aesthetic",
    "gaming-meta",
    "identity-affiliation",
    "internet-slang",
    "memetic",
    "music-entertainment",
    "politics-civic",
    "regional-cultural",
    "relationship-dating",
    "social-evaluation",
    "spiritual-mystic",
    "sports-competition",
    "technology-ai",
    "workplace-career",
)


def canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def reserve_contract() -> dict[str, Any]:
    return {
        "BEST": "UNCHANGED",
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "authorized_surface_rule": AUTHORIZED_SURFACE_RULE,
        "authorized_surface_sha256": AUTHORIZED_DATASET_SHA,
        "floors": dict(RESERVE_FLOORS),
        "frozen_thresholds": {
            "gate1_threshold": GATE1_THRESHOLD,
            "gate2_threshold": GATE2_THRESHOLD,
            "minimum_family_score": MINIMUM_FAMILY_SCORE,
            "minimum_family_margin": MINIMUM_FAMILY_MARGIN,
        },
        "indexed_surface_families": list(INDEXED_SURFACE_FAMILIES),
        "primary_gate_max": FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX,
        "recalibrate": False,
        "rebuild_index": False,
        "reserve_id": RESERVE_ID,
        "rule": RESERVE_RULE,
        "secondary_gate_min": FAMILY_EMISSION_PRECISION_MIN_AFTER_GATE,
        "stage_b_index_sha256": STAGE_B_INDEX_SHA256,
        "train": False,
    }


def _gold_family(row: Mapping[str, Any]) -> str | None:
    if str(row.get("evidence_subtype")) != POSITIVE_SUBTYPE:
        return None
    families = list(row.get("candidate_families") or [])
    if not families:
        raise ValueError("present_without_family")
    family = str(families[0])
    if family not in ACTIVE_FAMILY_VOCABULARY:
        raise ValueError(f"present_family_not_active:{family}")
    return family


def normalize_reserve_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Freeze a reserve row under the existing V5 gold-label mapping."""
    text = str(row["text"]).strip()
    if not text:
        raise ValueError("empty_reserve_text")
    subtype = str(row["evidence_subtype"])
    if subtype not in SUBTYPE_TO_GOLD:
        raise ValueError(f"subtype_unknown:{subtype}")
    evidence_label = SUBTYPE_TO_GOLD[subtype]
    if row.get("evidence_label") not in (None, evidence_label):
        raise ValueError("evidence_label_mismatch")
    provenance = str(row.get("provenance") or row.get("class") or "")
    if provenance not in {"OBSERVED", "INFERRED"}:
        raise ValueError(f"provenance_invalid:{provenance}")
    identity = str(row.get("identity") or normalized_text_sha256(text))
    if identity != normalized_text_sha256(text):
        raise ValueError("identity_text_mismatch")
    family = _gold_family({**row, "evidence_subtype": subtype}) if subtype == POSITIVE_SUBTYPE else None
    if subtype == POSITIVE_SUBTYPE and family is None:
        raise ValueError("present_family_required")
    if subtype == UNCERTAIN_SUBTYPE and not row.get("ambiguity_reason"):
        raise ValueError("uncertain_without_ambiguity_reason")
    out = {
        "active_family_support": [family] if family else list(row.get("active_family_support") or []),
        "ambiguity_reason": row.get("ambiguity_reason"),
        "candidate_families": [family] if family else list(row.get("candidate_families") or []),
        "evidence_label": evidence_label,
        "evidence_spans": list(row.get("evidence_spans") or []),
        "evidence_subtype": subtype,
        "evaluation_spent": False,
        "gold_decision_type": (
            "FAMILY"
            if evidence_label == "EVIDENCE_PRESENT"
            else ("ABSTAIN" if evidence_label == "UNCERTAIN" else "NONE")
        ),
        "gold_family": family,
        "identity": identity,
        "label_authority": row.get("label_authority") or "HUMAN_SETTLED",
        "label_derivation": row.get("label_derivation") or "semantic_source_evidence",
        "missing_required_semantics": list(row.get("missing_required_semantics") or []),
        "notes": row.get("notes"),
        "parent_identity": row.get("parent_identity"),
        "positive_evidence_spans": list(row.get("positive_evidence_spans") or []),
        "provenance": provenance,
        "required_evidence_present": bool(
            row.get("required_evidence_present", evidence_label == "EVIDENCE_PRESENT")
        ),
        "reserve_id": RESERVE_ID,
        "revision_id": row.get("revision_id"),
        "rights": row.get("rights"),
        "source_sha256": str(row.get("source_sha256") or hashlib.sha256(text.encode("utf-8")).hexdigest()),
        "source_url": row.get("source_url"),
        "split": "promotion_reserve",
        "text": text,
        "topic_domain": row.get("topic_domain"),
    }
    return out


def audit_reserve_composition(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    labels = Counter(str(row["evidence_label"]) for row in rows)
    subtypes = Counter(str(row["evidence_subtype"]) for row in rows)
    provenances = Counter(str(row["provenance"]) for row in rows)
    present = [row for row in rows if row["evidence_label"] == "EVIDENCE_PRESENT"]
    none_rows = [row for row in rows if row["evidence_label"] == "NO_EVIDENCE"]
    uncertain = [row for row in rows if row["evidence_label"] == "UNCERTAIN"]

    def _present_family(row: Mapping[str, Any]) -> str | None:
        if row.get("gold_family"):
            return str(row["gold_family"])
        families = list(row.get("candidate_families") or [])
        return str(families[0]) if families else None

    family_counts = Counter(
        family
        for family in (_present_family(row) for row in present)
        if family
    )
    max_share = 0.0
    dominant = None
    if present and family_counts:
        dominant, top = max(family_counts.items(), key=lambda item: (item[1], item[0]))
        max_share = top / len(present)

    def _obs_share(bucket: Sequence[Mapping[str, Any]]) -> float | None:
        if not bucket:
            return None
        return sum(1 for row in bucket if row.get("provenance") == "OBSERVED") / len(bucket)

    observed_overall = _obs_share(rows)
    observed_none = _obs_share(none_rows)
    observed_present = _obs_share(present)
    reasons: list[str] = []
    floors = RESERVE_FLOORS
    if len(rows) < floors["min_total"]:
        reasons.append(f"min_total:{len(rows)}<{floors['min_total']}")
    if labels.get("NO_EVIDENCE", 0) < floors["min_no_evidence"]:
        reasons.append(f"min_no_evidence:{labels.get('NO_EVIDENCE', 0)}")
    if labels.get("EVIDENCE_PRESENT", 0) < floors["min_evidence_present"]:
        reasons.append(f"min_evidence_present:{labels.get('EVIDENCE_PRESENT', 0)}")
    if labels.get("UNCERTAIN", 0) < floors["min_uncertain"]:
        reasons.append(f"min_uncertain:{labels.get('UNCERTAIN', 0)}")
    if subtypes.get("ORDINARY_DOMAIN_NONE", 0) < floors["min_ordinary_domain_none"]:
        reasons.append("min_ordinary_domain_none")
    if subtypes.get("HARD_NONE", 0) < floors["min_hard_none"]:
        reasons.append("min_hard_none")
    if subtypes.get("NEAR_DOMAIN_NONE", 0) < floors["min_near_domain_none"]:
        reasons.append("min_near_domain_none")
    for subtype in REQUIRED_NONE_SUBTYPES_NONEMPTY:
        if subtypes.get(subtype, 0) < 1:
            reasons.append(f"none_subtype_missing:{subtype}")
    if len(family_counts) < floors["min_distinct_present_families"]:
        reasons.append(
            f"min_distinct_present_families:{len(family_counts)}"
            f"<{floors['min_distinct_present_families']}"
        )
    if max_share > floors["max_single_family_share_of_present"] + 1e-12:
        reasons.append(
            f"max_single_family_share_of_present:{max_share:.4f}:{dominant}"
        )
    if observed_overall is None or observed_overall + 1e-12 < floors["min_observed_overall_share"]:
        reasons.append(f"observed_overall:{observed_overall}")
    if observed_none is None or observed_none + 1e-12 < floors["min_observed_none_share"]:
        reasons.append(f"observed_none:{observed_none}")
    if observed_present is None or observed_present + 1e-12 < floors["min_observed_present_share"]:
        reasons.append(f"observed_present:{observed_present}")
    for row in rows:
        if row.get("label_derivation") in {
            "model_probability",
            "threshold_outcome",
            "retrieval_score",
            "nearest_neighbor_score",
            "prototype_score",
            "reserve_behavior",
            "jev",
        }:
            reasons.append(f"forbidden_label_derivation:{row['identity']}")
            break
    return {
        "composition_pass": not reasons,
        "dominant_family": dominant,
        "evidence_label_counts": dict(sorted(labels.items())),
        "evidence_subtype_counts": dict(sorted(subtypes.items())),
        "family_counts": dict(sorted(family_counts.items())),
        "max_single_family_share_of_present": max_share,
        "n": len(rows),
        "n_distinct_present_families": len(family_counts),
        "n_no_evidence": len(none_rows),
        "n_present": len(present),
        "n_uncertain": len(uncertain),
        "observed_none_share": observed_none,
        "observed_overall_share": observed_overall,
        "observed_present_share": observed_present,
        "provenance_counts": dict(sorted(provenances.items())),
        "reasons": reasons,
    }


def collect_row_digests(row: Mapping[str, Any]) -> set[str]:
    digests: set[str] = set()
    for key in (
        "identity",
        "normalized_text_sha256",
        "parent_identity",
        "source_sha256",
        "source_identity",
        "paired_positive_identity",
    ):
        value = row.get(key)
        if isinstance(value, str) and len(value) == 64:
            digests.add(value)
    text = row.get("text")
    if isinstance(text, str) and text.strip():
        digests.add(normalized_text_sha256(text))
        digests.add(hashlib.sha256(text.encode("utf-8")).hexdigest())
    return digests


def audit_reserve_disjointness(
    rows: Sequence[Mapping[str, Any]],
    *,
    blocked: Mapping[str, str],
) -> dict[str, Any]:
    reasons: list[str] = []
    identities = [str(row["identity"]) for row in rows]
    if len(identities) != len(set(identities)):
        reasons.append("duplicate_reserve_identities")
    overlaps: Counter[str] = Counter()
    near_dup = 0
    for row in rows:
        for digest in collect_row_digests(row):
            reason = blocked.get(digest)
            if reason:
                overlaps[reason] += 1
        component = row.get("near_duplicate_component")
        if component is not None and str(component) in blocked:
            near_dup += 1
            overlaps["near_duplicate_component"] += 1
    for reason, count in sorted(overlaps.items()):
        reasons.append(f"overlap:{reason}:{count}")
    if not rows:
        reasons.append("empty_reserve")
    return {
        "disjoint_pass": not reasons,
        "identity_overlap": int(overlaps.get("identity", 0)),
        "n_blocked_hits": int(sum(overlaps.values())),
        "near_duplicate_overlap": near_dup,
        "overlap_by_reason": dict(sorted(overlaps.items())),
        "parent_lineage_overlap": int(
            overlaps.get("parent_identity", 0)
            + overlaps.get("derived_lineage", 0)
        ),
        "reasons": reasons,
        "source_hash_overlap": int(overlaps.get("source_sha256", 0)),
    }


def seal_reserve(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    normalized = [normalize_reserve_row(row) for row in rows]
    composition = audit_reserve_composition(normalized)
    if not composition["composition_pass"]:
        raise ValueError(f"composition_fail:{composition['reasons']}")
    ordered = sorted(normalized, key=lambda item: item["identity"])
    identities = [row["identity"] for row in ordered]
    body = "\n".join(canonical_json(row) for row in ordered) + ("\n" if ordered else "")
    rows_sha = sha256_text(body)
    identity_list_sha = sha256_text("\n".join(identities) + ("\n" if identities else ""))
    identity_witness = {
        "identities": identities,
        "n": len(identities),
        "reserve_id": RESERVE_ID,
        "schema": "hyperlex.classification.v5.promotion_reserve_identity_witness.v1",
    }
    identity_witness["witness_sha256"] = sha256_text(
        canonical_json({k: v for k, v in identity_witness.items() if k != "witness_sha256"})
    )
    provenance_witness = {
        "composition": composition,
        "provenance_counts": composition["provenance_counts"],
        "reserve_id": RESERVE_ID,
        "schema": "hyperlex.classification.v5.promotion_reserve_label_provenance_witness.v1",
    }
    provenance_witness["witness_sha256"] = sha256_text(
        canonical_json(
            {k: v for k, v in provenance_witness.items() if k != "witness_sha256"}
        )
    )
    manifest = {
        "BEST": "UNCHANGED",
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "composition": composition,
        "contract": reserve_contract(),
        "identity_list_sha256": identity_list_sha,
        "n": len(ordered),
        "reserve_id": RESERVE_ID,
        "rows_sha256": rows_sha,
        "rule": RESERVE_RULE,
        "schema": "hyperlex.classification.v5.promotion_reserve_manifest.v1",
        "stage_b_index_sha256": STAGE_B_INDEX_SHA256,
        "train": False,
    }
    manifest["manifest_sha256"] = sha256_text(
        canonical_json({k: v for k, v in manifest.items() if k != "manifest_sha256"})
    )
    seal = {
        "BEST": "UNCHANGED",
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "identity_list_sha256": identity_list_sha,
        "identity_witness_sha256": identity_witness["witness_sha256"],
        "immutable": True,
        "label_provenance_witness_sha256": provenance_witness["witness_sha256"],
        "manifest_sha256": manifest["manifest_sha256"],
        "reserve_id": RESERVE_ID,
        "rows_sha256": rows_sha,
        "rule": RESERVE_RULE,
        "schema": SCHEMA_SEAL,
        "stage_b_index_sha256": STAGE_B_INDEX_SHA256,
        "train": False,
    }
    seal["seal_sha256"] = sha256_text(
        canonical_json({k: v for k, v in seal.items() if k != "seal_sha256"})
    )
    return {
        "body": body,
        "identities": identities,
        "identity_witness": identity_witness,
        "manifest": manifest,
        "provenance_witness": provenance_witness,
        "rows": ordered,
        "seal": seal,
    }


def classify_wrong_family_emission(
    *,
    gold_evidence_label: str,
    gold_family: str | None,
    predicted_family: str | None,
) -> str:
    if gold_evidence_label == "NO_EVIDENCE":
        return "STAGE_A_FALSE_ENTRY"
    if gold_evidence_label == "UNCERTAIN":
        return "STAGE_A_AND_B_COMPOUND"
    if gold_evidence_label == "EVIDENCE_PRESENT" and gold_family != predicted_family:
        return "STAGE_B_WRONG_FAMILY"
    return "STAGE_A_AND_B_COMPOUND"


def score_reserve_rows(
    score_rows: Sequence[Mapping[str, Any]],
    *,
    family_score_min: float = MINIMUM_FAMILY_SCORE,
    family_margin_min: float = MINIMUM_FAMILY_MARGIN,
) -> dict[str, Any]:
    """One-shot end-to-end score under frozen Stage-A/B floors."""
    if abs(family_score_min - MINIMUM_FAMILY_SCORE) > 1e-12:
        raise ValueError("family_score_floor_mutated")
    if abs(family_margin_min - MINIMUM_FAMILY_MARGIN) > 1e-12:
        raise ValueError("family_margin_floor_mutated")

    decisions = []
    wrong_emissions = []
    stage_a_counts = Counter()
    e2e_counts = Counter()
    present_tp = present_fn = 0
    none_tp = none_fn = 0
    uncertain_tp = uncertain_fn = 0
    family_gold = 0
    family_top1 = 0
    family_top2 = 0
    family_correct_emit = 0
    family_emit = 0

    for row in score_rows:
        evidence_decision = str(row["evidence_decision"])
        stage_a_counts[evidence_decision] += 1
        candidates = None
        if may_invoke_stage_b(evidence_decision):
            candidates = [
                {"family": row["top1_family"], "score": row["top1_score"]},
                {"family": row["top2_family"], "score": row["top2_score"]},
            ]
            if row.get("top3_family") is not None:
                candidates.append(
                    {"family": row["top3_family"], "score": row["top3_score"]}
                )
        decided = compose_end_to_end(
            evidence_decision=evidence_decision,
            ranked_candidates=candidates,
            family_score_min=family_score_min,
            family_margin_min=family_margin_min,
        )
        decisions.append(decided)
        e2e_counts[str(decided["decision_type"])] += 1

        gold_label = str(row["evidence_label"])
        gold_family = row.get("gold_family")
        if gold_label == "EVIDENCE_PRESENT":
            family_gold += 1
            present_tp += int(evidence_decision == "EVIDENCE_PRESENT")
            present_fn += int(evidence_decision != "EVIDENCE_PRESENT")
            if evidence_decision == "EVIDENCE_PRESENT":
                if row.get("top1_family") == gold_family:
                    family_top1 += 1
                if gold_family in {row.get("top1_family"), row.get("top2_family")}:
                    family_top2 += 1
        elif gold_label == "NO_EVIDENCE":
            none_tp += int(evidence_decision == "NO_EVIDENCE")
            none_fn += int(evidence_decision != "NO_EVIDENCE")
        elif gold_label == "UNCERTAIN":
            uncertain_tp += int(evidence_decision == "UNCERTAIN")
            uncertain_fn += int(evidence_decision != "UNCERTAIN")

        if decided["decision_type"] == "FAMILY":
            family_emit += 1
            if decided.get("family") == gold_family:
                family_correct_emit += 1
            else:
                margin = None
                if row.get("top1_score") is not None and row.get("top2_score") is not None:
                    margin = float(row["top1_score"]) - float(row["top2_score"])
                wrong_emissions.append(
                    {
                        "classification": classify_wrong_family_emission(
                            gold_evidence_label=gold_label,
                            gold_family=gold_family if isinstance(gold_family, str) else None,
                            predicted_family=str(decided.get("family") or "") or None,
                        ),
                        "family_score": row.get("top1_score"),
                        "gold_family": gold_family,
                        "gold_stage_a_label": gold_label,
                        "identity": row["identity"],
                        "margin": margin,
                        "p_confirmed": row.get("p_confirmed"),
                        "p_possible": row.get("p_possible"),
                        "runner_up_family": row.get("top2_family"),
                        "runner_up_score": row.get("top2_score"),
                        "stage_a_decision": evidence_decision,
                        "stage_b_predicted_family": decided.get("family"),
                    }
                )

    none_gold = sum(1 for row in score_rows if row["evidence_label"] == "NO_EVIDENCE")
    false_entry = 0.0
    if none_gold:
        false_entry = (
            sum(
                1
                for row in score_rows
                if row["evidence_label"] == "NO_EVIDENCE"
                and row["evidence_decision"] == "EVIDENCE_PRESENT"
            )
            / none_gold
        )
    family_precision = None if family_emit == 0 else family_correct_emit / family_emit
    family_coverage = None if family_gold == 0 else family_emit / family_gold
    family_recall = None if family_gold == 0 else family_correct_emit / family_gold
    primary_pass = false_entry <= FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX + 1e-12
    secondary_pass = (
        primary_pass
        and family_precision is not None
        and family_precision + 1e-12 >= FAMILY_EMISSION_PRECISION_MIN_AFTER_GATE
    )
    if primary_pass and secondary_pass:
        settlement = "RESERVE_PASS"
    else:
        settlement = "RESERVE_FAIL"
    wrong_breakdown = Counter(item["classification"] for item in wrong_emissions)
    return {
        "decision_counts": dict(sorted(e2e_counts.items())),
        "false_evidence_entry_rate_on_none": false_entry,
        "family_emission_coverage": family_coverage,
        "family_emission_precision": family_precision,
        "family_emission_recall": family_recall,
        "family_top1_accuracy": None if family_gold == 0 else family_top1 / family_gold,
        "family_top2_accuracy": None if family_gold == 0 else family_top2 / family_gold,
        "n": len(score_rows),
        "n_family_emitted": family_emit,
        "none_recall": None if none_gold == 0 else none_tp / none_gold,
        "present_recall": None
        if family_gold == 0
        else present_tp / family_gold,
        "primary_gate_max": FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX,
        "primary_gate_pass": primary_pass,
        "secondary_gate_min": FAMILY_EMISSION_PRECISION_MIN_AFTER_GATE,
        "secondary_gate_pass": secondary_pass,
        "settlement": settlement,
        "stage_a_decision_counts": dict(sorted(stage_a_counts.items())),
        "uncertain_recall": None
        if sum(1 for row in score_rows if row["evidence_label"] == "UNCERTAIN") == 0
        else uncertain_tp
        / sum(1 for row in score_rows if row["evidence_label"] == "UNCERTAIN"),
        "wrong_emission_breakdown": dict(sorted(wrong_breakdown.items())),
        "wrong_emissions": wrong_emissions,
    }


def decide_settlement(
    *,
    composition: Mapping[str, Any],
    disjointness: Mapping[str, Any],
    metrics: Mapping[str, Any] | None,
    execution_error: str | None = None,
) -> str:
    if execution_error:
        return "RESERVE_INVALID"
    if not composition.get("composition_pass") or not disjointness.get("disjoint_pass"):
        return "RESERVE_INVALID"
    if metrics is None:
        return "RESERVE_INVALID"
    return str(metrics.get("settlement") or "RESERVE_INVALID")


def mark_evaluation_spent(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [{**dict(row), "evaluation_spent": True} for row in rows]


def assemble_score_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    receipt = {
        "BEST": "UNCHANGED",
        "BEST_MUTATED": False,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "STAGE_A_BEST_MUTATED": False,
        "composition": payload["composition"],
        "contract": reserve_contract(),
        "disjointness": payload["disjointness"],
        "evaluation_spent": True,
        "frozen_thresholds": {
            "gate1_threshold": GATE1_THRESHOLD,
            "gate2_threshold": GATE2_THRESHOLD,
            "minimum_family_score": MINIMUM_FAMILY_SCORE,
            "minimum_family_margin": MINIMUM_FAMILY_MARGIN,
        },
        "metrics": payload["metrics"],
        "next_action": payload["next_action"],
        "reserve_id": RESERVE_ID,
        "reserve_hashes": payload["reserve_hashes"],
        "rule": RESERVE_RULE,
        "schema": SCHEMA_SCORE,
        "settlement": payload["settlement"],
        "stage_b_index_sha256": STAGE_B_INDEX_SHA256,
        "train": False,
    }
    receipt["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in receipt.items() if k != "receipt_sha256"})
    )
    return receipt


def next_action_for_settlement(settlement: str) -> str:
    if settlement == "RESERVE_PASS":
        return (
            "PRODUCTION_PROMOTION_ELIGIBLE — both frozen promotion gates passed; "
            "do not promote automatically; await a separate production-promotion action; "
            "reserve identities remain evaluation_spent=true."
        )
    if settlement == "RESERVE_FAIL":
        return (
            "PRESERVE_RESERVE_FAIL — do not retune against the spent reserve; "
            "do not rebuild index; do not move BEST / STAGE_A_BEST; diagnose offline."
        )
    return (
        "RESERVE_INVALID — fix execution/contamination/provenance/seal/contract "
        "failure before any further score; do not promote."
    )
