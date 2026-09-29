"""Define the SELECT-005 operator-to-compute authorization edge.

This module does not authorize compute and does not train.
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
