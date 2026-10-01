"""Unit tests for RETRY_PROMOTE_STAGE_A_IDENT_FILTERED_FACTORIZED_CANDIDATE."""

from __future__ import annotations

from hyperlexical.classification_v5_stage_a_ident_filtered_repro_promote import (
    EXPECTED_METRICS,
    INCOMPLETE_HISTORICAL_CHECKPOINT_SHA256,
    MODEL_WIDE_BEST_SHA256,
    PREVIOUS_STAGE_A_BEST_SHA256,
    PROMOTE_RULE,
    STAGE_A_BEST_SHA256,
    build_promotion_receipt,
    build_stage_a_best_pointer,
    decide_canonical_stage_a,
    may_invoke_stage_b,
    metric_parity,
    preflight_promotion,
    round_trip_logit_parity,
    stage_b_entry_from_stage_a,
    verify_head_completeness,
)


def _complete_keys() -> list[str]:
    # 12 encoder overlay keys + 4 factorized head tensors.
    enc = []
    for layer in (20, 21):
        for name in (
            "attn.Wqkv.weight",
            "attn.Wqkv.bias",
            "attn.Wo.weight",
            "attn.Wo.bias",
            "mlp.Wi.weight",
            "mlp.Wi.bias",
            "mlp.Wo.weight",
            "mlp.Wo.bias",
        ):
            # ModernBERT last-2 layout uses fewer keys in practice; pad to 12.
            pass
    enc = [
        f"encoder.layers.{i}.{s}"
        for i, s in enumerate(
            [
                "attn.Wqkv.weight",
                "attn.Wqkv.bias",
                "attn.Wo.weight",
                "attn.Wo.bias",
                "mlp.Wi.weight",
                "mlp.Wi.bias",
            ]
            * 2
        )
    ][:12]
    return enc + [
        "relation_head.weight",
        "relation_head.bias",
        "resolvability_head.weight",
        "resolvability_head.bias",
    ]


def test_pins_and_rule():
    assert PROMOTE_RULE == "RETRY_PROMOTE_STAGE_A_IDENT_FILTERED_FACTORIZED_CANDIDATE"
    assert STAGE_A_BEST_SHA256.startswith("f2b00c5d")
    assert INCOMPLETE_HISTORICAL_CHECKPOINT_SHA256.startswith("8b2de447")
    assert PREVIOUS_STAGE_A_BEST_SHA256.startswith("cd2829c1")
    assert MODEL_WIDE_BEST_SHA256.startswith("9fba0f66")
    assert STAGE_A_BEST_SHA256 != INCOMPLETE_HISTORICAL_CHECKPOINT_SHA256


def test_head_completeness_requires_16_keys():
    ok = verify_head_completeness(_complete_keys())
    assert ok["pass"] is True
    assert ok["n_keys"] == 16
    assert ok["factorized_heads_cold_loadable"] is True
    bad = verify_head_completeness(_complete_keys()[:12])
    assert bad["pass"] is False


def test_canonical_inference_and_stage_b():
    assert decide_canonical_stage_a(p_relation=0.9, p_resolvable=0.5) == "UNCERTAIN"
    assert (
        decide_canonical_stage_a(p_relation=0.9, p_resolvable=0.8) == "EVIDENCE_PRESENT"
    )
    assert decide_canonical_stage_a(p_relation=0.4, p_resolvable=0.8) == "NO_EVIDENCE"
    assert may_invoke_stage_b("EVIDENCE_PRESENT") is True
    assert may_invoke_stage_b("NO_EVIDENCE") is False
    assert stage_b_entry_from_stage_a("UNCERTAIN")["action"] == "ABSTAIN"


def test_preflight_pass_and_reject_incomplete():
    train = {
        "SCIENTIFIC_RESULT": "SETTLED_PASS",
        "REPRODUCTION_CLASSIFICATION": "SCIENTIFICALLY_EQUIVALENT_REPRODUCTION",
        "EXPERIMENT_ID": (
            "HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-IDENT-FILTERED-REPRO-001"
        ),
        "PARENT_EXPERIMENT": (
            "HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-IDENT-FILTERED-001"
        ),
        "DATASET_SHA256": (
            "492ed36751c7fdc40fe10bcdfabb69fa8783f8680259c31b3a64ee6903326d73"
        ),
        "ANNOTATION_SHA256": (
            "95d5436555da33ef7aaccf4c32194c29f00caced9a17adf2d2f65f12db7dc1fc"
        ),
        "EXCLUSION_MANIFEST_SHA256": (
            "661c9edb095f7f7dc28a24256b42e0a2796f9ab78fbabc24b23cf9bd57b06d69"
        ),
        "AUTHORIZATION_RECEIPT_SHA256": (
            "09f3d456961aaa9027ff35ac653f3d6aeee627ceee1eb705fcd83dc9b9c3205b"
        ),
        "TRAINING_CONFIG_SHA256": (
            "731c0b260fb5f6966c47d1700d522c42aad8126b6be2f482b078eb6c8ab8325e"
        ),
        "CLASS_WEIGHT_ARTIFACT_SHA256": (
            "13e8d0ca250839500b71b4b9e23d8238a90488987b9a49cd2c6d2fc336f77fc6"
        ),
        "SELECTED_CHECKPOINT_SHA256": STAGE_A_BEST_SHA256,
        "restored_epoch": 11,
        "selection_score": 0.9672661029515868,
        "selected_thresholds": {
            "relation_threshold": 0.60,
            "resolvability_threshold": 0.75,
        },
        "acceptance_gates": {
            "false_evidence_entry_rate_on_none": {
                "pass": True,
                "value": 0.03356890459363958,
            },
            "EVIDENCE_PRESENT_recall": {"pass": True, "value": 0.951310861423221},
            "NO_EVIDENCE_recall": {"pass": True, "value": 0.9646643109540636},
        },
        "V1R2_MUTATED": False,
        "RESERVE": "SPENT",
        "SPENT_RESERVE": "HYPERLEX_V5_PROMOTION_RESERVE_001",
        "RUN_RECEIPT_SHA256": (
            "8b8585a8637176a64adf9ce6cff2a076fd4bf938070aef02203fa46978e20ed1"
        ),
        "OBJECTIVE_ID": "HYPERLEX_V5_STAGE_A_FACTORIZED_RELATION_OBJECTIVE_V1",
    }
    ok = preflight_promotion(
        train_receipt=train,
        selected_checkpoint_sha256=STAGE_A_BEST_SHA256,
        model_wide_best_sha256=MODEL_WIDE_BEST_SHA256,
        current_stage_a_best_sha256=PREVIOUS_STAGE_A_BEST_SHA256,
        dataset_sha256=train["DATASET_SHA256"],
        annotation_sha256=train["ANNOTATION_SHA256"],
        exclusion_manifest_sha256=train["EXCLUSION_MANIFEST_SHA256"],
        v1r2_mutated=False,
        stage_a_tensor_keys=_complete_keys(),
    )
    assert ok["pass"] is True
    bad = preflight_promotion(
        train_receipt=train,
        selected_checkpoint_sha256=INCOMPLETE_HISTORICAL_CHECKPOINT_SHA256,
        model_wide_best_sha256=MODEL_WIDE_BEST_SHA256,
        current_stage_a_best_sha256=PREVIOUS_STAGE_A_BEST_SHA256,
        dataset_sha256=train["DATASET_SHA256"],
        annotation_sha256=train["ANNOTATION_SHA256"],
        exclusion_manifest_sha256=train["EXCLUSION_MANIFEST_SHA256"],
        v1r2_mutated=False,
        stage_a_tensor_keys=_complete_keys(),
    )
    assert bad["pass"] is False
    assert bad["checks"]["not_incomplete_historical"] is False
    assert metric_parity(EXPECTED_METRICS, EXPECTED_METRICS)["pass"] is True


def test_round_trip_and_receipt():
    rt = round_trip_logit_parity(
        decisions_a=["NO_EVIDENCE", "EVIDENCE_PRESENT"],
        decisions_b=["NO_EVIDENCE", "EVIDENCE_PRESENT"],
        logits_a=[[0.1, 0.2], [0.3, 0.4]],
        logits_b=[[0.1, 0.2], [0.3, 0.4]],
    )
    assert rt["pass"] is True
    assert rt["decision_mismatch_count"] == 0
    pointer = build_stage_a_best_pointer(
        weights_path="/tmp/model.safetensors",
        previous_stage_a_best=PREVIOUS_STAGE_A_BEST_SHA256,
        code_revision="test",
        promoted_at="2026-10-01T00:00:00Z",
    )
    assert pointer["parent_model_wide_best"].startswith("9fba0f66")
    receipt = build_promotion_receipt(
        preflight={"pass": True, "checks": {}},
        pointer=pointer,
        overlay={"pass": True},
        post_replay={"pass": True, "metrics": {}, "replay_hash": "abc"},
        previous_stage_a_best=PREVIOUS_STAGE_A_BEST_SHA256,
        code_revision="test",
        promoted_at="2026-10-01T00:00:00Z",
        head_completeness={"pass": True, "n_keys": 16},
        round_trip=rt,
        factorized_head_manifest_hashes={"relation_head.weight": "x"},
        checkpoint_tensor_manifest_hash="y",
    )
    assert receipt["STAGE_A_PROMOTION"] == "APPLIED"
    assert receipt["STAGE_A_BEST"] == STAGE_A_BEST_SHA256
    assert receipt["MODEL_WIDE_BEST_MUTATED"] is False
    assert receipt["RESERVE_CONSUMED"] is False
    assert receipt["HISTORICAL_INCOMPLETE_ARTIFACT"]["may_become_STAGE_A_BEST"] is False
    assert "STAGE_A_PROMOTION_RECEIPT_SHA256" in receipt
