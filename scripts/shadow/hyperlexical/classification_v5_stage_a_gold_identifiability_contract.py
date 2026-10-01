"""HYPERLEX_STAGE_A_GOLD_IDENTIFIABILITY_CONTRACT_V1 — frozen spec.

Read-only gold-identifiability contract for text-only Stage-A.
Does not train, mutate V1R1, auto-relabel, create V1R2, expand inputs,
alter Stage B, score spent reserve, or move BEST.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

from .classification_v2_surface import word_count
from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_factorized_objective import (
    FACTORIZED_ANNOTATION_SHA256_PIN,
    MASKED,
    OBJECTIVE_ID,
    OBJECTIVE_RECEIPT_SHA256_PIN,
)
from .classification_v5_stage_a_factorized_relation_diagnose import (
    FAILED_CHECKPOINT_SHA256 as FACTORIZED_FAILED_CKPT,
)
from .classification_v5_stage_a_generalization_retrain_diagnose import (
    semantic_core_class,
    simple_tokens,
)
from .classification_v5_stage_a_two_stage_generalization import (
    AUTHORIZED_DATASET_SHA,
    PARENT_STAGE_A_BEST_SHA,
    SPENT_RESERVE,
    SPENT_RESERVE_OVERLAP,
    SPENT_RESERVE_STATUS,
)

CONTRACT_ID = "HYPERLEX_STAGE_A_GOLD_IDENTIFIABILITY_CONTRACT_V1"
CONTRACT_RULE = "REVISE_GOLD_IDENTIFIABILITY_CONTRACT"
DIAGNOSIS_RECEIPT_SHA256 = (
    "827c0e2be1619def2af0b93fc58b8edb04bc791a3ba4ed78e823819ba87a5c81"
)
PRIMARY_DIAGNOSIS_PIN = "MODEL_INPUT_INFORMATION_DEFICIT"
PARENT_EXPERIMENT_ID = "HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-001"

CONTRACT_STATE = "FROZEN_SPEC"
TRAIN_AUTHORIZED = False
DATASET_MUTATED = False
ARCHITECTURE_CHANGE_JUSTIFIED = False
INPUT_CONTRACT_EXPANSION_JUSTIFIED = False

MODEL_INPUT = ("text",)
ANNOTATION_ONLY_METADATA = (
    "subtype",
    "family_or_domain_label",
    "source_family",
    "source_provenance",
    "pair_identity",
    "contrast_partner",
    "dictionary_sense",
    "external_definition",
    "review_notes",
    "label_derivation_metadata",
)

IDENTIFIABILITY_STATES = (
    "TEXT_IDENTIFIABLE",
    "CONTEXT_REQUIRED",
    "INSUFFICIENT_TEXT",
    "INVALID_GOLD_FOR_TEXT_ONLY_MODEL",
)

SHORT_ATOM_DISPOSITIONS = (
    "SELF_CONTAINED_RELATION",
    "LEXEME_ONLY",
    "CONTEXT_DEPENDENT_RELATION",
    "SEMANTICALLY_UNDERDETERMINED",
)

EXTERNAL_INFO_CLASSES = (
    "NONE",
    "PAIR_CONTEXT",
    "SOURCE_CONTEXT",
    "DOMAIN_SENSE",
    "DICTIONARY_SENSE",
    "PROVENANCE_CONTEXT",
    "EXTERNAL_DEFINITION",
    "ANNOTATOR_NOTE",
    "OTHER",
)

DISPOSITIONS = (
    "KEEP_GOLD",
    "KEEP_GOLD_BUT_MASK_RELATION",
    "KEEP_FOR_RESOLVABILITY_ONLY",
    "EXCLUDE_FROM_TEXT_ONLY_STAGE_A",
    "REQUIRES_HUMAN_RESETTLEMENT",
)

PRIMARY_REPAIRS = (
    "FILTER_CONTEXT_DEPENDENT_GOLD",
    "MASK_CONTEXT_DEPENDENT_TARGETS",
    "RESETTLE_CONTEXT_DEPENDENT_GOLD",
    "FILTER_AND_RESETTLE_GOLD",
    "INPUT_CONTRACT_REDESIGN_REQUIRED",
)

DATASET_CONSEQUENCES = (
    "ANNOTATION_FILTER_ONLY",
    "ANNOTATION_MASK_ONLY",
    "ANNOTATION_FILTER_AND_MASK",
    "HUMAN_RESETTLEMENT_REQUIRED",
    "NEW_INPUT_CONTRACT_REQUIRED",
)

NEXT_ACTIONS = (
    "APPLY_GOLD_IDENTIFIABILITY_FILTER",
    "DESIGN_GOLD_RESETTLEMENT_PROTOCOL",
    "SPEC_NEW_MODEL_INPUT_CONTRACT",
    "STOP_STAGE_A_RESEARCH",
)

CANONICAL_PRINCIPLE = (
    "A text-only classifier may not be trained or evaluated against a "
    "semantic distinction that requires hidden metadata, pair context, "
    "source provenance, dictionary sense, or annotation-side information "
    "unavailable at inference."
)

MODEL_WIDE_BEST_SHA256 = (
    "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
)

PROPOSED_FUTURE_GATES = {
    "relation_training_targets_TEXT_IDENTIFIABLE": 1.0,
    "e2e_eval_TEXT_IDENTIFIABLE_or_genuine_SEMANTICALLY_UNDERDETERMINED": 1.0,
    "context_required_definitive_gold": 0,
    "hidden_metadata_dependent_gold": 0,
}


def normalize_text(text: str) -> str:
    t = str(text or "").strip().lower()
    return re.sub(r"\s+", " ", t)


def cell_family(row: Mapping[str, Any]) -> str:
    cell = str(row.get("primary_cell") or "")
    if cell.startswith("SHORT_ATOM/"):
        return "SHORT_ATOM"
    if cell.startswith("DEFINITION_STYLE/"):
        return "DEFINITION_STYLE"
    if cell.startswith("ORDINARY_PROSE/") or cell.startswith("PROSE/"):
        return "PROSE"
    if not cell and str(row.get("evidence_label") or "") == "UNCERTAIN":
        return "AMBIGUOUS"
    return "OTHER"


def is_short_atom(row: Mapping[str, Any]) -> bool:
    return cell_family(row) == "SHORT_ATOM"


def uncertain_reason_bucket(row: Mapping[str, Any]) -> str:
    """Map AMBIGUOUS notes to CONTEXT|MULTI|DOMAIN|RELATION|OTHER."""
    notes = str(row.get("notes") or "").upper()
    if "MULTI" in notes:
        return "MULTI"
    if "DOMAIN" in notes and "UNRESOLVED_SOURCE" not in notes:
        return "DOMAIN"
    if "RELATION" in notes and "UNRESOLVED_SOURCE" not in notes:
        return "RELATION"
    if (
        "CONTEXT" in notes
        or "UNRESOLVED_SOURCE" in notes
        or "SOURCE" in notes
        or "PROVENANCE" in notes
    ):
        return "CONTEXT"
    return "OTHER"


def uncertain_failure_type(row: Mapping[str, Any]) -> str:
    """genuine text-semantic uncertainty vs missing annotation context."""
    bucket = uncertain_reason_bucket(row)
    if bucket == "MULTI":
        return "GENUINE_TEXTUAL_UNCERTAINTY"
    if bucket in {"CONTEXT", "OTHER"}:
        # UNRESOLVED_SOURCE_MEANING / truncated wiki = annotation context
        return "MISSING_ANNOTATION_CONTEXT"
    if bucket in {"DOMAIN", "RELATION"}:
        return "GENUINE_TEXTUAL_UNCERTAINTY"
    return "MISSING_ANNOTATION_CONTEXT"


def short_atom_disposition(row: Mapping[str, Any]) -> str:
    """SHORT_ATOM review classes (also usable for non-SHORT_ATOM witness)."""
    core = semantic_core_class(row)
    label = str(row.get("evidence_label") or "")
    subtype = str(row.get("evidence_subtype") or "")
    missing = [str(x) for x in (row.get("missing_required_semantics") or [])]
    tokens = simple_tokens(str(row.get("text") or ""))
    notes_l = str(row.get("notes") or "").lower()
    wc = word_count(str(row.get("text") or ""))

    if label == "UNCERTAIN" or "evidence_sufficiency_unresolved" in missing:
        if uncertain_failure_type(row) == "GENUINE_TEXTUAL_UNCERTAINTY":
            return "SEMANTICALLY_UNDERDETERMINED"
        return "CONTEXT_DEPENDENT_RELATION"

    if core in {"LEXEME_ONLY", "CATEGORY_MENTION_ONLY"}:
        return "LEXEME_ONLY"

    if label == "EVIDENCE_PRESENT":
        # Bare atom / dictionary headword / pair-dependent sense
        bare_atom = is_short_atom(row) and wc <= 3
        metadata_sense = (
            "wikt" in notes_l
            or "atom_present" in notes_l
            or bool(row.get("pair_group_id"))
            or core in {"LEXEME_PLUS_RELATION", "LEXEME_ONLY"}
        )
        if bare_atom or (wc <= 3 and metadata_sense):
            return "CONTEXT_DEPENDENT_RELATION"
        if wc >= 4:
            return "SELF_CONTAINED_RELATION"
        return "CONTEXT_DEPENDENT_RELATION"

    if label == "NO_EVIDENCE":
        if core == "NEGATED_OR_NONASSERTED":
            return "SELF_CONTAINED_RELATION"
        if core in {"LEXEME_ONLY", "CATEGORY_MENTION_ONLY"}:
            return "LEXEME_ONLY"
        if subtype.endswith("_NONE") and "active_family_evidence_absent" in missing:
            return "LEXEME_ONLY"
        if core == "LEXEME_PLUS_CONTEXT" and wc >= 5:
            # Prose NONE: absence of asserted relation is usually text-visible
            return "SELF_CONTAINED_RELATION"
        if is_short_atom(row):
            return "LEXEME_ONLY"
        return "SELF_CONTAINED_RELATION"

    return "SEMANTICALLY_UNDERDETERMINED"


def required_external_information(row: Mapping[str, Any]) -> list[str]:
    disp = short_atom_disposition(row)
    label = str(row.get("evidence_label") or "")
    notes_l = str(row.get("notes") or "").lower()
    missing = [str(x) for x in (row.get("missing_required_semantics") or [])]
    req: list[str] = []

    if disp in {"SELF_CONTAINED_RELATION", "LEXEME_ONLY"} and label != "UNCERTAIN":
        # LEXEME_ONLY NONE is text-identifiable as no-relation without metadata
        if disp == "LEXEME_ONLY" and label == "NO_EVIDENCE":
            return ["NONE"]
        if disp == "SELF_CONTAINED_RELATION":
            return ["NONE"]

    if bool(row.get("pair_group_id") or row.get("paired_positive_identity")):
        if label == "EVIDENCE_PRESENT" or "paired_against_positive" in " ".join(missing):
            req.append("PAIR_CONTEXT")
    if "wikt" in notes_l or "wiktionary" in notes_l or "atom_present" in notes_l:
        req.append("DICTIONARY_SENSE")
    if "unresolved_source" in notes_l or "source etymology" in str(
        row.get("text") or ""
    ).lower():
        req.append("SOURCE_CONTEXT")
    if str(row.get("topic_domain") or "") and (
        disp == "CONTEXT_DEPENDENT_RELATION" or label == "EVIDENCE_PRESENT"
        and is_short_atom(row)
    ):
        req.append("DOMAIN_SENSE")
    if row.get("provenance") and disp == "CONTEXT_DEPENDENT_RELATION":
        req.append("PROVENANCE_CONTEXT")
    if "definition" in notes_l or "external" in notes_l:
        req.append("EXTERNAL_DEFINITION")
    if notes_l and disp == "CONTEXT_DEPENDENT_RELATION":
        req.append("ANNOTATOR_NOTE")
    if not req:
        if disp == "SEMANTICALLY_UNDERDETERMINED":
            return ["NONE"]
        if disp == "CONTEXT_DEPENDENT_RELATION":
            req.append("OTHER")
        else:
            return ["NONE"]
    # dedupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for x in req:
        if x not in seen and x in EXTERNAL_INFO_CLASSES:
            seen.add(x)
            out.append(x)
    return out or ["NONE"]


def base_identifiability(row: Mapping[str, Any]) -> tuple[str, str]:
    """Return (TEXT_IDENTIFIABLE|CONTEXT_REQUIRED|INSUFFICIENT_TEXT, reason)."""
    disp = short_atom_disposition(row)
    label = str(row.get("evidence_label") or "")
    wc = word_count(str(row.get("text") or ""))

    if label == "UNCERTAIN":
        ftype = uncertain_failure_type(row)
        if ftype == "GENUINE_TEXTUAL_UNCERTAINTY":
            return (
                "INSUFFICIENT_TEXT",
                "genuine_multi_or_domain_relation_ambiguity_in_text",
            )
        return (
            "CONTEXT_REQUIRED",
            f"uncertain_missing_annotation_context:{uncertain_reason_bucket(row)}",
        )

    if disp == "SELF_CONTAINED_RELATION":
        return ("TEXT_IDENTIFIABLE", "self_contained_relation_from_text")
    if disp == "LEXEME_ONLY":
        if label == "NO_EVIDENCE":
            return (
                "TEXT_IDENTIFIABLE",
                "lexeme_only_supports_no_evidence_relation",
            )
        if label == "EVIDENCE_PRESENT":
            return (
                "CONTEXT_REQUIRED",
                "lexeme_only_cannot_support_relation_present",
            )
    if disp == "CONTEXT_DEPENDENT_RELATION":
        return (
            "CONTEXT_REQUIRED",
            "relation_gold_depends_on_metadata_or_pair_or_dictionary_sense",
        )
    if disp == "SEMANTICALLY_UNDERDETERMINED":
        return ("INSUFFICIENT_TEXT", "text_admits_multiple_unresolved_readings")
    if wc == 0:
        return ("INSUFFICIENT_TEXT", "empty_text")
    return ("INSUFFICIENT_TEXT", "unclassified_underdetermined")


def identifiability_state(row: Mapping[str, Any]) -> dict[str, Any]:
    base, reason = base_identifiability(row)
    label = str(row.get("evidence_label") or "")
    definitive = label in {"EVIDENCE_PRESENT", "NO_EVIDENCE"}
    state = base
    if definitive and base != "TEXT_IDENTIFIABLE":
        state = "INVALID_GOLD_FOR_TEXT_ONLY_MODEL"
        reason = f"definitive_{label}_not_text_identifiable:{reason}"
    return {
        "identifiability_state": state,
        "base_identifiability": base,
        "identifiability_reason": reason,
        "short_atom_disposition": short_atom_disposition(row),
        "required_external_information": required_external_information(row),
    }


def none_identifiability_bucket(row: Mapping[str, Any]) -> str:
    assert str(row.get("evidence_label")) == "NO_EVIDENCE"
    info = identifiability_state(row)
    if info["identifiability_state"] == "TEXT_IDENTIFIABLE":
        return "TEXT_IDENTIFIABLE_NO_RELATION"
    if info["base_identifiability"] == "CONTEXT_REQUIRED":
        return "DOMAIN_OR_SENSE_REQUIRES_METADATA"
    return "SEMANTICALLY_UNDERDETERMINED"


def admissibility(row: Mapping[str, Any], ann: Mapping[str, Any] | None) -> dict[str, bool]:
    info = identifiability_state(row)
    state = info["identifiability_state"]
    base = info["base_identifiability"]
    label = str(row.get("evidence_label") or "")
    rel = None if ann is None else ann.get("evidence_relation_present")
    res = None if ann is None else ann.get("semantic_resolvable")

    # Relation training: definitive TEXT_IDENTIFIABLE only
    relation_train = state == "TEXT_IDENTIFIABLE" and label in {
        "EVIDENCE_PRESENT",
        "NO_EVIDENCE",
    }
    if rel == MASKED:
        relation_train = False

    # Resolvability: identifiable definitive OR genuine underdetermined UNCERTAIN
    if state == "TEXT_IDENTIFIABLE" and label in {"EVIDENCE_PRESENT", "NO_EVIDENCE"}:
        resolvability_train = True
    elif (
        label == "UNCERTAIN"
        and base == "INSUFFICIENT_TEXT"
        and uncertain_failure_type(row) == "GENUINE_TEXTUAL_UNCERTAINTY"
    ):
        resolvability_train = True
    else:
        resolvability_train = False

    # E2E: expected output knowable from text
    if state == "TEXT_IDENTIFIABLE":
        e2e = True
    elif (
        label == "UNCERTAIN"
        and base == "INSUFFICIENT_TEXT"
        and uncertain_failure_type(row) == "GENUINE_TEXTUAL_UNCERTAINTY"
    ):
        e2e = True
    else:
        e2e = False

    return {
        "admissible_for_relation_training": relation_train,
        "admissible_for_resolvability_training": resolvability_train,
        "admissible_for_end_to_end_eval": e2e,
        "semantic_resolvable_ann": res,
        "evidence_relation_present_ann": rel,
    }


def recommended_disposition(row: Mapping[str, Any], ann: Mapping[str, Any] | None) -> str:
    info = identifiability_state(row)
    adm = admissibility(row, ann)
    state = info["identifiability_state"]
    label = str(row.get("evidence_label") or "")

    if state == "TEXT_IDENTIFIABLE":
        return "KEEP_GOLD"
    if label == "UNCERTAIN":
        if uncertain_failure_type(row) == "GENUINE_TEXTUAL_UNCERTAINTY":
            return "KEEP_FOR_RESOLVABILITY_ONLY"
        # Missing annotation context — not genuine model-facing uncertainty
        return "EXCLUDE_FROM_TEXT_ONLY_STAGE_A"
    if state == "INVALID_GOLD_FOR_TEXT_ONLY_MODEL":
        # Hard rule: do not auto-relabel; filter or human settle
        if info["short_atom_disposition"] == "CONTEXT_DEPENDENT_RELATION":
            return "EXCLUDE_FROM_TEXT_ONLY_STAGE_A"
        return "REQUIRES_HUMAN_RESETTLEMENT"
    if state == "CONTEXT_REQUIRED":
        return "EXCLUDE_FROM_TEXT_ONLY_STAGE_A"
    if state == "INSUFFICIENT_TEXT":
        return "KEEP_GOLD_BUT_MASK_RELATION"
    return "REQUIRES_HUMAN_RESETTLEMENT"


def classify_row(
    row: Mapping[str, Any], ann: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    info = identifiability_state(row)
    adm = admissibility(row, ann)
    disp = recommended_disposition(row, ann)
    rel_target = None
    if ann is not None:
        rel_target = ann.get("evidence_relation_present")
    elif str(row.get("evidence_label")) == "EVIDENCE_PRESENT":
        rel_target = 1
    elif str(row.get("evidence_label")) == "NO_EVIDENCE":
        rel_target = 0
    else:
        rel_target = MASKED
    return {
        "identity": str(row.get("identity") or ""),
        "split": str(row.get("split") or ""),
        "current_final_gold": str(row.get("evidence_label") or ""),
        "current_subtype": str(row.get("evidence_subtype") or ""),
        "primary_cell": row.get("primary_cell"),
        "cell_family": cell_family(row),
        "current_derived_relation_target": rel_target,
        "identifiability_state": info["identifiability_state"],
        "base_identifiability": info["base_identifiability"],
        "identifiability_reason": info["identifiability_reason"],
        "short_atom_disposition": info["short_atom_disposition"],
        "required_external_information": info["required_external_information"],
        "admissible_for_relation_training": adm["admissible_for_relation_training"],
        "admissible_for_resolvability_training": adm[
            "admissible_for_resolvability_training"
        ],
        "admissible_for_end_to_end_eval": adm["admissible_for_end_to_end_eval"],
        "recommended_disposition": disp,
        "uncertain_reason_bucket": (
            uncertain_reason_bucket(row)
            if str(row.get("evidence_label")) == "UNCERTAIN"
            else None
        ),
        "uncertain_failure_type": (
            uncertain_failure_type(row)
            if str(row.get("evidence_label")) == "UNCERTAIN"
            else None
        ),
        "none_identifiability_bucket": (
            none_identifiability_bucket(row)
            if str(row.get("evidence_label")) == "NO_EVIDENCE"
            else None
        ),
        "source_family": str(row.get("source_family") or ""),
        "topic_domain": str(row.get("topic_domain") or ""),
        "word_count": word_count(str(row.get("text") or "")),
    }


def decide_primary_repair(summary: Mapping[str, Any]) -> dict[str, Any]:
    disp = summary.get("disposition_counts") or {}
    invalid = int(summary.get("identifiability_counts", {}).get(
        "INVALID_GOLD_FOR_TEXT_ONLY_MODEL", 0
    ))
    exclude = int(disp.get("EXCLUDE_FROM_TEXT_ONLY_STAGE_A", 0))
    resettlement = int(disp.get("REQUIRES_HUMAN_RESETTLEMENT", 0))
    mask_only = int(disp.get("KEEP_GOLD_BUT_MASK_RELATION", 0))
    viability = str(summary.get("repaired_surface_viability") or "")

    if resettlement > 0 and exclude > 0 and resettlement >= max(1, exclude // 10):
        primary = "FILTER_AND_RESETTLE_GOLD"
        dataset = "HUMAN_RESETTLEMENT_REQUIRED"
        next_action = "DESIGN_GOLD_RESETTLEMENT_PROTOCOL"
        scope = "FILTER_MASK_AND_RESETTLEMENT"
    elif exclude > 0 and resettlement == 0:
        if mask_only > 0:
            primary = "FILTER_CONTEXT_DEPENDENT_GOLD"
            dataset = "ANNOTATION_FILTER_AND_MASK"
            next_action = "APPLY_GOLD_IDENTIFIABILITY_FILTER"
            scope = "FILTER_AND_MASK"
        else:
            primary = "FILTER_CONTEXT_DEPENDENT_GOLD"
            dataset = "ANNOTATION_FILTER_ONLY"
            next_action = "APPLY_GOLD_IDENTIFIABILITY_FILTER"
            scope = "FILTER_ONLY"
    elif mask_only > 0 and exclude == 0:
        primary = "MASK_CONTEXT_DEPENDENT_TARGETS"
        dataset = "ANNOTATION_MASK_ONLY"
        next_action = "APPLY_GOLD_IDENTIFIABILITY_FILTER"
        scope = "MASKING_ONLY"
    elif resettlement > 0:
        primary = "RESETTLE_CONTEXT_DEPENDENT_GOLD"
        dataset = "HUMAN_RESETTLEMENT_REQUIRED"
        next_action = "DESIGN_GOLD_RESETTLEMENT_PROTOCOL"
        scope = "HUMAN_RESETTLEMENT"
    else:
        primary = "FILTER_CONTEXT_DEPENDENT_GOLD"
        dataset = "ANNOTATION_FILTER_ONLY"
        next_action = "APPLY_GOLD_IDENTIFIABILITY_FILTER"
        scope = "FILTER_ONLY"

    if viability == "NEW_DATA_REQUIRED_AFTER_REPAIR" and primary.startswith("FILTER"):
        # Still filter first; new data is a later consequence, not input redesign
        pass

    return {
        "primary_repair": primary,
        "dataset_consequence": dataset,
        "next_action": next_action,
        "repair_scope": scope,
        "invalid_definitive_gold": invalid,
        "NEXT_ACTION_AUTHORIZED": False,
    }


def classify_repaired_viability(counts: Mapping[str, Any]) -> str:
    rel_pos = int(counts.get("relation_positive", 0))
    rel_neg = int(counts.get("relation_negative", 0))
    res_pos = int(counts.get("resolvability_positive", 0))
    res_neg = int(counts.get("resolvability_negative", 0))
    min_cell = min(rel_pos, rel_neg, res_pos, res_neg) if all(
        x is not None for x in (rel_pos, rel_neg, res_pos, res_neg)
    ) else 0
    if rel_pos < 80 or rel_neg < 80 or min_cell < 40:
        if rel_pos < 40 or rel_neg < 40:
            return "NEW_DATA_REQUIRED_AFTER_REPAIR"
        return "REPAIRED_SURFACE_SPARSE"
    return "REPAIRED_SURFACE_VIABLE"


def assemble_contract_receipt(
    *,
    row_classifications: Sequence[Mapping[str, Any]],
    aggregate: Mapping[str, Any],
) -> dict[str, Any]:
    decision = decide_primary_repair(aggregate)
    receipt = {
        "CONTRACT_RULE": CONTRACT_RULE,
        "CONTRACT_ID": CONTRACT_ID,
        "CONTRACT_STATE": CONTRACT_STATE,
        "TRAIN_AUTHORIZED": TRAIN_AUTHORIZED,
        "DATASET_MUTATED": DATASET_MUTATED,
        "V1R1_MUTATED": False,
        "V1R2_CREATED": False,
        "AUTO_RELABEL": False,
        "ARCHITECTURE_CHANGE_JUSTIFIED": ARCHITECTURE_CHANGE_JUSTIFIED,
        "INPUT_CONTRACT_EXPANSION_JUSTIFIED": INPUT_CONTRACT_EXPANSION_JUSTIFIED,
        "MODEL_INPUT": list(MODEL_INPUT),
        "ANNOTATION_ONLY_METADATA": list(ANNOTATION_ONLY_METADATA),
        "CANONICAL_PRINCIPLE": CANONICAL_PRINCIPLE,
        "DIAGNOSIS_RECEIPT_SHA256": DIAGNOSIS_RECEIPT_SHA256,
        "PRIMARY_DIAGNOSIS_PIN": PRIMARY_DIAGNOSIS_PIN,
        "PARENT_EXPERIMENT_ID": PARENT_EXPERIMENT_ID,
        "OBJECTIVE_ID": OBJECTIVE_ID,
        "OBJECTIVE_RECEIPT_SHA256": OBJECTIVE_RECEIPT_SHA256_PIN,
        "FACTORIZED_ANNOTATION_SHA256": FACTORIZED_ANNOTATION_SHA256_PIN,
        "V1R1_DATASET_SHA256": AUTHORIZED_DATASET_SHA,
        "FACTORIZED_FAILED_CHECKPOINT_SHA256": FACTORIZED_FAILED_CKPT,
        "STAGE_A_BEST": PARENT_STAGE_A_BEST_SHA,
        "STAGE_A_BEST_MUTATED": False,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "SPENT_RESERVE": SPENT_RESERVE,
        "SPENT_RESERVE_OVERLAP": SPENT_RESERVE_OVERLAP,
        "SPENT_RESERVE_STATUS": SPENT_RESERVE_STATUS,
        "PRIMARY_REPAIR": decision["primary_repair"],
        "DATASET_CONSEQUENCE": decision["dataset_consequence"],
        "REPAIR_SCOPE": decision["repair_scope"],
        "NEXT_ACTION": decision["next_action"],
        "NEXT_ACTION_AUTHORIZED": False,
        "NEW_DATASET_VERSION_REQUIRED": bool(
            aggregate.get("NEW_DATASET_VERSION_REQUIRED", True)
        ),
        "PROPOSED_FUTURE_GATES": PROPOSED_FUTURE_GATES,
        "aggregate": aggregate,
        "n_rows_classified": len(row_classifications),
        "schema": "hyperlex.classification.v5.stage_a_gold_identifiability_contract.v1",
    }
    receipt["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in receipt.items() if k != "receipt_sha256"})
    )
    return receipt
