"""Tests for HYPERLEX_V5_STAGE_A_B_PIPELINE_V1."""

from __future__ import annotations

from hyperlexical.classification_v5_stage_a_b_pipeline import (
    PIPELINE_ID,
    integrate_text_probabilities,
    pipeline_contract,
    verify_entry_gating,
    verify_stage_b_parent_and_floors,
)
from hyperlexical.classification_v5_stage_b import (
    FROZEN_INDEX_SHA256,
    FROZEN_MINIMUM_FAMILY_SCORE,
    FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
)


def test_pipeline_and_integration():
    assert PIPELINE_ID == "HYPERLEX_V5_STAGE_A_B_PIPELINE_V1"
    assert verify_entry_gating()["pass"] is True
    parent = verify_stage_b_parent_and_floors()
    assert parent["pass"] is True
    assert parent["contract_slice"]["STAGE_A_BEST"].startswith("f2b00c5d")
    assert parent["contract_slice"]["frozen_index_sha256"] == FROZEN_INDEX_SHA256
    assert parent["contract_slice"]["minimum_family_score"] == FROZEN_MINIMUM_FAMILY_SCORE
    assert (
        parent["contract_slice"]["minimum_top1_top2_margin"]
        == FROZEN_MINIMUM_TOP1_TOP2_MARGIN
    )
    contract = pipeline_contract()
    assert contract["dependencies"]["stage_b_index_sha256"] == FROZEN_INDEX_SHA256
    present = integrate_text_probabilities(p_relation=0.91, p_resolvable=0.88)
    assert present["invokes_stage_b"] is True
    none = integrate_text_probabilities(p_relation=0.1, p_resolvable=0.9)
    assert none["invokes_stage_b"] is False
    uncertain = integrate_text_probabilities(p_relation=0.9, p_resolvable=0.2)
    assert uncertain["invokes_stage_b"] is False
