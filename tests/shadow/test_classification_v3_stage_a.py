"""Stage A evidence-gate metric/calibration tests. No GPU train."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v3_evidence_gate import (  # noqa: E402
    FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX,
)
from hyperlexical.classification_v3_stage_a import (  # noqa: E402
    STAGE_A_RULE,
    calibrate_thresholds,
    evaluate_decisions,
    false_evidence_entry_rate_on_none,
    next_action_for_stage_a,
    softmax_logits,
    stage_a_contract,
    stratified_label_indices,
)


def test_stage_a_contract_frozen():
    contract = stage_a_contract()
    assert contract["rule"] == STAGE_A_RULE
    assert contract["train"] is True
    assert contract["v3_reserve"] is None
    assert contract["false_evidence_entry_rate_on_none_max"] == 0.05
    assert contract["hyperparams"]["epochs"] == 4
    assert contract["hyperparams"]["stratified_label_batches"] is True


def test_false_entry_and_calibration_prefers_gate_pass():
    golds = (
        ["NO_EVIDENCE"] * 100
        + ["EVIDENCE_PRESENT"] * 50
        + ["UNCERTAIN"] * 20
    )
    # Low scores on NONE, high on PRESENT, mid on UNCERTAIN.
    scores = [0.02] * 100 + [0.9] * 50 + [0.45] * 20
    # Inject a few false entries if threshold is loose.
    scores[0] = 0.95
    scores[1] = 0.95
    rate = false_evidence_entry_rate_on_none(
        golds, ["EVIDENCE_PRESENT"] * 2 + ["NO_EVIDENCE"] * 98 + ["EVIDENCE_PRESENT"] * 50 + ["UNCERTAIN"] * 20
    )
    assert abs(rate - 0.02) < 1e-9
    calibration = calibrate_thresholds(golds, scores)
    assert calibration["feasible"] is True
    assert calibration["chosen"]["primary_gate_pass"] is True
    assert (
        calibration["metrics"]["false_evidence_entry_rate_on_none"]
        <= FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX
    )
    assert next_action_for_stage_a(primary_gate_pass=True).startswith("WIRE_STAGE_B")
    assert next_action_for_stage_a(primary_gate_pass=False).startswith("DIAGNOSE_STAGE_A")


def test_softmax_and_stratified_batches():
    probs = softmax_logits([0.0, 2.0, 0.0])
    assert abs(sum(probs.values()) - 1.0) < 1e-9
    assert probs["EVIDENCE_PRESENT"] > probs["NO_EVIDENCE"]
    labels = (
        ["NO_EVIDENCE"] * 30
        + ["EVIDENCE_PRESENT"] * 30
        + ["UNCERTAIN"] * 30
    )
    batches = stratified_label_indices(labels, batch_size=6, seed=7)
    assert batches
    assert all(len(batch) >= 3 for batch in batches)
    metrics = evaluate_decisions(
        ["NO_EVIDENCE", "EVIDENCE_PRESENT", "UNCERTAIN"],
        ["NO_EVIDENCE", "EVIDENCE_PRESENT", "UNCERTAIN"],
    )
    assert metrics["primary_gate_pass"] is True
    assert metrics["by_label"]["EVIDENCE_PRESENT"]["f1"] == 1.0
