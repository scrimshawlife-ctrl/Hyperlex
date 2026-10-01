"""QUALIFY_HYPERLEX_V5_PIPELINE_ON_FRESH_EVALUATION_SURFACE — phase contracts.

Fresh-surface qualification of the sealed V5 Stage-A/B V1R2 package.
Does not train, retune thresholds, rebuild Stage-B index, mutate V1R2,
score spent reserves as qualification data, or authorize Hub publish.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .classification_v2 import ACTIVE_FAMILY_VOCABULARY
from .classification_v5_seal_and_package import (
    ALIGNMENT_RECEIPT_SHA256_PIN,
    N_INDEX_RECORDS_PIN,
    PACKAGING_ID,
    PIPELINE_LIMITATIONS,
    package_contract,
)
from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_b_pipeline import PIPELINE_ID
from .classification_v5_stage_a_canonical import (
    CANONICAL_ID,
    MODEL_WIDE_BEST_SHA256,
    STAGE_A_BEST_SHA256,
    V5_STAGE_A_STATE,
    may_invoke_stage_b,
)
from .classification_v5_stage_a_gold_identifiability_contract import (
    CONTRACT_ID as GOLD_CONTRACT_ID,
    MODEL_INPUT,
    classify_row as classify_identifiability,
    is_short_atom,
)
from .classification_v5_stage_a_gold_identifiability_filter import (
    SURFACE_ID as V1R2_SURFACE_ID,
    V1R2_DATASET_SHA256_PIN,
)
from .classification_v5_stage_a_gold_label_mapping import SUBTYPE_TO_GOLD
from .classification_v5_stage_a_ident_filtered_promote import (
    CANONICAL_RELATION_THRESHOLD,
    CANONICAL_RESOLVABILITY_THRESHOLD,
)
from .classification_v5_stage_b import (
    FROZEN_INDEX_SHA256,
    FROZEN_MINIMUM_FAMILY_SCORE,
    FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
    gold_end_to_end,
)

QUALIFY_RULE = "QUALIFY_HYPERLEX_V5_PIPELINE_ON_FRESH_EVALUATION_SURFACE"
QUALIFICATION_ID = "HYPERLEX_V5_PIPELINE_QUALIFICATION_001"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V5-PIPELINE-QUALIFICATION-001"
SCHEMA_QUAL = "hyperlex.classification.v5.pipeline_qualification.v1"
SCHEMA_SURFACE = "hyperlex.classification.v5.pipeline_qualification_surface.v1"

DEPENDENCY_MANIFEST_SHA256_PIN = (
    "c2d19befb17be2337bc5f4ef97ebaf8ef20ea71ab5dd467830325654088f242a"
)
SEAL_PACKAGE_RECEIPT_SHA256_PIN = (
    "0e468234df919f030ea2f83b2867afd2e2352568df1d12f60bdc41e69e83e049"
)

# Composition floors (qualification support, not training targets).
TOTAL_MIN = 400
TOTAL_PREFERRED = 500
NONE_MIN = 140
PRESENT_MIN = 220
UNCERTAIN_MIN = 40
FAMILY_MIN = 12
FAMILY_PREFERRED = 15
FAMILY_MAX_SHARE = 0.20
SHORT_ATOM_NONE_TARGET = 40
SHORT_ATOM_PRESENT_TARGET = 30
OBSERVED_MIN_SHARE = 0.50
SOURCE_MAX_SHARE = 0.25

# Primary gates — frozen before scoring.
GATE_FALSE_ENTRY_MAX = 0.05
GATE_PRESENT_RECALL_MIN = 0.70
GATE_NONE_RECALL_MIN = 0.90
GATE_FAMILY_PRECISION_MIN = 0.80

NEXT_PASS = "PACKAGE_HYPERLEX_V5_FOR_INTEGRATION_OR_RELEASE"
NEXT_FAIL = "REVIEW_V5_QUALIFICATION_FAILURE_AT_SYSTEM_LEVEL"
NEXT_INVALID = "REPAIR_QUALIFICATION_INTEGRITY_THEN_RETRY"


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def qualification_binding() -> dict[str, Any]:
    return {
        "QUALIFICATION_ID": QUALIFICATION_ID,
        "QUALIFY_RULE": QUALIFY_RULE,
        "pipeline": PIPELINE_ID,
        "package": PACKAGING_ID,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "STAGE_B_INDEX": FROZEN_INDEX_SHA256,
        "STAGE_B_INDEX_N": N_INDEX_RECORDS_PIN,
        "dependency_manifest_sha256": DEPENDENCY_MANIFEST_SHA256_PIN,
        "seal_package_receipt_sha256": SEAL_PACKAGE_RECEIPT_SHA256_PIN,
        "alignment_receipt_sha256": ALIGNMENT_RECEIPT_SHA256_PIN,
        "STAGE_A_CANONICAL": CANONICAL_ID,
        "V5_STAGE_A_STATE": V5_STAGE_A_STATE,
        "blocked_surfaces": [
            "V1R1",
            "V1R2",
            V1R2_SURFACE_ID,
            "all_stage_a_train_val",
            "stage_b_index_identities",
            "spent_reserves",
            "diagnostic_surfaces",
            "measurement_surfaces",
            "generalization_surfaces",
        ],
        "v1r2_dataset_sha256": V1R2_DATASET_SHA256_PIN,
        "gold_identifiability_contract": GOLD_CONTRACT_ID,
        "model_input": list(MODEL_INPUT),
        "thresholds": {
            "relation": CANONICAL_RELATION_THRESHOLD,
            "resolvability": CANONICAL_RESOLVABILITY_THRESHOLD,
        },
        "floors": {
            "minimum_family_score": FROZEN_MINIMUM_FAMILY_SCORE,
            "minimum_top1_top2_margin": FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
        },
        "primary_gates": {
            "false_entry_on_NONE_max": GATE_FALSE_ENTRY_MAX,
            "PRESENT_recall_min": GATE_PRESENT_RECALL_MIN,
            "NONE_recall_min": GATE_NONE_RECALL_MIN,
            "family_emission_precision_min": GATE_FAMILY_PRECISION_MIN,
        },
        "composition_floors": {
            "total_min": TOTAL_MIN,
            "total_preferred": TOTAL_PREFERRED,
            "NO_EVIDENCE_min": NONE_MIN,
            "EVIDENCE_PRESENT_min": PRESENT_MIN,
            "UNCERTAIN_min": UNCERTAIN_MIN,
            "families_min": FAMILY_MIN,
            "families_preferred": FAMILY_PREFERRED,
            "family_max_share": FAMILY_MAX_SHARE,
            "short_atom_none_target": SHORT_ATOM_NONE_TARGET,
            "short_atom_present_target": SHORT_ATOM_PRESENT_TARGET,
            "observed_min_share": OBSERVED_MIN_SHARE,
            "source_max_share": SOURCE_MAX_SHARE,
        },
        "schema": SCHEMA_QUAL,
        "train": False,
        "threshold_search": False,
        "index_rebuild": False,
        "reserve_as_qualification": False,
        "hub_publish_authorized": False,
    }


def verify_package_binding(observed: Mapping[str, Any]) -> dict[str, Any]:
    expected = qualification_binding()
    checks = {
        "pipeline": observed.get("pipeline") == expected["pipeline"],
        "package": observed.get("package") == expected["package"],
        "MODEL_WIDE_BEST": observed.get("MODEL_WIDE_BEST")
        == expected["MODEL_WIDE_BEST"],
        "STAGE_A_BEST": observed.get("STAGE_A_BEST") == expected["STAGE_A_BEST"],
        "STAGE_B_INDEX": observed.get("STAGE_B_INDEX") == expected["STAGE_B_INDEX"],
        "dependency_manifest": observed.get("dependency_manifest_sha256")
        == expected["dependency_manifest_sha256"],
    }
    return {"checks": checks, "pass": all(checks.values()), "expected": expected}


def row_is_text_identifiable(row: Mapping[str, Any]) -> bool:
    info = classify_identifiability(row)
    return info.get("identifiability_state") == "TEXT_IDENTIFIABLE"


def finalize_qualification_row(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize a candidate into a sealed qualification row schema."""
    subtype = str(raw["evidence_subtype"])
    if subtype not in SUBTYPE_TO_GOLD:
        raise ValueError(f"unknown_subtype:{subtype}")
    label = SUBTYPE_TO_GOLD[subtype]
    families = list(raw.get("candidate_families") or [])
    if not families and raw.get("lineage") and raw["lineage"] != "none":
        families = [str(raw["lineage"])]
    if label == "EVIDENCE_PRESENT":
        if not families or families[0] not in ACTIVE_FAMILY_VOCABULARY:
            raise ValueError(f"present_without_active_family:{families}")
    else:
        families = []
    text = str(raw["text"]).strip()
    if not text:
        raise ValueError("empty_text")
    row = {
        "identity": str(raw["identity"]),
        "text": text,
        "evidence_label": label,
        "evidence_subtype": subtype,
        "candidate_families": families,
        "class": str(raw.get("class") or "OBSERVED"),
        "source_family": str(
            raw.get("source_family")
            or raw.get("notes")
            or raw.get("topic_domain")
            or "unknown"
        ),
        "topic_domain": str(raw.get("topic_domain") or "unknown"),
        "source_sha256": str(raw.get("source_sha256") or sha256_text(text)),
        "parent_identity": raw.get("parent_identity"),
        "uncertainty_reason": raw.get("uncertainty_reason"),
        "rights": raw.get("rights"),
        "source_url": raw.get("source_url"),
        "notes": raw.get("notes"),
        "split": "qualification",
        "evaluation_spent": False,
        "schema": SCHEMA_SURFACE,
    }
    gold = gold_end_to_end(
        {
            "evidence_subtype": subtype,
            "candidate_families": families,
        }
    )
    row["gold_decision_type"] = gold["decision_type"]
    row["gold_family"] = gold["family"]
    row["is_short_atom"] = is_short_atom(row)
    ident = classify_identifiability(row)
    row["identifiability_state"] = ident["identifiability_state"]
    row["identifiability_disposition"] = ident.get("recommended_disposition")
    if label in {"EVIDENCE_PRESENT", "NO_EVIDENCE"} and not row_is_text_identifiable(
        row
    ):
        raise ValueError(
            f"definitive_not_text_identifiable:{row['identity']}:"
            f"{row['identifiability_state']}"
        )
    if label == "UNCERTAIN" and not row.get("uncertainty_reason"):
        raise ValueError(f"uncertain_missing_reason:{row['identity']}")
    return row


def composition_report(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    labels = Counter(r["evidence_label"] for r in rows)
    present = [r for r in rows if r["evidence_label"] == "EVIDENCE_PRESENT"]
    none = [r for r in rows if r["evidence_label"] == "NO_EVIDENCE"]
    families = Counter(
        (r.get("candidate_families") or [None])[0] for r in present
    )
    sa_none = sum(
        1
        for r in none
        if r.get("is_short_atom") or r.get("evidence_subtype") == "SHORT_ATOM_NONE"
    )
    sa_present = sum(1 for r in present if r.get("is_short_atom"))
    observed = sum(1 for r in rows if r.get("class") == "OBSERVED")
    source_none = Counter(r.get("source_family") for r in none)
    source_present = Counter(r.get("source_family") for r in present)
    domain_irrelevant = sum(
        1
        for r in none
        if str(r.get("topic_domain") or "").startswith("domain_irrelevant")
        or r.get("evidence_subtype") == "GENERIC_NONE"
        and "domain_irrelevant" in str(r.get("notes") or "")
    )
    max_fam_share = (
        (families.most_common(1)[0][1] / len(present)) if present else 0.0
    )
    max_src_none = (
        (source_none.most_common(1)[0][1] / len(none)) if none else 0.0
    )
    max_src_present = (
        (source_present.most_common(1)[0][1] / len(present)) if present else 0.0
    )
    checks = {
        "total_min": len(rows) >= TOTAL_MIN,
        "none_min": labels.get("NO_EVIDENCE", 0) >= NONE_MIN,
        "present_min": labels.get("EVIDENCE_PRESENT", 0) >= PRESENT_MIN,
        "uncertain_min": labels.get("UNCERTAIN", 0) >= UNCERTAIN_MIN,
        "families_min": len(families) >= FAMILY_MIN,
        "family_share": max_fam_share <= FAMILY_MAX_SHARE + 1e-12 or len(present) < 5,
        "observed_share": (observed / max(1, len(rows))) >= OBSERVED_MIN_SHARE,
        "source_share_none": max_src_none <= SOURCE_MAX_SHARE + 1e-12 or len(none) < 5,
        "source_share_present": max_src_present <= SOURCE_MAX_SHARE + 1e-12
        or len(present) < 5,
    }
    return {
        "n": len(rows),
        "labels": dict(labels),
        "n_families": len(families),
        "families": dict(families),
        "max_family_share": max_fam_share,
        "short_atom_none": sa_none,
        "short_atom_present": sa_present,
        "short_atom_none_target": SHORT_ATOM_NONE_TARGET,
        "short_atom_present_target": SHORT_ATOM_PRESENT_TARGET,
        "short_atom_none_met": sa_none >= SHORT_ATOM_NONE_TARGET,
        "short_atom_present_met": sa_present >= SHORT_ATOM_PRESENT_TARGET,
        "observed_share": observed / max(1, len(rows)),
        "source_max_share_none": max_src_none,
        "source_max_share_present": max_src_present,
        "domain_irrelevant_none_support": domain_irrelevant,
        "checks": checks,
        "pass": all(checks.values()),
    }


def score_qualification_rows(
    rows: Sequence[Mapping[str, Any]],
    forwards: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Compute primary/secondary metrics from gold rows + runtime forwards."""
    if len(rows) != len(forwards):
        raise ValueError("row_forward_length_mismatch")

    none_idx = [
        i for i, r in enumerate(rows) if r["evidence_label"] == "NO_EVIDENCE"
    ]
    present_idx = [
        i for i, r in enumerate(rows) if r["evidence_label"] == "EVIDENCE_PRESENT"
    ]
    uncertain_idx = [
        i for i, r in enumerate(rows) if r["evidence_label"] == "UNCERTAIN"
    ]

    false_entry = (
        sum(
            1
            for i in none_idx
            if forwards[i].get("stage_a_decision") == "EVIDENCE_PRESENT"
        )
        / max(1, len(none_idx))
    )
    present_recall = (
        sum(
            1
            for i in present_idx
            if forwards[i].get("stage_a_decision") == "EVIDENCE_PRESENT"
        )
        / max(1, len(present_idx))
    )
    none_recall = (
        sum(
            1
            for i in none_idx
            if forwards[i].get("stage_a_decision") == "NO_EVIDENCE"
        )
        / max(1, len(none_idx))
    )
    uncertain_recall = (
        sum(
            1
            for i in uncertain_idx
            if forwards[i].get("stage_a_decision") == "UNCERTAIN"
        )
        / max(1, len(uncertain_idx))
    )

    family_emitted = 0
    family_correct = 0
    top1_correct = 0
    top2_correct = 0
    selective_correct = 0
    selective_total = 0
    decision_counts: Counter[str] = Counter()
    wrong_emissions: list[dict[str, Any]] = []
    stage_a_induced = 0
    pure_stage_b = 0
    compound = 0

    for row, fwd in zip(rows, forwards):
        final = str(fwd.get("final_decision"))
        decision_counts[final] += 1
        gold_type = row["gold_decision_type"]
        gold_family = row.get("gold_family")
        stage_a = str(fwd.get("stage_a_decision"))
        executed = bool(fwd.get("stage_b_executed"))

        if final == "FAMILY":
            family_emitted += 1
            pred = fwd.get("predicted_family")
            if pred == gold_family and gold_type == "FAMILY":
                family_correct += 1
            else:
                if stage_a == "EVIDENCE_PRESENT" and row["evidence_label"] != "EVIDENCE_PRESENT":
                    err = "STAGE_A_FALSE_ENTRY"
                    stage_a_induced += 1
                elif (
                    stage_a == "EVIDENCE_PRESENT"
                    and row["evidence_label"] == "EVIDENCE_PRESENT"
                    and pred != gold_family
                ):
                    err = "STAGE_B_WRONG_FAMILY"
                    pure_stage_b += 1
                else:
                    err = "STAGE_A_AND_B_COMPOUND"
                    compound += 1
                wrong_emissions.append(
                    {
                        "identity": row["identity"],
                        "gold_stage_a": row["evidence_label"],
                        "gold_family": gold_family,
                        "stage_a_decision": stage_a,
                        "p_relation": fwd.get("p_relation"),
                        "p_resolvable": fwd.get("p_resolvable"),
                        "predicted_family": pred,
                        "top1_score": fwd.get("family_score"),
                        "runner_up": fwd.get("runner_up_family"),
                        "runner_up_score": fwd.get("runner_up_score"),
                        "margin": fwd.get("margin"),
                        "error_class": err,
                    }
                )

        # top1/top2 among gold PRESENT admitted rows
        if row["evidence_label"] == "EVIDENCE_PRESENT" and executed:
            if fwd.get("predicted_family") == gold_family and final == "FAMILY":
                top1_correct += 1
            runners = {fwd.get("predicted_family"), fwd.get("runner_up_family")}
            if gold_family in runners:
                top2_correct += 1

        if final in {"FAMILY", "NO_EVIDENCE"}:
            selective_total += 1
            mapped_gold = (
                "NO_EVIDENCE" if gold_type == "NONE" else gold_type
            )
            if final == mapped_gold and (
                final != "FAMILY" or fwd.get("predicted_family") == gold_family
            ):
                selective_correct += 1

    n_present_gold = len(present_idx)
    family_precision = (
        None if family_emitted == 0 else family_correct / family_emitted
    )
    family_coverage = (
        None if n_present_gold == 0 else family_emitted / n_present_gold
    )
    family_recall = (
        None if n_present_gold == 0 else family_correct / n_present_gold
    )
    selective_accuracy = (
        None if selective_total == 0 else selective_correct / selective_total
    )
    admitted_present = sum(
        1
        for i in present_idx
        if forwards[i].get("stage_a_decision") == "EVIDENCE_PRESENT"
    )
    top1_acc = top1_correct / max(1, admitted_present)
    top2_acc = top2_correct / max(1, admitted_present)

    # SHORT_ATOM diagnostics
    sa_none = [
        i
        for i in none_idx
        if rows[i].get("is_short_atom")
        or rows[i].get("evidence_subtype") == "SHORT_ATOM_NONE"
    ]
    sa_present = [i for i in present_idx if rows[i].get("is_short_atom")]
    sa_none_false_entry = (
        sum(
            1
            for i in sa_none
            if forwards[i].get("stage_a_decision") == "EVIDENCE_PRESENT"
        )
        / max(1, len(sa_none))
    )
    sa_present_recall = (
        sum(
            1
            for i in sa_present
            if forwards[i].get("stage_a_decision") == "EVIDENCE_PRESENT"
        )
        / max(1, len(sa_present))
    )
    domain_irr = [
        i
        for i in none_idx
        if "domain_irrelevant" in str(rows[i].get("topic_domain") or "")
        or "domain_irrelevant" in str(rows[i].get("notes") or "")
    ]
    domain_irr_none_recall = (
        None
        if not domain_irr
        else sum(
            1
            for i in domain_irr
            if forwards[i].get("stage_a_decision") == "NO_EVIDENCE"
        )
        / len(domain_irr)
    )

    none_entered = sum(
        1
        for r, f in zip(rows, forwards)
        if r["evidence_label"] == "NO_EVIDENCE" and f.get("stage_b_executed")
    )
    uncertain_entered = sum(
        1
        for r, f in zip(rows, forwards)
        if r["evidence_label"] == "UNCERTAIN" and f.get("stage_b_executed")
    )

    gates = {
        "false_entry_on_NONE": {
            "value": false_entry,
            "max": GATE_FALSE_ENTRY_MAX,
            "pass": false_entry <= GATE_FALSE_ENTRY_MAX,
        },
        "PRESENT_recall": {
            "value": present_recall,
            "min": GATE_PRESENT_RECALL_MIN,
            "pass": present_recall >= GATE_PRESENT_RECALL_MIN,
        },
        "NONE_recall": {
            "value": none_recall,
            "min": GATE_NONE_RECALL_MIN,
            "pass": none_recall >= GATE_NONE_RECALL_MIN,
        },
        "family_emission_precision": {
            "value": family_precision,
            "min": GATE_FAMILY_PRECISION_MIN,
            "pass": family_precision is not None
            and family_precision + 1e-12 >= GATE_FAMILY_PRECISION_MIN,
        },
    }
    primary_pass = all(g["pass"] for g in gates.values())

    return {
        "n": len(rows),
        "decision_counts": dict(decision_counts),
        "false_evidence_entry_rate_on_none": false_entry,
        "present_recall": present_recall,
        "none_recall": none_recall,
        "uncertain_recall": uncertain_recall,
        "family_emission_precision": family_precision,
        "family_emission_coverage": family_coverage,
        "family_emission_recall": family_recall,
        "selective_accuracy": selective_accuracy,
        "top1_family_accuracy": top1_acc,
        "top2_family_accuracy": top2_acc,
        "n_family_emitted": family_emitted,
        "overall_abstention_rate": (
            decision_counts.get("ABSTAIN", 0) + decision_counts.get("AMBIGUOUS", 0)
        )
        / max(1, len(rows)),
        "gating": {
            "none_entered_stage_b": none_entered,
            "uncertain_entered_stage_b": uncertain_entered,
            "pass": none_entered == 0 and uncertain_entered == 0,
        },
        "short_atom": {
            "n_none": len(sa_none),
            "n_present": len(sa_present),
            "none_false_entry": sa_none_false_entry,
            "present_recall": sa_present_recall,
        },
        "domain_irrelevant": {
            "n_none": len(domain_irr),
            "none_recall": domain_irr_none_recall,
            "supported": bool(domain_irr),
        },
        "error_decomposition": {
            "STAGE_A_FALSE_ENTRY": stage_a_induced,
            "STAGE_B_WRONG_FAMILY": pure_stage_b,
            "STAGE_A_AND_B_COMPOUND": compound,
            "wrong_emissions": wrong_emissions,
        },
        "primary_gates": gates,
        "primary_gate_pass": primary_pass,
    }


def disposition_from_results(
    *,
    integrity_pass: bool,
    metrics: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not integrity_pass:
        return {
            "QUALIFICATION_DISPOSITION": "QUALIFICATION_INVALID",
            "RELEASE_ELIGIBLE": False,
            "HUB_PUBLISH_AUTHORIZED": False,
            "NEXT_ACTION": NEXT_INVALID,
        }
    assert metrics is not None
    if metrics.get("primary_gate_pass") and metrics.get("gating", {}).get("pass"):
        return {
            "QUALIFICATION_DISPOSITION": "QUALIFICATION_PASS",
            "RELEASE_ELIGIBLE": True,
            "HUB_PUBLISH_AUTHORIZED": False,
            "NEXT_ACTION": NEXT_PASS,
        }
    return {
        "QUALIFICATION_DISPOSITION": "QUALIFICATION_FAIL",
        "RELEASE_ELIGIBLE": False,
        "HUB_PUBLISH_AUTHORIZED": False,
        "NEXT_ACTION": NEXT_FAIL,
    }


def build_qualification_receipt(
    *,
    code_revision: str,
    surface_hashes: Mapping[str, str],
    composition: Mapping[str, Any],
    disjointness: Mapping[str, Any],
    identifiability: Mapping[str, Any],
    metrics: Mapping[str, Any] | None,
    cold_load: Mapping[str, Any],
    integrity_pass: bool,
    scored_at: str | None = None,
) -> dict[str, Any]:
    disp = disposition_from_results(integrity_pass=integrity_pass, metrics=metrics)
    # Rebuild package contract to confirm live pins still match sealed package.
    live_pkg = package_contract(code_revision=code_revision)
    # Manifest SHA is frozen at package seal (includes that seal's code_revision).
    # Live recomputation may differ by revision; runtime artifact pins must match.
    pin_ok = (
        live_pkg["STAGE_A_BEST"] == STAGE_A_BEST_SHA256
        and live_pkg["MODEL_WIDE_BEST"] == MODEL_WIDE_BEST_SHA256
        and live_pkg["STAGE_B_INDEX_SHA256"] == FROZEN_INDEX_SHA256
        and float(live_pkg["dependency_manifest"]["stage_b_score_floor"])
        == FROZEN_MINIMUM_FAMILY_SCORE
        and float(live_pkg["dependency_manifest"]["stage_b_margin_floor"])
        == FROZEN_MINIMUM_TOP1_TOP2_MARGIN
    )
    payload = {
        "BEST_MUTATED": False,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "QUALIFICATION_ID": QUALIFICATION_ID,
        "QUALIFY_RULE": QUALIFY_RULE,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "STAGE_B_INDEX": FROZEN_INDEX_SHA256,
        "PIPELINE_ID": PIPELINE_ID,
        "PACKAGING_ID": PACKAGING_ID,
        "PIPELINE_DEPENDENCY_MANIFEST_SHA256": DEPENDENCY_MANIFEST_SHA256_PIN,
        "SEAL_PACKAGE_RECEIPT_SHA256": SEAL_PACKAGE_RECEIPT_SHA256_PIN,
        "RESERVE_CONSUMED": False,
        "TRAIN": False,
        "THRESHOLD_CHANGED": False,
        "INDEX_REBUILT": False,
        "V1R2_MUTATED": False,
        "code_revision": code_revision,
        "binding": qualification_binding(),
        "cold_load": dict(cold_load),
        "composition": dict(composition),
        "disjointness": dict(disjointness),
        "identifiability": dict(identifiability),
        "known_limitations": dict(PIPELINE_LIMITATIONS),
        "metrics": None if metrics is None else dict(metrics),
        "package_pins_live_match": pin_ok,
        "scored_at": scored_at or utc_now_iso(),
        "surface_hashes": dict(surface_hashes),
        "schema": SCHEMA_QUAL,
        **disp,
    }
    payload["QUALIFICATION_RECEIPT_SHA256"] = sha256_text(
        canonical_json(
            {
                k: v
                for k, v in payload.items()
                if k != "QUALIFICATION_RECEIPT_SHA256"
            }
        )
    )
    return payload
