"""APPLY_RESIDUAL_HUB_BOUNDARY_PASS after post-merge residual review.

Tightens exclusive cores / drops weak colliding hub definitions under the
frozen encoder. Keeps social-evaluation and relationship-dating distinct.
Does not train, score the reserve, move BEST, or mutate historical artifacts.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

from .classification_v2 import ClassificationContractError, canonical_json, sha256_text
from .classification_v2_boundary_redefinition import (
    FAMILY_SEMANTIC_CORES,
    HIGH_OVERLAP_COSINE,
    MATERIAL_OVERLAP_REDUCTION,
    _tokens,
)
from .classification_v2_ontology_merge_pair import (
    FORWARD_ACTIVE_FAMILY_VOCABULARY,
    FORWARD_COLLAPSE_CLUSTER,
    KEEP_FAMILY,
    MERGED_LABEL,
)
from .classification_v2_post_merge_residual_review import MERGE_PAIR_ARTIFACT_SHA
from .classification_v2_separability_audit import BEST_SHA, SPARSE_FOCUS

HUB_SCHEMA = "hyperlex.classification.v2.residual_hub_boundary_pass.v1"
HUB_RULE = "HYPERLEX_ACTIVE_FAMILY_RESIDUAL_HUB_BOUNDARY_PASS_V1"
RESIDUAL_REVIEW_SHA = "617ba9eebfe9955ed3931ab659738a25de99b79a7301bc8a6ed5d952439955bc"
MERGE_EXPORT_SHA = "a8c064151973d7b2b9f439dc9fab499c69c2dd8a22a19206d7f486d970975130"
MERGE_BOUNDARY_SHA = "d7c16112412c546288be744fb426e495cdb77ec970e737455df01d00d3fd141a"

HUB_FAMILIES: tuple[str, ...] = (
    "internet-slang",
    "spiritual-mystic",
    "social-evaluation",
    "music-entertainment",
)
SACRIFICIAL_FAMILIES = frozenset({"ai-native", "gaming-meta", "crypto-degen"})
MIN_FAMILY_SUPPORT = 1
SPARSE_FLOOR = 12

# Forward semantic cores: historical map plus social-evaluation (AD∪SS).
FORWARD_FAMILY_SEMANTIC_CORES: dict[str, tuple[str, ...]] = {
    **{family: cues for family, cues in FAMILY_SEMANTIC_CORES.items() if family not in {"approval-disapproval", "social-status"}},
    MERGED_LABEL: tuple(
        dict.fromkeys(
            (
                *FAMILY_SEMANTIC_CORES["social-status"],
                *FAMILY_SEMANTIC_CORES["approval-disapproval"],
            )
        )
    ),
}


def hub_contract() -> dict[str, Any]:
    return {
        "applies_ontology_change": False,
        "best_sha256": BEST_SHA,
        "forward_vocabulary": list(FORWARD_ACTIVE_FAMILY_VOCABULARY),
        "high_overlap_cosine": HIGH_OVERLAP_COSINE,
        "historical_artifacts_rewritten": False,
        "hub_families": list(HUB_FAMILIES),
        "jev": "OFF",
        "keeps_se_rd_separate": True,
        "material_overlap_reduction_required": MATERIAL_OVERLAP_REDUCTION,
        "merge_pair_artifact_sha256": MERGE_PAIR_ARTIFACT_SHA,
        "moves_best": False,
        "residual_review_sha256": RESIDUAL_REVIEW_SHA,
        "reserve_scored": False,
        "rule": HUB_RULE,
        "schema": HUB_SCHEMA,
        "train": False,
    }


def core_hits(text: str, family: str) -> int:
    tokens = _tokens(text)
    return sum(1 for cue in FORWARD_FAMILY_SEMANTIC_CORES.get(family, ()) if cue in tokens)


def competitor_dominant(text: str, family: str, competitor: str) -> bool:
    tokens = _tokens(text)
    own = sum(1 for cue in FORWARD_FAMILY_SEMANTIC_CORES.get(family, ()) if cue in tokens)
    other = sum(1 for cue in FORWARD_FAMILY_SEMANTIC_CORES.get(competitor, ()) if cue in tokens)
    return other >= 2 and other > own


def support_floor(family: str) -> int:
    return SPARSE_FLOOR if family in SPARSE_FOCUS else MIN_FAMILY_SUPPORT


def classify_hub_row(
    *,
    family: str,
    text: str,
    identity: str,
    hub_competitors: Mapping[str, Sequence[str]],
) -> dict[str, Any]:
    """KEEP or DROP one training definition under hub exclusivity rules."""
    own = core_hits(text, family)
    reasons: list[str] = []
    decision = "KEEP"
    if family in HUB_FAMILIES or family in SACRIFICIAL_FAMILIES:
        for competitor in hub_competitors.get(family, ()):
            if competitor_dominant(text, family, competitor):
                decision = "DROP"
                reasons.append(f"competitor_dominant:{competitor}")
                break
        if decision == "KEEP" and family in HUB_FAMILIES and own == 0:
            # Hub rows with no own-core evidence are the soft attractors.
            decision = "DROP"
            reasons.append("hub_zero_core_hits")
    # Never auto-merge SE/RD: both may KEEP when exclusive.
    return {
        "decision": decision,
        "family": family,
        "identity": identity,
        "own_core_hits": own,
        "reasons": reasons,
        "text": text[:240],
    }


def enforce_support_floors(
    classifications: Sequence[Mapping[str, Any]],
    *,
    vocabulary: Sequence[str],
) -> list[dict[str, Any]]:
    """Promote lowest-identity DROPs back to KEEP when a floor would breach."""
    by_family: dict[str, list[dict[str, Any]]] = {family: [] for family in vocabulary}
    for row in classifications:
        item = dict(row)
        by_family.setdefault(str(item["family"]), []).append(item)
    out: list[dict[str, Any]] = []
    for family in vocabulary:
        rows = sorted(by_family.get(family, []), key=lambda item: str(item["identity"]))
        keep = [row for row in rows if row["decision"] == "KEEP"]
        drops = [row for row in rows if row["decision"] != "KEEP"]
        floor = support_floor(family)
        while len(keep) < floor and drops:
            rescued = drops.pop(0)
            rescued = dict(rescued)
            rescued["decision"] = "KEEP"
            rescued["reasons"] = list(rescued.get("reasons") or []) + ["rescued_support_floor"]
            keep.append(rescued)
        out.extend(keep)
        out.extend(drops)
    out.sort(key=lambda item: (str(item["family"]), str(item["identity"])))
    return out


def build_hub_competitors(high_pairs: Sequence[Mapping[str, Any]]) -> dict[str, list[str]]:
    neighbors: dict[str, list[tuple[float, str]]] = {family: [] for family in HUB_FAMILIES}
    for pair in high_pairs:
        a, b = str(pair["family_a"]), str(pair["family_b"])
        cos = float(pair.get("cosine") or 0.0)
        if a in neighbors:
            neighbors[a].append((cos, b))
        if b in neighbors:
            neighbors[b].append((cos, a))
    out: dict[str, list[str]] = {}
    for family, items in neighbors.items():
        items.sort(key=lambda item: (-item[0], item[1]))
        seen: list[str] = []
        for _cos, other in items:
            if other not in seen:
                seen.append(other)
        out[family] = seen[:6]
    # Sacrificial families compete with all hubs.
    for family in SACRIFICIAL_FAMILIES:
        out[family] = list(HUB_FAMILIES)
    return out


def overlap_reduction(pre: Mapping[str, Any], post: Mapping[str, Any]) -> dict[str, Any]:
    pre_count = int(pre["high_overlap_pair_count"])
    post_count = int(post["high_overlap_pair_count"])
    absolute = pre_count - post_count
    pct = 1.0 if pre_count == 0 and post_count == 0 else (0.0 if pre_count == 0 else absolute / pre_count)
    return {
        "absolute_reduction": absolute,
        "percentage_reduction": pct,
        "largest_collapse_component_pre": int(pre["largest_collapse_component"]),
        "largest_collapse_component_post": int(post["largest_collapse_component"]),
        "pre_high_overlap_pair_count": pre_count,
        "post_high_overlap_pair_count": post_count,
        "threshold": float(pre.get("threshold") or HIGH_OVERLAP_COSINE),
    }


def training_gate_hub(
    *,
    reduction: Mapping[str, Any],
    support_post: Mapping[str, int],
    vocabulary: Sequence[str],
) -> dict[str, Any]:
    zero = [family for family in vocabulary if support_post.get(family, 0) < 1]
    sparse_ok = all(support_post.get(family, 0) >= SPARSE_FLOOR for family in SPARSE_FOCUS)
    collapse_weakened = (
        int(reduction["largest_collapse_component_post"])
        < int(reduction["largest_collapse_component_pre"])
    )
    material = float(reduction["percentage_reduction"]) >= MATERIAL_OVERLAP_REDUCTION
    open_gate = not zero and sparse_ok and material and collapse_weakened
    blockers = []
    if zero:
        blockers.append("ZERO_DEFINITION_SUPPORT")
    if not sparse_ok:
        blockers.append("SPARSE_FLOOR_BREACHED")
    if not material:
        blockers.append("MATERIAL_OVERLAP_REDUCTION_NOT_MET")
    if not collapse_weakened:
        blockers.append("COLLAPSE_COMPONENT_NOT_WEAKENED")
    return {
        "allow_best_move": False,
        "allow_encoder_training": open_gate,
        "allow_reserve_scoring": False,
        "collapse_weakened": collapse_weakened,
        "material_ok": material,
        "next_action": "TRAIN_CLASSIFICATION_V2" if open_gate else "RESOLVE_RESIDUAL_BLOCKERS",
        "residual_blockers": blockers,
        "sparse_ok": sparse_ok,
        "training_gate": "OPEN" if open_gate else "CLOSED",
    }


def next_engineering_action(gate: Mapping[str, Any]) -> str:
    if gate.get("training_gate") == "OPEN":
        return (
            "TRAIN_CLASSIFICATION_V2 — residual hub boundary pass cleared the overlap gate; "
            "run one clean forward Classification v2 training pass. Do not score reserve or move BEST."
        )
    return (
        "CONTINUE_RESIDUAL_HUB_OR_ONTOLOGY_WORK — hub KEEP filtering did not clear the "
        "material overlap gate; acquire mutually exclusive hub senses or plan a broader "
        "ontology carve. Keep SE/RD separate. Do not train yet."
    )


def assemble_hub_pass(payload: Mapping[str, Any]) -> dict[str, Any]:
    required = (
        "classifications",
        "hub_competitors",
        "overlap_pre",
        "overlap_post",
        "overlap_reduction",
        "support_pre",
        "support_post",
        "training_gate",
        "export_path",
        "export_sha256",
    )
    for key in required:
        if key not in payload:
            raise ClassificationContractError("RESIDUAL_HUB_BOUNDARY_UNAVAILABLE", key)
    counts = Counter(str(row["decision"]) for row in payload["classifications"])
    artifact = {
        "applies_ontology_change": False,
        "best_sha256": BEST_SHA,
        "classifications": payload["classifications"],
        "contract": hub_contract(),
        "export_path": payload["export_path"],
        "export_sha256": payload["export_sha256"],
        "forward_collapse_cluster": list(FORWARD_COLLAPSE_CLUSTER),
        "forward_vocabulary": list(FORWARD_ACTIVE_FAMILY_VOCABULARY),
        "historical_artifacts_rewritten": False,
        "hub_competitors": payload["hub_competitors"],
        "hub_families": list(HUB_FAMILIES),
        "jev": "OFF",
        "keeps_se_rd_separate": True,
        "merge_boundary_sha256": MERGE_BOUNDARY_SHA,
        "merge_export_sha256": MERGE_EXPORT_SHA,
        "merge_pair_artifact_sha256": MERGE_PAIR_ARTIFACT_SHA,
        "moves_best": False,
        "overlap_absolute_reduction": payload["overlap_reduction"]["absolute_reduction"],
        "overlap_percentage_reduction": payload["overlap_reduction"]["percentage_reduction"],
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
        "relationship_dating_merged": False,
        "reserve_scored": False,
        "residual_review_sha256": RESIDUAL_REVIEW_SHA,
        "row_status_counts": dict(counts),
        "schema": HUB_SCHEMA,
        "support_post": {family: payload["support_post"].get(family, 0) for family in FORWARD_ACTIVE_FAMILY_VOCABULARY},
        "support_pre": {family: payload["support_pre"].get(family, 0) for family in FORWARD_ACTIVE_FAMILY_VOCABULARY},
        "train": False,
        "training_gate": payload["training_gate"]["training_gate"],
        "training_gate_detail": payload["training_gate"],
        "residual_blockers": payload["training_gate"]["residual_blockers"],
        "next_action": payload["training_gate"]["next_action"],
        "next_engineering_action": next_engineering_action(payload["training_gate"]),
        "hub_pass_state": "SEALED",
    }
    artifact["artifact_sha256"] = sha256_text(
        canonical_json({key: value for key, value in artifact.items() if key != "artifact_sha256"})
    )
    return artifact
