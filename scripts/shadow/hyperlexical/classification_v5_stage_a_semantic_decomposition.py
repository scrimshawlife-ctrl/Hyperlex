"""STAGE_A_SEMANTIC_DECOMPOSITION — spec + V1R1 recoverability audit.

Defines Stage-A semantic axes and audits whether V1R1 existing gold/subtypes
can support them. Does not train, create V1R2, relabel, or move BEST.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_gold_label_mapping import SUBTYPE_TO_GOLD
from .classification_v5_stage_a_two_stage_generalization import (
    AUTHORIZED_DATASET_SHA,
    AUTHORIZED_READINESS_SHA,
    AUTHORIZED_SURFACE_RECEIPT_SHA,
    PARENT_STAGE_A_BEST_SHA,
    SPENT_RESERVE,
    SPENT_RESERVE_OVERLAP,
    SPENT_RESERVE_STATUS,
)

DECOMPOSITION_RULE = "STAGE_A_SEMANTIC_DECOMPOSITION"
DIAGNOSIS_RECEIPT_SHA256 = (
    "c6ae58c78e7df2fdcd5675774c44c71510082d5749dfe90ff824f25809ffd90e"
)
FAILED_CHECKPOINT_SHA256 = (
    "26841d5f3a8b9cd4237f79203b80697f2da186e7d4b30ab6c08d528adba56e76"
)
PRIMARY_DIAGNOSIS = "GATE1_SEMANTIC_TARGET_MISMATCH"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V5-STAGE-A-TWO-STAGE-GENERALIZATION-001"

# Frozen V1R1 recoverability audit (3585 rows; gold/provenance fields only).
# Sealed from EVIDENCE_SURFACE.jsonl @ AUTHORIZED_DATASET_SHA — no model inference.
FROZEN_V1R1_SUBTYPE_COUNTS = {
    "POSITIVE_EVIDENCE": 1535,
    "ORDINARY_DOMAIN_NONE": 637,
    "NEAR_DOMAIN_NONE": 145,
    "HARD_NONE": 41,
    "LEXICAL_LOOKALIKE_NONE": 744,
    "SHORT_ATOM_NONE": 284,
    "GENERIC_NONE": 0,
    "AMBIGUOUS_EVIDENCE": 199,
}
FROZEN_V1R1_LABEL_COUNTS = {
    "EVIDENCE_PRESENT": 1535,
    "NO_EVIDENCE": 1851,
    "UNCERTAIN": 199,
}
FROZEN_V1R1_UNCERTAIN_NOTE_CAUSES = {
    "CONTEXT_INSUFFICIENT": 84,
    "MULTIPLE_SEMANTIC_READINGS": 54,
    "DOMAIN_UNCERTAIN": 44,
    "RELATION_UNCERTAIN": 17,
}
FROZEN_V1R1_STATUS_COUNTS = {
    "domain_relevant": {
        "DIRECTLY_SUPPORTED": 1535,
        "RULE_DERIVABLE": 1851,
        "REQUIRES_NEW_HUMAN_SETTLEMENT": 199,
    },
    "evidence_relation_present": {
        "DIRECTLY_SUPPORTED": 1535,
        "RULE_DERIVABLE": 1851,
        "REQUIRES_NEW_HUMAN_SETTLEMENT": 199,
    },
    "semantic_resolvable": {
        "DIRECTLY_SUPPORTED": 1734,
        "RULE_DERIVABLE": 1851,
    },
}
FROZEN_V1R1_VALUE_COUNTS = {
    "domain_relevant": {"1": 3386, "None": 199},
    "evidence_relation_present": {"0": 1851, "1": 1535, "None": 199},
    "semantic_resolvable": {"0": 199, "1": 3386},
}

# Frozen critical distinctions.
CRITICAL_DISTINCTIONS = {
    "DOMAIN_RELEVANT_NE_EVIDENCE_PRESENT": True,
    "LEXICAL_CUE_NE_EVIDENCE_RELATION": True,
    "MODEL_UNCERTAINTY_NE_SEMANTIC_UNCERTAINTY": True,
}

AXIS_DOMAIN_RELEVANCE = {
    "name": "DOMAIN_RELEVANCE",
    "question": "Does the text semantically concern a tracked Hyperlex domain/family?",
    "values": [
        "DOMAIN_IRRELEVANT",
        "DOMAIN_RELEVANT",
        "DOMAIN_RELEVANCE_UNCERTAIN",
    ],
    "must_not_determine": "evidence_sufficiency",
}

AXIS_EVIDENCE_RELATION = {
    "name": "EVIDENCE_RELATION",
    "question": (
        "Does the text assert, instantiate, or clearly express the semantic "
        "relation/core required to count as evidence?"
    ),
    "values": [
        "NO_EVIDENCE_RELATION",
        "EVIDENCE_RELATION_PRESENT",
        "EVIDENCE_RELATION_UNCERTAIN",
    ],
    "must_not_imply_from": "domain_relevant_lexeme_alone",
}

AXIS_SEMANTIC_RESOLVABILITY = {
    "name": "SEMANTIC_RESOLVABILITY",
    "question": "Is the evidence judgment semantically resolvable from the text?",
    "values": ["RESOLVABLE", "UNRESOLVABLE"],
    "distinct_from": "model_confidence",
}

EVIDENCE_RELATION_CONTRACT = {
    "label": "EVIDENCE_RELATION_PRESENT",
    "requires_more_than": [
        "domain_membership",
        "lexeme_occurrence",
        "family_associated_token_alone",
        "entity_or_name_alone",
        "category_label_alone",
        "dictionary_headword_alone",
        "topic_mention_alone",
        "unasserted_list_item_without_relation",
    ],
    "sufficient_forms": [
        "explicit_predicate_or_relation",
        "asserted_action_or_state",
        "clear_semantic_proposition",
        "context_establishing_required_evidence_core",
    ],
    "insufficient_forms": [
        "isolated_category_label",
        "dictionary_headword_alone",
        "topic_mention",
        "family_associated_token_alone",
        "entity_name_alone",
        "unasserted_list_item_where_relation_absent",
    ],
    "source_independent": True,
}

SHORT_ATOM_SEMANTIC_RULE = {
    "ban_short_inputs": False,
    "auto_none_for_dictionary_atoms": False,
    "EVIDENCE_PRESENT_when": (
        "1–4 token span still asserts/instantiates the required evidence "
        "relation/core (e.g. compact proposition, asserted state/action, or "
        "explicit affiliation/attribute that satisfies the evidence contract)"
    ),
    "DOMAIN_RELEVANT_NO_RELATION_when": (
        "1–4 token span names a tracked domain/family/lexeme without asserting "
        "the required relation (headword, category mention, bare cue token)"
    ),
    "decision_basis": "semantic_not_length",
}

RELATION_TAXONOMY_CANDIDATES = [
    "ASSERTED_STATE",
    "ASSERTED_ACTION",
    "ASSERTED_RELATION",
    "EXPLICIT_ATTRIBUTE",
    "EXPLICIT_AFFILIATION",
    "EXPLICIT_EVALUATION",
    "EXPLICIT_INTENT",
    "CATEGORY_MENTION_ONLY",
    "LEXEME_ONLY",
    "NONASSERTED_CONTEXT",
    "NEGATED_RELATION",
    "UNRESOLVED",
]

# Subtype → primitive recoverability without new inference.
# status: DETERMINISTIC | PARTIALLY_DETERMINISTIC | NOT_DETERMINABLE
SUBTYPE_AXIS_RECOVERABILITY: dict[str, dict[str, Any]] = {
    "POSITIVE_EVIDENCE": {
        "status": "DETERMINISTIC",
        "domain_relevant": 1,
        "evidence_relation_present": 1,
        "semantic_resolvable": 1,
        "basis": "final=EVIDENCE_PRESENT + required_evidence_present=true + nonempty active_family_support",
    },
    "ORDINARY_DOMAIN_NONE": {
        "status": "DETERMINISTIC",
        "domain_relevant": 1,
        "evidence_relation_present": 0,
        "semantic_resolvable": 1,
        "basis": (
            "subtype encodes in-domain ordinary negative; "
            "missing_required_semantics includes active_family_evidence_absent; "
            "final=NO_EVIDENCE"
        ),
    },
    "NEAR_DOMAIN_NONE": {
        "status": "DETERMINISTIC",
        "domain_relevant": 1,
        "evidence_relation_present": 0,
        "semantic_resolvable": 1,
        "basis": (
            "subtype encodes near-domain negative with family evidence absent; "
            "final=NO_EVIDENCE"
        ),
    },
    "HARD_NONE": {
        "status": "DETERMINISTIC",
        "domain_relevant": 1,
        "evidence_relation_present": 0,
        "semantic_resolvable": 1,
        "basis": (
            "paired/hard negatives retain domain adjacency while "
            "active_family_evidence_absent; final=NO_EVIDENCE"
        ),
    },
    "LEXICAL_LOOKALIKE_NONE": {
        "status": "DETERMINISTIC",
        "domain_relevant": 1,
        "evidence_relation_present": 0,
        "semantic_resolvable": 1,
        "basis": (
            "lookalike of domain-positive lexeme/surface without asserted "
            "evidence relation; final=NO_EVIDENCE"
        ),
    },
    "SHORT_ATOM_NONE": {
        "status": "DETERMINISTIC",
        "domain_relevant": 1,
        "evidence_relation_present": 0,
        "semantic_resolvable": 1,
        "basis": (
            "matched short-atom domain cue without family evidence relation; "
            "all V1R1 rows paired + active_family_evidence_absent; "
            "final=NO_EVIDENCE — the diagnosed failure mode"
        ),
    },
    "GENERIC_NONE": {
        "status": "NOT_DETERMINABLE",
        "domain_relevant": None,
        "evidence_relation_present": 0,
        "semantic_resolvable": 1,
        "basis": (
            "ontology admits GENERIC_NONE as possible DOMAIN_IRRELEVANT bucket, "
            "but V1R1 contains zero rows; cannot assign domain_relevant without "
            "settlement if/when present"
        ),
    },
    "AMBIGUOUS_EVIDENCE": {
        "status": "PARTIALLY_DETERMINISTIC",
        "domain_relevant": None,
        "evidence_relation_present": None,
        "semantic_resolvable": 0,
        "basis": (
            "final=UNCERTAIN + required_evidence_present=uncertain + "
            "missing evidence_sufficiency_unresolved ⇒ semantic_resolvable=0; "
            "which of domain/relation/context is unresolved is not unique from "
            "subtype alone (notes codes are optional secondary signal)"
        ),
    },
}

UNCERTAIN_NOTE_CAUSE_MAP = {
    "INSUFFICIENT_CONTEXT": "CONTEXT_INSUFFICIENT",
    "MULTIPLE_PLAUSIBLE_INTERPRETATIONS": "MULTIPLE_SEMANTIC_READINGS",
    "UNRESOLVED_SOURCE_MEANING": "DOMAIN_UNCERTAIN",
    "PARTIAL_REQUIRED_CORE": "RELATION_UNCERTAIN",
}


def canonical_decision_logic() -> dict[str, Any]:
    return {
        "graph": {
            "DOMAIN_RELEVANCE": {
                "DOMAIN_IRRELEVANT": "NO_EVIDENCE",
                "DOMAIN_RELEVANT": "inspect_EVIDENCE_RELATION",
                "DOMAIN_RELEVANCE_UNCERTAIN": "UNCERTAIN",
            },
            "EVIDENCE_RELATION": {
                "NO_EVIDENCE_RELATION": "NO_EVIDENCE",
                "EVIDENCE_RELATION_PRESENT": "EVIDENCE_PRESENT",
                "EVIDENCE_RELATION_UNCERTAIN": "UNCERTAIN",
            },
            "SEMANTIC_RESOLVABILITY": {
                "UNRESOLVABLE": "UNCERTAIN",
                "RESOLVABLE": "continue",
            },
        },
        "factorized": {
            "domain_relevant": "{0,1,MASKED/UNCERTAIN}",
            "evidence_relation_present": "{0,1,MASKED/UNCERTAIN}",
            "semantic_resolvable": "{0,1}",
            "deterministic_decision": [
                "if semantic_resolvable == 0: UNCERTAIN",
                "elif domain_relevant == 0: NO_EVIDENCE",
                "elif evidence_relation_present == 0: NO_EVIDENCE",
                "elif domain_relevant == 1 and evidence_relation_present == 1: EVIDENCE_PRESENT",
                "else: UNCERTAIN",
            ],
        },
        "neural_architecture": "UNSPECIFIED_IN_THIS_PASS",
    }


def backward_map_final_label(label: str) -> dict[str, Any]:
    label = str(label)
    if label == "EVIDENCE_PRESENT":
        return {
            "unique": True,
            "implies": {
                "domain_relevant": 1,
                "evidence_relation_present": 1,
                "semantic_resolvable": 1,
            },
        }
    if label == "NO_EVIDENCE":
        return {
            "unique": False,
            "implies": {
                "semantic_resolvable": 1,
                "evidence_relation_present": 0,
            },
            "does_not_uniquely_imply": [
                "domain_relevant=0",
                "domain_relevant=1 with evidence_relation_present=0",
            ],
            "note": (
                "final NO_EVIDENCE alone cannot choose among DOMAIN_IRRELEVANT vs "
                "DOMAIN_RELEVANT_NO_RELATION; subtype is required"
            ),
        }
    if label == "UNCERTAIN":
        return {
            "unique": False,
            "implies": {"semantic_resolvable": 0},
            "does_not_uniquely_imply": [
                "which primitive axis is unresolved",
                "domain_relevant value",
                "evidence_relation_present value",
            ],
        }
    return {"unique": False, "implies": {}, "error": "unknown_label"}


def uncertain_note_cause(notes: str) -> str | None:
    match = re.search(r"v5_uncertain_[^:]+:([A-Z_]+)", str(notes or ""))
    if not match:
        return None
    return UNCERTAIN_NOTE_CAUSE_MAP.get(match.group(1))


def derive_primitives(row: Mapping[str, Any]) -> dict[str, Any]:
    """Derive axis support from existing gold only — no model inference."""
    subtype = str(row.get("evidence_subtype") or "")
    label = str(row.get("evidence_label") or "")
    required = str(row.get("required_evidence_present") or "").lower()
    missing = [str(x) for x in (row.get("missing_required_semantics") or [])]
    rec = SUBTYPE_AXIS_RECOVERABILITY.get(subtype)

    out: dict[str, Any] = {
        "subtype": subtype,
        "final_label": label,
        "domain_relevant": {
            "status": "NOT_APPLICABLE",
            "value": None,
        },
        "evidence_relation_present": {
            "status": "NOT_APPLICABLE",
            "value": None,
        },
        "semantic_resolvable": {
            "status": "NOT_APPLICABLE",
            "value": None,
        },
    }

    if label == "EVIDENCE_PRESENT" and subtype == "POSITIVE_EVIDENCE" and required == "true":
        out["domain_relevant"] = {"status": "DIRECTLY_SUPPORTED", "value": 1}
        out["evidence_relation_present"] = {"status": "DIRECTLY_SUPPORTED", "value": 1}
        out["semantic_resolvable"] = {"status": "DIRECTLY_SUPPORTED", "value": 1}
        return out

    if label == "UNCERTAIN" and subtype == "AMBIGUOUS_EVIDENCE":
        out["semantic_resolvable"] = {"status": "DIRECTLY_SUPPORTED", "value": 0}
        cause = uncertain_note_cause(str(row.get("notes") or ""))
        # Domain/relation remain unsettled without human settlement.
        out["domain_relevant"] = {
            "status": "REQUIRES_NEW_HUMAN_SETTLEMENT",
            "value": None,
            "optional_note_cause": cause,
        }
        out["evidence_relation_present"] = {
            "status": "REQUIRES_NEW_HUMAN_SETTLEMENT",
            "value": None,
            "optional_note_cause": cause,
        }
        return out

    if label == "NO_EVIDENCE" and subtype in SUBTYPE_AXIS_RECOVERABILITY:
        if subtype == "GENERIC_NONE":
            out["evidence_relation_present"] = {
                "status": "RULE_DERIVABLE",
                "value": 0,
            }
            out["semantic_resolvable"] = {"status": "RULE_DERIVABLE", "value": 1}
            out["domain_relevant"] = {
                "status": "REQUIRES_NEW_HUMAN_SETTLEMENT",
                "value": None,
            }
            return out
        # All V1R1 NONE subtypes currently present are domain-adjacent negatives.
        if "active_family_evidence_absent" in missing or subtype.endswith("_NONE"):
            out["domain_relevant"] = {"status": "RULE_DERIVABLE", "value": 1}
            out["evidence_relation_present"] = {
                "status": "RULE_DERIVABLE",
                "value": 0,
            }
            out["semantic_resolvable"] = {"status": "RULE_DERIVABLE", "value": 1}
            if rec:
                out["subtype_recoverability_status"] = rec["status"]
            return out

    # Fallback: final-label partial implications only.
    back = backward_map_final_label(label)
    if "semantic_resolvable" in back.get("implies", {}):
        out["semantic_resolvable"] = {
            "status": "RULE_DERIVABLE",
            "value": back["implies"]["semantic_resolvable"],
        }
    if "evidence_relation_present" in back.get("implies", {}):
        out["evidence_relation_present"] = {
            "status": "RULE_DERIVABLE",
            "value": back["implies"]["evidence_relation_present"],
        }
    if "domain_relevant" in back.get("implies", {}):
        out["domain_relevant"] = {
            "status": "RULE_DERIVABLE",
            "value": back["implies"]["domain_relevant"],
        }
    else:
        out["domain_relevant"] = {
            "status": "REQUIRES_NEW_HUMAN_SETTLEMENT",
            "value": None,
        }
    return out


def audit_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    status_counts = {
        "domain_relevant": Counter(),
        "evidence_relation_present": Counter(),
        "semantic_resolvable": Counter(),
    }
    value_counts = {
        "domain_relevant": Counter(),
        "evidence_relation_present": Counter(),
        "semantic_resolvable": Counter(),
    }
    label_counts: Counter[str] = Counter()
    subtype_table = {}
    for subtype, meta in SUBTYPE_AXIS_RECOVERABILITY.items():
        n = sum(1 for r in rows if r.get("evidence_subtype") == subtype)
        subtype_table[subtype] = {**meta, "n_v1r1": n}

    uncertain_causes = Counter()
    for row in rows:
        label_counts[str(row.get("evidence_label") or "")] += 1
        derived = derive_primitives(row)
        for axis in status_counts:
            status_counts[axis][derived[axis]["status"]] += 1
            value_counts[axis][str(derived[axis]["value"])] += 1
        if row.get("evidence_label") == "UNCERTAIN":
            cause = uncertain_note_cause(str(row.get("notes") or ""))
            uncertain_causes[cause or "UNKNOWN"] += 1

    # Prefer single new primitive if domain + resolvable are already recoverable.
    n = len(rows)
    domain_ok = (
        status_counts["domain_relevant"]["DIRECTLY_SUPPORTED"]
        + status_counts["domain_relevant"]["RULE_DERIVABLE"]
    )
    relation_ok = (
        status_counts["evidence_relation_present"]["DIRECTLY_SUPPORTED"]
        + status_counts["evidence_relation_present"]["RULE_DERIVABLE"]
    )
    resolvable_ok = (
        status_counts["semantic_resolvable"]["DIRECTLY_SUPPORTED"]
        + status_counts["semantic_resolvable"]["RULE_DERIVABLE"]
    )
    domain_human = status_counts["domain_relevant"]["REQUIRES_NEW_HUMAN_SETTLEMENT"]
    relation_human = status_counts["evidence_relation_present"][
        "REQUIRES_NEW_HUMAN_SETTLEMENT"
    ]

    prefer_relation_only = (
        domain_ok >= int(0.94 * n)
        and resolvable_ok == n
        and relation_ok >= int(0.94 * n)
        and subtype_table.get("GENERIC_NONE", {}).get("n_v1r1", 0) == 0
    )

    return {
        "n_rows": n,
        "prefer_relation_only_decomposition": prefer_relation_only,
        "status_counts": {k: dict(v) for k, v in status_counts.items()},
        "value_counts": {k: dict(v) for k, v in value_counts.items()},
        "subtype_recoverability": subtype_table,
        "uncertain_note_causes": dict(uncertain_causes),
        "human_settlement_rows": {
            "domain_relevant": domain_human,
            "evidence_relation_present": relation_human,
            "semantic_resolvable": status_counts["semantic_resolvable"][
                "REQUIRES_NEW_HUMAN_SETTLEMENT"
            ],
        },
        "label_counts": dict(label_counts),
        "source": "live_v1r1_gold_field_audit",
    }


def candidate_objectives() -> dict[str, Any]:
    return {
        "A_predict_final_class_directly": {
            "semantic_correctness": "FAIL — conflates domain/relation/uncertainty",
            "required_new_annotation": "none",
            "v1r1_compatibility": "full (current)",
            "shortcut_risk": "high on SHORT_ATOM lexeme membership",
            "implementation_complexity": "already implemented",
            "viable": False,
        },
        "B_relation_plus_uncertainty": {
            "semantic_correctness": (
                "PASS for V1R1 failure mode if domain_relevant is fixed/derived "
                "as 1 for current NONE/PRESENT mass"
            ),
            "required_new_annotation": (
                "none new human gold — derive evidence_relation_present + "
                "semantic_resolvable from subtype/final gold"
            ),
            "v1r1_compatibility": "full via rule derivation",
            "shortcut_risk": "medium — still need careful short-atom relation definition",
            "implementation_complexity": "low–medium (objective/spec change)",
            "viable": True,
        },
        "C_domain_relation_resolvability": {
            "semantic_correctness": "PASS in general ontology",
            "required_new_annotation": (
                "domain_relevant needs DOMAIN_IRRELEVANT examples; V1R1 has none "
                "(GENERIC_NONE=0). Human settlement for UNCERTAIN axis split optional"
            ),
            "v1r1_compatibility": "partial — cannot supervise DOMAIN_IRRELEVANT on V1R1",
            "shortcut_risk": "lower if domain negatives exist; currently untrainable axis",
            "implementation_complexity": "high",
            "viable": False,
        },
        "D_relation_only_with_deterministic_metadata": {
            "semantic_correctness": (
                "PASS as minimum viable fix for diagnosed mismatch on V1R1"
            ),
            "required_new_annotation": "none — subtype+final gold suffice",
            "v1r1_compatibility": "full",
            "shortcut_risk": (
                "medium; mitigated by freezing EVIDENCE_RELATION_PRESENT contract "
                "and short-atom semantic rule"
            ),
            "implementation_complexity": "lowest among viable options",
            "viable": True,
            "preferred_when": "prefer_relation_only_decomposition=true",
        },
    }


def semantic_sufficiency_matrix(primary: str) -> dict[str, dict[str, bool]]:
    """Whether the chosen formulation can represent each case conceptually."""
    # RELATION_ONLY assumes domain_relevant known/derived; cannot alone express
    # domain-irrelevant vs domain-relevant-no-relation as distinct learnable
    # targets unless domain is supplied by metadata/rules.
    cases = [
        "domain_irrelevant_prose",
        "domain_relevant_lexeme_only",
        "domain_relevant_short_atom_with_explicit_relation",
        "domain_relevant_prose_with_no_asserted_relation",
        "explicit_positive_evidence",
        "negated_relation",
        "ambiguous_relation",
        "insufficient_context",
    ]
    if primary == "RELATION_ONLY_DECOMPOSITION":
        support = {
            "domain_irrelevant_prose": False,  # needs domain axis or GENERIC_NONE
            "domain_relevant_lexeme_only": True,
            "domain_relevant_short_atom_with_explicit_relation": True,
            "domain_relevant_prose_with_no_asserted_relation": True,
            "explicit_positive_evidence": True,
            "negated_relation": True,  # as NO_EVIDENCE_RELATION / resolvable
            "ambiguous_relation": True,  # via semantic_resolvable=0
            "insufficient_context": True,  # via semantic_resolvable=0
        }
    elif primary == "DOMAIN_PLUS_RELATION_DECOMPOSITION":
        support = {c: True for c in cases}
        support["ambiguous_relation"] = True
    elif primary == "DOMAIN_RELATION_RESOLVABILITY_DECOMPOSITION":
        support = {c: True for c in cases}
    else:
        support = {c: False for c in cases}
    return {
        case: {
            "representable": support[case],
            "notes": (
                "requires DOMAIN_IRRELEVANT supervision absent from V1R1"
                if case == "domain_irrelevant_prose" and primary == "RELATION_ONLY_DECOMPOSITION"
                else ""
            ),
        }
        for case in cases
    }


def decide_primary(audit: Mapping[str, Any]) -> dict[str, Any]:
    if audit.get("prefer_relation_only_decomposition"):
        primary = "RELATION_ONLY_DECOMPOSITION"
        reasons = [
            "V1R1 NONE subtypes are domain-adjacent; domain_relevant is rule-derivable as 1",
            "semantic_resolvable is directly/rule supported for all rows",
            "evidence_relation_present is rule-derivable from subtype+final gold",
            "diagnosed SHORT_ATOM failure is domain-relevant lexeme without relation",
            "three-axis redesign not justified until DOMAIN_IRRELEVANT mass exists",
        ]
    elif audit["human_settlement_rows"]["domain_relevant"] > 0 and (
        audit["status_counts"]["domain_relevant"].get("RULE_DERIVABLE", 0)
        + audit["status_counts"]["domain_relevant"].get("DIRECTLY_SUPPORTED", 0)
        < int(0.5 * int(audit["n_rows"]))
    ):
        primary = "DOMAIN_RELATION_RESOLVABILITY_DECOMPOSITION"
        reasons = ["domain axis not recoverable for most rows"]
    else:
        primary = "DOMAIN_PLUS_RELATION_DECOMPOSITION"
        reasons = ["relation alone insufficient given recoverability profile"]
    return {"primary_decomposition": primary, "reasons": reasons}


def supervision_requirement(primary: str, audit: Mapping[str, Any]) -> dict[str, Any]:
    # All trainable primitives for RELATION_ONLY are rule-derivable on V1R1.
    if primary == "RELATION_ONLY_DECOMPOSITION":
        return {
            "requirement": "NO_NEW_GOLD_REQUIRED",
            "materialize_derived_fields": [
                "evidence_relation_present",
                "semantic_resolvable",
                "domain_relevant_derived",
            ],
            "human_settlement": {
                "rows": "none required for V1R1 training primitives",
                "optional_future": (
                    "UNCERTAIN axis-cause split from notes is optional metadata, "
                    "not required to unblock the diagnosed mismatch"
                ),
            },
            "axes": {
                "evidence_relation_present": "derive from subtype+final gold",
                "semantic_resolvable": "derive from UNCERTAIN vs else",
                "domain_relevant": "derive as 1 for current V1R1 NONE/PRESENT mass",
            },
            "authorities": "existing subtype/final-gold/required_evidence_present contract",
        }
    return {
        "requirement": "PARTIAL_REANNOTATION_REQUIRED",
        "detail": audit.get("human_settlement_rows"),
    }


def dataset_consequence(primary: str) -> str:
    if primary == "RELATION_ONLY_DECOMPOSITION":
        return "ANNOTATION_ONLY_CHANGE"
    if primary in {
        "DOMAIN_PLUS_RELATION_DECOMPOSITION",
        "DOMAIN_RELATION_RESOLVABILITY_DECOMPOSITION",
    }:
        return "ANNOTATION_AND_NEW_DATA_REQUIRED"
    return "NO_DATASET_CHANGE"


def next_action_for(primary: str) -> str:
    if primary == "RELATION_ONLY_DECOMPOSITION":
        return "SPEC_STAGE_A_FACTORIZED_OBJECTIVE"
    if primary == "EXISTING_LABELS_SUFFICIENT":
        return "STOP_AND_ARCHIVE_V5"
    if primary == "SEMANTIC_ONTOLOGY_INSUFFICIENT":
        return "EXTEND_STAGE_A_SEMANTIC_ONTOLOGY"
    return "DESIGN_STAGE_A_REANNOTATION_PROTOCOL"


def none_semantic_reason_recommendation() -> dict[str, Any]:
    return {
        "mutate_current_subtype_ontology": False,
        "recommendation": (
            "Keep surface/hardness subtypes; add optional parallel semantic_reason "
            "field in a future annotation protocol: DOMAIN_IRRELEVANT | "
            "DOMAIN_RELEVANT_NO_RELATION | NEGATED_RELATION | "
            "NONASSERTED_REFERENCE | INSUFFICIENT_CONTEXT"
        ),
        "v1r1_current_none_mass_interprets_as": "DOMAIN_RELEVANT_NO_RELATION",
    }


def relation_taxonomy_recommendation() -> dict[str, Any]:
    return {
        "full_taxonomy_necessary_now": False,
        "recommendation": "BINARY_EVIDENCE_RELATION_PRESENCE",
        "values": [
            "NO_EVIDENCE_RELATION",
            "EVIDENCE_RELATION_PRESENT",
            "EVIDENCE_RELATION_UNCERTAIN",
        ],
        "deferred_taxonomy": RELATION_TAXONOMY_CANDIDATES,
        "reason": (
            "Smallest contract that resolves GATE1_SEMANTIC_TARGET_MISMATCH; "
            "finer asserted-state/action/relation tags can wait"
        ),
    }


def frozen_v1r1_audit() -> dict[str, Any]:
    """Return the sealed V1R1 recoverability audit without reading private rows."""
    subtype_table = {}
    for subtype, meta in SUBTYPE_AXIS_RECOVERABILITY.items():
        subtype_table[subtype] = {
            **meta,
            "n_v1r1": int(FROZEN_V1R1_SUBTYPE_COUNTS.get(subtype, 0)),
        }
    return {
        "n_rows": sum(FROZEN_V1R1_LABEL_COUNTS.values()),
        "prefer_relation_only_decomposition": True,
        "status_counts": {
            axis: dict(counts) for axis, counts in FROZEN_V1R1_STATUS_COUNTS.items()
        },
        "value_counts": {
            axis: dict(counts) for axis, counts in FROZEN_V1R1_VALUE_COUNTS.items()
        },
        "subtype_recoverability": subtype_table,
        "uncertain_note_causes": dict(FROZEN_V1R1_UNCERTAIN_NOTE_CAUSES),
        "human_settlement_rows": {
            "domain_relevant": FROZEN_V1R1_STATUS_COUNTS["domain_relevant"][
                "REQUIRES_NEW_HUMAN_SETTLEMENT"
            ],
            "evidence_relation_present": FROZEN_V1R1_STATUS_COUNTS[
                "evidence_relation_present"
            ]["REQUIRES_NEW_HUMAN_SETTLEMENT"],
            "semantic_resolvable": 0,
        },
        "label_counts": dict(FROZEN_V1R1_LABEL_COUNTS),
        "source": "frozen_v1r1_gold_field_audit",
    }


def assemble_decomposition_receipt(audit: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Seal the decomposition receipt.

    When ``audit`` is supplied (live row audit), it is hard-pinned against the
    frozen V1R1 snapshot; the receipt body always uses the frozen audit so the
    receipt hash is stable offline.
    """
    if audit is not None:
        assert_audit_matches_frozen(audit)
    audit_payload = frozen_v1r1_audit()
    primary_payload = decide_primary(audit_payload)
    primary = primary_payload["primary_decomposition"]
    supervision = supervision_requirement(primary, audit_payload)
    dataset = dataset_consequence(primary)
    next_action = next_action_for(primary)
    receipt = {
        "DECOMPOSITION_RULE": DECOMPOSITION_RULE,
        "DECOMPOSITION_STATE": "SEALED",
        "DIAGNOSIS_RECEIPT_SHA256": DIAGNOSIS_RECEIPT_SHA256,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "FAILED_CHECKPOINT_SHA256": FAILED_CHECKPOINT_SHA256,
        "MODEL_WIDE_BEST": "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6",
        "MODEL_WIDE_BEST_MUTATED": False,
        "NEXT_ACTION": next_action,
        "NEXT_ACTION_AUTHORIZED": False,
        "PARENT_STAGE_A_BEST": PARENT_STAGE_A_BEST_SHA,
        "PRIMARY_DIAGNOSIS": PRIMARY_DIAGNOSIS,
        "PRIMARY_DECOMPOSITION": primary,
        "SPENT_RESERVE": SPENT_RESERVE,
        "SPENT_RESERVE_OVERLAP": SPENT_RESERVE_OVERLAP,
        "SPENT_RESERVE_STATUS": SPENT_RESERVE_STATUS,
        "STAGE_A_BEST": PARENT_STAGE_A_BEST_SHA,
        "STAGE_A_BEST_MUTATED": False,
        "TRAIN": False,
        "V1R1_DATASET_SHA256": AUTHORIZED_DATASET_SHA,
        "V1R1_MUTATED": False,
        "V1R1_READINESS_SHA256": AUTHORIZED_READINESS_SHA,
        "V1R1_SURFACE_RECEIPT_SHA256": AUTHORIZED_SURFACE_RECEIPT_SHA,
        "V1R2_CREATED": False,
        "architecture_change_justified": False,
        "architecture_neutrality": True,
        "audit": audit_payload,
        "axes": {
            "DOMAIN_RELEVANCE": AXIS_DOMAIN_RELEVANCE,
            "EVIDENCE_RELATION": AXIS_EVIDENCE_RELATION,
            "SEMANTIC_RESOLVABILITY": AXIS_SEMANTIC_RESOLVABILITY,
        },
        "backward_mapping": {
            "EVIDENCE_PRESENT": backward_map_final_label("EVIDENCE_PRESENT"),
            "NO_EVIDENCE": backward_map_final_label("NO_EVIDENCE"),
            "UNCERTAIN": backward_map_final_label("UNCERTAIN"),
        },
        "candidate_objectives": candidate_objectives(),
        "canonical_decision_logic": canonical_decision_logic(),
        "critical_distinctions": CRITICAL_DISTINCTIONS,
        "dataset_consequence": dataset,
        "evidence_relation_contract": EVIDENCE_RELATION_CONTRACT,
        "minimum_new_gold_requirement": supervision["requirement"],
        "next_action": next_action,
        "none_semantic_reason_recommendation": none_semantic_reason_recommendation(),
        "objective_change_justified": True,
        "preferred_objective": (
            "D_relation_only_with_deterministic_metadata"
            if primary == "RELATION_ONLY_DECOMPOSITION"
            else "C_domain_relation_resolvability"
        ),
        "primary_reasons": primary_payload["reasons"],
        "relation_taxonomy_recommendation": relation_taxonomy_recommendation(),
        "schema": "hyperlex.classification.v5.stage_a_semantic_decomposition.v1",
        "semantic_defect_frozen": {
            "conflated_axis": "NO_EVIDENCE_vs_POSSIBLE_EVIDENCE",
            "conflates": [
                "domain_relevance",
                "lexical_family_cues",
                "assertion_presence",
                "relation_presence",
                "evidence_sufficiency",
                "semantic_uncertainty",
            ],
            "not_dataset_size": True,
            "primary_diagnosis": PRIMARY_DIAGNOSIS,
        },
        "semantic_sufficiency_matrix": semantic_sufficiency_matrix(primary),
        "short_atom_semantic_rule": SHORT_ATOM_SEMANTIC_RULE,
        "supervision_requirement": supervision,
        "uncertain_decomposition": {
            "distinguish_for_future_supervision": True,
            "required_to_unblock_now": False,
            "causes_observed_in_notes": dict(
                audit_payload.get("uncertain_note_causes") or {}
            ),
            "cause_classes": [
                "DOMAIN_UNCERTAIN",
                "RELATION_UNCERTAIN",
                "CONTEXT_INSUFFICIENT",
                "MULTIPLE_SEMANTIC_READINGS",
            ],
        },
    }
    receipt["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in receipt.items() if k != "receipt_sha256"})
    )
    return receipt


def assert_audit_matches_frozen(audit: Mapping[str, Any]) -> None:
    """Hard-pin live row audit against the sealed V1R1 recoverability snapshot."""
    frozen = frozen_v1r1_audit()
    if int(audit["n_rows"]) != int(frozen["n_rows"]):
        raise AssertionError("n_rows mismatch vs frozen V1R1 audit")
    if dict(audit.get("label_counts") or {}) != frozen["label_counts"]:
        raise AssertionError("label_counts mismatch vs frozen V1R1 audit")
    if audit["status_counts"] != frozen["status_counts"]:
        raise AssertionError("status_counts mismatch vs frozen V1R1 audit")
    if audit["value_counts"] != frozen["value_counts"]:
        raise AssertionError("value_counts mismatch vs frozen V1R1 audit")
    if dict(audit.get("uncertain_note_causes") or {}) != frozen["uncertain_note_causes"]:
        raise AssertionError("uncertain_note_causes mismatch vs frozen V1R1 audit")
    for subtype, meta in frozen["subtype_recoverability"].items():
        live_n = audit["subtype_recoverability"].get(subtype, {}).get("n_v1r1")
        if live_n != meta["n_v1r1"]:
            raise AssertionError(f"subtype count mismatch for {subtype}")
    if audit["prefer_relation_only_decomposition"] is not True:
        raise AssertionError("expected prefer_relation_only_decomposition")
    if audit["subtype_recoverability"]["GENERIC_NONE"]["n_v1r1"] != 0:
        raise AssertionError("GENERIC_NONE must remain 0 on V1R1")
