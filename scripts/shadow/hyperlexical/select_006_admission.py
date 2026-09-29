"""SELECT-006 admission evidence. Read-only. Does not train or score the reserve."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .eval_routing import (
    UNBIND_CLEAN_DERIVATION,
    canonical_json,
    contract_validation,
    derive_batch,
)
from .identity_ledger import IdentityLedger
from .select_006_efficiency_preservation import (
    BEST_SHA256,
    BEST_WEIGHTS,
    EPSILON,
    EXPERIMENT_ID,
    TRUNK_SHA256,
    WARM_START_DIR,
    WARM_START_SHA256,
    _schedules,
    _shared_settings,
)
from .select_006_reserve_acquisition import SELECT_005_ID, metric_surface

SELECT006_THRESHOLD_SCHEMA = "hyperlex.select_006_threshold_authorization.v1"
VERIFIED = "ZERO_INIT_LOADER_VERIFIED"
HISTORICAL_PIN_STATUS = "NOT_YET_IMPLEMENTED"

PREFLIGHT_FAILURE = "ADMISSION_PREFLIGHT_FAILURE"
PIN_MISMATCH = "ADMISSION_PIN_MISMATCH"
RESERVE_FAILURE = "ADMISSION_RESERVE_FAILURE"
LOADER_NOT_VERIFIED = "ADMISSION_LOADER_NOT_VERIFIED"
WITNESS_MISMATCH = "ADMISSION_ZERO_INIT_WITNESS_MISMATCH"
IDENTITY_FAILURE = "ADMISSION_IDENTITY_FAILURE"

PREREGISTRATION_SHA256 = "3692ac63425fcbd57e5fdc355a4e565d653ffc3c2a6703cfdda1fde7cc6404b8"
THRESHOLD_SHA256 = "91081de5f9b348102fa5d0359150f9aedca0d53e98c9f4275aeb127c9de3642c"
RESERVE_MANIFEST_SHA256 = "33ee588bdd13a322020e2a0105a71265899b856b44b6c3fcde40eb943b36cab6"
LEDGER_EVENTS_SHA256 = "4471e3339b3708f0f494f7fe60a0d30118609e7312d5d0334b946d2bbc4efbf1"
LEDGER_PROJECTION_SHA256 = "dad556c7f6bba58c7456a6b88b607c72ebe8149e36c176a602e0def2edfdc435"
ROLE_WEIGHT_SHA256 = "94aa92d4c6f17f56a6d7a68a5951ad98bb38764d029ed93916fb9b870c54c20d"
ROLE_BIAS_SHA256 = "ce7b6ecb2b276d4d5b46ae23f38a749d1939cadc336e82b76548e01065151b93"
FILLER_WEIGHT_SHA256 = "b3d11a8eb1fcfb4f616c36b9f5b32be84aab9c91d642e54294dccfea36a385a3"
FILLER_BIAS_SHA256 = "cce2ff11650d8b9734f84f1d05acd65003b68e31adb5e0c9e035beaa7f5a03bf"
COMBINED_WITNESS_SHA256 = "58a3e733087c33c5ffea5909b46098e666337e1b99fb83d87c3744db4aef91b2"

SPEC = Path("/home/morpheus/hlx-private/exp-20260929-select-006/spec-001")
PREREGISTRATION = SPEC / "SELECT_006_PREREGISTRATION.json"
THRESHOLD = SPEC / "SELECT_006_THRESHOLD_AUTHORIZATION.json"
RESERVE_DIR = Path("/home/morpheus/hlx-private/exp-20260929-select-006/reserve-acquisition-002")
WITNESS = Path(
    "/home/morpheus/hlx-private/exp-20260929-select-006/zero-init-loader-001/LOADER_WITNESS.json"
)
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
SETTLEMENT_PROVENANCE = "Blind review of SELECT-006 reserve-acquisition-002."
EXPECTED_COUNTS = {
    "classify": 32,
    "classify_non_none": 32,
    "classify_observed": 32,
    "unbind_clean": 5,
}


class Select006AdmissionError(Exception):
    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(f"{code}: {detail}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Select006AdmissionError(PREFLIGHT_FAILURE, f"{path.name} is unreadable") from exc
    if not isinstance(payload, dict):
        raise Select006AdmissionError(PREFLIGHT_FAILURE, f"{path.name} is not an object")
    return payload


def _pin(path: Path, expected: str, label: str) -> str:
    try:
        actual = _sha256(path)
    except OSError as exc:
        raise Select006AdmissionError(PIN_MISMATCH, f"{label} is unreadable") from exc
    if actual != expected:
        raise Select006AdmissionError(PIN_MISMATCH, label)
    return actual


def verify_zero_init_witness(witness: dict[str, Any]) -> None:
    """Live loader state is the verified witness, not the historical pin text."""
    if witness.get("execution_loader_status") != VERIFIED:
        raise Select006AdmissionError(
            LOADER_NOT_VERIFIED,
            "zero-init execution loader is not verified",
        )
    expected = {
        "expanded_role_weight_sha256": ROLE_WEIGHT_SHA256,
        "expanded_role_bias_sha256": ROLE_BIAS_SHA256,
        "expanded_filler_weight_sha256": FILLER_WEIGHT_SHA256,
        "expanded_filler_bias_sha256": FILLER_BIAS_SHA256,
        "expanded_loader_witness_sha256": COMBINED_WITNESS_SHA256,
    }
    for key, value in expected.items():
        if witness.get(key) != value:
            raise Select006AdmissionError(WITNESS_MISMATCH, key)
    if witness.get("optimizer_constructed") is not False or witness.get("training_started") is not False:
        raise Select006AdmissionError(LOADER_NOT_VERIFIED, "zero-init witness records training")


def select006_threshold_is_sealed(payload: dict[str, Any], experiment_id: str) -> bool:
    if payload.get("schema") != SELECT006_THRESHOLD_SCHEMA:
        return False
    if experiment_id != EXPERIMENT_ID or payload.get("experiment_id") != EXPERIMENT_ID:
        raise Select006AdmissionError(PIN_MISMATCH, "threshold experiment_id")
    if payload.get("sealed") is not True or payload.get("authorization_state") != "SEALED":
        raise Select006AdmissionError(PIN_MISMATCH, "threshold authorization is not sealed")
    if payload.get("epsilon") != 0 or payload.get("training_launch_authorized") is not False:
        raise Select006AdmissionError(PIN_MISMATCH, "threshold epsilon or launch flag")
    rule = payload.get("decision_rule")
    if not isinstance(rule, dict) or rule.get("compensation") is not False or rule.get("primary_equality") != "PASS":
        raise Select006AdmissionError(PIN_MISMATCH, "threshold decision rule")
    return True


def _routing_metadata(raw: dict[str, Any]) -> dict[str, Any]:
    task = "unbind" if raw.get("unbind_clean_derivation") == UNBIND_CLEAN_DERIVATION else "classify"
    return {
        "normalized_identity": raw["normalized_hash"],
        "provenance_state": raw["provenance_status"],
        "row_id": raw["candidate_id"],
        "source_identity": raw["source_url"],
        "task": task,
        "unbind_clean": task == "unbind",
        "unbind_clean_derivation": raw.get("unbind_clean_derivation"),
    }


def _verify_routing(receipt: dict[str, Any]) -> str:
    routing_path = RESERVE_DIR / "ROUTING_RECORDS.jsonl"
    raw_path = RESERVE_DIR / "RAW_CANDIDATES.jsonl"
    routing = [json.loads(line) for line in routing_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    raws = {
        row["candidate_id"]: row
        for row in (
            json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines() if line.strip()
        )
    }
    events: dict[str, dict[str, Any]] = {}
    for line in (LEDGER / "settlement" / "events.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if event.get("provenance") == SETTLEMENT_PROVENANCE:
            events[str(event["row_id"])] = event
    if len(routing) != 37 or len(events) != 37:
        raise Select006AdmissionError(RESERVE_FAILURE, "routing or settlement row count")
    pairs = []
    for record in routing:
        row_id = str(record["row_id"])
        if row_id not in events or row_id not in raws:
            raise Select006AdmissionError(RESERVE_FAILURE, f"routing row {row_id} is unbound")
        pairs.append((events[row_id], _routing_metadata(raws[row_id])))
    validation = contract_validation(pairs)
    if validation["state"] != "ROUTING_VALIDATION_COMPLETE" or validation["determinism"] != "IDENTICAL":
        raise Select006AdmissionError(RESERVE_FAILURE, "routing validation")
    derived = derive_batch(pairs)
    if [canonical_json(row) for row in derived] != [canonical_json(row) for row in routing]:
        raise Select006AdmissionError(RESERVE_FAILURE, "routing replay differed")
    routing_sha = _sha256(routing_path)
    if routing_sha != receipt.get("routing_sha256"):
        raise Select006AdmissionError(RESERVE_FAILURE, "routing sha256")
    surface = metric_surface(derived)
    if surface["slice_counts"] != EXPECTED_COUNTS or surface["head_mapped_non_none"] != 32:
        raise Select006AdmissionError(RESERVE_FAILURE, "metric slice counts")
    if surface["floors_met"] is not True or any(value is not True for value in surface["computable"].values()):
        raise Select006AdmissionError(RESERVE_FAILURE, "metric computability")
    return routing_sha


def select006_admission_evidence() -> dict[str, Any]:
    """Verify sealed pins, the frozen reserve, and the zero-init witness."""
    prereg_sha = _pin(PREREGISTRATION, PREREGISTRATION_SHA256, "preregistration")
    threshold_sha = _pin(THRESHOLD, THRESHOLD_SHA256, "threshold authorization")
    manifest_sha = _pin(RESERVE_DIR / "RESERVE_MANIFEST.json", RESERVE_MANIFEST_SHA256, "reserve manifest")
    warm_sha = _pin(Path(WARM_START_DIR) / "model.safetensors", WARM_START_SHA256, "warm start")
    best_sha = _pin(Path(BEST_WEIGHTS), BEST_SHA256, "BEST")
    events_sha = _pin(LEDGER / "events.jsonl", LEDGER_EVENTS_SHA256, "ledger events")
    projection_sha = _pin(LEDGER / "ledger.json", LEDGER_PROJECTION_SHA256, "ledger projection")
    if _sha256(Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base/model.safetensors")) != TRUNK_SHA256:
        raise Select006AdmissionError(PIN_MISMATCH, "trunk")

    prereg = _load(PREREGISTRATION)
    if prereg.get("epsilon") != 0 or EPSILON != 0:
        raise Select006AdmissionError(PIN_MISMATCH, "EPSILON")
    control, candidate = _schedules()
    if prereg.get("control_schedule") != control or prereg.get("candidate_schedule") != candidate:
        raise Select006AdmissionError(PIN_MISMATCH, "schedules")
    if prereg.get("shared_settings") != _shared_settings():
        raise Select006AdmissionError(PIN_MISMATCH, "shared settings")
    historical = (prereg.get("vocabulary_expansion") or {}).get("execution_loader_status")
    if historical != HISTORICAL_PIN_STATUS:
        raise Select006AdmissionError(PIN_MISMATCH, "historical vocabulary pin")
    if not select006_threshold_is_sealed(_load(THRESHOLD), EXPERIMENT_ID):
        raise Select006AdmissionError(PIN_MISMATCH, "threshold authorization")

    witness = _load(WITNESS)
    verify_zero_init_witness(witness)

    reserve_receipt = _load(RESERVE_DIR / "RESERVE_RECEIPT.json")
    if reserve_receipt.get("state") != "RESERVE_FROZEN" or reserve_receipt.get("ledger_replay") != "PASS":
        raise Select006AdmissionError(RESERVE_FAILURE, "reserve receipt")
    isolation = _load(RESERVE_DIR / "ISOLATION_REPORT.json")
    provenance = _load(RESERVE_DIR / "PROVENANCE_REPORT.json")
    if isolation.get("result") != "PASS" or isolation.get("overlaps"):
        raise Select006AdmissionError(RESERVE_FAILURE, "isolation")
    if provenance.get("result") != "PASS":
        raise Select006AdmissionError(RESERVE_FAILURE, "provenance")
    if _sha256(RESERVE_DIR / "ISOLATION_REPORT.json") != reserve_receipt.get("isolation_sha256"):
        raise Select006AdmissionError(RESERVE_FAILURE, "isolation sha256")
    if _sha256(RESERVE_DIR / "PROVENANCE_REPORT.json") != reserve_receipt.get("provenance_sha256"):
        raise Select006AdmissionError(RESERVE_FAILURE, "provenance sha256")
    manifest = _load(RESERVE_DIR / "RESERVE_MANIFEST.json")
    if manifest.get("slice_counts") != EXPECTED_COUNTS or manifest.get("head_mapped_non_none") != 32:
        raise Select006AdmissionError(RESERVE_FAILURE, "manifest slices")
    if len(manifest.get("rows") or []) != 37:
        raise Select006AdmissionError(IDENTITY_FAILURE, "manifest identity count")
    routing_sha = _verify_routing(reserve_receipt)

    ledger = IdentityLedger.load(LEDGER)
    projected = json.dumps(ledger.project(), indent=2, sort_keys=True) + "\n"
    if projected != (LEDGER / "ledger.json").read_text(encoding="utf-8"):
        raise Select006AdmissionError(RESERVE_FAILURE, "ledger replay")
    active = ledger.active_reserve_records(EXPERIMENT_ID)
    counts = ledger.active_reserve_counts(EXPERIMENT_ID)
    if len(active) != 37 or counts != EXPECTED_COUNTS:
        raise Select006AdmissionError(IDENTITY_FAILURE, "active SELECT-006 reserve")
    if len(ledger.active_reserve_records(SELECT_005_ID)) != 78:
        raise Select006AdmissionError(RESERVE_FAILURE, "SELECT-005 reserve changed")

    return {
        "admission_reason": "ADMISSION_PASS",
        "best_sha256": best_sha,
        "epsilon": 0,
        "execution_loader_status": VERIFIED,
        "expanded_filler_bias_sha256": FILLER_BIAS_SHA256,
        "expanded_filler_weight_sha256": FILLER_WEIGHT_SHA256,
        "expanded_loader_witness_sha256": COMBINED_WITNESS_SHA256,
        "expanded_role_bias_sha256": ROLE_BIAS_SHA256,
        "expanded_role_weight_sha256": ROLE_WEIGHT_SHA256,
        "head_mapped_non_none": 32,
        "historical_vocabulary_pin_status": HISTORICAL_PIN_STATUS,
        "isolation": "PASS",
        "ledger_events_sha256": events_sha,
        "ledger_projection_sha256": projection_sha,
        "ledger_replay": "PASS",
        "metric_computability": "PASS",
        "preregistration_sha256": prereg_sha,
        "provenance": "PASS",
        "reserve_manifest_sha256": manifest_sha,
        "routing_validation": "PASS",
        "routing_sha256": routing_sha,
        "select_006_active_reserve": 37,
        "threshold_authorization_sha256": threshold_sha,
        "warm_start_sha256": warm_sha,
    }
