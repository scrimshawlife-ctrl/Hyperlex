"""SELECT-005 operator-to-compute authorization.

``launch_authorization_spec`` does not authorize compute and does not train.
``training_launch_authorization`` records the operator decision and does not train.
``ready_to_train`` is not ``training_launch_authorized``.
``training_launch_authorized`` is not ``training_started``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from .select_005_reserve import EXPERIMENT_ID, canonical_json, sha256_text
from .select_contract_schema import (
    training_launch_authorization_schema_errors,
    training_launch_authorization_spec_schema_errors,
)

TRANSITION = "SELECT_005_TRAINING_LAUNCH_AUTHORIZATION_SPEC"
STATE = "TRAINING_LAUNCH_AUTHORIZATION_SPEC_SEALED"
SCHEMA = "hyperlex.select_005_training_launch_authorization_spec.v1"
AUTHORIZATION_SCHEMA = "hyperlex.training_launch_authorization.v1"
AUTHORIZATION_TRANSITION = "SELECT_005_TRAINING_LAUNCH_AUTHORIZATION"
LAUNCH_TRANSITION = "SELECT_005_TRAINING_LAUNCH"

ADMISSION_RECEIPT_SHA256 = "874ac309f1a51a677a692705aebd8fd48ae25dbdb5ca4d1e5c08c7870bdef382"
PREREGISTRATION_SHA256 = "c2dcf3b703f50cb8eb80bb6c2c45335071ded3c4ce89cc669e8a869eb3498baf"
THRESHOLD_AUTHORIZATION_SHA256 = "e0d8d81b6392692784d92542d0cc5aa6ee6756b93c44bab86e2167ef57cfbc55"
RESERVE_MANIFEST_SHA256 = "2567b3e2d1a3b95b8ea4a474d4dda3ccbe2b6d55b016dd999b5eedcacd4b1f79"
ENVIRONMENT_SHA256 = "ad253140ed539fd664188c472ff95ed42a98a8b6e7cf6389d6188dde8b83206d"
WARM_START_SHA256 = "96838b9656a84c3fee1773a41fdf2fbbec2f88f3bc948e4acfbe06c194ac5587"
SPEC_RECEIPT_SHA256 = "34e2f0a6be0e8f4a3af079183d83869afe7a80995757881352bec7e978fe3cd2"
LEDGER_EVENTS_SHA256 = "4ec441f545e37cd9e691ab322fa438269c79b6a6ed82f56b58ce740e94665763"
LEDGER_PROJECTION_SHA256 = "83d7dde24f723e750b487819aa1a5b6c7d847ca55fa5b1bf2dcd8b8157cc50d2"
ISOLATION_SHA256 = "82bc57c2bbec9793f61a8a783e04e6f988fdb23a1288c79c5f86ccf63ae30b67"
PROVENANCE_SHA256 = "fc798d1ae67a5f575659722558316bdbf76f63d131a8905632c4faff7797fa74"
BEST_SHA256 = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
ACTIVE_EVAL_RESERVE = 78
RESERVE_COUNTS = {
    "classify": 51,
    "classify_non_none": 11,
    "classify_observed": 11,
    "unbind_clean": 27,
}
PRECONDITION_FAILURE = "LAUNCH_AUTHORIZATION_PRECONDITION_FAILURE"
PIN_MISMATCH = "LAUNCH_AUTHORIZATION_PIN_MISMATCH"
SCHEMA_FAILURE = "LAUNCH_AUTHORIZATION_SCHEMA_FAILURE"
SEAL_FAILURE = "LAUNCH_AUTHORIZATION_SEAL_FAILURE"

REQUIRED_PINS = {
    "admission_receipt_sha256": ADMISSION_RECEIPT_SHA256,
    "environment_sha256": ENVIRONMENT_SHA256,
    "experiment_id": EXPERIMENT_ID,
    "preregistration_sha256": PREREGISTRATION_SHA256,
    "reserve_manifest_sha256": RESERVE_MANIFEST_SHA256,
    "threshold_authorization_sha256": THRESHOLD_AUTHORIZATION_SHA256,
    "warm_start_sha256": WARM_START_SHA256,
}

SEALED_SCHEDULE = {
    "baseline": {
        "HYPERLEX_EARLY_STOP": "0",
        "HYPERLEX_EARLY_STOP_MIN_EPOCHS": None,
        "HYPERLEX_EARLY_STOP_PATIENCE": None,
        "HYPERLEX_TRAIN_EPOCHS": "40",
    },
    "candidate": {
        "HYPERLEX_EARLY_STOP": "1",
        "HYPERLEX_EARLY_STOP_MIN_EPOCHS": "4",
        "HYPERLEX_EARLY_STOP_PATIENCE": "4",
        "HYPERLEX_TRAIN_EPOCHS": "12",
    },
    "checkpoint_rule": {
        "restore_best": True,
        "strict_increase": True,
        "ties": "keep_earlier",
    },
    "selection_metric": "classify_macro_f1_nonnone",
}


def launch_authorization_spec() -> dict[str, Any]:
    """Frozen spec. Calling it does not authorize compute and does not train."""
    spec = {
        "admission_result": "ADMISSION_PASS",
        "authorization_record": {
            "next_legal_transition_after_seal": LAUNCH_TRANSITION,
            "operator_decision_required": "AUTHORIZE",
            "performs_training": False,
            "schema": AUTHORIZATION_SCHEMA,
            "sealed_by_this_spec": False,
            "training_launch_authorized_required": True,
            "training_started_required": False,
        },
        "best_changed": False,
        "edge": [
            "TRAINING_READY",
            AUTHORIZATION_TRANSITION,
            "TRAINING_LAUNCH_AUTHORIZED",
            LAUNCH_TRANSITION,
            "TRAINING_STARTED",
        ],
        "epochs": 0,
        "executes_training": False,
        "experiment_id": EXPERIMENT_ID,
        "gradient_steps": 0,
        "launch_legal": False,
        "next_legal_transition": AUTHORIZATION_TRANSITION,
        "optimizer_constructed": False,
        "ready_to_train": True,
        "required_pins": dict(REQUIRED_PINS),
        "schema": SCHEMA,
        "sealed_schedule": json.loads(canonical_json(SEALED_SCHEDULE)),
        "separation": {
            "ready_to_train": "all scientific and admission gates passed",
            "training_launch_authorized": "operator has explicitly authorized compute",
            "training_started": "training actually began",
        },
        "state": STATE,
        "status": "TRAINING_READY",
        "training_launch_authorized": False,
        "training_started": False,
        "transition": TRANSITION,
        "weights_mutated": False,
    }
    _validate(spec)
    return spec


def _validate(spec: Mapping[str, Any]) -> None:
    if spec.get("operator_decision") == "AUTHORIZE":
        raise SystemExit("REFUSE: this spec does not record operator_decision AUTHORIZE")
    if spec.get("training_launch_authorized") is not False:
        raise SystemExit("REFUSE: ready_to_train is not launch authorization")
    if spec.get("training_started") is not False or spec.get("executes_training") is not False:
        raise SystemExit("REFUSE: this spec must not train")
    if spec.get("epochs") != 0 or spec.get("gradient_steps") != 0:
        raise SystemExit("REFUSE: this spec must not record steps")
    if spec.get("optimizer_constructed") or spec.get("weights_mutated") or spec.get("best_changed"):
        raise SystemExit("REFUSE: this spec must not touch weights")
    if spec.get("next_legal_transition") == LAUNCH_TRANSITION:
        raise SystemExit("REFUSE: training launch is not legal until the authorization record is sealed")
    if spec.get("launch_legal") is not False:
        raise SystemExit("REFUSE: training launch is not legal")
    record = spec.get("authorization_record")
    if not isinstance(record, Mapping) or record.get("sealed_by_this_spec") is not False:
        raise SystemExit("REFUSE: this spec must not seal the authorization record")
    if record.get("performs_training") is not False or record.get("training_started_required") is not False:
        raise SystemExit("REFUSE: the authorization transition must perform zero training")
    errors = training_launch_authorization_spec_schema_errors(spec)
    if errors:
        raise SystemExit("REFUSE: spec schema: " + "; ".join(errors))
    if not training_launch_authorization_schema_errors(spec):
        raise SystemExit("REFUSE: spec must not validate as a launch authorization")


def spec_receipt() -> dict[str, Any]:
    body = launch_authorization_spec()
    record = dict(body)
    record["record_sha256"] = sha256_text(canonical_json(body))
    return record


def freeze_spec(path: str) -> dict[str, Any]:
    """Write the spec receipt. Does not authorize compute and does not train."""
    receipt = spec_receipt()
    target = Path(path)
    if target.exists():
        raise SystemExit(f"REFUSE: launch authorization spec already exists: {target}")
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(target.parent, 0o700)
    target.write_text(canonical_json(receipt), encoding="utf-8")
    os.chmod(target, 0o600)
    return receipt


def _fail(state: str, reason: str) -> None:
    raise SystemExit(f"{state}: {reason}")


def require_authorization_record(record: Mapping[str, Any]) -> None:
    """Reject any authorization record that would train or drift from the pins."""
    errors = training_launch_authorization_schema_errors(record)
    if errors:
        _fail(SCHEMA_FAILURE, "; ".join(errors))
    if record.get("operator_decision") != "AUTHORIZE":
        _fail(SCHEMA_FAILURE, "operator_decision")
    if record.get("training_launch_authorized") is not True:
        _fail(SCHEMA_FAILURE, "training_launch_authorized")
    if record.get("ready_to_train") is not True:
        _fail(SCHEMA_FAILURE, "ready_to_train")
    if record.get("training_started") is not False or record.get("executes_training") is not False:
        _fail(SCHEMA_FAILURE, "authorization must perform zero training")
    if record.get("epochs") != 0 or record.get("gradient_steps") != 0:
        _fail(SCHEMA_FAILURE, "steps")
    if record.get("optimizer_constructed") or record.get("weights_mutated") or record.get("best_changed"):
        _fail(SCHEMA_FAILURE, "weights")
    if record.get("state") != "TRAINING_LAUNCH_AUTHORIZED":
        _fail(SCHEMA_FAILURE, "state")
    if record.get("next_legal_transition") != LAUNCH_TRANSITION:
        _fail(SCHEMA_FAILURE, "next transition")
    if record.get("transition") != AUTHORIZATION_TRANSITION:
        _fail(SCHEMA_FAILURE, "transition")


def training_launch_authorization() -> dict[str, Any]:
    """Operator authorization of compute. Calling it does not train."""
    record = {
        "admission_receipt_sha256": ADMISSION_RECEIPT_SHA256,
        "best_changed": False,
        "environment_sha256": ENVIRONMENT_SHA256,
        "epochs": 0,
        "executes_training": False,
        "experiment_id": EXPERIMENT_ID,
        "gradient_steps": 0,
        "next_legal_transition": LAUNCH_TRANSITION,
        "operator_decision": "AUTHORIZE",
        "optimizer_constructed": False,
        "preregistration_sha256": PREREGISTRATION_SHA256,
        "ready_to_train": True,
        "reserve_manifest_sha256": RESERVE_MANIFEST_SHA256,
        "schedule": json.loads(canonical_json(SEALED_SCHEDULE)),
        "schema": AUTHORIZATION_SCHEMA,
        "scientific_variable": "train_schedule",
        "state": "TRAINING_LAUNCH_AUTHORIZED",
        "threshold_authorization_sha256": THRESHOLD_AUTHORIZATION_SHA256,
        "training_launch_authorized": True,
        "training_started": False,
        "transition": AUTHORIZATION_TRANSITION,
        "warm_start_sha256": WARM_START_SHA256,
        "weights_mutated": False,
    }
    require_authorization_record(record)
    return record


def _sealed_schedule() -> dict[str, Any]:
    return json.loads(canonical_json(SEALED_SCHEDULE))


def _check_evidence(evidence: Mapping[str, Any]) -> None:
    preconditions = {
        "active_eval_reserve": ACTIVE_EVAL_RESERVE,
        "admission_result": "ADMISSION_PASS",
        "best_changed": False,
        "epochs": 0,
        "gradient_steps": 0,
        "ledger_replay": "PASS",
        "optimizer_constructed": False,
        "output_absent": True,
        "ready_to_train": True,
        "reserve_counts": RESERVE_COUNTS,
        "reserve_isolation": "PASS",
        "reserve_provenance": "PASS",
        "spec_state": STATE,
        "status": "TRAINING_READY",
        "training_launch_authorized": False,
        "training_started": False,
        "weights_mutated": False,
    }
    for key, expected in preconditions.items():
        if evidence.get(key) != expected:
            _fail(PRECONDITION_FAILURE, key)
    pins = {
        "best_sha256": BEST_SHA256,
        "isolation_sha256": ISOLATION_SHA256,
        "ledger_events_sha256": LEDGER_EVENTS_SHA256,
        "ledger_projection_sha256": LEDGER_PROJECTION_SHA256,
        "pins": REQUIRED_PINS,
        "provenance_sha256": PROVENANCE_SHA256,
        "schedule": _sealed_schedule(),
        "spec_receipt_sha256": SPEC_RECEIPT_SHA256,
    }
    for key, expected in pins.items():
        if evidence.get(key) != expected:
            _fail(PIN_MISMATCH, key)


def seal_training_launch_authorization(path: str, evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Write the authorization record after the pins match. Does not train."""
    _check_evidence(evidence)
    record = training_launch_authorization()
    target = Path(path)
    if "launch-authorization-spec" in target.parts:
        _fail(SEAL_FAILURE, "refusing to overwrite the spec")
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
    except SystemExit:
        target.unlink()
        raise
    if sealed != record:
        target.unlink()
        _fail(SEAL_FAILURE, "sealed bytes drifted")
    return sealed
