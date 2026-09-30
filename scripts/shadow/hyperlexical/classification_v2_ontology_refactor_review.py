"""Ontology refactor review for the three structural families.

Read-only recommendation. Does not mutate the active vocabulary, train, score
the reserve, move BEST, or rewrite historical artifacts.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

from .classification_v2 import (
    ACTIVE_FAMILY_VOCABULARY,
    ClassificationContractError,
    canonical_json,
    sha256_text,
)
from .classification_v2_boundary_redefinition import (
    HIGH_OVERLAP_COSINE,
    PHASE_D_AUDIT_SHA,
    PHASE_EXECUTION_SHA,
    REDEF_RULE,
)
from .classification_v2_boundary_tightening_v2 import (
    BOUNDARY_REDEFINITION_SHA,
    TIGHTEN_RULE,
)
from .classification_v2_separability_audit import (
    BEST_SHA,
    BOUNDARY_SHA,
    REPAIR_PRIMARY_SHA,
    SEPARATION_SHA,
    lexical_pair_report,
    token_document_counts,
)
from .holdout_guard import normalized_text_sha256

REVIEW_SCHEMA = "hyperlex.classification.v2.active_family_ontology_refactor_review.v1"
REVIEW_RULE = "HYPERLEX_ACTIVE_FAMILY_ONTOLOGY_REFACTOR_REVIEW_V1"
TIGHTENING_V2_SHA = "8c9f88b0431b3598d5336bdb7fa25b80e8201c2ad8487d5aea878997cb6aa5a9"
OVERLAY_SHA = "8a934806885fb939f8b4ca26f10ab5bc6600c495d3be77d5a2366dc6c62146e0"

FOCUS_FAMILIES: tuple[str, ...] = (
    "approval-disapproval",
    "social-status",
    "relationship-dating",
)
RECOMMENDATIONS = (
    "KEEP_SEPARATE",
    "MERGE_PAIR",
    "MERGE_THREE",
    "SPLIT_FAMILY",
    "REDEFINE_BOUNDARIES",
)

# Frozen decision thresholds — declared before applying to evidence.
PROBE_LEARNABLE_F1 = 0.60
CENTROID_COLLISION = HIGH_OVERLAP_COSINE  # 0.80
LEXICAL_DISTINCT_MAX_SHARED = 0.05
MERGED_LABEL = "social-evaluation"


def review_contract() -> dict[str, Any]:
    return {
        "applies_ontology_change": False,
        "best_sha256": BEST_SHA,
        "boundary_redefinition_rule": REDEF_RULE,
        "boundary_redefinition_sha256": BOUNDARY_REDEFINITION_SHA,
        "boundary_sha256": BOUNDARY_SHA,
        "boundary_tightening_rule": TIGHTEN_RULE,
        "boundary_tightening_v2_sha256": TIGHTENING_V2_SHA,
        "centroid_collision": CENTROID_COLLISION,
        "focus_families": list(FOCUS_FAMILIES),
        "historical_artifacts_rewritten": False,
        "jev": "OFF",
        "lexical_distinct_max_shared": LEXICAL_DISTINCT_MAX_SHARED,
        "moves_best": False,
        "opens_training_gate": False,
        "overlay_sha256": OVERLAY_SHA,
        "phase_d_audit_sha256": PHASE_D_AUDIT_SHA,
        "phase_execution_sha256": PHASE_EXECUTION_SHA,
        "probe_learnable_f1": PROBE_LEARNABLE_F1,
        "repair_primary_sha256": REPAIR_PRIMARY_SHA,
        "reserve_scored": False,
        "rule": REVIEW_RULE,
        "schema": REVIEW_SCHEMA,
        "separation_sha256": SEPARATION_SHA,
        "train": False,
    }


def summarize_family(
    family: str,
    *,
    contract: Mapping[str, Any] | None,
    texts: Sequence[str],
    pair_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    contract = contract or {}
    counts = token_document_counts(texts)
    positive = list(contract.get("positive_cues") or [])
    if not positive:
        positive = sorted(counts, key=lambda token: (-counts[token], token))[:8]
    nearest = []
    for row in pair_rows:
        other = row["family_b"] if row["family_a"] == family else row["family_a"] if row["family_b"] == family else None
        if other is None:
            continue
        flags = set(row.get("flags") or [])
        if flags & {"ONTOLOGY_OVERLAP", "REPRESENTATION_COLLAPSE", "LABEL_NOISE"}:
            emb = row.get("embedding") or {}
            nearest.append(
                {
                    "family": other,
                    "centroid_cosine": emb.get("centroid_cosine"),
                    "flags": sorted(flags),
                }
            )
    nearest.sort(key=lambda item: (-float(item.get("centroid_cosine") or -1.0), item["family"]))
    examples = [str(text)[:160] for text in texts[:5]]
    return {
        "exclusion_cues": list(contract.get("exclusion_cues") or [])[:6],
        "examples": examples,
        "family": family,
        "n_train_definitions": len(texts),
        "nearest_collisions": nearest[:4],
        "positive_cues": list(positive)[:8],
        "required_semantic_core": list(contract.get("required_semantic_core") or [])[:8],
    }


def _pair_row(
    pair_rows: Sequence[Mapping[str, Any]], family_a: str, family_b: str
) -> Mapping[str, Any] | None:
    for row in pair_rows:
        names = {row.get("family_a"), row.get("family_b")}
        if names == {family_a, family_b}:
            return row
    return None


def classify_unique_and_ambiguous(
    texts_a: Sequence[str],
    texts_b: Sequence[str],
    *,
    cues_a: Sequence[str],
    cues_b: Sequence[str],
) -> dict[str, Any]:
    def hits(text: str, cues: Sequence[str]) -> int:
        lowered = str(text).lower()
        return sum(1 for cue in cues if str(cue).lower() in lowered)

    unique_a = unique_b = ambiguous = neither = 0
    for text in texts_a:
        a, b = hits(text, cues_a), hits(text, cues_b)
        if a and b:
            ambiguous += 1
        elif a and not b:
            unique_a += 1
        elif b and not a:
            # gold-a text matching only b cues
            ambiguous += 1
        else:
            neither += 1
    for text in texts_b:
        a, b = hits(text, cues_a), hits(text, cues_b)
        if a and b:
            ambiguous += 1
        elif b and not a:
            unique_b += 1
        elif a and not b:
            ambiguous += 1
        else:
            neither += 1
    return {
        "ambiguous_rows": ambiguous,
        "neither_core_rows": neither,
        "unique_a": unique_a,
        "unique_b": unique_b,
        "unique_total": unique_a + unique_b,
    }


def analyze_pair(
    family_a: str,
    family_b: str,
    *,
    texts_a: Sequence[str],
    texts_b: Sequence[str],
    summary_a: Mapping[str, Any],
    summary_b: Mapping[str, Any],
    sealed_pair: Mapping[str, Any] | None,
) -> dict[str, Any]:
    lexical = lexical_pair_report(texts_a, texts_b)
    sealed_pair = sealed_pair or {}
    emb = sealed_pair.get("embedding") or {}
    probe = sealed_pair.get("probe") or {}
    flags = list(sealed_pair.get("flags") or [])
    cues_a = list(summary_a.get("required_semantic_core") or []) + list(
        summary_a.get("positive_cues") or []
    )[:4]
    cues_b = list(summary_b.get("required_semantic_core") or []) + list(
        summary_b.get("positive_cues") or []
    )[:4]
    assign = classify_unique_and_ambiguous(texts_a, texts_b, cues_a=cues_a, cues_b=cues_b)
    centroid = emb.get("centroid_cosine")
    probe_f1 = probe.get("f1")
    shared_ratio = float(lexical.get("shared_token_ratio") or 0.0)
    learnable = (
        probe.get("status") == "OK"
        and probe_f1 is not None
        and float(probe_f1) >= PROBE_LEARNABLE_F1
        and centroid is not None
        and float(centroid) < CENTROID_COLLISION
    )
    lexically_distinct = (
        shared_ratio <= LEXICAL_DISTINCT_MAX_SHARED
        and bool(lexical.get("tokens_enriched_in_a"))
        and bool(lexical.get("tokens_enriched_in_b"))
    )
    collapsed = "REPRESENTATION_COLLAPSE" in flags and "ONTOLOGY_OVERLAP" in flags
    return {
        "boundary_overlap": {
            "centroid_cosine": centroid,
            "cross_family_similarity": emb.get("cross_family_similarity"),
            "flags": flags,
            "nearest_neighbor_confusion_a": emb.get("nearest_neighbor_confusion_a"),
            "nearest_neighbor_confusion_b": emb.get("nearest_neighbor_confusion_b"),
        },
        "distinct_semantics": {
            "a": list(lexical.get("tokens_enriched_in_a") or [])[:8],
            "b": list(lexical.get("tokens_enriched_in_b") or [])[:8],
        },
        "family_a": family_a,
        "family_b": family_b,
        "inherently_ambiguous_rows": assign["ambiguous_rows"],
        "learnable": learnable,
        "lexically_distinct": lexically_distinct,
        "pairwise_probe_separability": {
            "accuracy": probe.get("accuracy"),
            "f1": probe_f1,
            "n_train": probe.get("n_train"),
            "n_val": probe.get("n_val"),
            "status": probe.get("status"),
        },
        "representation_collapsed": collapsed,
        "rows_uniquely_assignable": assign["unique_total"],
        "shared_semantics": list(lexical.get("shared_high_frequency_tokens") or [])[:8],
        "shared_token_ratio": shared_ratio,
        "unique_assignable_detail": assign,
    }


def decide_recommendation(pair_analyses: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Deterministic primary recommendation from pairwise evidence."""
    by_key = {
        "||".join(sorted((row["family_a"], row["family_b"]))): row for row in pair_analyses
    }
    ad_ss = by_key["approval-disapproval||social-status"]
    ad_rd = by_key["approval-disapproval||relationship-dating"]
    ss_rd = by_key["relationship-dating||social-status"]

    learnable_n = sum(1 for row in pair_analyses if row["learnable"])
    if learnable_n == 3:
        return {
            "affected_families": list(FOCUS_FAMILIES),
            "primary_recommendation": "KEEP_SEPARATE",
            "proposed_resulting_labels": list(FOCUS_FAMILIES),
            "rationale": (
                "all three pairwise probes clear the learnability bar with centroid "
                "below collision; keep distinct labels"
            ),
        }

    # Prefer smallest merge that removes an unlearnable collapsed pair while
    # preserving a lexically distinct third family.
    unlearnable_collapsed = [
        row
        for row in pair_analyses
        if (not row["learnable"]) and row["representation_collapsed"]
    ]
    if (
        (not ad_ss["learnable"])
        and ad_ss["representation_collapsed"]
        and ss_rd["lexically_distinct"]
        and ad_rd["lexically_distinct"]
    ):
        return {
            "affected_families": ["approval-disapproval", "social-status"],
            "primary_recommendation": "MERGE_PAIR",
            "proposed_resulting_labels": [MERGED_LABEL, "relationship-dating"],
            "rationale": (
                "approval-disapproval vs social-status is not operationally learnable "
                f"(probe F1={ad_ss['pairwise_probe_separability'].get('f1')}, "
                f"centroid={ad_ss['boundary_overlap'].get('centroid_cosine')}) after two "
                "boundary-cleaning passes; relationship-dating remains lexically distinct "
                "from both and should stay separate"
            ),
        }

    if len(unlearnable_collapsed) >= 3 and not any(row["lexically_distinct"] for row in pair_analyses):
        return {
            "affected_families": list(FOCUS_FAMILIES),
            "primary_recommendation": "MERGE_THREE",
            "proposed_resulting_labels": ["social-relational-evaluation"],
            "rationale": (
                "all three pairs are collapsed and none retain lexical distinctness; "
                "merge the trio"
            ),
        }

    # Internal split only when one family is the sole collapsed peer and has mixed cores.
    if learnable_n <= 1:
        return {
            "affected_families": ["approval-disapproval", "social-status"],
            "primary_recommendation": "MERGE_PAIR",
            "proposed_resulting_labels": [MERGED_LABEL, "relationship-dating"],
            "rationale": (
                "default smallest refactor: merge the densest unlearnable pair "
                "(approval-disapproval, social-status); keep relationship-dating"
            ),
        }

    return {
        "affected_families": list(FOCUS_FAMILIES),
        "primary_recommendation": "REDEFINE_BOUNDARIES",
        "proposed_resulting_labels": list(FOCUS_FAMILIES),
        "rationale": (
            "labels remain conceptually valid but current evidence underspecifies "
            "admission boundaries; redefine before merge"
        ),
    }


def build_semantic_definitions(recommendation: Mapping[str, Any]) -> dict[str, Any]:
    primary = recommendation["primary_recommendation"]
    if primary == "MERGE_PAIR":
        return {
            MERGED_LABEL: {
                "definition": (
                    "Lexical items whose primary sense encodes social standing, rank, "
                    "prestige, hierarchy, or evaluative approval/disapproval directed at "
                    "persons or statuses (praise, pejoration, honorific rank language)."
                ),
                "required_core": [
                    "status",
                    "rank",
                    "prestige",
                    "hierarchy",
                    "derogatory",
                    "endearing",
                    "insult",
                    "pejorative",
                    "praise",
                    "honorific",
                ],
                "excludes": [
                    "romantic relationship",
                    "courtship",
                    "dating partner",
                    "spouse",
                ],
            },
            "relationship-dating": {
                "definition": (
                    "Lexical items whose primary sense encodes romantic involvement, "
                    "dating, courtship, or partner relations."
                ),
                "required_core": [
                    "romantic",
                    "dating",
                    "courtship",
                    "boyfriend",
                    "girlfriend",
                    "spouse",
                    "marriage",
                    "partner",
                ],
                "excludes": [
                    "social status",
                    "prestige hierarchy",
                    "derogatory insult",
                ],
            },
        }
    if primary == "MERGE_THREE":
        return {
            "social-relational-evaluation": {
                "definition": (
                    "Broad social/relational evaluation covering status, approval, and "
                    "intimate-relation senses pending later re-carve."
                ),
                "required_core": ["social", "relationship", "status", "romantic", "approval"],
                "excludes": [],
            }
        }
    return {
        family: {
            "definition": f"Retain current operator definition for {family}.",
            "required_core": [],
            "excludes": [],
        }
        for family in recommendation.get("proposed_resulting_labels") or FOCUS_FAMILIES
    }


def build_migration_mapping(recommendation: Mapping[str, Any]) -> dict[str, Any]:
    primary = recommendation["primary_recommendation"]
    if primary == "MERGE_PAIR":
        mapping = {
            "approval-disapproval": MERGED_LABEL,
            "social-status": MERGED_LABEL,
            "relationship-dating": "relationship-dating",
        }
        compatibility = {
            "approval-disapproval": MERGED_LABEL,
            "social-status": MERGED_LABEL,
            "relationship-dating": "relationship-dating",
        }
        for family in ACTIVE_FAMILY_VOCABULARY:
            if family not in compatibility:
                compatibility[family] = family
        return {
            "compatibility_map": compatibility,
            "migration_mapping": mapping,
            "new_families_added": [MERGED_LABEL],
            "deprecated_families": ["approval-disapproval", "social-status"],
            "split_pending": [],
        }
    if primary == "MERGE_THREE":
        mapping = {family: "social-relational-evaluation" for family in FOCUS_FAMILIES}
        compatibility = {family: family for family in ACTIVE_FAMILY_VOCABULARY}
        for family in FOCUS_FAMILIES:
            compatibility[family] = "social-relational-evaluation"
        return {
            "compatibility_map": compatibility,
            "migration_mapping": mapping,
            "new_families_added": ["social-relational-evaluation"],
            "deprecated_families": list(FOCUS_FAMILIES),
            "split_pending": [],
        }
    compatibility = {family: family for family in ACTIVE_FAMILY_VOCABULARY}
    return {
        "compatibility_map": compatibility,
        "migration_mapping": {family: family for family in FOCUS_FAMILIES},
        "new_families_added": [],
        "deprecated_families": [],
        "split_pending": [],
    }


def estimate_impacts(
    recommendation: Mapping[str, Any],
    *,
    support_train: Mapping[str, int],
    support_val: Mapping[str, int],
    pair_analyses: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    primary = recommendation["primary_recommendation"]
    rows_affected = sum(support_train.get(family, 0) for family in recommendation["affected_families"])
    val_affected = sum(support_val.get(family, 0) for family in recommendation["affected_families"])
    if primary == "MERGE_PAIR":
        merged_train = support_train.get("approval-disapproval", 0) + support_train.get(
            "social-status", 0
        )
        merged_val = support_val.get("approval-disapproval", 0) + support_val.get("social-status", 0)
        support_after = {
            MERGED_LABEL: {"train": merged_train, "val": merged_val},
            "relationship-dating": {
                "train": support_train.get("relationship-dating", 0),
                "val": support_val.get("relationship-dating", 0),
            },
        }
        # Expect removal of the AD-SS high-overlap pair; RD pairs may remain.
        expected_overlap = (
            "Removes the densest approval-disapproval↔social-status collision pair from the "
            "active vocabulary; relationship-dating pairwise collisions remain until "
            "post-merge overlap reseal."
        )
    elif primary == "MERGE_THREE":
        support_after = {
            "social-relational-evaluation": {
                "train": sum(support_train.get(family, 0) for family in FOCUS_FAMILIES),
                "val": sum(support_val.get(family, 0) for family in FOCUS_FAMILIES),
            }
        }
        expected_overlap = "Removes all three structural pairs by collapsing the trio."
    else:
        support_after = {
            family: {"train": support_train.get(family, 0), "val": support_val.get(family, 0)}
            for family in FOCUS_FAMILIES
        }
        expected_overlap = "No vocabulary change; overlap expected unchanged until data work."
    return {
        "checkpoint_compatibility_impact": {
            "historical_best_unchanged": True,
            "best_sha256": BEST_SHA,
            "note": (
                "Historical BEST and sealed boundary/separation artifacts stay as-is. "
                "A future applied ontology change needs a new surface export + readiness "
                "rerun; old family logits map via compatibility_map."
            ),
        },
        "expected_overlap_impact": expected_overlap,
        "rows_affected_train": rows_affected,
        "rows_affected_val": val_affected,
        "support_after_proposed": support_after,
        "support_before": {
            family: {
                "train": support_train.get(family, 0),
                "val": support_val.get(family, 0),
            }
            for family in FOCUS_FAMILIES
        },
        "training_gate_remains_closed": True,
        "future_reopen_requirements": [
            "apply approved ontology change to surface vocabulary",
            "all resulting families have training support",
            "all resulting families have validation support",
            "overlap gate rerun",
            "readiness rerun",
        ],
        "pair_learnability": {
            "||".join(sorted((row["family_a"], row["family_b"]))): {
                "learnable": row["learnable"],
                "lexically_distinct": row["lexically_distinct"],
                "probe_f1": (row.get("pairwise_probe_separability") or {}).get("f1"),
                "centroid_cosine": (row.get("boundary_overlap") or {}).get("centroid_cosine"),
            }
            for row in pair_analyses
        },
    }


def next_engineering_action(artifact: Mapping[str, Any]) -> str:
    primary = artifact.get("primary_recommendation")
    if primary == "MERGE_PAIR":
        return (
            "APPLY_ONTOLOGY_MERGE_PAIR — operator-approve merging approval-disapproval and "
            "social-status into social-evaluation; migrate surface labels via compatibility "
            "map; rerun overlap + readiness before any training. Do not train yet."
        )
    if primary == "MERGE_THREE":
        return (
            "APPLY_ONTOLOGY_MERGE_THREE — operator-approve trio merge; migrate labels; "
            "rerun overlap + readiness before any training. Do not train yet."
        )
    if primary == "KEEP_SEPARATE":
        return (
            "RESUME_BOUNDARY_OR_DATA_WORK — ontology kept; acquire mutually exclusive "
            "definitions for the trio. Do not train yet."
        )
    if primary == "SPLIT_FAMILY":
        return (
            "APPLY_ONTOLOGY_SPLIT — operator-approve the proposed split; migrate labels; "
            "rerun overlap + readiness. Do not train yet."
        )
    return (
        "REDEFINE_BOUNDARIES_THEN_RESEAL — rewrite admission contracts for the trio and "
        "reseal tightening before reconsidering merge. Do not train yet."
    )


def assemble_ontology_review(payload: Mapping[str, Any]) -> dict[str, Any]:
    required = (
        "family_summaries",
        "pairwise_analyses",
        "recommendation",
        "semantic_definitions",
        "migration",
        "impacts",
    )
    for key in required:
        if key not in payload:
            raise ClassificationContractError("ONTOLOGY_REFACTOR_REVIEW_UNAVAILABLE", key)
    recommendation = payload["recommendation"]
    if recommendation.get("primary_recommendation") not in RECOMMENDATIONS:
        raise ClassificationContractError("ONTOLOGY_REFACTOR_REVIEW_UNAVAILABLE", "recommendation")
    contract = review_contract()
    artifact = {
        "applies_ontology_change": False,
        "best_sha256": BEST_SHA,
        "boundary_redefinition_sha256": BOUNDARY_REDEFINITION_SHA,
        "boundary_sha256": BOUNDARY_SHA,
        "boundary_tightening_v2_sha256": TIGHTENING_V2_SHA,
        "compatibility_map": payload["migration"]["compatibility_map"],
        "contract": contract,
        "deprecated_families": payload["migration"]["deprecated_families"],
        "family_summaries": payload["family_summaries"],
        "focus_families": list(FOCUS_FAMILIES),
        "historical_artifacts_rewritten": False,
        "impacts": payload["impacts"],
        "jev": "OFF",
        "migration_mapping": payload["migration"]["migration_mapping"],
        "moves_best": False,
        "new_families_added": payload["migration"]["new_families_added"],
        "opens_training_gate": False,
        "ontology_review_state": "SEALED",
        "overlay_sha256": OVERLAY_SHA,
        "pairwise_analyses": payload["pairwise_analyses"],
        "phase_d_audit_sha256": PHASE_D_AUDIT_SHA,
        "phase_execution_sha256": PHASE_EXECUTION_SHA,
        "primary_recommendation": recommendation["primary_recommendation"],
        "proposed_resulting_labels": recommendation["proposed_resulting_labels"],
        "rationale": recommendation["rationale"],
        "affected_families": recommendation["affected_families"],
        "repair_primary_sha256": REPAIR_PRIMARY_SHA,
        "reserve_scored": False,
        "schema": REVIEW_SCHEMA,
        "semantic_definitions": payload["semantic_definitions"],
        "separation_sha256": SEPARATION_SHA,
        "split_pending": payload["migration"]["split_pending"],
        "train": False,
        "training_gate": "CLOSED",
    }
    artifact["next_engineering_action"] = next_engineering_action(artifact)
    artifact["artifact_sha256"] = sha256_text(
        canonical_json({key: value for key, value in artifact.items() if key != "artifact_sha256"})
    )
    return artifact
