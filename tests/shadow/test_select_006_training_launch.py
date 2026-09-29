"""SELECT-006 launch checks reject a drifted schedule and a drifted loader."""

from hyperlexical.select_006_reserve_eval import EXPECTED_COUNTS, reserve_examples
from hyperlexical.select_006_training_launch import (
    LaunchFailure,
    require_witness,
    validate_arm_telemetry,
)
import pytest


def _row(epoch: int, score: float, *, improved: bool, step: int, ckpt: str, early: bool = False, since: int = 0, tie: bool = False) -> dict:
    return {
        "checkpoint_sha256": ckpt,
        "classification_accuracy": 0.5,
        "classify_macro_f1_nonnone": score,
        "early_stop": early,
        "epoch": epoch,
        "epoch_wallclock_seconds": 1.0,
        "epochs_since_best": since,
        "global_step": step,
        "improved": improved,
        "learning_rate": 2e-5,
        "observed_label_accuracy": 0.5,
        "tie": tie,
        "training_elapsed_seconds": float(epoch + 1),
        "training_loss": 1.0,
        "unbind_clean_exact": None,
    }


def _control():
    rows = [
        _row(epoch, 0.1 + epoch * 0.01, improved=True, step=(epoch + 1) * 10, ckpt=f"c{epoch}")
        for epoch in range(40)
    ]
    receipt = {
        "best_checkpoint_sha256": "c39",
        "best_epoch": 39,
        "global_steps": 400,
        "primary_weights_sha256": "c39",
        "stop_reason": "max_epochs",
        "training_elapsed_seconds": 40.0,
    }
    return rows, receipt


def test_control_schedule_accepts_forty_epochs_without_early_stopping():
    rows, receipt = _control()
    summary = validate_arm_telemetry(
        "control",
        rows,
        receipt,
        primary_file_sha="c39",
        best_file_sha="c39",
    )
    assert summary["epochs_completed"] == 40
    assert summary["optimizer_steps"] == 400
    assert summary["stop_reason"] == "max_epochs"


def test_restore_mismatch_fails_closed():
    rows, receipt = _control()
    with pytest.raises(LaunchFailure, match="RESTORE_BEST_FAILURE"):
        validate_arm_telemetry(
            "control",
            rows,
            receipt,
            primary_file_sha="other",
            best_file_sha="c39",
        )


def test_witness_mismatch_fails_closed():
    with pytest.raises(LaunchFailure, match="ZERO_INIT_LOADER_MISMATCH"):
        require_witness(
            {
                "execution_loader_status": "ZERO_INIT_LOADER_VERIFIED",
                "expanded_filler_bias_sha256": "0" * 64,
                "expanded_filler_weight_sha256": "b3d11a8eb1fcfb4f616c36b9f5b32be84aab9c91d642e54294dccfea36a385a3",
                "expanded_loader_witness_sha256": "58a3e733087c33c5ffea5909b46098e666337e1b99fb83d87c3744db4aef91b2",
                "expanded_role_bias_sha256": "ce7b6ecb2b276d4d5b46ae23f38a749d1939cadc336e82b76548e01065151b93",
                "expanded_role_weight_sha256": "94aa92d4c6f17f56a6d7a68a5951ad98bb38764d029ed93916fb9b870c54c20d",
                "optimizer_constructed": False,
                "stopped_before_optimizer": True,
            }
        )


def test_frozen_reserve_join_keeps_the_sealed_slices():
    examples = reserve_examples()
    assert len(examples) == 37
    counts = {name: 0 for name in EXPECTED_COUNTS if name != "head_mapped_non_none"}
    families = {}
    for example in examples:
        for name in example["slices"]:
            counts[name] += 1
        if example["task"] == "classify":
            families[example["lineage"]] = families.get(example["lineage"], 0) + 1
            assert example["text"]
        else:
            assert example["unbind_clean"] is True
            assert example["fillers"]
    assert counts == {key: value for key, value in EXPECTED_COUNTS.items() if key != "head_mapped_non_none"}
    assert sum(families.values()) == EXPECTED_COUNTS["head_mapped_non_none"]
    assert families == {
        "ai-native": 8,
        "betting-sharp": 8,
        "crypto-degen": 8,
        "gaming-meta": 8,
    }
