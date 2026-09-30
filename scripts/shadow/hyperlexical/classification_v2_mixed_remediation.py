"""Sealed mixed remediation plan from the active-family separability audit.

Turns MIXED_REMEDIATION_REQUIRED into an ordered, non-mutating plan:
data expansion, label cleanup, boundary refinement, and ontology refactor
candidates. Does not train, score the reserve, move BEST, or change the
active ontology.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

from .classification_v2 import (
    ACTIVE_FAMILY_VOCABULARY,
    ClassificationContractError,
    EXACT_COPY_FAMILIES,
    canonical_json,
    sha256_text,
)
from .classification_v2_acquire import DISCOVERY_QUERIES, GLOSS_RULES, SENSE_LABELS
from .classification_v2_separability_audit import (
    AUDIT_SCHEMA,
    BEST_SHA,
    BOUNDARY_SHA,
    COLLAPSE_CLUSTER,
    REPAIR_PRIMARY_SHA,
    SEPARATION_SHA,
    SPARSE_FOCUS,
)

REMEDIATION_SCHEMA = "hyperlex.classification.v2.active_family_mixed_remediation.v1"
REMEDIATION_RULE = "HYPERLEX_ACTIVE_FAMILY_MIXED_REMEDIATION_V1"
AUDIT_ARTIFACT_SHA = "2cb2fe2459a86323dfa8aa50136bb8e6822598ffd8895a1988af459949853d5f"
AUDIT_DECISION = "MIXED_REMEDIATION_REQUIRED"

# Minimum train definition support before pairwise probes are broadly computable.
TARGET_TRAIN_DEFINITIONS = 12
# Prefer OBSERVED when expanding; INFERRED allowed only as fill.
OBSERVED_FRACTION_TARGET = 0.75
# Ontology refactor needs a dense overlap clique, not a single bad pair.
MERGE_MIN_SHARED_NEIGHBORS = 2
PHASES = (
    "PHASE_A_DATA_AND_NOISE",
    "PHASE_B_BOUNDARY_REFINEMENT",
    "PHASE_C_ONTOLOGY_REFACTOR_REVIEW",
    "PHASE_D_REAUDIT_BEFORE_TRAINING",
)


def remediation_contract() -> dict[str, Any]:
    return {
        "audit_artifact_sha256": AUDIT_ARTIFACT_SHA,
        "audit_decision": AUDIT_DECISION,
        "audit_schema": AUDIT_SCHEMA,
        "best_sha256": BEST_SHA,
        "boundary_sha256": BOUNDARY_SHA,
        "encoder_updated": False,
        "jev": "OFF",
        "mutates_ontology": False,
        "moves_best": False,
        "phases": list(PHASES),
        "repair_primary_sha256": REPAIR_PRIMARY_SHA,
        "reserve_scored": False,
        "rule": REMEDIATION_RULE,
        "schema": REMEDIATION_SCHEMA,
        "separation_sha256": SEPARATION_SHA,
        "target_train_definitions": TARGET_TRAIN_DEFINITIONS,
        "train": False,
    }


def _require_audit(audit: Mapping[str, Any]) -> None:
    if audit.get("schema") != AUDIT_SCHEMA:
        raise ClassificationContractError("MIXED_REMEDIATION_UNAVAILABLE", "audit_schema")
    if audit.get("decision") != AUDIT_DECISION:
        raise ClassificationContractError("MIXED_REMEDIATION_UNAVAILABLE", "audit_decision")
    if audit.get("artifact_sha256") != AUDIT_ARTIFACT_SHA:
        raise ClassificationContractError("MIXED_REMEDIATION_UNAVAILABLE", "audit_hash")
    if audit.get("best_sha256") != BEST_SHA:
        raise ClassificationContractError("MIXED_REMEDIATION_UNAVAILABLE", "best")
    if audit.get("train") or audit.get("reserve_scored") or audit.get("moves_best"):
        raise ClassificationContractError("MIXED_REMEDIATION_UNAVAILABLE", "audit_side_effects")


def data_expansion_plan(audit: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Smallest data asks that make sparse/under-supported families probeable."""
    support = audit["support"]
    sparse_treatment = {row["family"]: row for row in audit.get("sparse_treatment", [])}
    plans: list[dict[str, Any]] = []
    for family in ACTIVE_FAMILY_VOCABULARY:
        status = audit["family_status"][family]
        current = int(support[family]["n"])
        observed = int(support[family]["observed"])
        inferred = int(support[family]["inferred"])
        val_defs = int(support[family].get("n_val_definitions") or 0)
        if status not in {"UNDER_SUPPORTED", "NOISY", "UNRESOLVED", "OVERLAPPING"}:
            continue
        if current >= TARGET_TRAIN_DEFINITIONS and status != "UNDER_SUPPORTED":
            # Still list collapse-cluster families below target only.
            if family not in COLLAPSE_CLUSTER and family not in SPARSE_FOCUS:
                continue
        need = max(0, TARGET_TRAIN_DEFINITIONS - current)
        if need == 0 and family not in SPARSE_FOCUS:
            continue
        observed_target = max(0, int(round(TARGET_TRAIN_DEFINITIONS * OBSERVED_FRACTION_TARGET)) - observed)
        sense_labels = list(SENSE_LABELS.get(family, ()))
        discovery = list(DISCOVERY_QUERIES.get(family, ()))
        gloss = [pattern for name, pattern in GLOSS_RULES if name == family]
        treatment = sparse_treatment.get(family)
        plans.append(
            {
                "acquire_path": (
                    "exact_copy_family_definition_prose"
                    if family in EXACT_COPY_FAMILIES
                    else "wiktionary_sense_label_or_gloss"
                ),
                "additional_data_plausibly_resolves": None
                if treatment is None
                else bool(treatment.get("additional_data_plausibly_resolves")),
                "discovery_queries": discovery,
                "family": family,
                "gloss_rules": gloss,
                "n_train_current": current,
                "n_val_definitions": val_defs,
                "observed_needed": observed_target,
                "priority": (
                    0
                    if family in SPARSE_FOCUS
                    else 1
                    if status == "UNDER_SUPPORTED"
                    else 2
                    if status == "NOISY"
                    else 3
                ),
                "sense_labels": sense_labels,
                "status": status,
                "target_train_definitions": TARGET_TRAIN_DEFINITIONS,
                "train_needed": need if need else max(0, TARGET_TRAIN_DEFINITIONS - current),
                "val_definitions_are_not_auto_promoted": True,
                "notes": (
                    "Expand train definitions via acquire evidence rules. "
                    "Validation definitions are evidence of capacity only; do not auto-promote."
                    if family in SPARSE_FOCUS or val_defs
                    else "Collect direct positive definition prose under existing sense labels."
                ),
            }
        )
    plans.sort(key=lambda row: (row["priority"], row["family"]))
    return plans


def label_cleanup_plan(audit: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Review queue for suspected boundary-violating rows. No auto-relabel."""
    queue: list[dict[str, Any]] = []
    for row in audit.get("suspected_label_noise", []):
        family = str(row["family"])
        nearest = str(row["nearest_family"])
        queue.append(
            {
                "action": "human_review",
                "allowed_decisions": ["KEEP", "RELABEL", "DROP", "VOID"],
                "auto_relabel": False,
                "family": family,
                "identity": row["identity"],
                "nearest_family": nearest,
                "recommendation": (
                    "DROP_OR_RELABEL"
                    if family in COLLAPSE_CLUSTER and nearest in COLLAPSE_CLUSTER
                    else "KEEP_UNLESS_DEFINITION_MISMATCH"
                ),
                "score": row.get("score"),
                "text": row.get("text"),
            }
        )
    queue.sort(key=lambda row: (row["family"], row["identity"]))
    return queue


def boundary_refinement_plan(audit: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Concrete positive/exclusion cue packs. Does not mutate sealed boundaries."""
    evidence = {row["family"]: row for row in audit.get("boundary_evidence", [])}
    plans: list[dict[str, Any]] = []
    for family in ACTIVE_FAMILY_VOCABULARY:
        status = audit["family_status"][family]
        if status in {"SEPARABLE", "UNDER_SUPPORTED"}:
            # Sparse families need data first; still emit a light pack for focus families.
            if family not in SPARSE_FOCUS:
                continue
        item = evidence.get(family) or {}
        competitors = list(item.get("nearest_competing_families") or [])[:3]
        plans.append(
            {
                "apply_to_sealed_boundaries": False,
                "exclusion_cues": list(item.get("exclusion_cues") or [])[:6],
                "family": family,
                "nearest_competitors": competitors,
                "positive_cues": list(item.get("positive_semantic_cues") or [])[:6],
                "require_before_training": status in {"OVERLAPPING", "NOISY"},
                "shared_overlapping_cues": item.get("shared_overlapping_cues") or {},
                "status": status,
                "suggestion": (
                    "Rewrite definition admission rules so positives require family cues and "
                    "exclude nearest-competitor senses without those cues."
                    if status in {"OVERLAPPING", "NOISY", "UNRESOLVED"}
                    else "After data expansion, re-check whether exclusion cues are still needed."
                ),
            }
        )
    plans.sort(key=lambda row: (0 if row["require_before_training"] else 1, row["family"]))
    return plans


def _overlap_graph(audit: Mapping[str, Any]) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {family: set() for family in COLLAPSE_CLUSTER}
    for row in audit.get("pair_rows", []):
        if "ONTOLOGY_OVERLAP" not in set(row.get("flags") or []):
            continue
        left = row["family_a"]
        right = row["family_b"]
        if left in graph and right in graph:
            graph[left].add(right)
            graph[right].add(left)
    return graph


def ontology_refactor_candidates(audit: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Merge/split candidates only. Active vocabulary is not changed here."""
    graph = _overlap_graph(audit)
    parent = {family: family for family in COLLAPSE_CLUSTER}

    def find(node: str) -> str:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(left: str, right: str) -> None:
        root_left = find(left)
        root_right = find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    for family, neighbors in graph.items():
        for other in neighbors:
            union(family, other)
    components: dict[str, list[str]] = defaultdict(list)
    for family in COLLAPSE_CLUSTER:
        components[find(family)].append(family)

    pair_index = {
        f"{row['family_a']}||{row['family_b']}": row for row in audit.get("pair_rows", [])
    }
    candidates: list[dict[str, Any]] = []
    for members in components.values():
        ordered = sorted(members)
        if len(ordered) < 2:
            candidates.append(
                {
                    "action": "KEEP_AND_EXPAND_DATA",
                    "families": ordered,
                    "reason": "no_collapse_cluster_ontology_overlap_edge",
                }
            )
            continue
        # Rank pairwise merge strength by failed probe + high cross-sim.
        pair_scores: list[dict[str, Any]] = []
        for index, left in enumerate(ordered):
            for right in ordered[index + 1 :]:
                key = f"{left}||{right}"
                alt = f"{right}||{left}"
                row = pair_index.get(key) or pair_index.get(alt)
                if row is None:
                    continue
                probe_f1 = row.get("probe", {}).get("f1")
                cross = float(row.get("embedding", {}).get("cross_family_similarity") or 0.0)
                shared_neighbors = len(graph[left] & graph[right])
                if shared_neighbors < MERGE_MIN_SHARED_NEIGHBORS and "ONTOLOGY_OVERLAP" not in set(
                    row.get("flags") or []
                ):
                    continue
                severity = cross + (0.0 if probe_f1 is None else (1.0 - float(probe_f1)))
                pair_scores.append(
                    {
                        "cross_family_similarity": row.get("embedding", {}).get(
                            "cross_family_similarity"
                        ),
                        "family_a": left,
                        "family_b": right,
                        "flags": list(row.get("flags") or []),
                        "probe_f1": probe_f1,
                        "severity": severity,
                        "shared_overlap_neighbors": shared_neighbors,
                    }
                )
        pair_scores.sort(key=lambda item: (-float(item["severity"]), item["family_a"], item["family_b"]))
        top = pair_scores[:8]
        candidates.append(
            {
                "action": "REVIEW_MERGE_OR_SPLIT",
                "apply_to_active_ontology": False,
                "component_size": len(ordered),
                "families": ordered,
                "recommended_first_reviews": top[:3],
                "split_hint": (
                    "Prefer split/redefinition when family names encode distinct social practices "
                    "but current Wiktionary sense labels admit cross-family glosses."
                ),
                "top_merge_pairs": top,
            }
        )
    candidates.sort(key=lambda row: (-int(row.get("component_size") or 1), row["families"][0]))
    return candidates


def phase_plan(
    *,
    data_plans: Sequence[Mapping[str, Any]],
    noise_plans: Sequence[Mapping[str, Any]],
    boundary_plans: Sequence[Mapping[str, Any]],
    ontology_plans: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    sparse_data = [row for row in data_plans if row["family"] in SPARSE_FOCUS]
    required_boundaries = [row for row in boundary_plans if row.get("require_before_training")]
    refactor_reviews = [
        row for row in ontology_plans if row.get("action") == "REVIEW_MERGE_OR_SPLIT"
    ]
    return [
        {
            "blocks_training": True,
            "phase": "PHASE_A_DATA_AND_NOISE",
            "actions": [
                "expand_train_definitions_for_sparse_families",
                "human_review_suspected_label_noise",
            ],
            "families": [row["family"] for row in sparse_data],
            "label_noise_rows": len(noise_plans),
            "exit_criterion": (
                "Each sparse-focus family reaches >=12 train definitions or an explicit "
                "operator waiver, and every suspected label-noise row has KEEP|RELABEL|DROP|VOID."
            ),
        },
        {
            "blocks_training": True,
            "phase": "PHASE_B_BOUNDARY_REFINEMENT",
            "actions": [
                "rewrite_definition_admission_positive_and_exclusion_cues",
                "do_not_mutate_sealed_boundary_artifact_until_reassembly_pass",
            ],
            "families": [row["family"] for row in required_boundaries],
            "exit_criterion": (
                "Overlapping/noisy families have explicit positive and exclusion cues recorded "
                "for a future boundary re-seal."
            ),
        },
        {
            "blocks_training": True,
            "phase": "PHASE_C_ONTOLOGY_REFACTOR_REVIEW",
            "actions": [
                "operator_review_merge_or_split_for_collapse_component",
                "no_automatic_vocabulary_change",
            ],
            "components": [
                {"families": row["families"], "size": row.get("component_size")}
                for row in refactor_reviews
            ],
            "exit_criterion": (
                "Operator accepts KEEP, MERGE, or SPLIT for the large collapse component before "
                "another 19-way training spend."
            ),
        },
        {
            "blocks_training": False,
            "phase": "PHASE_D_REAUDIT_BEFORE_TRAINING",
            "actions": [
                "rerun_HYPERLEX_ACTIVE_FAMILY_SEPARABILITY_AUDIT_V1",
                "allow_training_only_if_decision_is_CURRENT_ONTOLOGY_DATA_SEPARABLE_or_explicitly_waived",
            ],
            "exit_criterion": (
                "Fresh separability audit no longer returns MIXED_REMEDIATION_REQUIRED / "
                "ONTOLOGY_REFACTOR_REQUIRED without an operator waiver."
            ),
        },
    ]


def training_gate(audit: Mapping[str, Any], phases: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    statuses = Counter(audit["family_status"].values())
    return {
        "allow_encoder_training": False,
        "allow_family_scorer_training": False,
        "allow_reserve_scoring": False,
        "allow_best_move": False,
        "blocked_by_phases": [row["phase"] for row in phases if row.get("blocks_training")],
        "family_status_counts": dict(statuses),
        "reason": (
            "Separability audit sealed MIXED_REMEDIATION_REQUIRED. Data, boundary, and ontology "
            "remediation must complete and re-audit before another training spend."
        ),
    }


def assemble_remediation(audit: Mapping[str, Any]) -> dict[str, Any]:
    _require_audit(audit)
    data_plans = data_expansion_plan(audit)
    noise_plans = label_cleanup_plan(audit)
    boundary_plans = boundary_refinement_plan(audit)
    ontology_plans = ontology_refactor_candidates(audit)
    phases = phase_plan(
        data_plans=data_plans,
        noise_plans=noise_plans,
        boundary_plans=boundary_plans,
        ontology_plans=ontology_plans,
    )
    gate = training_gate(audit, phases)
    contract = remediation_contract()
    artifact = {
        "audit_artifact_sha256": AUDIT_ARTIFACT_SHA,
        "audit_decision": AUDIT_DECISION,
        "best_sha256": BEST_SHA,
        "boundary_refinement": boundary_plans,
        "boundary_sha256": BOUNDARY_SHA,
        "contract": contract,
        "data_expansion": data_plans,
        "encoder_updated": False,
        "jev": "OFF",
        "label_cleanup": noise_plans,
        "moves_best": False,
        "mutates_ontology": False,
        "ontology_refactor_candidates": ontology_plans,
        "phases": phases,
        "remediation_state": "SEALED",
        "repair_primary_sha256": REPAIR_PRIMARY_SHA,
        "reserve_scored": False,
        "schema": REMEDIATION_SCHEMA,
        "separation_sha256": SEPARATION_SHA,
        "sparse_focus": list(SPARSE_FOCUS),
        "train": False,
        "training_gate": gate,
    }
    artifact["artifact_sha256"] = sha256_text(
        canonical_json({key: value for key, value in artifact.items() if key != "artifact_sha256"})
    )
    return artifact


def next_engineering_action(artifact: Mapping[str, Any]) -> str:
    if artifact.get("remediation_state") != "SEALED":
        raise ClassificationContractError("MIXED_REMEDIATION_UNAVAILABLE", "state")
    sparse = [row["family"] for row in artifact.get("data_expansion", []) if row["family"] in SPARSE_FOCUS]
    noise_n = len(artifact.get("label_cleanup") or [])
    return (
        "Execute PHASE_A_DATA_AND_NOISE: acquire direct train definitions for "
        + ", ".join(sparse)
        + f" to >= {TARGET_TRAIN_DEFINITIONS} each, and human-review {noise_n} suspected label-noise "
        "rows. Do not train. Do not score the reserve. Do not move BEST. Do not mutate the active "
        "ontology until PHASE_C operator review."
    )
