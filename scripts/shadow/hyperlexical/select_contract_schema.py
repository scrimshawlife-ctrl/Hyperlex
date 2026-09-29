"""JSON Schema checks for routing, admission, threshold, and launch authorization.

Historical artifacts are validated and not rewritten.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_DIR = REPO_ROOT / "specs/007-hyperlexical-model/schemas/hyperlex/select"
ROUTING_SCHEMA_PATH = SCHEMA_DIR / "eval-routing.schema.json"
THRESHOLD_SCHEMA_PATH = SCHEMA_DIR / "threshold-authorization.schema.json"
ADMISSION_SCHEMA_PATH = SCHEMA_DIR / "admission.schema.json"
TRAINING_LAUNCH_AUTHORIZATION_SCHEMA_PATH = SCHEMA_DIR / "training-launch-authorization.schema.json"
TRAINING_LAUNCH_AUTHORIZATION_SPEC_SCHEMA_PATH = (
    SCHEMA_DIR / "training-launch-authorization-spec.schema.json"
)
SELECT_006_TRAINING_LAUNCH_AUTHORIZATION_SCHEMA_PATH = (
    SCHEMA_DIR / "select-006-training-launch-authorization.schema.json"
)


def _validator(path: Path) -> Draft202012Validator:
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def routing_schema_errors(instance: Mapping[str, Any]) -> list[str]:
    return sorted(error.message for error in _validator(ROUTING_SCHEMA_PATH).iter_errors(instance))


def threshold_schema_errors(instance: Mapping[str, Any]) -> list[str]:
    return sorted(error.message for error in _validator(THRESHOLD_SCHEMA_PATH).iter_errors(instance))


def admission_schema_errors(instance: Mapping[str, Any]) -> list[str]:
    return sorted(error.message for error in _validator(ADMISSION_SCHEMA_PATH).iter_errors(instance))


def training_launch_authorization_schema_errors(instance: Mapping[str, Any]) -> list[str]:
    return sorted(
        error.message
        for error in _validator(TRAINING_LAUNCH_AUTHORIZATION_SCHEMA_PATH).iter_errors(instance)
    )


def training_launch_authorization_spec_schema_errors(instance: Mapping[str, Any]) -> list[str]:
    return sorted(
        error.message
        for error in _validator(TRAINING_LAUNCH_AUTHORIZATION_SPEC_SCHEMA_PATH).iter_errors(instance)
    )


def select_006_training_launch_authorization_schema_errors(instance: Mapping[str, Any]) -> list[str]:
    return sorted(
        error.message
        for error in _validator(SELECT_006_TRAINING_LAUNCH_AUTHORIZATION_SCHEMA_PATH).iter_errors(instance)
    )


def historical_schema_report(
    admission_artifacts: Mapping[str, Mapping[str, Any]],
    threshold_artifacts: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """VALIDATE_ONLY. Names and messages, no artifact rewrite."""
    gaps = []
    for name, payload in sorted(admission_artifacts.items()):
        for message in admission_schema_errors(payload):
            gaps.append({"artifact": name, "schema": "hyperlex.admission.v1", "message": message})
    for name, payload in sorted(threshold_artifacts.items()):
        for message in threshold_schema_errors(payload):
            gaps.append(
                {"artifact": name, "schema": "hyperlex.threshold_authorization.v1", "message": message}
            )
    return {
        "gaps": gaps,
        "mode": "VALIDATE_ONLY",
        "mutated": False,
        "result": "SCHEMA_CONFORMANCE_GAP" if gaps else "HISTORICAL_VALIDATION_COMPLETE",
    }
