"""SELECT-006 launch checks. Scoring and training stay outside this module."""

from __future__ import annotations

from typing import Any, Mapping

WITNESS = {
    "expanded_filler_bias_sha256": "cce2ff11650d8b9734f84f1d05acd65003b68e31adb5e0c9e035beaa7f5a03bf",
    "expanded_filler_weight_sha256": "b3d11a8eb1fcfb4f616c36b9f5b32be84aab9c91d642e54294dccfea36a385a3",
    "expanded_loader_witness_sha256": "58a3e733087c33c5ffea5909b46098e666337e1b99fb83d87c3744db4aef91b2",
    "expanded_role_bias_sha256": "ce7b6ecb2b276d4d5b46ae23f38a749d1939cadc336e82b76548e01065151b93",
    "expanded_role_weight_sha256": "94aa92d4c6f17f56a6d7a68a5951ad98bb38764d029ed93916fb9b870c54c20d",
}
TRACE_FIELDS = (
    "checkpoint_sha256",
    "classification_accuracy",
    "classify_macro_f1_nonnone",
    "early_stop",
    "epoch",
    "epoch_wallclock_seconds",
    "global_step",
    "improved",
    "learning_rate",
    "observed_label_accuracy",
    "tie",
    "training_elapsed_seconds",
    "training_loss",
    "unbind_clean_exact",
)


class LaunchFailure(SystemExit):
    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(f"{code}: {detail}")


def require_witness(receipt: Mapping[str, Any]) -> None:
    if receipt.get("execution_loader_status") != "ZERO_INIT_LOADER_VERIFIED":
        raise LaunchFailure("ZERO_INIT_LOADER_MISMATCH", "execution_loader_status")
    if receipt.get("stopped_before_optimizer") is not True or receipt.get("optimizer_constructed") is not False:
        raise LaunchFailure("ZERO_INIT_LOADER_MISMATCH", "optimizer was constructed")
    for key, expected in WITNESS.items():
        if receipt.get(key) != expected:
            raise LaunchFailure("ZERO_INIT_LOADER_MISMATCH", key)


def validate_arm_telemetry(
    name: str,
    rows: list[Mapping[str, Any]],
    receipt: Mapping[str, Any],
    *,
    primary_file_sha: str,
    best_file_sha: str,
) -> dict[str, Any]:
    """Require the sealed schedule, exact telemetry, and restore-best identity."""
    if not rows:
        raise LaunchFailure("TELEMETRY_INCOMPLETE", f"{name} progress is empty")
    for row in rows:
        missing = [key for key in TRACE_FIELDS if key not in row]
        if missing:
            raise LaunchFailure("TELEMETRY_INCOMPLETE", f"{name} missing {','.join(missing)}")
        if row["training_loss"] is None or row["classify_macro_f1_nonnone"] is None:
            raise LaunchFailure("TELEMETRY_INCOMPLETE", f"{name} epoch {row['epoch']} metric")
        if row["classification_accuracy"] is None or row["observed_label_accuracy"] is None:
            raise LaunchFailure("TELEMETRY_INCOMPLETE", f"{name} accuracy")
        if row["unbind_clean_exact"] is not None:
            raise LaunchFailure("TELEMETRY_INCOMPLETE", f"{name} inferred unbind_clean_exact")
        if row["checkpoint_sha256"] in (None, ""):
            raise LaunchFailure("CHECKPOINT_FAILURE", f"{name} checkpoint identity")
        if float(row["learning_rate"]) != 2e-5:
            raise LaunchFailure("SCHEDULE_VIOLATION", f"{name} learning rate")
        if row["global_step"] is None or int(row["global_step"]) < 0:
            raise LaunchFailure("TELEMETRY_INCOMPLETE", f"{name} optimizer step")
    if rows[-1]["global_step"] <= 0:
        raise LaunchFailure("TRAINING_RUNTIME_FAILURE", f"{name} took no optimizer steps")
    if receipt.get("global_steps") != rows[-1]["global_step"]:
        raise LaunchFailure("TELEMETRY_INCOMPLETE", f"{name} global step mismatch")
    if receipt.get("training_elapsed_seconds") is None:
        raise LaunchFailure("TELEMETRY_INCOMPLETE", f"{name} wall time")
    primary = receipt.get("primary_weights_sha256")
    best = receipt.get("best_checkpoint_sha256")
    if not primary or primary != best or primary != primary_file_sha or best != best_file_sha:
        raise LaunchFailure("RESTORE_BEST_FAILURE", f"{name} restored file is not the best checkpoint")
    best_score = None
    previous = None
    for row in rows:
        score = float(row["classify_macro_f1_nonnone"])
        if row["improved"]:
            if best_score is not None and score <= best_score:
                raise LaunchFailure("EARLY_STOPPING_VIOLATION", f"{name} non-strict improvement")
            best_score = score
        elif row["tie"]:
            if best_score is None or score != best_score:
                raise LaunchFailure("EARLY_STOPPING_VIOLATION", f"{name} tie")
            if previous and row["checkpoint_sha256"] != previous["checkpoint_sha256"]:
                raise LaunchFailure("EARLY_STOPPING_VIOLATION", f"{name} tie replaced the checkpoint")
        previous = row
    if name == "control":
        if len(rows) != 40 or receipt.get("stop_reason") != "max_epochs":
            raise LaunchFailure("SCHEDULE_VIOLATION", "control did not complete 40 epochs")
        if any(row["early_stop"] for row in rows):
            raise LaunchFailure("SCHEDULE_VIOLATION", "control early-stopped")
    else:
        if len(rows) < 4 or len(rows) > 12:
            raise LaunchFailure("SCHEDULE_VIOLATION", "candidate epoch count")
        if any(row["early_stop"] and int(row["epoch"]) < 3 for row in rows):
            raise LaunchFailure("EARLY_STOPPING_VIOLATION", "candidate stopped before 4 scored epochs")
        if receipt.get("stop_reason") == "early_stopping":
            if rows[-1]["epochs_since_best"] is None or int(rows[-1]["epochs_since_best"]) < 4:
                raise LaunchFailure("EARLY_STOPPING_VIOLATION", "candidate patience")
        elif receipt.get("stop_reason") != "max_epochs" or len(rows) != 12:
            raise LaunchFailure("SCHEDULE_VIOLATION", "candidate stop reason")
    return {
        "best_checkpoint_sha256": best,
        "best_epoch": receipt.get("best_epoch"),
        "epochs_completed": len(rows),
        "optimizer_steps": int(receipt["global_steps"]),
        "primary_weights_sha256": primary,
        "stop_reason": receipt.get("stop_reason"),
        "wall_seconds": float(receipt["training_elapsed_seconds"]),
    }


def assert_experiment_valid(control: Mapping[str, Any], candidate: Mapping[str, Any]) -> None:
    """Same surface except the sealed schedule. A miss is not an ordinary FAIL."""
    keys = (
        "data_sha256",
        "init_from",
        "last_trainable",
        "n_train_classify",
        "n_train_unbind",
        "training_export_rows",
        "training_export_sha256_actual",
        "unbind_curriculum",
        "unbind_every_n",
        "unbind_loss_weight",
        "unbind_primary",
        "warm_start",
    )
    for key in keys:
        if control.get(key) != candidate.get(key):
            raise LaunchFailure("EXPERIMENT_INVALID", key)
    if control.get("init_expand_vocab_applied") is not True or candidate.get("init_expand_vocab_applied") is not True:
        raise LaunchFailure("EXPERIMENT_INVALID", "zero-init expansion")
    for arm, receipt in (("control", control), ("candidate", candidate)):
        role = receipt.get("init_expand_role") or {}
        filler = receipt.get("init_expand_filler") or {}
        if role.get("new_row_policy") != "exact_zero" or filler.get("new_row_policy") != "exact_zero":
            raise LaunchFailure("EXPERIMENT_INVALID", f"{arm} zero-init policy")
        disjoint = receipt.get("eval_reserve_disjoint") or {}
        if disjoint.get("reserve_train_row_id_overlap") != 0 or disjoint.get("reserve_train_text_hash_overlap") != 0:
            raise LaunchFailure("EXPERIMENT_INVALID", f"{arm} reserve leakage")
        if receipt.get("training_export_sha256_actual") != receipt.get("training_export_sha256_expected"):
            raise LaunchFailure("EXPERIMENT_INVALID", f"{arm} export hash")
    if int(control.get("epochs") or 0) != 40 or int(candidate.get("epochs") or 0) != 12:
        raise LaunchFailure("EXPERIMENT_INVALID", "configured schedule")
    if control.get("last_trainable") != 2 or control.get("unbind_primary") != "mixed":
        raise LaunchFailure("EXPERIMENT_INVALID", "shared hyperparameters")
    if control.get("unbind_loss_weight") != 1.0 or control.get("unbind_every_n") != 1:
        raise LaunchFailure("EXPERIMENT_INVALID", "unbind settings")
    if control.get("unbind_curriculum") not in (False, 0):
        raise LaunchFailure("EXPERIMENT_INVALID", "unbind curriculum")
