"""Multi-anchor family boundaries. No training, no reserve, no BEST writes."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY, EXACT_COPY_FAMILIES  # noqa: E402
from hyperlexical.classification_v2_boundaries import (  # noqa: E402
    ANCHOR_MAX,
    ANCHOR_MIN,
    BOUNDARY_SCHEMA,
    CANONICAL_REPRESENTATION,
    CLUSTER_MAX_ITERATIONS,
    CLUSTER_SEED,
    COLLISION_COSINE,
    REJECTED_REPRESENTATION,
    SILHOUETTE_MIN,
    SUPPORT_OK,
    SUPPORT_SPARSE,
    anchor_count_bounds,
    anchor_id_for,
    assemble_boundaries,
    assess_boundary_artifact,
    boundary_training_sources,
    build_family_anchors,
    canonical_boundary_representation,
    choose_anchor_count,
)
from hyperlexical.classification_v2_prototype import _f32_hash, _f32_round, _unit, weighted_mean  # noqa: E402
from hyperlexical.holdout_guard import normalized_text_sha256  # noqa: E402


def _member(identity: str, vector: list[float], text: str = "", weight: float = 1.0) -> dict:
    return {
        "class": "OBSERVED",
        "identity": identity,
        "text": text or identity,
        "vector": vector,
        "weight": weight,
    }


def _axis(slot: int, identity: str, text: str) -> dict:
    vector = [0.0] * 8
    vector[slot] = 1.0
    return _member(identity, vector, text)


def _separated(family: str, count: int = 3) -> list[dict]:
    members = []
    for index in range(count):
        members.append(_axis(0, f"{family}-a-{index}", f"{family} rank prestige hierarchy {index}"))
        members.append(_axis(1, f"{family}-b-{index}", f"{family} melody chorus performance {index}"))
    return members


def _sparse_family(family: str) -> list[dict]:
    return [_axis(2, f"{family}-only", f"{family} lone definition gloss")]


def _all_families(rich: str = "social-status") -> dict[str, list[dict]]:
    payload = {family: _sparse_family(family) for family in ACTIVE_FAMILY_VOCABULARY}
    payload[rich] = _separated(rich)
    return payload


def test_anchor_count_rule_is_support_then_smallest_separated_k():
    assert CLUSTER_SEED == 0
    assert CLUSTER_MAX_ITERATIONS == 32
    assert SILHOUETTE_MIN == 0.20
    assert (ANCHOR_MIN, ANCHOR_MAX) == (1, 5)
    assert COLLISION_COSINE == 0.80
    assert anchor_count_bounds(1)["fixed_k"] == 1
    assert anchor_count_bounds(2)["support_status"] == SUPPORT_SPARSE
    assert anchor_count_bounds(3)["fixed_k"] == 2
    assert anchor_count_bounds(5)["fixed_k"] == 2
    assert anchor_count_bounds(6)["k_max"] == 3
    assert anchor_count_bounds(11)["k_max"] == 3
    assert anchor_count_bounds(12)["k_max"] == 4
    assert anchor_count_bounds(23)["k_max"] == 4
    assert anchor_count_bounds(24)["k_max"] == 5
    assert anchor_count_bounds(500)["k_max"] == 5


def test_sparse_family_uses_one_anchor_and_does_not_fail():
    built = build_family_anchors("memetic", _sparse_family("memetic"))
    assert built["support_status"] == SUPPORT_SPARSE
    assert len(built["anchors"]) == 1
    assert built["anchors"][0]["support_count"] == 1
    pair = [
        _axis(0, "memetic-1", "meme one"),
        _axis(0, "memetic-2", "meme two"),
    ]
    built = build_family_anchors("memetic", list(reversed(pair)))
    assert built["support_status"] == SUPPORT_SPARSE
    assert built["anchors"][0]["support_count"] == 2


def test_small_support_is_two_anchors_and_n3_may_keep_a_singleton():
    triple = [_axis(0, f"id-{index}", f"gloss {index}") for index in range(3)]
    built = build_family_anchors("regional-cultural", triple)
    assert built["support_status"] == SUPPORT_OK
    assert len(built["anchors"]) == 2
    supports = sorted(anchor["support_count"] for anchor in built["anchors"])
    assert supports == [1, 2]
    four = [_axis(0, f"same-{index}", f"same gloss {index}") for index in range(4)]
    built = build_family_anchors("identity-affiliation", four)
    assert [anchor["support_count"] for anchor in built["anchors"]] == [2, 2]


def test_smallest_separated_k_wins_and_collapsed_points_fall_back_to_two():
    separated = choose_anchor_count(_separated("social-status", 4))
    assert separated["n"] == 8
    assert separated["k"] == 2
    assert separated["trace"][0]["accepted"] is True
    assert len(separated["trace"]) == 1
    collapsed = choose_anchor_count(
        [_axis(0, f"flat-{index:02d}", "same gloss") for index in range(8)]
    )
    assert collapsed["k"] == 2
    assert collapsed["trace"]
    assert all(item["accepted"] is False for item in collapsed["trace"])
    wide = choose_anchor_count(_separated("ai-native", 12))
    assert wide["n"] == 24
    assert wide["k"] == 2
    assert wide["k"] <= 5


def test_clustering_and_anchor_ids_are_stable_under_input_order():
    forward = _separated("politics-civic", 3)
    backward = list(reversed(forward))
    left = build_family_anchors("politics-civic", forward)
    right = build_family_anchors("politics-civic", backward)
    assert [anchor["anchor_id"] for anchor in left["anchors"]] == [
        anchor["anchor_id"] for anchor in right["anchors"]
    ]
    assert [anchor["centroid_hash"] for anchor in left["anchors"]] == [
        anchor["centroid_hash"] for anchor in right["anchors"]
    ]
    for anchor in left["anchors"]:
        assert anchor["anchor_id"] == anchor_id_for("politics-civic", anchor["source_identity_hashes"])
        assert anchor["source_identity_hashes"] == sorted(anchor["source_identity_hashes"])
        assert anchor["centroid_hash"] == _f32_hash(anchor["vector"])
        assert anchor["support_count"] >= 2


def test_reserved_validation_and_jev_identities_are_not_sources():
    kept = "A romantic relationship between two people who share status"
    blocked_text = "rank without the kept definition should stay out of anchors"
    rows = [
        {
            "class": "OBSERVED",
            "lineage": "relationship-dating",
            "provenance": {"definition_prose": kept},
            "split": "train",
            "task": "classify",
            "text": kept,
        },
        {
            "class": "OBSERVED",
            "evaluation_reserve": True,
            "lineage": "relationship-dating",
            "provenance": {"definition_prose": blocked_text},
            "split": "train",
            "task": "classify",
            "text": blocked_text,
        },
        {
            "class": "OBSERVED",
            "held_out": True,
            "lineage": "relationship-dating",
            "provenance": {"definition_prose": "held out romantic gloss for later"},
            "split": "train",
            "task": "classify",
            "text": "held out romantic gloss for later",
        },
        {
            "class": "OBSERVED",
            "lineage": "relationship-dating",
            "provenance": {"definition_prose": "validation romantic gloss must stay out"},
            "split": "val",
            "task": "classify",
            "text": "validation romantic gloss must stay out",
        },
        {
            "class": "OBSERVED",
            "lineage": "relationship-dating",
            "provenance": {"definition_prose": "measurement surface romantic gloss"},
            "split": "train",
            "surface": "measurement",
            "task": "classify",
            "text": "measurement surface romantic gloss",
        },
        {
            "class": "OBSERVED",
            "lineage": "relationship-dating",
            "provenance": {"definition_prose": "jev romantic gloss is not evidence", "source": "jev"},
            "split": "train",
            "task": "classify",
            "text": "jev romantic gloss is not evidence",
        },
        {
            "class": "OBSERVED",
            "lineage": "gaming-meta",
            "split": "train",
            "task": "unbind",
            "text": "this unbind prose is not a classification definition at all",
        },
    ]
    spent = "spent reserve romantic gloss stays excluded"
    rows.append(
        {
            "class": "OBSERVED",
            "lineage": "relationship-dating",
            "provenance": {"definition_prose": spent},
            "split": "train",
            "task": "classify",
            "text": spent,
        }
    )
    state = {
        normalized_text_sha256(spent): "EVAL_SPENT",
        normalized_text_sha256("fresh reserve romantic gloss"): "EVAL_RESERVE",
        normalized_text_sha256("bound romantic gloss"): "EVAL_BOUND",
    }
    for label, text in (("EVAL_RESERVE", "fresh reserve romantic gloss"), ("EVAL_BOUND", "bound romantic gloss")):
        rows.append(
            {
                "class": "OBSERVED",
                "lineage": "relationship-dating",
                "provenance": {"definition_prose": text},
                "split": "train",
                "task": "classify",
                "text": text,
            }
        )
        state[normalized_text_sha256(text)] = label
    collected = boundary_training_sources(rows, state)
    identities = collected["sources"]["relationship-dating"]["identities"]
    assert identities == [normalized_text_sha256(kept)]
    blocked = {
        normalized_text_sha256(blocked_text),
        normalized_text_sha256(spent),
        normalized_text_sha256("fresh reserve romantic gloss"),
        normalized_text_sha256("bound romantic gloss"),
        normalized_text_sha256("held out romantic gloss for later"),
        normalized_text_sha256("validation romantic gloss must stay out"),
        normalized_text_sha256("measurement surface romantic gloss"),
        normalized_text_sha256("jev romantic gloss is not evidence"),
    }
    assert blocked.isdisjoint(identities)
    assert "gaming-meta" not in collected["sources"]
    assert EXACT_COPY_FAMILIES


def test_pairwise_geometry_is_deterministic_and_covers_nineteen_families():
    first = assemble_boundaries(_all_families())
    second = assemble_boundaries(_all_families())
    shuffled = _all_families()
    shuffled["social-status"] = list(reversed(shuffled["social-status"]))
    third = assemble_boundaries(shuffled)
    assert first["separation_sha256"] == second["separation_sha256"] == third["separation_sha256"]
    assert first["anchor_witness_sha256"] == third["anchor_witness_sha256"]
    assert first["boundary_sha256"] == third["boundary_sha256"]
    assert [family["family"] for family in first["families"]] == list(ACTIVE_FAMILY_VOCABULARY)
    assert len(first["families"]) == 19
    assert len(first["separation"]) == 19 * 18
    rich = next(family for family in first["families"] if family["family"] == "social-status")
    assert rich["k"] == 2
    assert rich["support_status"] == SUPPORT_OK
    sparse = [family["family"] for family in first["families"] if family["support_status"] == SUPPORT_SPARSE]
    assert len(sparse) == 18
    report = assess_boundary_artifact(first)
    assert report["pass"] is True
    assert canonical_boundary_representation(first) == CANONICAL_REPRESENTATION


def test_single_centroid_is_not_the_canonical_boundary_representation():
    artifact = assemble_boundaries(_all_families())
    assert artifact["schema"] == BOUNDARY_SCHEMA
    assert artifact["representation"] == CANONICAL_REPRESENTATION
    contract = artifact["future_discriminator"]
    assert contract["semantic_score"] == "max_anchor_cosine"
    assert contract["rejected_semantic_score"] == REJECTED_REPRESENTATION
    assert contract["hard_negatives"] == "nearest_competing_anchors"
    assert contract["train"] is False
    assert "single_family_centroid" not in contract["formula"]
    members = _separated("social-status", 3)
    pooled = _f32_round(_unit(weighted_mean([_unit(member["vector"]) for member in members], [1.0] * len(members))))
    pooled_hash = _f32_hash(pooled)
    rich = next(family for family in artifact["families"] if family["family"] == "social-status")
    assert len(rich["anchors"]) >= 2
    assert pooled_hash not in {anchor["centroid_hash"] for anchor in rich["anchors"]}
    refused = assess_boundary_artifact(
        {"schema": "hyperlex.classification.v2.prototype_geometry.v1", "representation": "single_family_centroid"}
    )
    assert refused["pass"] is False
