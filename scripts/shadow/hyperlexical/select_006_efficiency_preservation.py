"""SELECT-006 efficiency-preservation specification.

This module seals governance. It does not train, construct an optimizer,
create a checkpoint, score a reserve, or move BEST.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

EXPERIMENT_ID = "HLX-EXP-2026-09-29-SELECT-006"
SELECT_005_ID = "HLX-EXP-2026-09-27-SELECT-005"
TRANSITION = "SELECT_006_EFFICIENCY_PRESERVATION_SPEC"
NEXT_TRANSITION = "SELECT_006_RESERVE_ACQUISITION"
HYPOTHESIS = (
    "A reduced training schedule can preserve primary evaluation quality "
    "and all preservation metrics while using substantially fewer optimizer "
    "steps than the control schedule."
)
WARM_START_SHA256 = "96838b9656a84c3fee1773a41fdf2fbbec2f88f3bc948e4acfbe06c194ac5587"
BEST_SHA256 = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
TRUNK_SHA256 = "340ac08b74eef0d7bdec2d7981a6a3d4249bf0e6aab60634b72ad02c2b8023a9"
EXPORT_SHA256 = "64b7d3dede25047cb6dd2e5b663f7fa72946ec82ac1a8816ae34622d1aaac430"
EXPORT_ROWS = 9150
EXPORT_PATH = "/home/morpheus/hlx-private/d1-spark-tree-20260924T213846Z/morph78-train-export.jsonl"
WARM_START_DIR = "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph65"
BEST_WEIGHTS = "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/model.safetensors"
TRUNK_DIR = "/home/morpheus/.hyperlex/models/trunks/ModernBERT-base"
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
IMAGE_SHA256 = "616a3e97f45191af975896cfa644279096cb31bd408a071c2e99ca7209c3cafe"
LEDGER_EVENTS_SHA256 = "4ec441f545e37cd9e691ab322fa438269c79b6a6ed82f56b58ce740e94665763"
LEDGER_PROJECTION_SHA256 = "83d7dde24f723e750b487819aa1a5b6c7d847ca55fa5b1bf2dcd8b8157cc50d2"
SELECT_005_SETTLEMENT_SHA256 = "70f5ccddf41f357c75191d519427c2c1d5baac8f6a7b39575a325e8522d7ea27"
SELECT_005_METRIC_TABLE_SHA256 = "ba9e57a538c5e834321ace3cb6b7aa134e9c3c406cd05823853ebf540043fd39"
INVALID_LOADER_DIR = (
    "/home/morpheus/hlx-private/exp-20260927-select-005/launch-001/invalid-loader-001"
)
LEDGER_DIR = "/home/morpheus/hlx-private/eval-reserve-20260926"
WARM_START_WEIGHTS = WARM_START_DIR + "/model.safetensors"
CONTROL_CONFIG = (
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select005-control/config.json"
)
CANDIDATE_CONFIG = (
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select005/config.json"
)
SPEC_DIR = "/home/morpheus/hlx-private/exp-20260929-select-006/spec-001"
EPSILON = 0
EFFICIENCY_MAX_STEP_RATIO = 0.25
NEW_ROLES = ("pos_6", "pos_7", "unknown")
QUESTION = "non-inferiority plus compute efficiency"
SCHEMA_DIR = Path(__file__).resolve().parents[3] / "specs/007-hyperlexical-model/schemas/hyperlex/select"
WARM_START_PIN_MISMATCH = "WARM_START_PIN_MISMATCH"
VOCAB_EXPANSION_SPEC_INCOMPLETE = "VOCAB_EXPANSION_SPEC_INCOMPLETE"
EVALUATION_RESERVE_STATE_UNRESOLVED = "EVALUATION_RESERVE_STATE_UNRESOLVED"
THRESHOLD_UNDERSPECIFIED = "THRESHOLD_UNDERSPECIFIED"
EPSILON_UNJUSTIFIED = "EPSILON_UNJUSTIFIED"
SCHEDULE_UNDERSPECIFIED = "SCHEDULE_UNDERSPECIFIED"
ARTIFACT_MANIFEST_FAILURE = "ARTIFACT_MANIFEST_FAILURE"
SPEC_SEAL_FAILURE = "SPEC_SEAL_FAILURE"


class SpecSealError(SystemExit):
    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise SpecSealError(code, detail)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def _forbidden_training() -> dict[str, Any]:
    return {
        "best_changed": False,
        "epochs": 0,
        "gradient_steps": 0,
        "optimizer_constructed": False,
        "training_launch_authorized": False,
        "training_started": False,
        "weights_mutated": False,
    }


def vocabulary_expansion_pin() -> dict[str, Any]:
    """Explicit loader contract. New rows are zeros, not an unset torch draw."""
    return {
        "filler_expansion": {
            "mapped_existing_fillers": 1750,
            "newly_initialized_fillers": 29,
            "skipped_warm_start_only": 230,
            "target_filler_count": 1779,
            "warm_start_filler_count": 1980,
        },
        "counts_include_unk_token": True,
        "current_loader_behavior": (
            "warm_load_checkpoint with expand_vocab copies mapped rows by name "
            "and leaves new rows at nn.Linear initialization. That draw is not "
            "the sealed zero policy."
        ),
        "execution_loader_status": "NOT_YET_IMPLEMENTED",
        "init_expand_vocab": True,
        "initialization_policy": {
            "mapped_rows": "copy warm-start weight and bias by label name",
            "new_rows": "zeros",
            "seed_used": False,
        },
        "launch_blocked_until_loader_honors_zeros": True,
        "mapped_existing_roles": 10,
        "newly_initialized_roles": 3,
        "new_role_names_in_sorted_order": list(NEW_ROLES),
        "ordering_policy": "unk_then_sorted_labels",
        "unk_token": "<unk>",
        "unk_token_is_not_a_new_role": True,
        "schema": "hyperlex.select_006_vocabulary_expansion.v1",
        "target_role_count": 13,
        "warm_start_role_count": 10,
        "warm_start_sha256": WARM_START_SHA256,
    }


def _schedules() -> tuple[dict[str, Any], dict[str, Any]]:
    control = {
        "early_stopping": "disabled",
        "max_epochs": 40,
        "restore_best": True,
    }
    candidate = {
        "early_stopping_patience": 4,
        "improvement": "strict",
        "max_epochs": 12,
        "minimum_epochs": 4,
        "restore_best": True,
        "ties": "keep_earlier",
    }
    return control, candidate


def _shared_settings() -> dict[str, Any]:
    return {
        "batch_size": 8,
        "environment_hash_omits": [
            "HLX_SEED",
            "HYPERLEX_EARLY_STOP",
            "HYPERLEX_EARLY_STOP_MIN_EPOCHS",
            "HYPERLEX_EARLY_STOP_PATIENCE",
            "HYPERLEX_FILLER_FILTER",
            "HYPERLEX_INIT_EXPAND_VOCAB",
            "HYPERLEX_INIT_FROM",
            "HYPERLEX_LAST_TRAINABLE",
            "HYPERLEX_TRAIN_BATCH",
            "HYPERLEX_TRAIN_EPOCHS",
            "HYPERLEX_TRAIN_LR",
            "HYPERLEX_UNBIND_CURRICULUM",
            "HYPERLEX_UNBIND_EVERY_N",
            "HYPERLEX_UNBIND_LOSS_WEIGHT",
            "HYPERLEX_UNBIND_PRIMARY",
        ],
        "filler_filter": "strict",
        "gradient_accumulation": 1,
        "gradient_accumulation_authority": (
            "The trainer takes one optimizer step per batch and has no "
            "accumulation parameter. 1 freezes that behavior."
        ),
        "image": IMAGE,
        "image_sha256": IMAGE_SHA256,
        "last_trainable": 2,
        "learning_rate": "2e-5",
        "max_len": 64,
        "must_remain_unset": ["HLX_SEED", "HYPERLEX_INCLUDE_LIVE"],
        "not_in_sealed_env": ["HYPERLEX_TRAIN_OUT"],
        "output_directories_not_reused": [
            "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select005",
            "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select005-control",
        ],
        "seed_policy": "HLX_SEED_UNSET_FROZEN",
        "selection_metric": "classify_macro_f1_nonnone",
        "training_export_path": EXPORT_PATH,
        "training_export_rows": EXPORT_ROWS,
        "training_export_sha256": EXPORT_SHA256,
        "trunk_dir": TRUNK_DIR,
        "trunk_sha256": TRUNK_SHA256,
        "unbind_curriculum": False,
        "unbind_every_n": 1,
        "unbind_loss_weight": 1.0,
        "unbind_primary": "mixed",
    }


def invalid_loader_exclusion() -> dict[str, Any]:
    return {
        "allowed_use": "debugging provenance",
        "forbidden_uses": [
            "aggregate reporting",
            "baseline comparison",
            "BEST selection",
            "SELECT-006 initialization",
            "threshold calculation",
        ],
        "path": INVALID_LOADER_DIR,
        "status": "PERMANENTLY_NON_RESULT",
    }


def evaluation_reserve_decision() -> dict[str, Any]:
    """SELECT-005's 78 rows stay bound to SELECT-005 and must not be scored again."""
    return {
        "decision": "REUSE_FORBIDDEN",
        "ledger_events_sha256": LEDGER_EVENTS_SHA256,
        "ledger_projection_sha256": LEDGER_PROJECTION_SHA256,
        "reason": (
            "The 78 identities are still EVAL_RESERVE and are bound only to "
            "HLX-EXP-2026-09-27-SELECT-005. A reserve bound to another experiment "
            "does not satisfy SELECT-006. The sealed reserve policy also forbids "
            "repeated scoring. evaluation_spent was not flipped; the completed "
            "SELECT-005 score is the scientific spend. SELECT-006 has no reserve."
        ),
        "repeated_scoring_allowed": False,
        "satisfies_select_006": False,
        "select_005_active_count": 78,
        "select_005_binding": [SELECT_005_ID],
        "select_005_ledger_lifecycle": "EVAL_RESERVE",
        "select_005_slice_counts": {
            "classify": 51,
            "classify_non_none": 11,
            "classify_observed": 11,
            "unbind_clean": 27,
        },
        "select_006_reserve": None,
    }


def preregistration() -> dict[str, Any]:
    control, candidate = _schedules()
    return {
        "candidate_schedule": candidate,
        "control_schedule": control,
        "efficiency_gate": {
            "candidate_optimizer_steps_le_ratio_of_control": EFFICIENCY_MAX_STEP_RATIO,
            "comparison": "candidate_optimizer_steps * 4 <= control_optimizer_steps",
            "descriptive_only": ["epochs_ratio", "step_ratio", "step_reduction_percent", "wall_clock_ratio"],
            "wall_clock_is_a_gate": False,
        },
        "epsilon": EPSILON,
        "epsilon_justification": (
            "SELECT-006 has no frozen reserve. The only scored surface is the "
            "SELECT-005 reserve, which this experiment must not reuse. That surface "
            "has 51 classify rows and 4 head-mapped non-none golds, and both arms "
            "landed on exactly 1/3. A nonzero band would be finer than that surface "
            "can support. EPSILON is 0: exact non-inferiority. A later reserve must "
            "not widen it."
        ),
        "evaluation_reserve": evaluation_reserve_decision(),
        "experiment_id": EXPERIMENT_ID,
        "hypothesis": HYPOTHESIS,
        "question": QUESTION,
        "inherited_from_select_005_settlement": False,
        "invalid_loader_exclusion": invalid_loader_exclusion(),
        "schema": "hyperlex.select_006_preregistration.v1",
        "scientific_variable": "train_schedule",
        "sealed": True,
        "select_005_citation": {
            "metric_table_sha256": SELECT_005_METRIC_TABLE_SHA256,
            "role": "prior empirical motivation only",
            "settlement": "REJECT",
            "settlement_sha256": SELECT_005_SETTLEMENT_SHA256,
            "threshold": "FAIL",
            "use_as_authorization": False,
        },
        "shared_settings": _shared_settings(),
        "state": "PREREGISTERED",
        "telemetry": {
            "incomplete": "EXPERIMENT_INVALID",
            "per_epoch": [
                "checkpoint identity",
                "classification_accuracy",
                "classify_macro_f1_nonnone",
                "epoch",
                "global_step",
                "learning_rate",
                "observed_label_accuracy",
                "training_loss",
                "unbind_clean_exact",
            ],
            "required_reconstructions": [
                "best checkpoint",
                "best epoch",
                "final optimizer steps",
                "patience trace",
                "restore-best proof",
                "stop reason",
            ],
            "unbind_clean_exact_on_train_val": (
                "null is required when the val split has no unbind_clean flag; "
                "do not infer it. The reserve score is the gate value and must be computable."
            ),
        },
        "training_launch_authorized": False,
        "training_started": False,
        "vocabulary_expansion": vocabulary_expansion_pin(),
        "warm_start_sha256": WARM_START_SHA256,
    }


def threshold_authorization(preregistration_sha256: str) -> dict[str, Any]:
    return {
        "authorization_state": "SEALED",
        "decision_rule": {
            "compensation": False,
            "efficiency": "candidate_optimizer_steps * 4 <= control_optimizer_steps",
            "missing_required_metric": "FAIL",
            "noncomputable_required_metric": "FAIL",
            "primary_equality": "PASS",
            "primary_strict_increase_required": False,
            "select_005_rule_not_reused": "primary delta > 0",
            "pass_requires": [
                "classification_accuracy",
                "efficiency",
                "observed_label_accuracy",
                "primary_preservation",
                "unbind_clean_exact",
            ],
            "preservation": "candidate >= control on each preservation metric",
            "primary_preservation": "candidate_classify_macro_f1_nonnone >= control_classify_macro_f1_nonnone - EPSILON",
        },
        "efficiency_max_step_ratio": EFFICIENCY_MAX_STEP_RATIO,
        "epsilon": EPSILON,
        "experiment_id": EXPERIMENT_ID,
        "inherited_from_select_005_settlement": False,
        "preregistration_sha256": preregistration_sha256,
        "schema": "hyperlex.select_006_threshold_authorization.v1",
        "sealed": True,
        "training_launch_authorized": False,
    }


def dependency_statement() -> dict[str, Any]:
    return {
        "best_not_moved": True,
        "best_sha256": BEST_SHA256,
        "best_weights": BEST_WEIGHTS,
        "evaluation_reserve": evaluation_reserve_decision(),
        "experiment_id": EXPERIMENT_ID,
        "image_sha256": IMAGE_SHA256,
        "invalid_loader_exclusion": invalid_loader_exclusion(),
        "schema": "hyperlex.select_006_dependency_statement.v1",
        "training_export_path": EXPORT_PATH,
        "training_export_rows": EXPORT_ROWS,
        "training_export_sha256": EXPORT_SHA256,
        "trunk_dir": TRUNK_DIR,
        "trunk_sha256": TRUNK_SHA256,
        "warm_start_dir": WARM_START_DIR,
        "warm_start_sha256": WARM_START_SHA256,
        **_forbidden_training(),
    }


def schema_errors(payload: Mapping[str, Any], schema_name: str) -> list[str]:
    import jsonschema

    schema = json.loads((SCHEMA_DIR / schema_name).read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    return [error.message for error in validator.iter_errors(payload)]


def apply_decision(
    *,
    control: Mapping[str, float],
    candidate: Mapping[str, float],
    control_steps: int,
    candidate_steps: int,
) -> dict[str, Any]:
    """Apply the sealed rule to caller-supplied numbers. This does not score."""
    gates = []
    primary = "classify_macro_f1_nonnone"
    for name in (
        primary,
        "classification_accuracy",
        "observed_label_accuracy",
        "unbind_clean_exact",
    ):
        if name not in control or name not in candidate:
            gates.append({"metric": name, "pass": False, "reason": "MISSING"})
            continue
        left = control[name]
        right = candidate[name]
        if isinstance(left, bool) or isinstance(right, bool):
            gates.append({"metric": name, "pass": False, "reason": "NON_COMPUTABLE"})
            continue
        try:
            delta = float(right) - float(left)
        except (TypeError, ValueError):
            gates.append({"metric": name, "pass": False, "reason": "NON_COMPUTABLE"})
            continue
        limit = -EPSILON if name == primary else 0.0
        ok = delta >= limit
        gates.append(
            {
                "delta": delta,
                "metric": name,
                "pass": ok,
                "reason": "PASS" if ok else "PRESERVATION_DEGRADED",
            }
        )
    if (
        isinstance(control_steps, bool)
        or isinstance(candidate_steps, bool)
        or not isinstance(control_steps, int)
        or not isinstance(candidate_steps, int)
        or control_steps <= 0
        or candidate_steps < 0
    ):
        efficiency = {"metric": "optimizer_steps", "pass": False, "reason": "NON_COMPUTABLE"}
    else:
        ratio = candidate_steps / control_steps
        ok = candidate_steps * 4 <= control_steps
        efficiency = {
            "metric": "optimizer_steps",
            "pass": ok,
            "reason": "PASS" if ok else "EFFICIENCY_FAIL",
            "step_ratio": ratio,
            "step_reduction_percent": (1.0 - ratio) * 100.0,
        }
    gates.append(efficiency)
    passed = all(gate["pass"] for gate in gates)
    return {"compensation": False, "epsilon": EPSILON, "gates": gates, "outcome": "PASS" if passed else "FAIL", "pass": passed}


def _common_env() -> dict[str, str]:
    return {
        "HLX_EXPERIMENT_ID": EXPERIMENT_ID,
        "HLX_SCIENTIFIC_VARIABLE": "train_schedule",
        "HLX_SELECT_METRIC": "classify_macro_f1_nonnone",
        "HLX_TRAIN_EXPORT_PATH": EXPORT_PATH,
        "HLX_TRAIN_EXPORT_ROWS": str(EXPORT_ROWS),
        "HLX_TRAIN_EXPORT_SHA256": EXPORT_SHA256,
        "HYPERLEX_FILLER_FILTER": "strict",
        "HYPERLEX_INIT_EXPAND_VOCAB": "1",
        "HYPERLEX_INIT_FROM": WARM_START_DIR,
        "HYPERLEX_LAST_TRAINABLE": "2",
        "HYPERLEX_TRAIN_BATCH": "8",
        "HYPERLEX_TRAIN_LR": "2e-5",
        "HYPERLEX_TRUNK_DIR": TRUNK_DIR,
        "HYPERLEX_UNBIND_CURRICULUM": "0",
        "HYPERLEX_UNBIND_EVERY_N": "1",
        "HYPERLEX_UNBIND_LOSS_WEIGHT": "1.0",
        "HYPERLEX_UNBIND_PRIMARY": "mixed",
    }


def baseline_env() -> dict[str, str]:
    env = _common_env()
    env["HYPERLEX_EARLY_STOP"] = "0"
    env["HYPERLEX_TRAIN_EPOCHS"] = "40"
    return env


def candidate_env() -> dict[str, str]:
    env = _common_env()
    env["HYPERLEX_EARLY_STOP"] = "1"
    env["HYPERLEX_EARLY_STOP_MIN_EPOCHS"] = "4"
    env["HYPERLEX_EARLY_STOP_PATIENCE"] = "4"
    env["HYPERLEX_TRAIN_EPOCHS"] = "12"
    return env


def _expected_observations() -> dict[str, Any]:
    pin = vocabulary_expansion_pin()
    reserve = evaluation_reserve_decision()
    return {
        "best_sha256": BEST_SHA256,
        "candidate_config": CANDIDATE_CONFIG,
        "configs_agree": True,
        "control_config": CONTROL_CONFIG,
        "export_sha256": EXPORT_SHA256,
        "filler_expansion": pin["filler_expansion"],
        "ledger_events_sha256": LEDGER_EVENTS_SHA256,
        "ledger_projection_sha256": LEDGER_PROJECTION_SHA256,
        "mapped_existing_roles": 10,
        "new_role_names_in_sorted_order": list(NEW_ROLES),
        "newly_initialized_roles": 3,
        "role_order_ok": True,
        "select_005_active_count": 78,
        "select_005_slice_counts": reserve["select_005_slice_counts"],
        "select_006_active_count": 0,
        "target_role_count": 13,
        "trunk_sha256": TRUNK_SHA256,
        "warm_start_only_roles": 0,
        "warm_start_role_count": 10,
        "warm_start_sha256": WARM_START_SHA256,
    }


def _check_observations(observations: Mapping[str, Any]) -> None:
    expected = _expected_observations()
    if observations.get("warm_start_sha256") != WARM_START_SHA256:
        _fail(WARM_START_PIN_MISMATCH, "warm-start weights")
    if observations.get("best_sha256") != BEST_SHA256:
        _fail(SPEC_SEAL_FAILURE, "BEST pin")
    if observations.get("export_sha256") != EXPORT_SHA256 or observations.get("trunk_sha256") != TRUNK_SHA256:
        _fail(SPEC_SEAL_FAILURE, "export or trunk pin")
    vocab_keys = (
        "configs_agree",
        "filler_expansion",
        "mapped_existing_roles",
        "new_role_names_in_sorted_order",
        "newly_initialized_roles",
        "role_order_ok",
        "target_role_count",
        "warm_start_only_roles",
        "warm_start_role_count",
    )
    if any(observations.get(key) != expected[key] for key in vocab_keys):
        _fail(VOCAB_EXPANSION_SPEC_INCOMPLETE, "live role or filler expansion")
    reserve_keys = (
        "ledger_events_sha256",
        "ledger_projection_sha256",
        "select_005_active_count",
        "select_005_slice_counts",
        "select_006_active_count",
    )
    if any(observations.get(key) != expected[key] for key in reserve_keys):
        _fail(EVALUATION_RESERVE_STATE_UNRESOLVED, "ledger lifecycle")


def _check_documents(pre: Mapping[str, Any], threshold: Mapping[str, Any]) -> None:
    if pre.get("epsilon") != 0 or "exact non-inferiority" not in str(pre.get("epsilon_justification") or ""):
        _fail(EPSILON_UNJUSTIFIED, "EPSILON")
    if pre.get("evaluation_reserve", {}).get("decision") != "REUSE_FORBIDDEN":
        _fail(EVALUATION_RESERVE_STATE_UNRESOLVED, "reserve decision")
    if pre.get("evaluation_reserve", {}).get("select_006_reserve") is not None:
        _fail(EVALUATION_RESERVE_STATE_UNRESOLVED, "SELECT-006 has no reserve")
    control, candidate = _schedules()
    if pre.get("control_schedule") != control or pre.get("candidate_schedule") != candidate:
        _fail(SCHEDULE_UNDERSPECIFIED, "schedule")
    if baseline_env().get("HYPERLEX_EARLY_STOP_PATIENCE") or baseline_env().get("HYPERLEX_EARLY_STOP_MIN_EPOCHS"):
        _fail(SCHEDULE_UNDERSPECIFIED, "control early-stop keys must stay absent")
    vocab = pre.get("vocabulary_expansion") or {}
    if (
        vocab.get("execution_loader_status") != "NOT_YET_IMPLEMENTED"
        or vocab.get("new_role_names_in_sorted_order") != list(NEW_ROLES)
        or vocab.get("initialization_policy", {}).get("new_rows") != "zeros"
        or vocab.get("init_expand_vocab") is not True
    ):
        _fail(VOCAB_EXPANSION_SPEC_INCOMPLETE, "vocabulary pin")
    rule = threshold.get("decision_rule") or {}
    required = {
        "classification_accuracy",
        "efficiency",
        "observed_label_accuracy",
        "primary_preservation",
        "unbind_clean_exact",
    }
    if set(rule.get("pass_requires") or []) != required or rule.get("compensation") is not False:
        _fail(THRESHOLD_UNDERSPECIFIED, "decision rule")
    if threshold.get("epsilon") != 0 or threshold.get("efficiency_max_step_ratio") != 0.25:
        _fail(THRESHOLD_UNDERSPECIFIED, "epsilon or efficiency ratio")
    if rule.get("primary_strict_increase_required") is not False or rule.get("primary_equality") != "PASS":
        _fail(THRESHOLD_UNDERSPECIFIED, "primary equality")
    pre_errors = schema_errors(pre, "select-006-preregistration.schema.json")
    threshold_errors = schema_errors(threshold, "select-006-threshold-authorization.schema.json")
    if pre_errors or threshold_errors:
        _fail(SPEC_SEAL_FAILURE, "; ".join([*pre_errors, *threshold_errors]))


def build_sealed_documents(observations: Mapping[str, Any], repository_head: str) -> dict[str, dict[str, Any]]:
    _check_observations(observations)
    if not isinstance(repository_head, str) or len(repository_head) != 40:
        _fail(SPEC_SEAL_FAILURE, "repository head")
    pre = preregistration()
    pre_sha = sha256_text(canonical_json(pre))
    threshold = threshold_authorization(pre_sha)
    _check_documents(pre, threshold)
    vocab = vocabulary_expansion_pin()
    dependencies = dependency_statement()
    baseline = baseline_env()
    candidate = candidate_env()
    bodies = {
        "SELECT_006_PREREGISTRATION.json": pre,
        "SELECT_006_THRESHOLD_AUTHORIZATION.json": threshold,
        "VOCABULARY_EXPANSION_PIN.json": vocab,
        "DATA_EVALUATION_DEPENDENCIES.json": dependencies,
        "BASELINE_ENV.json": baseline,
        "CANDIDATE_ENV.json": candidate,
    }
    hashes = {name: sha256_text(canonical_json(body)) for name, body in bodies.items()}
    manifest = {
        "artifacts": [
            {"name": name, "sha256": digest} for name, digest in sorted(hashes.items())
        ],
        "experiment_id": EXPERIMENT_ID,
        "schema": "hyperlex.select_006_artifact_manifest.v1",
        **_forbidden_training(),
    }
    manifest_text = canonical_json(manifest)
    hashes["ARTIFACT_MANIFEST.json"] = sha256_text(manifest_text)
    receipt = {
        "artifact_sha256": hashes,
        "experiment_id": EXPERIMENT_ID,
        "next_legal_transition": NEXT_TRANSITION,
        "observations": {
            "best_sha256": observations["best_sha256"],
            "candidate_config": observations.get("candidate_config", CANDIDATE_CONFIG),
            "configs_agree": True,
            "control_config": observations.get("control_config", CONTROL_CONFIG),
            "export_sha256": observations["export_sha256"],
            "ledger_events_sha256": observations["ledger_events_sha256"],
            "ledger_projection_sha256": observations["ledger_projection_sha256"],
            "new_role_names_in_sorted_order": list(NEW_ROLES),
            "select_005_active_count": 78,
            "select_006_active_count": 0,
            "trunk_sha256": observations["trunk_sha256"],
            "warm_start_sha256": observations["warm_start_sha256"],
        },
        "repository_commit": repository_head,
        "schema": "hyperlex.select_006_spec_receipt.v1",
        "state": "SELECT_006_EFFICIENCY_PRESERVATION_SPEC_SEALED",
        "transition": TRANSITION,
        **_forbidden_training(),
    }
    bodies["ARTIFACT_MANIFEST.json"] = manifest
    bodies["SPEC_RECEIPT.json"] = receipt
    return bodies


def seal_specification(
    directory: str | Path,
    *,
    observations: Mapping[str, Any],
    repository_head: str,
    repository_dirty: bool = False,
) -> dict[str, str]:
    """Write the spec directory. Does not train, score, or move BEST."""
    if repository_dirty:
        _fail(SPEC_SEAL_FAILURE, "repository is dirty")
    target = Path(directory)
    if target.exists():
        _fail(SPEC_SEAL_FAILURE, f"spec directory already exists: {target}")
    bodies = build_sealed_documents(observations, repository_head)
    parent = target.parent
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(parent, 0o700)
    temporary = parent / f".{target.name}.tmp"
    if temporary.exists():
        _fail(SPEC_SEAL_FAILURE, f"temporary spec directory already exists: {temporary}")
    temporary.mkdir(mode=0o700)
    try:
        for name, body in bodies.items():
            path = temporary / name
            path.write_text(canonical_json(body), encoding="utf-8")
            os.chmod(path, 0o600)
        manifest = json.loads((temporary / "ARTIFACT_MANIFEST.json").read_text(encoding="utf-8"))
        for item in manifest["artifacts"]:
            observed = sha256_file(temporary / item["name"])
            if observed != item["sha256"]:
                _fail(ARTIFACT_MANIFEST_FAILURE, item["name"])
        receipt_path = temporary / "SPEC_RECEIPT.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        for name, digest in receipt["artifact_sha256"].items():
            if sha256_file(temporary / name) != digest:
                _fail(ARTIFACT_MANIFEST_FAILURE, name)
        os.rename(temporary, target)
    except BaseException:
        if temporary.exists():
            for child in temporary.iterdir():
                child.unlink()
            temporary.rmdir()
        raise
    os.chmod(target, 0o700)
    return {name: sha256_file(target / name) for name in bodies}
