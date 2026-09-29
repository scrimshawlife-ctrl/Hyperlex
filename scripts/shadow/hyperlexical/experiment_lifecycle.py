"""Compact experiment lifecycle.

States are DRAFT, PREREGISTERED, READY, RUNNING, then one of
SETTLED_PASS, SETTLED_FAIL, or SETTLED_INVALID. Promotion is a later
decision and does not follow from PASS.

Historical SELECT receipts stay valid. This module reads them. It does
not rewrite them and it does not train.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "hyperlex.experiment_lifecycle.v1"
EVIDENCE_SCHEMA = "hyperlex.experiment_readiness.v1"
SCHEMA_PATH = (
    Path(__file__).resolve().parents[3]
    / "specs/007-hyperlexical-model/schemas/hyperlex/select/experiment-readiness.schema.json"
)

DRAFT = "DRAFT"
PREREGISTERED = "PREREGISTERED"
READY = "READY"
RUNNING = "RUNNING"
SETTLED_PASS = "SETTLED_PASS"
SETTLED_FAIL = "SETTLED_FAIL"
SETTLED_INVALID = "SETTLED_INVALID"
PROMOTED = "PROMOTED"

FROZEN_FIELDS = (
    "acceptance_rules",
    "candidate_schedule",
    "control_schedule",
    "evaluation_design",
    "experiment_id",
    "hypothesis",
    "promotion_policy",
    "selection_metric",
    "shared_hyperparameters",
    "training_data_sha256",
    "warm_start_sha256",
)

EVIDENCE_KEYS = (
    "environment",
    "isolation",
    "ledger",
    "loader",
    "metric_computability",
    "operator_authorization",
    "preregistration",
    "provenance",
    "reserve",
    "schedule",
    "telemetry_plan",
    "thresholds",
    "training_data",
    "warm_start",
)

DEFAULT_BLOCKER = {
    "environment": "ENVIRONMENT_MISMATCH",
    "isolation": "EVALUATION_LEAKAGE",
    "ledger": "LEDGER_REPLAY_FAILURE",
    "loader": "LOADER_INVALID",
    "metric_computability": "METRIC_NONCOMPUTABLE",
    "operator_authorization": "OPERATOR_AUTHORIZATION_MISSING",
    "preregistration": "PREREGISTRATION_MISMATCH",
    "provenance": "PROVENANCE_FAILURE",
    "reserve": "RESERVE_INVALID",
    "schedule": "PREREGISTRATION_MISMATCH",
    "telemetry_plan": "TELEMETRY_PLAN_INVALID",
    "thresholds": "PREREGISTRATION_MISMATCH",
    "training_data": "DATA_INTEGRITY_FAILURE",
    "warm_start": "DATA_INTEGRITY_FAILURE",
}

AUTHORIZE = "AUTHORIZE"
AUTHORIZE_PROMOTION = "AUTHORIZE_PROMOTION"

SELECT_006_ID = "HLX-EXP-2026-09-29-SELECT-006"
SELECT_006_PINS = {
    "admission_receipt_sha256": "7ff98e8bc9a49a8875e8c7310f18ae9c5bb53ca4ad40e9b954ca89d52a7551bd",
    "baseline_env_sha256": "ca26a7cb12fcd0ce96e0f198fbcd30a1fd3e61fe0164e14dad823a2d17516a9d",
    "candidate_env_sha256": "f67c45774b173d7c894177252f16e3abe39cbdbb6f20f83c4db53b8485bd3ea6",
    "config_sha256": "fec14e56789f1c761b5f2e6ab0ef1958a3518b3fc4b1d44d15bd1afeb8f1865b",
    "launch_authorization_sha256": "4c13b58cc05a6418a1281e21fcf1d586bfacedbaa0a11354526b3ccf80c4b9db",
    "preregistration_sha256": "3692ac63425fcbd57e5fdc355a4e565d653ffc3c2a6703cfdda1fde7cc6404b8",
    "reserve_manifest_sha256": "33ee588bdd13a322020e2a0105a71265899b856b44b6c3fcde40eb943b36cab6",
    "threshold_authorization_sha256": "91081de5f9b348102fa5d0359150f9aedca0d53e98c9f4275aeb127c9de3642c",
    "training_data_sha256": "64b7d3dede25047cb6dd2e5b663f7fa72946ec82ac1a8816ae34622d1aaac430",
    "warm_start_sha256": "96838b9656a84c3fee1773a41fdf2fbbec2f88f3bc948e4acfbe06c194ac5587",
    "witness_sha256": "58a3e733087c33c5ffea5909b46098e666337e1b99fb83d87c3744db4aef91b2",
    "ledger_events_sha256": "4471e3339b3708f0f494f7fe60a0d30118609e7312d5d0334b946d2bbc4efbf1",
    "ledger_projection_sha256": "dad556c7f6bba58c7456a6b88b607c72ebe8149e36c176a602e0def2edfdc435",
}


class LifecycleError(Exception):
    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(f"{code}: {detail}")


def _copy(record: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(record))


def _sha_ok(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _entry(
    *,
    status: str,
    artifact: str | None,
    sha256: str | None,
    timestamp: str | None,
    blocking_reason: str | None,
) -> dict[str, Any]:
    if status not in {"PASS", "FAIL"}:
        raise LifecycleError("PREREGISTRATION_MISMATCH", "evidence status")
    if status == "PASS":
        if blocking_reason is not None or not _sha_ok(sha256):
            raise LifecycleError("PREREGISTRATION_MISMATCH", "passing evidence needs a hash and no blocker")
    elif not blocking_reason:
        raise LifecycleError("PREREGISTRATION_MISMATCH", "failed evidence needs a blocking reason")
    return {
        "artifact": artifact,
        "blocking_reason": blocking_reason,
        "sha256": sha256,
        "status": status,
        "timestamp": timestamp,
    }


def _validate_evidence(evidence: Mapping[str, Any]) -> None:
    import jsonschema

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(error.message for error in jsonschema.Draft202012Validator(schema).iter_errors(evidence))
    if errors:
        raise LifecycleError("PREREGISTRATION_MISMATCH", "; ".join(errors))


def draft(experiment_id: str) -> dict[str, Any]:
    """An open experiment. Compute is not authorized."""
    return {
        "evidence": None,
        "experiment_id": experiment_id,
        "next_action": "PREREGISTER",
        "promotion_applied": False,
        "schema": SCHEMA,
        "state": DRAFT,
    }


def preregister(experiment_id: str, definition: Mapping[str, Any]) -> dict[str, Any]:
    """Freeze the scientific definition. Later edits need a new experiment id."""
    if definition.get("experiment_id") not in (None, experiment_id):
        raise LifecycleError("PREREGISTRATION_MISMATCH", "experiment id")
    missing = [key for key in FROZEN_FIELDS if key != "experiment_id" and key not in definition]
    if missing:
        raise LifecycleError("PREREGISTRATION_MISMATCH", "incomplete preregistration")
    body = {key: definition[key] for key in FROZEN_FIELDS if key != "experiment_id"}
    policy = body.get("promotion_policy")
    if not isinstance(policy, Mapping) or policy.get("separate_from_settlement") is not True:
        raise LifecycleError("PREREGISTRATION_MISMATCH", "promotion stays a separate decision")
    if policy.get("pass_promotes_best") is not False:
        raise LifecycleError("PREREGISTRATION_MISMATCH", "PASS does not move BEST")
    return {
        "definition": {"experiment_id": experiment_id, **body},
        "evidence": None,
        "experiment_id": experiment_id,
        "next_action": "PREFLIGHT",
        "promotion_applied": False,
        "schema": SCHEMA,
        "state": PREREGISTERED,
    }


def assert_same_science(record: Mapping[str, Any], proposed: Mapping[str, Any]) -> None:
    """Scientific variables change only by allocating a new experiment id."""
    if record.get("state") == DRAFT:
        return
    current = record.get("definition") or {}
    if proposed.get("experiment_id") == record.get("experiment_id"):
        for key in FROZEN_FIELDS:
            if proposed.get(key) != current.get(key):
                raise LifecycleError(
                    "PREREGISTRATION_MISMATCH",
                    f"{key} changed without a new experiment id",
                )


def _observe(key: str, observation: Mapping[str, Any] | None) -> dict[str, Any]:
    observation = observation or {}
    timestamp = observation.get("timestamp")
    artifact = observation.get("artifact")
    digest = observation.get("sha256")
    if key == "operator_authorization":
        decision = observation.get("decision")
        inferred = observation.get("inferred_from")
        if decision != AUTHORIZE or inferred == "TRAINING_READY":
            return _entry(
                status="FAIL",
                artifact=artifact if isinstance(artifact, str) else None,
                sha256=digest if _sha_ok(digest) else None,
                timestamp=timestamp if isinstance(timestamp, str) else None,
                blocking_reason="OPERATOR_AUTHORIZATION_MISSING",
            )
    ok = observation.get("ok") is True
    if not ok:
        reason = observation.get("blocking_reason") or DEFAULT_BLOCKER[key]
        return _entry(
            status="FAIL",
            artifact=artifact if isinstance(artifact, str) else None,
            sha256=digest if _sha_ok(digest) else None,
            timestamp=timestamp if isinstance(timestamp, str) else None,
            blocking_reason=str(reason),
        )
    return _entry(
        status="PASS",
        artifact=str(artifact),
        sha256=str(digest),
        timestamp=timestamp if isinstance(timestamp, str) else None,
        blocking_reason=None,
    )


def preflight(record: Mapping[str, Any], observations: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """One pass. Any failed check stays PREREGISTERED and names the blocker."""
    if record.get("state") != PREREGISTERED:
        raise LifecycleError("PREREGISTRATION_MISMATCH", "preflight starts from PREREGISTERED")
    evidence = {key: _observe(key, observations.get(key)) for key in EVIDENCE_KEYS}
    _validate_evidence(evidence)
    blockers = [
        {"blocking_reason": item["blocking_reason"], "check": key}
        for key, item in evidence.items()
        if item["status"] != "PASS"
    ]
    updated = _copy(record)
    updated["evidence"] = evidence
    updated["blocking_reasons"] = blockers
    if blockers:
        updated["state"] = PREREGISTERED
        updated["next_action"] = "PREFLIGHT"
        return updated
    updated["state"] = READY
    updated["next_action"] = "RUN"
    return updated


def begin_run(record: Mapping[str, Any]) -> dict[str, Any]:
    """The first optimizer step. Authorization is checked again here."""
    if record.get("state") != READY:
        raise LifecycleError("OPERATOR_AUTHORIZATION_MISSING", "run starts from READY")
    auth = (record.get("evidence") or {}).get("operator_authorization") or {}
    if auth.get("status") != "PASS" or auth.get("blocking_reason") is not None:
        raise LifecycleError("OPERATOR_AUTHORIZATION_MISSING", "operator authorization")
    updated = _copy(record)
    updated["state"] = RUNNING
    updated["next_action"] = "SETTLE"
    updated["running_since_optimizer_step"] = 1
    return updated


def settle(
    record: Mapping[str, Any],
    *,
    scientifically_valid: bool,
    acceptance_passed: bool,
) -> dict[str, Any]:
    """One settlement. Integrity failure is INVALID, not FAIL."""
    if record.get("state") != RUNNING:
        raise LifecycleError("TELEMETRY_PLAN_INVALID", "settlement starts from RUNNING")
    updated = _copy(record)
    updated["promotion_applied"] = False
    if not scientifically_valid:
        updated["state"] = SETTLED_INVALID
        updated["next_action"] = "NONE"
        return updated
    if acceptance_passed:
        updated["state"] = SETTLED_PASS
        updated["next_action"] = "PROMOTE_OPTIONAL"
        return updated
    updated["state"] = SETTLED_FAIL
    updated["next_action"] = "NONE"
    return updated


def promote(record: Mapping[str, Any], decision: str) -> dict[str, Any]:
    """Explicit promotion. PASS does not call this."""
    if record.get("state") != SETTLED_PASS:
        raise LifecycleError("OPERATOR_AUTHORIZATION_MISSING", "only SETTLED_PASS can promote")
    if decision != AUTHORIZE_PROMOTION:
        raise LifecycleError("OPERATOR_AUTHORIZATION_MISSING", "promotion decision")
    updated = _copy(record)
    updated["state"] = PROMOTED
    updated["promotion_applied"] = True
    updated["next_action"] = "NONE"
    return updated


def _historical_ok(flag: Any) -> bool:
    return flag == "PASS" or flag is True


def map_historical(markers: Mapping[str, Any]) -> dict[str, Any]:
    """Map sealed legacy markers onto readiness evidence. Does not rewrite them.

    ``TRAINING_READY`` is not operator authorization.
    ``TRAINING_LAUNCH_AUTHORIZED`` counts only together with decision AUTHORIZE.
    ``RESERVE_FROZEN`` and ``ZERO_INIT_LOADER_VERIFIED`` are evidence, not states.
    """
    timestamp = markers.get("timestamp")
    if timestamp is not None and not isinstance(timestamp, str):
        timestamp = None

    def obs(ok: bool, artifact: str, sha: Any, reason: str) -> dict[str, Any]:
        body: dict[str, Any] = {
            "artifact": artifact,
            "ok": ok and _sha_ok(sha),
            "sha256": sha,
            "timestamp": timestamp,
        }
        if not body["ok"]:
            body["blocking_reason"] = reason
        return body

    authorized = (
        markers.get("state") == "TRAINING_LAUNCH_AUTHORIZED"
        and markers.get("training_launch_authorized") is True
        and markers.get("operator_decision") == AUTHORIZE
    )
    observations = {
        "preregistration": obs(
            markers.get("preregistration_sha256") == markers.get("expected_preregistration_sha256"),
            str(markers.get("preregistration_artifact") or "preregistration"),
            markers.get("preregistration_sha256"),
            "PREREGISTRATION_MISMATCH",
        ),
        "warm_start": obs(
            markers.get("warm_start_sha256") == markers.get("expected_warm_start_sha256"),
            str(markers.get("warm_start_artifact") or "warm-start"),
            markers.get("warm_start_sha256"),
            "DATA_INTEGRITY_FAILURE",
        ),
        "training_data": obs(
            markers.get("training_data_sha256") == markers.get("expected_training_data_sha256"),
            str(markers.get("training_data_artifact") or "training-export"),
            markers.get("training_data_sha256"),
            "DATA_INTEGRITY_FAILURE",
        ),
        "reserve": obs(
            markers.get("reserve_state") == "RESERVE_FROZEN"
            and markers.get("reserve_manifest_sha256") == markers.get("expected_reserve_manifest_sha256"),
            str(markers.get("reserve_artifact") or "reserve-manifest"),
            markers.get("reserve_manifest_sha256"),
            "RESERVE_INVALID",
        ),
        "isolation": obs(
            _historical_ok(markers.get("isolation")),
            str(markers.get("isolation_artifact") or "isolation"),
            markers.get("isolation_sha256"),
            "EVALUATION_LEAKAGE",
        ),
        "provenance": obs(
            _historical_ok(markers.get("provenance")),
            str(markers.get("provenance_artifact") or "provenance"),
            markers.get("provenance_sha256"),
            "PROVENANCE_FAILURE",
        ),
        "metric_computability": obs(
            _historical_ok(markers.get("metric_computability")),
            str(markers.get("metric_artifact") or "metric-computability"),
            markers.get("metric_sha256"),
            "METRIC_NONCOMPUTABLE",
        ),
        "loader": obs(
            markers.get("execution_loader_status") == "ZERO_INIT_LOADER_VERIFIED"
            and markers.get("witness_sha256") == markers.get("expected_witness_sha256"),
            str(markers.get("loader_artifact") or "loader-witness"),
            markers.get("witness_sha256"),
            "LOADER_INVALID",
        ),
        "environment": obs(
            markers.get("baseline_env_sha256") == markers.get("expected_baseline_env_sha256")
            and markers.get("candidate_env_sha256") == markers.get("expected_candidate_env_sha256")
            and markers.get("config_sha256") == markers.get("expected_config_sha256"),
            str(markers.get("environment_artifact") or "spec-001/BASELINE_ENV.json"),
            markers.get("baseline_env_sha256"),
            "ENVIRONMENT_MISMATCH",
        ),
        "schedule": obs(
            markers.get("schedule_pinned") is True,
            str(markers.get("schedule_artifact") or "schedules"),
            markers.get("preregistration_sha256"),
            "PREREGISTRATION_MISMATCH",
        ),
        "thresholds": obs(
            markers.get("threshold_authorization_sha256") == markers.get("expected_threshold_sha256")
            and markers.get("epsilon") == 0,
            str(markers.get("threshold_artifact") or "threshold"),
            markers.get("threshold_authorization_sha256"),
            "PREREGISTRATION_MISMATCH",
        ),
        "ledger": obs(
            _historical_ok(markers.get("ledger_replay"))
            and markers.get("ledger_events_sha256") == markers.get("expected_ledger_events_sha256")
            and markers.get("ledger_projection_sha256") == markers.get("expected_ledger_projection_sha256"),
            str(markers.get("ledger_artifact") or "ledger"),
            markers.get("ledger_events_sha256"),
            "LEDGER_REPLAY_FAILURE",
        ),
        "telemetry_plan": obs(
            markers.get("telemetry_plan_valid") is True,
            str(markers.get("telemetry_artifact") or "telemetry-plan"),
            markers.get("preregistration_sha256"),
            "TELEMETRY_PLAN_INVALID",
        ),
        "operator_authorization": {
            "artifact": str(markers.get("authorization_artifact") or "training-launch-authorization"),
            "decision": markers.get("operator_decision") if authorized else markers.get("status"),
            "inferred_from": None if authorized else "TRAINING_READY",
            "ok": authorized,
            "sha256": markers.get("launch_authorization_sha256"),
            "timestamp": timestamp,
        },
    }
    if not authorized:
        observations["operator_authorization"]["blocking_reason"] = "OPERATOR_AUTHORIZATION_MISSING"
    definition = markers.get("definition")
    if not isinstance(definition, Mapping):
        raise LifecycleError("PREREGISTRATION_MISMATCH", "historical definition")
    registered = preregister(str(markers.get("experiment_id")), definition)
    return preflight(registered, observations)


def select_006_historical_markers(*, timestamp: str | None = None) -> dict[str, Any]:
    """The sealed SELECT-006 chain, expressed as legacy markers."""
    pins = SELECT_006_PINS
    return {
        "baseline_env_sha256": pins["baseline_env_sha256"],
        "candidate_env_sha256": pins["candidate_env_sha256"],
        "config_sha256": pins["config_sha256"],
        "definition": {
            "acceptance_rules": {"epsilon": 0, "compensation": False},
            "candidate_schedule": {"max_epochs": 12, "minimum_epochs": 4, "early_stopping_patience": 4},
            "control_schedule": {"max_epochs": 40, "early_stopping": "disabled"},
            "evaluation_design": {"active_eval_reserve": 37},
            "experiment_id": SELECT_006_ID,
            "hypothesis": "A reduced schedule can preserve quality with fewer optimizer steps.",
            "promotion_policy": {"pass_promotes_best": False, "separate_from_settlement": True},
            "selection_metric": "classify_macro_f1_nonnone",
            "shared_hyperparameters": {"learning_rate": "2e-5", "batch_size": 8},
            "training_data_sha256": pins["training_data_sha256"],
            "warm_start_sha256": pins["warm_start_sha256"],
        },
        "epsilon": 0,
        "execution_loader_status": "ZERO_INIT_LOADER_VERIFIED",
        "loader_artifact": "zero-init-loader-001/LOADER_WITNESS.json#expanded_loader_witness_sha256",
        "expected_baseline_env_sha256": pins["baseline_env_sha256"],
        "expected_candidate_env_sha256": pins["candidate_env_sha256"],
        "expected_config_sha256": pins["config_sha256"],
        "expected_ledger_events_sha256": pins["ledger_events_sha256"],
        "expected_ledger_projection_sha256": pins["ledger_projection_sha256"],
        "expected_preregistration_sha256": pins["preregistration_sha256"],
        "expected_reserve_manifest_sha256": pins["reserve_manifest_sha256"],
        "expected_threshold_sha256": pins["threshold_authorization_sha256"],
        "expected_training_data_sha256": pins["training_data_sha256"],
        "expected_warm_start_sha256": pins["warm_start_sha256"],
        "expected_witness_sha256": pins["witness_sha256"],
        "experiment_id": SELECT_006_ID,
        "isolation": "PASS",
        "isolation_artifact": "reserve-acquisition-002/ISOLATION_REPORT.json",
        "isolation_sha256": "b306aed3465551a24f33a4f99deb6b58d0d0c748bdf9cd3a99ded754b44d6eb2",
        "authorization_artifact": "launch-authorization-001/TRAINING_LAUNCH_AUTHORIZATION.json",
        "launch_authorization_sha256": pins["launch_authorization_sha256"],
        "ledger_events_sha256": pins["ledger_events_sha256"],
        "ledger_projection_sha256": pins["ledger_projection_sha256"],
        "ledger_replay": "PASS",
        "metric_computability": "PASS",
        "metric_artifact": "reserve-acquisition-002/METRIC_COMPUTABILITY.json",
        "metric_sha256": "be56861dfdbbf2d4e03955b13deec6f1e83e5689abad3e079dd5e098b555bef8",
        "operator_decision": AUTHORIZE,
        "preregistration_artifact": "spec-001/SELECT_006_PREREGISTRATION.json",
        "preregistration_sha256": pins["preregistration_sha256"],
        "provenance": "PASS",
        "provenance_artifact": "reserve-acquisition-002/PROVENANCE_REPORT.json",
        "provenance_sha256": "8b0b688d9d5e002229b8e3905e4c4337b27c508ba8fe6dcfbc63a9efe0e58a3a",
        "reserve_manifest_sha256": pins["reserve_manifest_sha256"],
        "reserve_artifact": "reserve-acquisition-002/RESERVE_MANIFEST.json",
        "reserve_state": "RESERVE_FROZEN",
        "schedule_artifact": "spec-001/SELECT_006_PREREGISTRATION.json",
        "schedule_pinned": True,
        "state": "TRAINING_LAUNCH_AUTHORIZED",
        "status": "TRAINING_READY",
        "telemetry_artifact": "spec-001/SELECT_006_PREREGISTRATION.json",
        "telemetry_plan_valid": True,
        "threshold_artifact": "spec-001/SELECT_006_THRESHOLD_AUTHORIZATION.json",
        "threshold_authorization_sha256": pins["threshold_authorization_sha256"],
        "timestamp": timestamp,
        "training_data_sha256": pins["training_data_sha256"],
        "training_launch_authorized": True,
        "warm_start_sha256": pins["warm_start_sha256"],
        "witness_sha256": pins["witness_sha256"],
    }


def select_006_readiness(*, timestamp: str | None = None) -> dict[str, Any]:
    """Map the sealed SELECT-006 chain. Does not train and does not rewrite receipts."""
    return map_historical(select_006_historical_markers(timestamp=timestamp))


def main(argv: list[str] | None = None) -> int:
    """Five commands: preregister, preflight, run, settle, promote.

    ``select-006`` only prints the mapped readiness. It does not start compute.
    """
    args = list(argv or [])
    if args == ["select-006"]:
        record = select_006_readiness()
        print(
            json.dumps(
                {
                    "experiment_id": record["experiment_id"],
                    "next_action": record["next_action"],
                    "state": record["state"],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    print(
        "commands: preregister, preflight, run, settle, promote\n"
        "select-006 prints the mapped state and does not train"
    )
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
