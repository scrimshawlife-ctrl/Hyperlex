"""Forward-hub error decomposition tests. No train / reserve / BEST."""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
import hyperlexical.classification_v2 as v2  # noqa: E402

importlib.reload(v2)

from hyperlexical.classification_v2_forward_hub_error_decomposition import (  # noqa: E402
    DECISIONS,
    FAILURE_CAUSES,
    PRIOR_INTERNAL_ACTIVE_FAMILY_MACRO_F1,
    RULE,
    SOCIAL_EVALUATION,
    assign_primary_cause,
    assemble_error_decomposition,
    decide_remediation,
    detect_prediction_hubs,
    error_decomposition_contract,
    logit_rank,
    score_validation_bundle_from_tensors,
)


def test_contract_is_read_only():
    contract = error_decomposition_contract()
    assert contract["rule"] == RULE
    assert contract["train"] is False
    assert contract["moves_best"] is False
    assert contract["reserve_scored"] is False
    assert contract["modifies_prototypes"] is False
    assert contract["applies_ontology_change"] is False
    assert contract["prior_internal_active_family_macro_f1"] == PRIOR_INTERNAL_ACTIVE_FAMILY_MACRO_F1


def test_logit_rank_and_hub_detection():
    assert logit_rank([0.1, 0.5, 0.2], 1) == 1
    assert logit_rank([0.1, 0.5, 0.2], 0) == 3
    labels = list(v2.ACTIVE_FAMILY_VOCABULARY)
    golds = [labels[0]] * 4 + [labels[1]] * 4
    preds = [labels[0]] * 8  # family0 absorbs all
    hubs = detect_prediction_hubs(golds, preds, labels, incoming_fp_min=3, ratio_min=1.5)
    assert hubs
    assert hubs[0]["family"] == labels[0]
    assert hubs[0]["flag"] == "PREDICTION_HUB"


def test_cause_priority_under_supported_and_hub():
    labels = list(v2.ACTIVE_FAMILY_VOCABULARY)
    gold = labels[5]
    pred = labels[0]
    assigned = assign_primary_cause(
        gold=gold,
        pred=pred,
        gold_support=2,
        gold_residual_rank=4,
        gold_prototype_rank=5,
        residual_logits=[0.0] * len(labels),
        gold_index=5,
        pred_index=0,
        prediction_hubs={pred},
        overlap_pairs=set(),
        gold_surface="ATOM",
        gold_majority_surface="PROSE",
        pred_majority_surface="ATOM",
        initialization_mode="SEMANTIC_PROTOTYPE",
        evidence_class="OBSERVED",
    )
    assert assigned["cause"] == "UNDER_SUPPORTED_FAMILY"
    assigned_hub = assign_primary_cause(
        gold=gold,
        pred=pred,
        gold_support=20,
        gold_residual_rank=4,
        gold_prototype_rank=5,
        residual_logits=[0.0] * len(labels),
        gold_index=5,
        pred_index=0,
        prediction_hubs={pred},
        overlap_pairs=set(),
        gold_surface="ATOM",
        gold_majority_surface="ATOM",
        pred_majority_surface="ATOM",
        initialization_mode="SEMANTIC_PROTOTYPE",
        evidence_class="OBSERVED",
    )
    assert assigned_hub["cause"] == "DOMINANT_CLASS_ATTRACTOR"


def test_decide_blocks_reserve_when_below_baseline():
    decision = decide_remediation(
        active_family_macro_f1=0.1856,
        prototype_family_macro_f1=0.0545,
        hubs=[{"family": SOCIAL_EVALUATION}],
        se_audit={
            "flag": "LARGER_ATTRACTOR",
            "f1": 0.0,
            "is_prediction_hub": True,
        },
        cause_counts={"DOMINANT_CLASS_ATTRACTOR": 10, "UNDER_SUPPORTED_FAMILY": 4},
        loss_drivers={"families_with_zero_f1": [SOCIAL_EVALUATION] + ["x"] * 6},
        prototype_compare={"prototype_path_macro_f1": 0.04, "residual_macro_f1": 0.18},
    )
    assert decision["decision"] == "ONTOLOGY_REMEDIATION_JUSTIFIED"
    assert decision["decision"] in DECISIONS
    assert decision["competitive_with_prior_baseline"] is False


def test_assemble_roundtrip_small_bundle():
    labels = list(v2.ACTIVE_FAMILY_VOCABULARY)
    assert len(labels) == 18
    n = 18
    golds = list(labels)
    # Perfect residual predictions except SE -> internet-slang and RD -> SE.
    residual_preds = list(labels)
    residual_preds[labels.index(SOCIAL_EVALUATION)] = "internet-slang"
    residual_preds[labels.index("relationship-dating")] = SOCIAL_EVALUATION
    residual_logits = []
    prototype_logits = []
    for index, _gold in enumerate(golds):
        residual = [-1.0] * n
        residual[index] = 2.0
        proto = [-1.0] * n
        proto[index] = 1.0
        residual_logits.append(residual)
        prototype_logits.append(proto)
    # Force the two intentional errors in logits too.
    se_i = labels.index(SOCIAL_EVALUATION)
    rd_i = labels.index("relationship-dating")
    is_i = labels.index("internet-slang")
    residual_logits[se_i] = [-1.0] * n
    residual_logits[se_i][is_i] = 3.0
    residual_logits[se_i][se_i] = 0.5
    residual_logits[rd_i] = [-1.0] * n
    residual_logits[rd_i][se_i] = 3.0
    residual_logits[rd_i][rd_i] = 0.5
    init = {
        name: ("EXACT_ROW_COPY" if name in v2.EXACT_COPY_FAMILIES else "SEMANTIC_PROTOTYPE")
        for name in labels
    }
    artifact = score_validation_bundle_from_tensors(
        labels=labels,
        residual_logits=residual_logits,
        prototype_logits=prototype_logits,
        golds=golds,
        texts=["alpha beta"] * n,
        evidence_classes=["OBSERVED"] * n,
        initialization_by_family=init,
        overlap_pairs=[
            {
                "cosine": 0.93,
                "family_a": SOCIAL_EVALUATION,
                "family_b": "relationship-dating",
            },
            {
                "cosine": 0.92,
                "family_a": SOCIAL_EVALUATION,
                "family_b": "internet-slang",
            },
        ],
        train_rows=[
            {"lineage": name, "text": "alpha beta gamma delta epsilon zeta"}
            for name in labels
        ],
    )
    assert artifact["rule"] == RULE
    assert artifact["audit_state"]["reserve_scored"] is False
    assert artifact["audit_state"]["train"] is False
    assert artifact["n_family_rows"] == 18
    assert artifact["n_errors"] == 2
    assert set(FAILURE_CAUSES) == {row["cause"] for row in artifact["dominant_failure_categories"]}
    assert "confusion_matrix_sha256" in artifact
    assert artifact["decision"] in DECISIONS
    assert SOCIAL_EVALUATION in artifact["per_family"]
    assert "relationship_dating_confusion" in artifact["social_evaluation"]
    # Hash stability on a second assembly with the same payload.
    again = assemble_error_decomposition(
        {
            "evidence_classes": ["OBSERVED"] * n,
            "golds": golds,
            "initialization_by_family": init,
            "labels": labels,
            "overlap_pairs": [
                {
                    "cosine": 0.93,
                    "family_a": SOCIAL_EVALUATION,
                    "family_b": "relationship-dating",
                },
                {
                    "cosine": 0.92,
                    "family_a": SOCIAL_EVALUATION,
                    "family_b": "internet-slang",
                },
            ],
            "prototype_preds": list(labels),
            "prototype_ranks": [1] * n,
            "residual_logits": residual_logits,
            "residual_preds": residual_preds,
            "residual_ranks": [
                1 if gold == pred else 2
                for gold, pred in zip(golds, residual_preds, strict=True)
            ],
            "surfaces": ["ATOM"] * n,
            "train_rows": [
                {"lineage": name, "text": "alpha beta gamma delta epsilon zeta"}
                for name in labels
            ],
        }
    )
    assert again["confusion_matrix_sha256"] == artifact["confusion_matrix_sha256"]
