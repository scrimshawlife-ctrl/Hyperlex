"""Max-anchor family scorer. No training, no reserve, no BEST writes."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v2 import EXACT_COPY_FAMILIES  # noqa: E402
from hyperlexical.classification_v2_boundaries import assemble_boundaries  # noqa: E402
from hyperlexical.classification_v2_max_anchor import (  # noqa: E402
    ACTIVE_FAMILY_VOCABULARY,  # snapshot matching max_anchor module internal state
    BOUNDARY_SHA,
    FUSION_ALPHA,
    FUSION_BETA,
    REPAIR_PRIMARY_SHA,
    SCORER_RULE,
    SEPARATION_SHA,
    decide_max_anchor,
    fusion_scores,
    load_sealed_anchors,
    max_anchor_scores,
    predict_family,
    residual_scores,
    scorer_contract,
    topk_families,
)


def _axis(slot: int, identity: str, text: str) -> dict:
    vector = [0.0] * 8
    vector[slot % 8] = 1.0
    return {
        "class": "OBSERVED",
        "identity": identity,
        "text": text,
        "vector": vector,
        "weight": 1.0,
    }


def _toy_boundaries() -> dict:
    members = {}
    for index, family in enumerate(ACTIVE_FAMILY_VOCABULARY):
        if family in {"internet-slang", "memetic", "betting-sharp"}:
            members[family] = [_axis(index, f"{family}-only", f"{family} lone")]
        else:
            members[family] = [
                _axis(index, f"{family}-a", f"{family} alpha"),
                _axis(index + 1, f"{family}-b", f"{family} beta"),
                _axis(index, f"{family}-c", f"{family} alpha two"),
            ]
    artifact = assemble_boundaries(members, vocabulary=ACTIVE_FAMILY_VOCABULARY)
    artifact["boundary_sha256"] = BOUNDARY_SHA
    artifact["separation_sha256"] = SEPARATION_SHA
    # assess_boundary_artifact recomputes hashes, so load_sealed_anchors will fail
    # unless we bypass via a patched path. For unit tests that need sealed load,
    # we use a helper that only checks coverage when hashes are forced after
    # monkeypatching assess. Instead, test load through a thin wrapper using
    # the public API on a real-shaped object by stubbing assess in the module.
    return artifact


def test_scorer_contract_is_read_only_and_pins_geometry_inputs():
    contract = scorer_contract()
    assert contract["rule"] == SCORER_RULE
    assert contract["train"] is False
    assert contract["jev"] == "OFF"
    assert contract["fusion_diagnostic_only"] is True
    assert contract["fusion_alpha"] == FUSION_ALPHA == 1.0
    assert contract["fusion_beta"] == FUSION_BETA == 1.0
    assert contract["boundary_sha256"] == BOUNDARY_SHA
    assert contract["separation_sha256"] == SEPARATION_SHA
    assert contract["repair_primary_sha256"] == REPAIR_PRIMARY_SHA
    assert "none" not in ACTIVE_FAMILY_VOCABULARY
    assert "ABSTAIN" not in ACTIVE_FAMILY_VOCABULARY


def test_max_over_anchor_scoring_is_deterministic_and_covers_nineteen_families(monkeypatch):
    import hyperlexical.classification_v2_max_anchor as module

    toy = _toy_boundaries()
    monkeypatch.setattr(
        module,
        "assess_boundary_artifact",
        lambda _boundaries: {"pass": True},
    )
    loaded = load_sealed_anchors(toy)
    assert loaded["n_anchors"] >= len(ACTIVE_FAMILY_VOCABULARY)
    assert set(loaded["anchors"]) == set(ACTIVE_FAMILY_VOCABULARY)
    for family in ("internet-slang", "memetic", "betting-sharp"):
        assert len(loaded["anchors"][family]) == 1
    test_family = "gaming-meta"
    before = copy.deepcopy(loaded["anchors"][test_family])
    query = [0.0] * 8
    query[ACTIVE_FAMILY_VOCABULARY.index(test_family) % 8] = 1.0
    first = max_anchor_scores(query, loaded["anchors"])
    second = max_anchor_scores(list(reversed(query)) and query, loaded["anchors"])
    assert first == second
    assert len(first) == len(ACTIVE_FAMILY_VOCABULARY)
    assert loaded["anchors"][test_family] == before
    assert predict_family(first) == test_family


def test_tie_breaking_is_vocabulary_order_and_forbids_none_family_row():
    scores = [0.1 for _name in ACTIVE_FAMILY_VOCABULARY]
    scores[0] = 0.9
    scores[1] = 0.9
    assert predict_family(scores) == ACTIVE_FAMILY_VOCABULARY[0]
    assert topk_families(scores, 2) == [
        ACTIVE_FAMILY_VOCABULARY[0],
        ACTIVE_FAMILY_VOCABULARY[1],
    ]
    residual = residual_scores([0.0 for _name in ACTIVE_FAMILY_VOCABULARY])
    assert len(residual) == len(ACTIVE_FAMILY_VOCABULARY)
    fused = fusion_scores(scores, residual)
    assert len(fused) == len(ACTIVE_FAMILY_VOCABULARY)
    assert FUSION_ALPHA == 1.0 and FUSION_BETA == 1.0


def test_decision_gate_and_residual_scorer_path_remain_separate():
    supported = decide_max_anchor(
        {
            "active_family_macro_f1": 0.20,
            "breadth": {"new_family_f1_gt_0": 4},
        }
    )
    assert supported["decision"] == "MAX_ANCHOR_SCORER_SUPPORTED"
    assert supported["canonical_integration_justified"] is True
    rejected = decide_max_anchor(
        {
            "active_family_macro_f1": 0.19,
            "breadth": {"new_family_f1_gt_0": 5},
        }
    )
    assert rejected["decision"] == "MAX_ANCHOR_SCORER_REJECTED"
    assert rejected["canonical_integration_justified"] is False
    assert EXACT_COPY_FAMILIES
    # Residual scores are pass-through logits; they are not mixed into max-anchor.
    logits = [float(index) for index, _name in enumerate(ACTIVE_FAMILY_VOCABULARY)]
    assert residual_scores(logits) == logits
    assert scorer_contract()["train"] is False
