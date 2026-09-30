"""Post-merge residual overlap review after APPLY_ONTOLOGY_MERGE_PAIR.

Read-only. Does not mutate the forward ontology, train, score the reserve,
move BEST, or merge relationship-dating automatically.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

from .classification_v2 import ClassificationContractError, canonical_json, sha256_text
from .classification_v2_boundary_redefinition import HIGH_OVERLAP_COSINE
from .classification_v2_boundary_tightening_v2 import MATERIAL_OVERLAP_REDUCTION
from .classification_v2_ontology_merge_pair import (
    FORWARD_ACTIVE_FAMILY_VOCABULARY,
    FORWARD_COLLAPSE_CLUSTER,
    KEEP_FAMILY,
    MERGE_RULE,
    MERGED_LABEL,
)
from .classification_v2_ontology_refactor_review import LEXICAL_DISTINCT_MAX_SHARED
from .classification_v2_separability_audit import BEST_SHA, lexical_pair_report
from .holdout_guard import normalized_text_sha256

REVIEW_SCHEMA = "hyperlex.classification.v2.post_merge_residual_overlap_review.v1"
REVIEW_RULE = "HYPERLEX_ACTIVE_FAMILY_POST_MERGE_RESIDUAL_REVIEW_V1"
MERGE_PAIR_ARTIFACT_SHA = (
    "c901badb70c0c72f1af20fe4dd0b64bcbdfad917568682e9abb2cc9321ad69d5"
)
MERGE_ONTOLOGY_SHA = "67d6b100e48171c522dd43fcc2038bdc97ef479cfcc9ae98f0534e520224b813"
MERGE_BOUNDARY_SHA = "d7c16112412c546288be744fb426e495cdb77ec970e737455df01d00d3fd141a"
MERGE_EXPORT_SHA = "a8c064151973d7b2b9f439dc9fab499c69c2dd8a22a19206d7f486d970975130"

RECOMMENDATIONS = (
    "KEEP_SE_RD_SEPARATE_REFINE_HUBS",
    "MERGE_SE_RD",
    "BROADER_ONTOLOGY_COLLAPSE",
    "DATA_OR_GEOMETRY_CLEAN",
)


def residual_review_contract() -> dict[str, Any]:
    return {
        "applies_ontology_change": False,
        "best_sha256": BEST_SHA,
        "forward_vocabulary": list(FORWARD_ACTIVE_FAMILY_VOCABULARY),
        "high_overlap_cosine": HIGH_OVERLAP_COSINE,
        "historical_artifacts_rewritten": False,
        "jev": "OFF",
        "material_overlap_reduction_required": MATERIAL_OVERLAP_REDUCTION,
        "merge_pair_artifact_sha256": MERGE_PAIR_ARTIFACT_SHA,
        "merge_rule": MERGE_RULE,
        "merges_relationship_dating_automatically": False,
        "moves_best": False,
        "opens_training_gate": False,
        "reserve_scored": False,
        "rule": REVIEW_RULE,
        "schema": REVIEW_SCHEMA,
        "train": False,
    }


def degree_table(pairs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    deg: Counter[str] = Counter()
    for pair in pairs:
        deg[str(pair["family_a"])] += 1
        deg[str(pair["family_b"])] += 1
    return [
        {"degree": int(count), "family": family}
        for family, count in sorted(deg.items(), key=lambda item: (-item[1], item[0]))
    ]


def largest_component_members(
    pairs: Sequence[Mapping[str, Any]],
    cluster: Sequence[str],
) -> list[str]:
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

    collapse_pairs = [
        pair
        for pair in pairs
        if pair.get("in_collapse_cluster")
        and pair.get("family_a") in parent
        and pair.get("family_b") in parent
    ]
    for pair in collapse_pairs:
        union(str(pair["family_a"]), str(pair["family_b"]))
    groups: dict[str, list[str]] = defaultdict(list)
    for family in cluster:
        groups[find(family)].append(family)
    if not groups:
        return []
    largest = max(groups.values(), key=lambda members: (len(members), sorted(members)))
    return sorted(largest)


def analyze_se_rd(
    *,
    texts_se: Sequence[str],
    texts_rd: Sequence[str],
    cosine: float | None,
) -> dict[str, Any]:
    lexical = lexical_pair_report(texts_se, texts_rd)
    shared_ratio = float(lexical.get("shared_token_ratio") or 0.0)
    lexically_distinct = (
        shared_ratio <= LEXICAL_DISTINCT_MAX_SHARED
        and bool(lexical.get("tokens_enriched_in_a"))
        and bool(lexical.get("tokens_enriched_in_b"))
    )
    return {
        "cosine": cosine,
        "family_a": MERGED_LABEL,
        "family_b": KEEP_FAMILY,
        "lexically_distinct": lexically_distinct,
        "n_train_a": len(texts_se),
        "n_train_b": len(texts_rd),
        "shared_high_frequency_tokens": list(lexical.get("shared_high_frequency_tokens") or [])[:8],
        "shared_token_ratio": shared_ratio,
        "tokens_enriched_a": list(lexical.get("tokens_enriched_in_a") or [])[:8],
        "tokens_enriched_b": list(lexical.get("tokens_enriched_in_b") or [])[:8],
        "above_overlap_threshold": cosine is not None and float(cosine) >= HIGH_OVERLAP_COSINE,
    }


def decide_residual_recommendation(
    *,
    se_rd: Mapping[str, Any],
    degrees: Sequence[Mapping[str, Any]],
    overlap_post: Mapping[str, Any],
    overlap_reduction_pct: float,
    collapse_pre: int,
    collapse_post: int,
) -> dict[str, Any]:
    """Deterministic residual next-step recommendation."""
    hubs = [row["family"] for row in degrees[:4]]
    post_count = int(overlap_post.get("high_overlap_pair_count") or 0)
    # Smallest wrong action to reject first: merging SE+RD when lexically distinct.
    if se_rd.get("lexically_distinct") and se_rd.get("above_overlap_threshold"):
        return {
            "affected_families": [MERGED_LABEL, KEEP_FAMILY, *hubs[:3]],
            "primary_recommendation": "KEEP_SE_RD_SEPARATE_REFINE_HUBS",
            "proposed_actions": [
                "keep social-evaluation and relationship-dating as distinct labels",
                "treat relationship-dating as structural future candidate only",
                "target high-degree residual hubs for exclusive-definition / boundary work",
            ],
            "hub_families": hubs,
            "rationale": (
                "post-merge social-evaluation↔relationship-dating remains high-cosine "
                f"({se_rd.get('cosine')}) but lexically distinct "
                f"(shared_token_ratio={se_rd.get('shared_token_ratio')}); "
                "do not merge them. Overlap reduction "
                f"{overlap_reduction_pct:.2%} and collapse {collapse_pre}→{collapse_post} "
                f"leave gate closed at {post_count} pairs. Next smallest useful work is "
                f"hub refinement on {', '.join(hubs[:3])}."
            ),
        }
    if (
        se_rd.get("above_overlap_threshold")
        and not se_rd.get("lexically_distinct")
        and float(se_rd.get("shared_token_ratio") or 0.0) > LEXICAL_DISTINCT_MAX_SHARED
    ):
        return {
            "affected_families": [MERGED_LABEL, KEEP_FAMILY],
            "primary_recommendation": "MERGE_SE_RD",
            "proposed_actions": [
                "operator-approve merging social-evaluation and relationship-dating"
            ],
            "hub_families": hubs,
            "rationale": (
                "SE↔RD is both high-cosine and not lexically distinct after the AD/SS merge; "
                "a second pair-merge is the smallest ontology cut."
            ),
        }
    if post_count >= 30 and collapse_post >= 12:
        return {
            "affected_families": hubs,
            "primary_recommendation": "BROADER_ONTOLOGY_COLLAPSE",
            "proposed_actions": [
                "plan a multi-family ontology carve beyond a single pair merge"
            ],
            "hub_families": hubs,
            "rationale": (
                "residual high-overlap remains broad after the approved pair merge; "
                "pair-scale ontology edits are unlikely to clear the 30% gate alone."
            ),
        }
    return {
        "affected_families": hubs,
        "primary_recommendation": "DATA_OR_GEOMETRY_CLEAN",
        "proposed_actions": [
            "re-run exclusive definition / KEEP filtering on residual high-overlap rows"
        ],
        "hub_families": hubs,
        "rationale": "residual pairs look addressable by data/geometry cleaning before ontology mutation.",
    }


def next_engineering_action(recommendation: Mapping[str, Any]) -> str:
    primary = recommendation["primary_recommendation"]
    if primary == "KEEP_SE_RD_SEPARATE_REFINE_HUBS":
        return (
            "APPLY_RESIDUAL_HUB_BOUNDARY_PASS — keep SE/RD separate; acquire or tighten "
            "mutually exclusive definitions for residual high-degree hubs "
            f"({', '.join(recommendation.get('hub_families') or [])}); "
            "rerun overlap + readiness. Do not train yet."
        )
    if primary == "MERGE_SE_RD":
        return (
            "APPLY_ONTOLOGY_MERGE_SE_RD — operator-approve merging social-evaluation and "
            "relationship-dating; migrate; reseal overlap + readiness. Do not train yet."
        )
    if primary == "BROADER_ONTOLOGY_COLLAPSE":
        return (
            "PLAN_MULTI_FAMILY_ONTOLOGY_CARVE — pair merges are insufficient; design a "
            "broader forward ontology cut. Do not train yet."
        )
    return (
        "APPLY_RESIDUAL_DATA_GEOMETRY_CLEAN — exclusive-definition / KEEP filtering on "
        "residual collapse rows; reseal overlap. Do not train yet."
    )


def assemble_residual_review(payload: Mapping[str, Any]) -> dict[str, Any]:
    required = (
        "degrees",
        "largest_component",
        "overlap_post",
        "overlap_pre",
        "overlap_reduction",
        "recommendation",
        "se_rd_analysis",
        "top_pairs",
    )
    for key in required:
        if key not in payload:
            raise ClassificationContractError("POST_MERGE_RESIDUAL_REVIEW_UNAVAILABLE", key)
    recommendation = payload["recommendation"]
    if recommendation.get("primary_recommendation") not in RECOMMENDATIONS:
        raise ClassificationContractError("POST_MERGE_RESIDUAL_REVIEW_UNAVAILABLE", "recommendation")
    contract = residual_review_contract()
    reduction = payload["overlap_reduction"]
    artifact = {
        "applies_ontology_change": False,
        "best_sha256": BEST_SHA,
        "collapse_component_after": int(
            payload["overlap_post"].get("largest_collapse_component") or 0
        ),
        "collapse_component_before": int(
            payload["overlap_pre"].get("largest_collapse_component") or 0
        ),
        "contract": contract,
        "degrees": payload["degrees"],
        "forward_vocabulary": list(FORWARD_ACTIVE_FAMILY_VOCABULARY),
        "historical_artifacts_rewritten": False,
        "jev": "OFF",
        "largest_component_members": list(payload["largest_component"]),
        "merge_boundary_sha256": MERGE_BOUNDARY_SHA,
        "merge_export_sha256": MERGE_EXPORT_SHA,
        "merge_ontology_sha256": MERGE_ONTOLOGY_SHA,
        "merge_pair_artifact_sha256": MERGE_PAIR_ARTIFACT_SHA,
        "moves_best": False,
        "opens_training_gate": False,
        "overlap_absolute_reduction": reduction.get("absolute_reduction"),
        "overlap_percentage_reduction": reduction.get("percentage_reduction"),
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
        "primary_recommendation": recommendation["primary_recommendation"],
        "proposed_actions": recommendation["proposed_actions"],
        "hub_families": recommendation.get("hub_families"),
        "affected_families": recommendation.get("affected_families"),
        "rationale": recommendation["rationale"],
        "relationship_dating_status": {
            "family": KEEP_FAMILY,
            "future_ontology_refactor_candidate": True,
            "merged_automatically": False,
            "se_rd": payload["se_rd_analysis"],
        },
        "reserve_scored": False,
        "residual_blockers": [
            "MATERIAL_OVERLAP_REDUCTION_NOT_MET",
            "COLLAPSE_COMPONENT_NOT_WEAKENED",
        ],
        "schema": REVIEW_SCHEMA,
        "se_rd_analysis": payload["se_rd_analysis"],
        "top_pairs": payload["top_pairs"],
        "train": False,
        "training_gate": "CLOSED",
    }
    artifact["next_engineering_action"] = next_engineering_action(recommendation)
    artifact["artifact_sha256"] = sha256_text(
        canonical_json({key: value for key, value in artifact.items() if key != "artifact_sha256"})
    )
    return artifact
