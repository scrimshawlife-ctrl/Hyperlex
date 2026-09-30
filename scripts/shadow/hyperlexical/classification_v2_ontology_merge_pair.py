"""APPLY_ONTOLOGY_MERGE_PAIR — forward AD+SS → social-evaluation.

Creates a new versioned forward ontology. Does not mutate historical v1/v2
vocabularies, rewrite sealed checkpoints, train, score the reserve, or move BEST.
Jev remains OFF.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

from .classification_v2 import (
    HISTORICAL_ACTIVE_FAMILY_VOCABULARY,
    ClassificationContractError,
    canonical_json,
    sha256_text,
)
from .classification_v2_boundary_redefinition import HIGH_OVERLAP_COSINE
from .classification_v2_boundary_tightening_v2 import MATERIAL_OVERLAP_REDUCTION
from .classification_v2_ontology_refactor_review import (
    MERGED_LABEL,
    OVERLAY_SHA,
    TIGHTENING_V2_SHA,
)
from .classification_v2_separability_audit import (
    BEST_SHA,
    COLLAPSE_CLUSTER,
    REPAIR_PRIMARY_SHA,
)
from .holdout_guard import normalized_text_sha256

MERGE_SCHEMA = "hyperlex.classification.v2.active_family_ontology_merge_pair.v1"
MERGE_RULE = "HYPERLEX_ACTIVE_FAMILY_ONTOLOGY_MERGE_PAIR_V1"
ONTOLOGY_REVIEW_SHA = "ebab1e4d4d5a0f9169def6426de5b6137fb15f0b7c7d6b57d7aa295cbf6b7178"
FORWARD_VOCABULARY_ID = "hyperlex.active_families.v2.forward_merge_pair_ad_ss"
HISTORICAL_VOCABULARY_ID = "hyperlex.active_families.v1"

SOURCE_MERGE_FAMILIES: tuple[str, ...] = ("approval-disapproval", "social-status")
KEEP_FAMILY = "relationship-dating"

SOCIAL_EVALUATION_DEFINITION = (
    "rank, prestige, hierarchy, social standing, evaluative praise, pejoration, "
    "approval, or disapproval"
)
RELATIONSHIP_DATING_DEFINITION = (
    "romantic, dating, courtship, partner, or relationship semantics"
)
RELATIONSHIP_DATING_EXCLUSION = (
    "status/evaluative semantics without romantic or relationship content"
)

# Fail-closed expected definition-support migration counts (sealed review).
EXPECTED_MIGRATED_TRAIN = 12
EXPECTED_MIGRATED_VAL = 4
EXPECTED_SE_TRAIN = 12
EXPECTED_SE_VAL = 4
EXPECTED_RD_TRAIN = 5
EXPECTED_RD_VAL = 2

# Pre-merge overlap pinned from sealed BOUNDARY_TIGHTENING_V2 post state.
PRE_MERGE_OVERLAP_PIN = {
    "collapse_high_overlap_pairs": 33,
    "high_overlap_pair_count": 35,
    "largest_collapse_component": 12,
    "threshold": HIGH_OVERLAP_COSINE,
}


def forward_active_family_vocabulary() -> tuple[str, ...]:
    """18-family forward vocabulary. Historical vocabulary tuple untouched."""
    out: list[str] = []
    inserted = False
    for family in HISTORICAL_ACTIVE_FAMILY_VOCABULARY:
        if family in SOURCE_MERGE_FAMILIES:
            if not inserted:
                out.append(MERGED_LABEL)
                inserted = True
            continue
        out.append(family)
    if not inserted:
        out.append(MERGED_LABEL)
    return tuple(out)


FORWARD_ACTIVE_FAMILY_VOCABULARY = forward_active_family_vocabulary()


def forward_collapse_cluster() -> tuple[str, ...]:
    out: list[str] = []
    inserted = False
    for family in COLLAPSE_CLUSTER:
        if family in SOURCE_MERGE_FAMILIES:
            if not inserted:
                out.append(MERGED_LABEL)
                inserted = True
            continue
        out.append(family)
    if not inserted:
        out.append(MERGED_LABEL)
    return tuple(out)


FORWARD_COLLAPSE_CLUSTER = forward_collapse_cluster()


def freeze_migration_map() -> dict[str, Any]:
    mapping = {family: family for family in HISTORICAL_ACTIVE_FAMILY_VOCABULARY}
    mapping["approval-disapproval"] = MERGED_LABEL
    mapping["social-status"] = MERGED_LABEL
    mapping["relationship-dating"] = KEEP_FAMILY
    # Forward identity for the new family.
    mapping[MERGED_LABEL] = MERGED_LABEL
    focus = {
        "approval-disapproval": MERGED_LABEL,
        "social-status": MERGED_LABEL,
        "relationship-dating": KEEP_FAMILY,
    }
    body = {
        "compatibility_map": dict(sorted(mapping.items())),
        "deprecated_families": list(SOURCE_MERGE_FAMILIES),
        "focus_migration": focus,
        "new_families_added": [MERGED_LABEL],
        "rule": MERGE_RULE,
        "schema": "hyperlex.classification.v2.forward_migration_map.v1",
    }
    body["migration_map_sha256"] = sha256_text(canonical_json(body))
    return body


def forward_ontology_identity() -> dict[str, Any]:
    vocab = FORWARD_ACTIVE_FAMILY_VOCABULARY
    definitions = {
        MERGED_LABEL: {
            "definition": SOCIAL_EVALUATION_DEFINITION,
            "excludes": [
                "romantic relationship without evaluative/status content as primary sense"
            ],
            "required_core": [
                "rank",
                "prestige",
                "hierarchy",
                "social standing",
                "praise",
                "pejoration",
                "approval",
                "disapproval",
            ],
        },
        KEEP_FAMILY: {
            "definition": RELATIONSHIP_DATING_DEFINITION,
            "excludes": [RELATIONSHIP_DATING_EXCLUSION],
            "required_core": [
                "romantic",
                "dating",
                "courtship",
                "partner",
                "relationship",
            ],
        },
    }
    body = {
        "active_family_count": len(vocab),
        "active_family_vocabulary": list(vocab),
        "definitions": definitions,
        "historical_vocabulary_id": HISTORICAL_VOCABULARY_ID,
        "historical_vocabulary_mutated": False,
        "removed_families": list(SOURCE_MERGE_FAMILIES),
        "added_families": [MERGED_LABEL],
        "vocabulary_id": FORWARD_VOCABULARY_ID,
    }
    body["ontology_sha256"] = sha256_text(canonical_json(body))
    return body


def head_initialization_policy() -> dict[str, Any]:
    """Future Classification v2 head init — no silent single-predecessor inherit."""
    return {
        MERGED_LABEL: {
            "legacy_row_claim": False,
            "mode": "SEMANTIC_PROTOTYPE_FROM_TRAINING_DEFINITIONS",
            "predecessors": list(SOURCE_MERGE_FAMILIES),
            "predecessors_are_compatibility_evidence_only": True,
            "prototype_source": (
                "all social-evaluation training definition strings after forward migration"
            ),
        },
        "default_for_unmapped_exact_copy": "EXACT_COPY_FROM_V1_WHEN_PRESENT",
        "note": (
            "social-evaluation must not silently inherit approval-disapproval or "
            "social-status head rows. Historical predecessor rows remain compatibility "
            "evidence only."
        ),
    }


def merge_contract() -> dict[str, Any]:
    return {
        "applies_ontology_change": True,
        "best_sha256": BEST_SHA,
        "forward_only": True,
        "historical_artifacts_rewritten": False,
        "historical_checkpoints_rewritten": False,
        "historical_vocabulary_mutated": False,
        "high_overlap_cosine": HIGH_OVERLAP_COSINE,
        "jev": "OFF",
        "material_overlap_reduction_required": MATERIAL_OVERLAP_REDUCTION,
        "merges_relationship_dating": False,
        "moves_best": False,
        "ontology_review_sha256": ONTOLOGY_REVIEW_SHA,
        "overlay_sha256": OVERLAY_SHA,
        "repair_primary_sha256": REPAIR_PRIMARY_SHA,
        "reserve_scored": False,
        "rule": MERGE_RULE,
        "schema": MERGE_SCHEMA,
        "tightening_v2_sha256": TIGHTENING_V2_SHA,
        "train": False,
    }


def map_lineage(lineage: str, migration_map: Mapping[str, str]) -> str:
    return str(migration_map.get(lineage, lineage))


def migrate_forward_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    migration_map: Mapping[str, str],
) -> dict[str, Any]:
    """Rewrite train/val classify lineages via the forward map. Other rows pass through."""
    migrated: list[dict[str, Any]] = []
    affected = Counter()
    for row in rows:
        item = dict(row)
        lineage = str(item.get("lineage") or "")
        split = str(item.get("split") or "")
        task = str(item.get("task") or "classify")
        if (
            lineage in SOURCE_MERGE_FAMILIES
            and split in {"train", "val"}
            and task in {"classify", "classification"}
        ):
            new_lineage = map_lineage(lineage, migration_map)
            if new_lineage != lineage:
                item["lineage"] = new_lineage
                item["legacy_lineage"] = lineage
                item["ontology_migration"] = MERGE_RULE
                affected[split] += 1
        migrated.append(item)
    return {
        "affected_train": int(affected.get("train", 0)),
        "affected_val": int(affected.get("val", 0)),
        "rows": migrated,
    }


def count_definition_support(
    sources: Mapping[str, Mapping[str, Any]],
    *,
    vocabulary: Sequence[str],
) -> dict[str, int]:
    return {
        family: len((sources.get(family) or {}).get("rows") or [])
        for family in vocabulary
    }


def verify_migration_counts(
    *,
    definition_train: Mapping[str, int],
    definition_val: Mapping[str, int],
    affected_train: int | None = None,
    affected_val: int | None = None,
) -> dict[str, Any]:
    se_train = int(definition_train.get(MERGED_LABEL, 0))
    se_val = int(definition_val.get(MERGED_LABEL, 0))
    rd_train = int(definition_train.get(KEEP_FAMILY, 0))
    rd_val = int(definition_val.get(KEEP_FAMILY, 0))
    # Migrated definition rows = SE support after merge (AD+SS defs).
    migrated_train = se_train
    migrated_val = se_val
    errors: list[str] = []
    if migrated_train != EXPECTED_MIGRATED_TRAIN:
        errors.append(f"migrated_train={migrated_train} expected={EXPECTED_MIGRATED_TRAIN}")
    if migrated_val != EXPECTED_MIGRATED_VAL:
        errors.append(f"migrated_val={migrated_val} expected={EXPECTED_MIGRATED_VAL}")
    if se_train != EXPECTED_SE_TRAIN or se_val != EXPECTED_SE_VAL:
        errors.append(f"social-evaluation support train/val={se_train}/{se_val}")
    if rd_train != EXPECTED_RD_TRAIN or rd_val != EXPECTED_RD_VAL:
        errors.append(f"relationship-dating support train/val={rd_train}/{rd_val}")
    if MERGED_LABEL not in definition_train or definition_train[MERGED_LABEL] < 1:
        errors.append("social-evaluation missing train definitions")
    lingering = [
        family for family in SOURCE_MERGE_FAMILIES if definition_train.get(family, 0) > 0
    ]
    if lingering:
        errors.append(f"deprecated families still present in train defs: {lingering}")
    ok = not errors
    return {
        "ok": ok,
        "errors": errors,
        "migrated_train": migrated_train,
        "migrated_val": migrated_val,
        "social_evaluation": {"train": se_train, "validation": se_val},
        "relationship_dating": {"train": rd_train, "validation": rd_val},
        "affected_train_rows": affected_train,
        "affected_val_rows": affected_val,
    }


def overlap_reduction(pre: Mapping[str, Any], post: Mapping[str, Any]) -> dict[str, Any]:
    pre_count = int(pre["high_overlap_pair_count"])
    post_count = int(post["high_overlap_pair_count"])
    absolute = pre_count - post_count
    if pre_count == 0:
        pct = 1.0 if post_count == 0 else 0.0
    else:
        pct = absolute / pre_count
    return {
        "absolute_reduction": absolute,
        "percentage_reduction": pct,
        "pre_high_overlap_pair_count": pre_count,
        "post_high_overlap_pair_count": post_count,
        "largest_collapse_component_pre": int(pre["largest_collapse_component"]),
        "largest_collapse_component_post": int(post["largest_collapse_component"]),
        "threshold": float(pre.get("threshold") or HIGH_OVERLAP_COSINE),
    }


def existing_overlap_gate_pass(
    *,
    reduction: Mapping[str, Any],
    support: Mapping[str, int],
    vocabulary: Sequence[str],
) -> dict[str, Any]:
    """Reuse material-reduction + collapse-weaken gate from boundary tightening."""
    zero = [family for family in vocabulary if support.get(family, 0) < 1]
    collapse_weakened = (
        int(reduction["largest_collapse_component_post"])
        < int(reduction["largest_collapse_component_pre"])
    )
    material = float(reduction["percentage_reduction"]) >= MATERIAL_OVERLAP_REDUCTION
    open_gate = (
        not zero
        and len(support) == len(vocabulary)
        and all(support.get(family, 0) >= 1 for family in vocabulary)
        and material
        and collapse_weakened
    )
    blockers = []
    if zero:
        blockers.append("ZERO_DEFINITION_SUPPORT")
    if not material:
        blockers.append("MATERIAL_OVERLAP_REDUCTION_NOT_MET")
    if not collapse_weakened:
        blockers.append("COLLAPSE_COMPONENT_NOT_WEAKENED")
    return {
        "collapse_weakened": collapse_weakened,
        "material_ok": material,
        "overlap_gate": "PASS" if open_gate else "FAIL",
        "residual_blockers": blockers,
        "required_material_reduction": MATERIAL_OVERLAP_REDUCTION,
    }


def relationship_dating_post_merge_status(
    overlap_post: Mapping[str, Any],
) -> dict[str, Any]:
    """Reassess RD after AD/SS merge. Do not auto-merge."""
    pairs = list(overlap_post.get("high_overlap_pairs") or [])
    rd_pairs = [
        pair
        for pair in pairs
        if KEEP_FAMILY in {pair.get("family_a"), pair.get("family_b")}
    ]
    se_pairs = [
        pair
        for pair in rd_pairs
        if MERGED_LABEL in {pair.get("family_a"), pair.get("family_b")}
    ]
    structural = bool(rd_pairs)
    return {
        "family": KEEP_FAMILY,
        "high_overlap_pair_count": len(rd_pairs),
        "high_overlap_with_social_evaluation": len(se_pairs),
        "merged_in_this_pass": False,
        "future_ontology_refactor_candidate": structural,
        "status": (
            "OVERLAP_REMAINS_STRUCTURAL_FUTURE_CANDIDATE"
            if structural
            else "NO_HIGH_OVERLAP_REMAINING"
        ),
        "sample_pairs": sorted(
            rd_pairs,
            key=lambda item: (-float(item.get("cosine") or 0.0), item.get("family_a"), item.get("family_b")),
        )[:8],
    }


def forward_support_readiness(
    *,
    train_support: Mapping[str, int],
    val_support: Mapping[str, int],
    ontology: Mapping[str, Any],
    migration: Mapping[str, Any],
    boundary_assessment: Mapping[str, Any],
    overlap_gate: Mapping[str, Any],
    isolation_pass: bool,
    train_eval_separation_pass: bool,
    vocabulary: Sequence[str],
) -> dict[str, Any]:
    missing_train = [family for family in vocabulary if train_support.get(family, 0) < 1]
    missing_val = [family for family in vocabulary if val_support.get(family, 0) < 1]
    checks = {
        "all_18_active_families_have_training_support": not missing_train and len(vocabulary) == 18,
        "all_18_active_families_have_validation_support": not missing_val and len(vocabulary) == 18,
        "ontology_hash_frozen": bool(ontology.get("ontology_sha256")),
        "forward_migration_map_frozen": bool(migration.get("migration_map_sha256")),
        "boundary_artifact_valid": bool(boundary_assessment.get("pass")),
        "overlap_gate_evaluated": overlap_gate.get("overlap_gate") in {"PASS", "FAIL"},
        "isolation_pass": isolation_pass,
        "training_evaluation_separation_pass": train_eval_separation_pass,
    }
    blockers = [name for name, ok in checks.items() if not ok]
    if missing_train:
        blockers.append("MISSING_TRAIN_SUPPORT")
    if missing_val:
        blockers.append("MISSING_VALIDATION_SUPPORT")
    if overlap_gate.get("overlap_gate") != "PASS":
        blockers.extend(list(overlap_gate.get("residual_blockers") or []))
    ready = all(checks.values()) and overlap_gate.get("overlap_gate") == "PASS"
    return {
        "blockers": blockers,
        "checks": checks,
        "missing_train_support": missing_train,
        "missing_validation_support": missing_val,
        "ready": ready,
        "state": "READY" if ready else "NOT_READY",
    }


def training_gate_from_readiness(
    readiness: Mapping[str, Any],
    overlap_gate: Mapping[str, Any],
) -> dict[str, Any]:
    open_gate = bool(readiness.get("ready")) and overlap_gate.get("overlap_gate") == "PASS"
    residual = []
    if not open_gate:
        residual = list(dict.fromkeys([*(readiness.get("blockers") or []), *(overlap_gate.get("residual_blockers") or [])]))
    return {
        "allow_best_move": False,
        "allow_encoder_training": open_gate,
        "allow_reserve_scoring": False,
        "next_action": "TRAIN_CLASSIFICATION_V2" if open_gate else "RESOLVE_RESIDUAL_BLOCKERS",
        "residual_blockers": residual,
        "training_gate": "OPEN" if open_gate else "CLOSED",
    }


def connected_component_sizes(
    high_pairs: Sequence[Mapping[str, Any]],
    cluster: Sequence[str],
) -> list[int]:
    parent = {family: family for family in cluster}

    def find(node: str) -> str:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(left: str, right: str) -> None:
        root_l, root_r = find(left), find(right)
        if root_l != root_r:
            parent[root_r] = root_l

    present = set(cluster)
    for pair in high_pairs:
        a, b = pair.get("family_a"), pair.get("family_b")
        if a in present and b in present:
            union(str(a), str(b))
    sizes: dict[str, int] = defaultdict(int)
    for family in cluster:
        sizes[find(family)] += 1
    return sorted(sizes.values(), reverse=True)


def assemble_merge_artifact(payload: Mapping[str, Any]) -> dict[str, Any]:
    required = (
        "ontology",
        "migration",
        "migration_verification",
        "boundary",
        "overlap_pre",
        "overlap_post",
        "overlap_reduction",
        "overlap_gate",
        "readiness",
        "training_gate",
        "relationship_dating_status",
        "head_initialization",
        "export_path",
        "export_sha256",
    )
    for key in required:
        if key not in payload:
            raise ClassificationContractError("ONTOLOGY_MERGE_PAIR_UNAVAILABLE", key)
    if not payload["migration_verification"].get("ok"):
        raise ClassificationContractError(
            "ONTOLOGY_MERGE_PAIR_COUNT_MISMATCH",
            payload["migration_verification"].get("errors"),
        )
    contract = merge_contract()
    reduction = payload["overlap_reduction"]
    artifact = {
        "active_family_count": payload["ontology"]["active_family_count"],
        "applies_ontology_change": True,
        "best_sha256": BEST_SHA,
        "boundary_sha256": payload["boundary"].get("boundary_sha256"),
        "contract": contract,
        "export_path": payload["export_path"],
        "export_sha256": payload["export_sha256"],
        "forward_collapse_cluster": list(FORWARD_COLLAPSE_CLUSTER),
        "forward_vocabulary": list(FORWARD_ACTIVE_FAMILY_VOCABULARY),
        "forward_vocabulary_id": FORWARD_VOCABULARY_ID,
        "head_initialization": payload["head_initialization"],
        "historical_artifacts_rewritten": False,
        "historical_vocabulary_mutated": False,
        "jev": "OFF",
        "merge_application_state": "APPLIED",
        "migration_map": payload["migration"]["compatibility_map"],
        "migration_map_sha256": payload["migration"]["migration_map_sha256"],
        "migration_verification": payload["migration_verification"],
        "moves_best": False,
        "ontology_review_sha256": ONTOLOGY_REVIEW_SHA,
        "ontology_sha256": payload["ontology"]["ontology_sha256"],
        "ontology": payload["ontology"],
        "overlap_absolute_reduction": reduction["absolute_reduction"],
        "overlap_gate": payload["overlap_gate"],
        "overlap_percentage_reduction": reduction["percentage_reduction"],
        "overlap_post": {
            "collapse_high_overlap_pairs": payload["overlap_post"]["collapse_high_overlap_pairs"],
            "high_overlap_pair_count": payload["overlap_post"]["high_overlap_pair_count"],
            "largest_collapse_component": payload["overlap_post"]["largest_collapse_component"],
            "threshold": payload["overlap_post"]["threshold"],
        },
        "overlap_pre": {
            "collapse_high_overlap_pairs": payload["overlap_pre"]["collapse_high_overlap_pairs"],
            "high_overlap_pair_count": payload["overlap_pre"]["high_overlap_pair_count"],
            "largest_collapse_component": payload["overlap_pre"]["largest_collapse_component"],
            "threshold": payload["overlap_pre"]["threshold"],
        },
        "overlay_sha256": OVERLAY_SHA,
        "readiness": payload["readiness"],
        "relationship_dating_status": payload["relationship_dating_status"],
        "repair_primary_sha256": REPAIR_PRIMARY_SHA,
        "reserve_scored": False,
        "schema": MERGE_SCHEMA,
        "separation_sha256": payload["boundary"].get("separation_sha256"),
        "social_evaluation_support": payload["migration_verification"]["social_evaluation"],
        "relationship_dating_support": payload["migration_verification"]["relationship_dating"],
        "train": False,
        "training_gate": payload["training_gate"]["training_gate"],
        "training_gate_detail": payload["training_gate"],
        "next_action": payload["training_gate"]["next_action"],
        "residual_blockers": payload["training_gate"]["residual_blockers"],
    }
    artifact["artifact_sha256"] = sha256_text(
        canonical_json({key: value for key, value in artifact.items() if key != "artifact_sha256"})
    )
    return artifact
