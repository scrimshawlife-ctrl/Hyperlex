"""SELECT-006 operator authorization of a future training launch.

This module records ``operator_decision = AUTHORIZE``. It does not infer that
decision from ``TRAINING_READY``. Sealing the record performs zero training.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from .select_006_admission import (
    COMBINED_WITNESS_SHA256,
    FILLER_BIAS_SHA256,
    FILLER_WEIGHT_SHA256,
    HISTORICAL_PIN_STATUS,
    LEDGER_EVENTS_SHA256,
    LEDGER_PROJECTION_SHA256,
    PREREGISTRATION_SHA256,
    RESERVE_MANIFEST_SHA256,
    ROLE_BIAS_SHA256,
    ROLE_WEIGHT_SHA256,
    THRESHOLD_SHA256,
    VERIFIED,
    WITNESS,
    Select006AdmissionError,
    select006_admission_evidence,
)
from .select_006_efficiency_preservation import (
    BEST_SHA256,
    EFFICIENCY_MAX_STEP_RATIO,
    EPSILON,
    EXPERIMENT_ID,
    WARM_START_SHA256,
    _schedules,
    _shared_settings,
    canonical_json,
    sha256_file,
    threshold_authorization,
    vocabulary_expansion_pin,
)
from .select_contract_schema import select_006_training_launch_authorization_schema_errors

TRANSITION = "SELECT_006_TRAINING_LAUNCH_AUTHORIZATION"
LAUNCH_TRANSITION = "SELECT_006_TRAINING_LAUNCH"
STATE = "TRAINING_LAUNCH_AUTHORIZED"
SCHEMA = "hyperlex.select_006_training_launch_authorization.v1"

ADMISSION_RECEIPT_SHA256 = "7ff98e8bc9a49a8875e8c7310f18ae9c5bb53ca4ad40e9b954ca89d52a7551bd"
BASELINE_ENV_SHA256 = "ca26a7cb12fcd0ce96e0f198fbcd30a1fd3e61fe0164e14dad823a2d17516a9d"
CANDIDATE_ENV_SHA256 = "f67c45774b173d7c894177252f16e3abe39cbdbb6f20f83c4db53b8485bd3ea6"
CONFIG_SHA256 = "fec14e56789f1c761b5f2e6ab0ef1958a3518b3fc4b1d44d15bd1afeb8f1865b"
ADMISSION_OVERLAY_ENVIRONMENT_SHA256 = (
    "f51a809664f444050a4ddd7b0f0b1bf2c564865f0988ed801ed1d654d83fda57"
)
VOCABULARY_PIN_SHA256 = "8e1cce3de9ca6dfd346e926cfa3c8bffd5a9d05dfdc671b7da26e01aa539f076"
WITNESS_FILE_SHA256 = "79509a3f1a3fb10bfe2faac66fb6f190b928de98fadadca2923b7b88b8d2fb07"
ACTIVE_EVAL_RESERVE = 37
SLICE_COUNTS = {
    "classify": 32,
    "classify_non_none": 32,
    "classify_observed": 32,
    "head_mapped_non_none": 32,
    "unbind_clean": 5,
}

PREFLIGHT_FAILURE = "LAUNCH_AUTHORIZATION_PREFLIGHT_FAILURE"
PIN_MISMATCH = "LAUNCH_AUTHORIZATION_PIN_MISMATCH"
RESERVE_FAILURE = "LAUNCH_AUTHORIZATION_RESERVE_FAILURE"
LOADER_FAILURE = "LAUNCH_AUTHORIZATION_LOADER_FAILURE"
SCHEMA_FAILURE = "LAUNCH_AUTHORIZATION_SCHEMA_FAILURE"
SEAL_FAILURE = "LAUNCH_AUTHORIZATION_SEAL_FAILURE"

_ADMISSION_CODE_MAP = {
    "ADMISSION_PREFLIGHT_FAILURE": PREFLIGHT_FAILURE,
    "ADMISSION_PIN_MISMATCH": PIN_MISMATCH,
    "ADMISSION_RESERVE_FAILURE": RESERVE_FAILURE,
    "ADMISSION_IDENTITY_FAILURE": RESERVE_FAILURE,
    "ADMISSION_LOADER_NOT_VERIFIED": LOADER_FAILURE,
    "ADMISSION_ZERO_INIT_WITNESS_MISMATCH": LOADER_FAILURE,
}

SPEC = Path("/home/morpheus/hlx-private/exp-20260929-select-006/spec-001")
ADMISSION_RECEIPT = Path(
    "/home/morpheus/hlx-private/exp-20260929-select-006/admission-only-001/ADMISSION_RECEIPT.json"
)
RESERVE_DIR = Path("/home/morpheus/hlx-private/exp-20260929-select-006/reserve-acquisition-002")
CONTROL_CONFIG = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select005-control/config.json"
)
CANDIDATE_CONFIG = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select005/config.json"
)
FORBIDDEN_OUTPUTS = (
    Path("/tmp/select006-admission-only-out-41af"),
    Path("/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select006"),
    Path("/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select006-control"),
)


class LaunchAuthorizationError(SystemExit):
    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise LaunchAuthorizationError(code, detail)


def _load(path: Path, code: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail(code, f"{path.name} is unreadable: {exc}")
    if not isinstance(payload, dict):
        _fail(code, f"{path.name} is not an object")
    return payload


def _sha(path: Path, code: str, label: str) -> str:
    try:
        return sha256_file(path)
    except OSError as exc:
        _fail(code, f"{label} is unreadable: {exc}")


def _expected_decision_rule() -> dict[str, Any]:
    return threshold_authorization(PREREGISTRATION_SHA256)["decision_rule"]


def _schedule_body() -> dict[str, Any]:
    control, candidate = _schedules()
    return {"candidate": candidate, "control": control}


def training_launch_authorization() -> dict[str, Any]:
    """The sealed body. Calling it does not train."""
    record = {
        "admission_receipt_sha256": ADMISSION_RECEIPT_SHA256,
        "admission_result": "ADMISSION_PASS",
        "best_changed": False,
        "best_sha256": BEST_SHA256,
        "decision_rule": _expected_decision_rule(),
        "efficiency_max_step_ratio": EFFICIENCY_MAX_STEP_RATIO,
        "environment": {
            "admission_overlay_environment_hash": ADMISSION_OVERLAY_ENVIRONMENT_SHA256,
            "baseline_env_sha256": BASELINE_ENV_SHA256,
            "candidate_config_sha256": CONFIG_SHA256,
            "candidate_env_sha256": CANDIDATE_ENV_SHA256,
            "configs_agree": True,
            "control_config_sha256": CONFIG_SHA256,
        },
        "epochs": 0,
        "epsilon": EPSILON,
        "executes_training": False,
        "experiment_id": EXPERIMENT_ID,
        "gradient_steps": 0,
        "ledger": {
            "authorization_recorded_in_identity_ledger": False,
            "event_type": None,
            "events_sha256": LEDGER_EVENTS_SHA256,
            "projection_sha256": LEDGER_PROJECTION_SHA256,
            "replay": "PASS",
        },
        "next_legal_transition": LAUNCH_TRANSITION,
        "operator_decision": "AUTHORIZE",
        "optimizer_constructed": False,
        "preregistration_sha256": PREREGISTRATION_SHA256,
        "ready_to_train": True,
        "reserve": {
            "active_select_006_eval_reserve": ACTIVE_EVAL_RESERVE,
            "identities_consumed": 0,
            "identities_transitioned": 0,
            "isolation": "PASS",
            "ledger_replay": "PASS",
            "metric_computability": "PASS",
            "provenance": "PASS",
            "routing_validation": "PASS",
            "slice_counts": dict(SLICE_COUNTS),
            "state": "RESERVE_FROZEN",
        },
        "reserve_manifest_sha256": RESERVE_MANIFEST_SHA256,
        "schedule": _schedule_body(),
        "schema": SCHEMA,
        "scientific_variable": "train_schedule",
        "shared_settings": _shared_settings(),
        "state": STATE,
        "status": "TRAINING_READY",
        "threshold_authorization_sha256": THRESHOLD_SHA256,
        "training_launch_authorized": True,
        "training_output_directory_created": False,
        "training_started": False,
        "transition": TRANSITION,
        "warm_start_sha256": WARM_START_SHA256,
        "weights_mutated_by_training": False,
        "zero_init": {
            "combined_witness_sha256": COMBINED_WITNESS_SHA256,
            "execution_loader_status": VERIFIED,
            "filler_bias_sha256": FILLER_BIAS_SHA256,
            "filler_weight_sha256": FILLER_WEIGHT_SHA256,
            "historical_vocabulary_pin_rewritten": False,
            "historical_vocabulary_pin_sha256": VOCABULARY_PIN_SHA256,
            "historical_vocabulary_pin_status": HISTORICAL_PIN_STATUS,
            "role_bias_sha256": ROLE_BIAS_SHA256,
            "role_weight_sha256": ROLE_WEIGHT_SHA256,
            "witness_file_sha256": WITNESS_FILE_SHA256,
        },
    }
    require_authorization_record(record)
    return record


def require_authorization_record(record: Mapping[str, Any]) -> None:
    """Reject a record that would train or drift from the sealed pins."""
    errors = select_006_training_launch_authorization_schema_errors(record)
    if errors:
        _fail(SCHEMA_FAILURE, "; ".join(errors))
    if record.get("operator_decision") != "AUTHORIZE":
        _fail(SCHEMA_FAILURE, "operator_decision")
    if record.get("training_launch_authorized") is not True:
        _fail(SCHEMA_FAILURE, "training_launch_authorized")
    if record.get("ready_to_train") is not True:
        _fail(SCHEMA_FAILURE, "ready_to_train is not operator authorization")
    if record.get("training_started") is not False or record.get("executes_training") is not False:
        _fail(SCHEMA_FAILURE, "authorization must perform zero training")
    if record.get("epochs") != 0 or record.get("gradient_steps") != 0:
        _fail(SCHEMA_FAILURE, "steps")
    if (
        record.get("optimizer_constructed")
        or record.get("weights_mutated_by_training")
        or record.get("best_changed")
        or record.get("training_output_directory_created")
    ):
        _fail(SCHEMA_FAILURE, "weights or output")
    if record.get("epsilon") != 0:
        _fail(SCHEMA_FAILURE, "EPSILON")
    if record.get("state") != STATE or record.get("transition") != TRANSITION:
        _fail(SCHEMA_FAILURE, "state")
    if record.get("next_legal_transition") != LAUNCH_TRANSITION:
        _fail(SCHEMA_FAILURE, "next transition")
    if record.get("schedule") != _schedule_body():
        _fail(SCHEMA_FAILURE, "schedule")
    if record.get("shared_settings") != _shared_settings():
        _fail(SCHEMA_FAILURE, "shared settings")
    if record.get("decision_rule") != _expected_decision_rule():
        _fail(SCHEMA_FAILURE, "decision rule")
    zero_init = record.get("zero_init")
    if not isinstance(zero_init, Mapping) or zero_init.get("execution_loader_status") != VERIFIED:
        _fail(SCHEMA_FAILURE, "execution loader")
    if zero_init.get("historical_vocabulary_pin_status") != HISTORICAL_PIN_STATUS:
        _fail(SCHEMA_FAILURE, "historical vocabulary pin")
    if zero_init.get("historical_vocabulary_pin_rewritten") is not False:
        _fail(SCHEMA_FAILURE, "historical vocabulary pin rewritten")
    ledger = record.get("ledger")
    if not isinstance(ledger, Mapping) or ledger.get("authorization_recorded_in_identity_ledger") is not False:
        _fail(SCHEMA_FAILURE, "ledger authorization event")
    if ledger.get("event_type") is not None:
        _fail(SCHEMA_FAILURE, "ledger event type")


def _check_evidence(evidence: Mapping[str, Any]) -> None:
    preflight = {
        "admission_result": "ADMISSION_PASS",
        "best_changed": False,
        "epochs": 0,
        "experiment_id": EXPERIMENT_ID,
        "gradient_steps": 0,
        "optimizer_constructed": False,
        "output_absent": True,
        "pre_training_launch_authorized": False,
        "pre_training_started": False,
        "ready_to_train": True,
        "status": "TRAINING_READY",
        "weights_mutated_by_training": False,
    }
    for key, expected in preflight.items():
        if evidence.get(key) != expected:
            _fail(PREFLIGHT_FAILURE, key)
    pins = {
        "admission_overlay_environment_hash": ADMISSION_OVERLAY_ENVIRONMENT_SHA256,
        "admission_receipt_sha256": ADMISSION_RECEIPT_SHA256,
        "baseline_env_sha256": BASELINE_ENV_SHA256,
        "best_sha256": BEST_SHA256,
        "candidate_config_sha256": CONFIG_SHA256,
        "candidate_env_sha256": CANDIDATE_ENV_SHA256,
        "control_config_sha256": CONFIG_SHA256,
        "decision_rule": _expected_decision_rule(),
        "epsilon": 0,
        "historical_vocabulary_pin_sha256": VOCABULARY_PIN_SHA256,
        "historical_vocabulary_pin_status": HISTORICAL_PIN_STATUS,
        "preregistration_sha256": PREREGISTRATION_SHA256,
        "reserve_manifest_sha256": RESERVE_MANIFEST_SHA256,
        "schedule": _schedule_body(),
        "shared_settings": _shared_settings(),
        "threshold_authorization_sha256": THRESHOLD_SHA256,
        "warm_start_sha256": WARM_START_SHA256,
    }
    for key, expected in pins.items():
        if evidence.get(key) != expected:
            _fail(PIN_MISMATCH, key)
    if evidence.get("configs_agree") is not True:
        _fail(PIN_MISMATCH, "configs")
    reserve = {
        "active_eval_reserve": ACTIVE_EVAL_RESERVE,
        "isolation": "PASS",
        "ledger_replay": "PASS",
        "metric_computability": "PASS",
        "provenance": "PASS",
        "reserve_state": "RESERVE_FROZEN",
        "routing_validation": "PASS",
        "slice_counts": SLICE_COUNTS,
    }
    for key, expected in reserve.items():
        if evidence.get(key) != expected:
            _fail(RESERVE_FAILURE, key)
    loader = {
        "combined_witness_sha256": COMBINED_WITNESS_SHA256,
        "execution_loader_status": VERIFIED,
        "filler_bias_sha256": FILLER_BIAS_SHA256,
        "filler_weight_sha256": FILLER_WEIGHT_SHA256,
        "role_bias_sha256": ROLE_BIAS_SHA256,
        "role_weight_sha256": ROLE_WEIGHT_SHA256,
        "witness_file_sha256": WITNESS_FILE_SHA256,
    }
    for key, expected in loader.items():
        if evidence.get(key) != expected:
            _fail(LOADER_FAILURE, key)
    if evidence.get("historical_vocabulary_pin_rewritten") is not False:
        _fail(LOADER_FAILURE, "historical vocabulary pin rewritten")
    ledger = evidence.get("ledger")
    expected_ledger = {
        "authorization_recorded_in_identity_ledger": False,
        "event_type": None,
        "events_sha256": LEDGER_EVENTS_SHA256,
        "projection_sha256": LEDGER_PROJECTION_SHA256,
        "replay": "PASS",
    }
    if ledger != expected_ledger:
        _fail(RESERVE_FAILURE, "ledger")


def seal_training_launch_authorization(path: str, evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Write the authorization record after the pins match. Does not train."""
    _check_evidence(evidence)
    record = training_launch_authorization()
    target = Path(path)
    if target.exists():
        _fail(SEAL_FAILURE, f"authorization already exists: {target}")
    temporary = target.with_suffix(target.suffix + ".tmp")
    if temporary.exists():
        _fail(SEAL_FAILURE, f"authorization temporary already exists: {temporary}")
    try:
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(target.parent, 0o700)
        temporary.write_text(canonical_json(record), encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, target)
    except OSError as exc:
        if temporary.exists():
            temporary.unlink()
        _fail(SEAL_FAILURE, str(exc))
    sealed = json.loads(target.read_text(encoding="utf-8"))
    try:
        require_authorization_record(sealed)
    except LaunchAuthorizationError:
        target.unlink()
        raise
    if sealed != record:
        target.unlink()
        _fail(SEAL_FAILURE, "sealed bytes drifted")
    for output in FORBIDDEN_OUTPUTS:
        if output.exists():
            target.unlink()
            _fail(SEAL_FAILURE, f"training output appeared: {output}")
    return sealed


def observe_launch_authorization() -> dict[str, Any]:
    """Read sealed artifacts. Does not train, score, or append the ledger."""
    if vocabulary_expansion_pin()["execution_loader_status"] != HISTORICAL_PIN_STATUS:
        _fail(PIN_MISMATCH, "historical vocabulary pin function")
    for output in FORBIDDEN_OUTPUTS:
        if output.exists():
            _fail(PREFLIGHT_FAILURE, f"training output exists: {output}")
    admission_sha = _sha(ADMISSION_RECEIPT, PREFLIGHT_FAILURE, "admission receipt")
    if admission_sha != ADMISSION_RECEIPT_SHA256:
        _fail(PIN_MISMATCH, "admission receipt")
    receipt = _load(ADMISSION_RECEIPT, PREFLIGHT_FAILURE)
    prereg_sha = _sha(SPEC / "SELECT_006_PREREGISTRATION.json", PIN_MISMATCH, "preregistration")
    if prereg_sha != PREREGISTRATION_SHA256:
        _fail(PIN_MISMATCH, "preregistration")
    prereg = _load(SPEC / "SELECT_006_PREREGISTRATION.json", PIN_MISMATCH)
    threshold_sha = _sha(SPEC / "SELECT_006_THRESHOLD_AUTHORIZATION.json", PIN_MISMATCH, "threshold")
    if threshold_sha != THRESHOLD_SHA256:
        _fail(PIN_MISMATCH, "threshold authorization")
    threshold = _load(SPEC / "SELECT_006_THRESHOLD_AUTHORIZATION.json", PIN_MISMATCH)
    manifest_sha = _sha(RESERVE_DIR / "RESERVE_MANIFEST.json", RESERVE_FAILURE, "reserve manifest")
    if manifest_sha != RESERVE_MANIFEST_SHA256:
        _fail(PIN_MISMATCH, "reserve manifest")
    manifest = _load(RESERVE_DIR / "RESERVE_MANIFEST.json", RESERVE_FAILURE)
    reserve_receipt = _load(RESERVE_DIR / "RESERVE_RECEIPT.json", RESERVE_FAILURE)
    baseline_sha = _sha(SPEC / "BASELINE_ENV.json", PIN_MISMATCH, "baseline env")
    candidate_sha = _sha(SPEC / "CANDIDATE_ENV.json", PIN_MISMATCH, "candidate env")
    control_config_sha = _sha(CONTROL_CONFIG, PIN_MISMATCH, "control config")
    candidate_config_sha = _sha(CANDIDATE_CONFIG, PIN_MISMATCH, "candidate config")
    pin_sha = _sha(SPEC / "VOCABULARY_EXPANSION_PIN.json", PIN_MISMATCH, "vocabulary pin")
    witness_sha = _sha(WITNESS, LOADER_FAILURE, "loader witness")
    try:
        live = select006_admission_evidence()
    except Select006AdmissionError as exc:
        _fail(_ADMISSION_CODE_MAP.get(exc.code, PREFLIGHT_FAILURE), str(exc))
    slices = dict(manifest.get("slice_counts") or {})
    slices["head_mapped_non_none"] = manifest.get("head_mapped_non_none")
    historical = (prereg.get("vocabulary_expansion") or {}).get("execution_loader_status")
    return {
        "active_eval_reserve": live["select_006_active_reserve"],
        "admission_overlay_environment_hash": receipt.get("environment_hash"),
        "admission_receipt_sha256": admission_sha,
        "admission_result": receipt.get("admission_result"),
        "baseline_env_sha256": baseline_sha,
        "best_changed": receipt.get("best_moved"),
        "best_sha256": live["best_sha256"],
        "candidate_config_sha256": candidate_config_sha,
        "candidate_env_sha256": candidate_sha,
        "combined_witness_sha256": live["expanded_loader_witness_sha256"],
        "configs_agree": control_config_sha == candidate_config_sha,
        "control_config_sha256": control_config_sha,
        "decision_rule": threshold.get("decision_rule"),
        "epochs": receipt.get("epochs"),
        "epsilon": receipt.get("epsilon"),
        "execution_loader_status": live["execution_loader_status"],
        "experiment_id": receipt.get("experiment_id"),
        "filler_bias_sha256": live["expanded_filler_bias_sha256"],
        "filler_weight_sha256": live["expanded_filler_weight_sha256"],
        "gradient_steps": receipt.get("gradient_steps"),
        "historical_vocabulary_pin_rewritten": historical != HISTORICAL_PIN_STATUS,
        "historical_vocabulary_pin_sha256": pin_sha,
        "historical_vocabulary_pin_status": historical,
        "isolation": live["isolation"],
        "ledger": {
            "authorization_recorded_in_identity_ledger": False,
            "event_type": None,
            "events_sha256": live["ledger_events_sha256"],
            "projection_sha256": live["ledger_projection_sha256"],
            "replay": live["ledger_replay"],
        },
        "ledger_replay": live["ledger_replay"],
        "metric_computability": live["metric_computability"],
        "optimizer_constructed": receipt.get("optimizer_loaded"),
        "output_absent": True,
        "pre_training_launch_authorized": receipt.get("training_launch_authorized"),
        "pre_training_started": receipt.get("training_started"),
        "preregistration_sha256": prereg_sha,
        "provenance": live["provenance"],
        "ready_to_train": receipt.get("ready_to_train"),
        "reserve_manifest_sha256": manifest_sha,
        "reserve_state": reserve_receipt.get("state"),
        "role_bias_sha256": live["expanded_role_bias_sha256"],
        "role_weight_sha256": live["expanded_role_weight_sha256"],
        "routing_validation": live["routing_validation"],
        "schedule": {
            "candidate": prereg.get("candidate_schedule"),
            "control": prereg.get("control_schedule"),
        },
        "shared_settings": prereg.get("shared_settings"),
        "slice_counts": slices,
        "status": receipt.get("status"),
        "threshold_authorization_sha256": threshold_sha,
        "warm_start_sha256": live["warm_start_sha256"],
        "weights_mutated_by_training": False,
        "witness_file_sha256": witness_sha,
    }
