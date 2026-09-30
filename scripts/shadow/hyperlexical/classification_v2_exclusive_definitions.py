"""Exclusive-definition pass after boundary redefinition.

Replaces/removes training definitions that still produce cosine>=0.80
cross-family collisions under the frozen encoder, then admits mutually
exclusive Wiktionary senses. Does not train, score the reserve, move BEST,
or mutate historical boundary artifacts / the active ontology.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

from .classification_v2 import (
    ACTIVE_FAMILY_VOCABULARY,
    ClassificationContractError,
    canonical_json,
    sha256_text,
)
from .classification_v2_boundary_redefinition import (
    FAMILY_SEMANTIC_CORES,
    HIGH_OVERLAP_COSINE,
    MATERIAL_OVERLAP_REDUCTION,
    OVERLAY_SHA as PHASE_OVERLAY_SHA,
    PHASE_D_AUDIT_SHA,
    PHASE_EXECUTION_SHA,
    PRESERVED_NOISE_COUNTS,
    REDEF_RULE,
    _tokens,
    redefinition_contract,
)
from .classification_v2_separability_audit import (
    BEST_SHA,
    BOUNDARY_SHA,
    COLLAPSE_CLUSTER,
    REPAIR_PRIMARY_SHA,
    SEPARATION_SHA,
    SPARSE_FOCUS,
)

EXCLUSIVE_SCHEMA = "hyperlex.classification.v2.active_family_exclusive_definitions.v1"
EXCLUSIVE_RULE = "HYPERLEX_ACTIVE_FAMILY_EXCLUSIVE_DEFINITION_PASS_V1"
BOUNDARY_REDEFINITION_SHA = "4757d46aa7f0c95732378d5f710cbd1a28d048f60bee2fc35dfb6d5c0fe8cad1"

# Families that may lose colliding rows without replacement (large support).
SACRIFICIAL_FAMILIES = frozenset({"ai-native", "gaming-meta", "crypto-degen"})
# Prefer exclusive re-acquire for these collision-heavy small/medium families.
REACQUIRE_FAMILIES: tuple[str, ...] = (
    "approval-disapproval",
    "social-status",
    "relationship-dating",
    "internet-slang",
    "music-entertainment",
    "spiritual-mystic",
    "fashion-aesthetic",
    "identity-affiliation",
    "politics-civic",
    "conflict-aggression",
    "technology-ai",
    "workplace-career",
    "sports-competition",
    "regional-cultural",
    "memetic",
    "betting-sharp",
)
MIN_FAMILY_SUPPORT = 1
SPARSE_FLOOR = 12
TARGET_EXCLUSIVE = 12


def exclusive_contract() -> dict[str, Any]:
    return {
        "best_sha256": BEST_SHA,
        "boundary_redefinition_rule": REDEF_RULE,
        "boundary_redefinition_sha256": BOUNDARY_REDEFINITION_SHA,
        "boundary_sha256": BOUNDARY_SHA,
        "encoder_updated": False,
        "high_overlap_cosine": HIGH_OVERLAP_COSINE,
        "historical_boundaries_mutated": False,
        "jev": "OFF",
        "material_overlap_reduction": MATERIAL_OVERLAP_REDUCTION,
        "moves_best": False,
        "mutates_ontology": False,
        "phase_d_audit_sha256": PHASE_D_AUDIT_SHA,
        "phase_execution_sha256": PHASE_EXECUTION_SHA,
        "phase_overlay_sha256": PHASE_OVERLAY_SHA,
        "repair_primary_sha256": REPAIR_PRIMARY_SHA,
        "reserve_scored": False,
        "rule": EXCLUSIVE_RULE,
        "schema": EXCLUSIVE_SCHEMA,
        "separation_sha256": SEPARATION_SHA,
        "sparse_floor": SPARSE_FLOOR,
        "target_exclusive_definitions": TARGET_EXCLUSIVE,
        "train": False,
    }


def core_hit_count(text: str, family: str) -> int:
    tokens = _tokens(text)
    return sum(1 for cue in FAMILY_SEMANTIC_CORES.get(family, ()) if cue in tokens)


def select_collision_replacements(
    collisions: Sequence[Mapping[str, Any]],
    *,
    support: Mapping[str, int],
    contracts: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Choose which colliding KEEP identities to remove/replace.

    Prefer sacrificial large families. Otherwise prefer the side with fewer
    semantic-core hits, then higher identity hash. Never propose a removal that
    would breach sparse floors or zero out a family.
    """
    del contracts  # reserved for future cue-aware ranking
    remaining = {family: int(support.get(family, 0)) for family in ACTIVE_FAMILY_VOCABULARY}
    doomed: dict[str, dict[str, Any]] = {}
    ordered = sorted(
        collisions,
        key=lambda row: (
            -float(row["cosine"]),
            row["family_a"],
            row["family_b"],
            row["identity_a"],
            row["identity_b"],
        ),
    )
    for row in ordered:
        a_fam, b_fam = row["family_a"], row["family_b"]
        a_id, b_id = row["identity_a"], row["identity_b"]
        if a_id in doomed or b_id in doomed:
            continue
        a_hits = int(row.get("core_hits_a") or 0)
        b_hits = int(row.get("core_hits_b") or 0)

        def _can_drop(family: str) -> bool:
            floor = SPARSE_FLOOR if family in SPARSE_FOCUS else MIN_FAMILY_SUPPORT
            return remaining[family] - 1 >= floor

        choice = None
        reason = None
        if a_fam in SACRIFICIAL_FAMILIES and _can_drop(a_fam) and b_fam not in SACRIFICIAL_FAMILIES:
            choice, reason = ("a", "sacrificial_large_family")
        elif b_fam in SACRIFICIAL_FAMILIES and _can_drop(b_fam) and a_fam not in SACRIFICIAL_FAMILIES:
            choice, reason = ("b", "sacrificial_large_family")
        elif a_fam in SACRIFICIAL_FAMILIES and b_fam in SACRIFICIAL_FAMILIES:
            if _can_drop(a_fam) and (not _can_drop(b_fam) or (a_hits, a_id) <= (b_hits, b_id)):
                choice, reason = ("a", "sacrificial_large_family_tie")
            elif _can_drop(b_fam):
                choice, reason = ("b", "sacrificial_large_family_tie")
        else:
            if a_hits < b_hits and _can_drop(a_fam):
                choice, reason = ("a", "fewer_core_hits")
            elif b_hits < a_hits and _can_drop(b_fam):
                choice, reason = ("b", "fewer_core_hits")
            elif _can_drop(a_fam) and (not _can_drop(b_fam) or a_id > b_id):
                choice, reason = ("a", "identity_tiebreak")
            elif _can_drop(b_fam):
                choice, reason = ("b", "identity_tiebreak")

        if choice is None:
            continue
        if choice == "a":
            family, identity, text = a_fam, a_id, row.get("text_a")
            peer = b_fam
        else:
            family, identity, text = b_fam, b_id, row.get("text_b")
            peer = a_fam
        doomed[identity] = {
            "cosine": float(row["cosine"]),
            "decision": "REPLACE" if family in REACQUIRE_FAMILIES else "DROP",
            "family": family,
            "identity": identity,
            "peer_family": peer,
            "reason": reason,
            "text": text,
        }
        remaining[family] -= 1
    return [doomed[key] for key in sorted(doomed)]


def exclusive_admission_ok(
    *,
    family: str,
    text: str,
    competitor_families: Sequence[str],
) -> bool:
    """Forbid competitor-dominant cores; prefer own-core evidence when present."""
    tokens = _tokens(text)
    own = FAMILY_SEMANTIC_CORES.get(family, ())
    own_hits = sum(1 for cue in own if cue in tokens)
    for competitor in competitor_families:
        if competitor == family:
            continue
        other = FAMILY_SEMANTIC_CORES.get(competitor, ())
        other_hits = sum(1 for cue in other if cue in tokens)
        if other_hits >= 2 and other_hits > own_hits:
            return False
    return True


def next_engineering_action(artifact: Mapping[str, Any]) -> str:
    gate = (artifact.get("training_gate") or {}).get("training_gate") or artifact.get("gate_status")
    if gate == "OPEN":
        return (
            "EXCLUSIVE_DEFINITIONS_CLEARED — run one clean classification-v2 training pass "
            "on the exclusive overlay KEEP set; do not score the reserve or move BEST until sealed."
        )
    return (
        "EXCLUSIVE_DEFINITIONS_STILL_COLLIDE — continue replacing structural collision "
        "identities / acquiring mutually exclusive senses for unresolved high-overlap pairs. "
        "Do not train, score the reserve, or move BEST."
    )


def assemble_exclusive_pass(payload: Mapping[str, Any]) -> dict[str, Any]:
    required = (
        "replacement_decisions",
        "acquired_rows",
        "support_pre",
        "support_post_overlay",
        "collision_pairs_pre",
        "overlay_sha256",
        "boundary_redefinition",
    )
    for key in required:
        if key not in payload:
            raise ClassificationContractError("EXCLUSIVE_DEFINITION_UNAVAILABLE", key)
    contract = exclusive_contract()
    redef = payload["boundary_redefinition"]
    artifact = {
        "acquired_count": len(payload["acquired_rows"]),
        "acquired_rows": payload["acquired_rows"],
        "best_sha256": BEST_SHA,
        "boundary_redefinition_sha256": redef.get("artifact_sha256"),
        "boundary_sha256": BOUNDARY_SHA,
        "collision_pairs_pre": payload["collision_pairs_pre"],
        "contract": contract,
        "encoder_updated": False,
        "exclusive_state": "SEALED",
        "historical_boundaries_mutated": False,
        "jev": "OFF",
        "moves_best": False,
        "mutates_ontology": False,
        "overlay_sha256": payload["overlay_sha256"],
        "phase_overlay_sha256": PHASE_OVERLAY_SHA,
        "preserved_noise_audit": PRESERVED_NOISE_COUNTS,
        "replacement_decisions": payload["replacement_decisions"],
        "replacement_counts": dict(Counter(row["decision"] for row in payload["replacement_decisions"])),
        "reserve_scored": False,
        "schema": EXCLUSIVE_SCHEMA,
        "support_post_overlay": {
            family: payload["support_post_overlay"].get(family, 0) for family in ACTIVE_FAMILY_VOCABULARY
        },
        "support_pre": {
            family: payload["support_pre"].get(family, 0) for family in ACTIVE_FAMILY_VOCABULARY
        },
        "train": False,
        "training_gate": redef.get("training_gate"),
        "overlap_pre": redef.get("overlap_pre"),
        "overlap_post": redef.get("overlap_post"),
        "overlap_reduction": redef.get("overlap_reduction"),
        "row_status_counts": redef.get("row_status_counts"),
        "split_candidate_assessments": redef.get("split_candidate_assessments"),
    }
    artifact["next_engineering_action"] = next_engineering_action(artifact)
    artifact["artifact_sha256"] = sha256_text(
        canonical_json({key: value for key, value in artifact.items() if key != "artifact_sha256"})
    )
    return artifact
