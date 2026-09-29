"""Write the threshold preregistration artifacts. Does not score rows."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from hyperlexical.residual_threshold_v1 import RULE, TRACK_STATE, documents

ROOT = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
SEM = ROOT / "operator-review" / "HLX-EVAL-UNBIND-SEMANTIC-EVIDENCE-SOURCE-V1-001"
HYP = ROOT / "operator-review" / "HLX-EVAL-UNBIND-SENSE-SCREEN-V1-HYPOTHESIS-001"
MODULE = Path("/home/morpheus/Hyperlex/scripts/shadow/hyperlexical/residual_threshold_v1.py")

EXPECTED = {
    SEM / "RESIDUAL_CANDIDATE_SPEC.json": "39c2914e32557ffe1a456a56f8742ea4fe8f1aaec1dc1da451656cd22f0db32d",
    SEM / "RESIDUAL_DEVELOPMENT_SCORES.jsonl": "cea638679faeee1bc1c689823e7c0c08562c4d7ef1f8230bbbf4079239e7c3e7",
    SEM / "INTEGRATED_CONSTITUENT_RESOLUTION_V1.jsonl": "0f5dafc3676a4071ce8c889e58958b90203589aa3e91d78111b4e3292bdd87fb",
    SEM / "RESIDUAL_V1_MODEL_RESOLVED_REPLAY_SCORES.jsonl": "16c0a9eaa918ac4a6e8223cafcbf4b1918cb212769063e262cf29a279f1048f6",
    SEM / "RESIDUAL_V1_MODEL_RESOLVED_REPLAY_RECEIPT.json": "675b1b8b8f1b1e6f19c7d320e7b8fe516eae92b60e966afbce407c1f0482e736",
    SEM / "RESIDUAL_V1_MODEL_RESOLVED_DEVELOPMENT_ANALYSIS.json": "4367930648a68c2f84a1fd8e011fa07d9f3bf111303079f3ec07688f7d5425fb",
    SEM / "RESIDUAL_V1_MODEL_RESOLVED_CONFOUND_ANALYSIS.json": "d0f2496ca7623050eb5519969abcf7c5e2d0e23e0c1961859c40cae4dcdb7021",
    SEM / "RESIDUAL_V1_MODEL_RESOLVED_CANDIDATE_DECISION.json": "ed0296fe6888e7c9fe864a2c6c7ab6cecbd4f490d6b7d650e442dafc0bd0976d",
    SEM / "MODEL_BASED_WSD_CANDIDATE_SPEC.json": "c861ff7fff11ae6a790531267229c18d6e6e0a171a9bf6c34cfb6f7e7b14498c",
    SEM / "MODEL_BASED_WSD_RESOLUTION.jsonl": "ed945989cf4947ac84633ba2c4aa10c1ba381d2396da0b573a844f83ec367a18",
    SEM / "MODEL_BASED_WSD_READINESS_PROJECTION.json": "c75834faf4a84d36e83246244e0aa7c6c7788c3a57cfdb7f77c7628a52023328",
    SEM / "CONSTITUENT_SENSE_RESOLUTION_V1_SPEC.json": "176e6219ddc3127814a25d39ad26e3571817f7ea8323d685e081d2e0fd867acb",
    SEM / "CONSTITUENT_SENSE_RESOLUTION_V1_REPLAY.jsonl": "a0c707ab55e02f627a698c33ddc0ca398e34aa0bafc19b13e72422bc26d97d0a",
    SEM / "MAGPIE_CANDIDATE_DECISION.json": "6eaa968b6260946998dba13e5c423f178d3349cdfe06e5ea401717f5a9bcdd0d",
    SEM / "KM_CANDIDATE_DECISION.json": "93a07e3c78b53a69965497410c34ddb52c2a5d3add3fb2f3cd3fd9ca84eb3d9f",
    HYP / "CLASSIFICATION_PROCEDURE.v2.json": "3f4071640d0c9f29cf56f53969a88ec25c635444b87765e77e1b9158470e5662",
    HYP / "DEVELOPMENT_EVIDENCE.json": "0e9b3c1af9dd573bf6e2034640e468e8ab9074e1e76c90cef1f39f68d607bc03",
    HYP / "WORDNET_STRUCTURAL_SOURCE_LIMITATION.json": "3c05cd9d6301fab0791e31b542d767cc757307cf3e304065362b479cc40e964a",
    ROOT / "events.jsonl": "96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c",
    ROOT / "ledger.json": "77e22433203879b252f7a9e309d2013d7550101d1c4a014b494d2c96df87d0e0",
    HYP / "HYPOTHESIS.json": "6500394d24543d1797eb9a2a05ba31868e035ffcbc7ae568f53116d4b016e62a",
}

OUTPUTS = (
    "RESIDUAL_THRESHOLD_V1_ACCEPTANCE.json",
    "RESIDUAL_THRESHOLD_V1_ARTIFACT_SCHEMA.json",
    "RESIDUAL_THRESHOLD_V1_CALIBRATION_CONTRACT.json",
    "RESIDUAL_THRESHOLD_V1_MEASUREMENT_CONTRACT.json",
    "RESIDUAL_THRESHOLD_V1_PREREGISTRATION.json",
    "RESIDUAL_THRESHOLD_V1_SELECTION_PROCEDURE.json",
    "RESIDUAL_THRESHOLD_V1_SURFACE_ISOLATION_POLICY.json",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, document: dict) -> str:
    if path.exists():
        raise SystemExit(f"REFUSE: {path.name} already exists")
    payload = (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, payload)
    finally:
        os.close(fd)
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    for path, expected in EXPECTED.items():
        got = _sha(path)
        if got != expected:
            raise SystemExit(f"REFUSE: {path.name} sha {got} != {expected}")
    sealed = {
        "constituent_resolution_replay_sha256": EXPECTED[SEM / "CONSTITUENT_SENSE_RESOLUTION_V1_REPLAY.jsonl"],
        "constituent_resolution_spec_sha256": EXPECTED[SEM / "CONSTITUENT_SENSE_RESOLUTION_V1_SPEC.json"],
        "development_evidence_sha256": EXPECTED[HYP / "DEVELOPMENT_EVIDENCE.json"],
        "events_sha256": EXPECTED[ROOT / "events.jsonl"],
        "integrated_resolution_sha256": EXPECTED[SEM / "INTEGRATED_CONSTITUENT_RESOLUTION_V1.jsonl"],
        "km_candidate_decision_sha256": EXPECTED[SEM / "KM_CANDIDATE_DECISION.json"],
        "ledger_sha256": EXPECTED[ROOT / "ledger.json"],
        "magpie_candidate_decision_sha256": EXPECTED[SEM / "MAGPIE_CANDIDATE_DECISION.json"],
        "model_based_wsd_projection_sha256": EXPECTED[SEM / "MODEL_BASED_WSD_READINESS_PROJECTION.json"],
        "model_based_wsd_resolution_sha256": EXPECTED[SEM / "MODEL_BASED_WSD_RESOLUTION.jsonl"],
        "model_based_wsd_spec_sha256": EXPECTED[SEM / "MODEL_BASED_WSD_CANDIDATE_SPEC.json"],
        "original_residual_scores_sha256": EXPECTED[SEM / "RESIDUAL_DEVELOPMENT_SCORES.jsonl"],
        "previous_tracker_sha256": EXPECTED[HYP / "HYPOTHESIS.json"],
        "procedure_module_sha256": _sha(MODULE),
        "procedure_v2_sha256": EXPECTED[HYP / "CLASSIFICATION_PROCEDURE.v2.json"],
        "replay_analysis_sha256": EXPECTED[SEM / "RESIDUAL_V1_MODEL_RESOLVED_DEVELOPMENT_ANALYSIS.json"],
        "replay_confound_sha256": EXPECTED[SEM / "RESIDUAL_V1_MODEL_RESOLVED_CONFOUND_ANALYSIS.json"],
        "replay_decision_sha256": EXPECTED[SEM / "RESIDUAL_V1_MODEL_RESOLVED_CANDIDATE_DECISION.json"],
        "replay_receipt_sha256": EXPECTED[SEM / "RESIDUAL_V1_MODEL_RESOLVED_REPLAY_RECEIPT.json"],
        "replay_scores_sha256": EXPECTED[SEM / "RESIDUAL_V1_MODEL_RESOLVED_REPLAY_SCORES.jsonl"],
        "residual_candidate_spec_sha256": EXPECTED[SEM / "RESIDUAL_CANDIDATE_SPEC.json"],
        "wordnet_limitation_sha256": EXPECTED[HYP / "WORDNET_STRUCTURAL_SOURCE_LIMITATION.json"],
    }
    first = documents(sealed, {})
    sibling = {}
    for name in OUTPUTS:
        if name.endswith("PREREGISTRATION.json"):
            continue
        sibling[name] = _write(SEM / name, first[name])
    second = documents(sealed, sibling)
    sibling["RESIDUAL_THRESHOLD_V1_PREREGISTRATION.json"] = _write(
        SEM / "RESIDUAL_THRESHOLD_V1_PREREGISTRATION.json",
        second["RESIDUAL_THRESHOLD_V1_PREREGISTRATION.json"],
    )
    tracker_path = HYP / "HYPOTHESIS.json"
    tracker = json.loads(tracker_path.read_text(encoding="utf-8"))
    if tracker["residual_model_resolved_state"] != "RESIDUAL_DEVELOPMENT_ANALYZED_V2":
        raise SystemExit("REFUSE: residual development state changed")
    if tracker["residual_model_resolved_candidate_status"] != "CANDIDATE_PROMISING":
        raise SystemExit("REFUSE: residual candidate status changed")
    if tracker["selected_source"] != "none" or tracker["admitted"] != 0 or tracker["settled"] != 0 or tracker["gold"] != 0:
        raise SystemExit("REFUSE: source or settlement state changed")
    tracker["previous_tracker_sha256"] = EXPECTED[tracker_path]
    tracker["residual_threshold_rule"] = RULE
    tracker["residual_threshold_state"] = TRACK_STATE
    tracker["residual_threshold_value"] = None
    tracker["residual_threshold"] = None
    tracker["residual_threshold_calibration_surface_drawn"] = False
    tracker["residual_threshold_measurement_surface_drawn"] = False
    tracker["residual_threshold_frozen"] = False
    tracker["residual_threshold_eligible"] = False
    tracker["development_rows_reusable_for_threshold_selection"] = False
    tracker["residual_threshold_json_schema_document"] = None
    tracker["next_legal_transition"] = "RESIDUAL_CALIBRATION_SURFACE_DRAW_AUTHORIZATION"
    tracker["next_transition_authorized"] = False
    tracker["residual_threshold_preregistration_sha256"] = sibling["RESIDUAL_THRESHOLD_V1_PREREGISTRATION.json"]
    tracker["residual_threshold_acceptance_sha256"] = sibling["RESIDUAL_THRESHOLD_V1_ACCEPTANCE.json"]
    tracker["residual_threshold_selection_procedure_sha256"] = sibling["RESIDUAL_THRESHOLD_V1_SELECTION_PROCEDURE.json"]
    tracker["residual_threshold_calibration_contract_sha256"] = sibling["RESIDUAL_THRESHOLD_V1_CALIBRATION_CONTRACT.json"]
    tracker["residual_threshold_measurement_contract_sha256"] = sibling["RESIDUAL_THRESHOLD_V1_MEASUREMENT_CONTRACT.json"]
    tracker["residual_threshold_artifact_schema_sha256"] = sibling["RESIDUAL_THRESHOLD_V1_ARTIFACT_SCHEMA.json"]
    tracker["residual_threshold_isolation_policy_sha256"] = sibling["RESIDUAL_THRESHOLD_V1_SURFACE_ISOLATION_POLICY.json"]
    payload = (json.dumps(tracker, indent=2, sort_keys=True) + "\n").encode("utf-8")
    tmp = tracker_path.with_suffix(".json.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, payload)
    finally:
        os.close(fd)
    os.replace(tmp, tracker_path)
    os.chmod(tracker_path, 0o600)
    if _sha(ROOT / "events.jsonl") != EXPECTED[ROOT / "events.jsonl"]:
        raise SystemExit("REFUSE: events changed")
    if _sha(ROOT / "ledger.json") != EXPECTED[ROOT / "ledger.json"]:
        raise SystemExit("REFUSE: ledger changed")
    for path, expected in EXPECTED.items():
        if path.name == "HYPOTHESIS.json":
            continue
        if _sha(path) != expected:
            raise SystemExit(f"REFUSE: {path.name} changed during freeze")
    print("tracker", hashlib.sha256(payload).hexdigest())
    for name in OUTPUTS:
        print(name, sibling[name])


if __name__ == "__main__":
    main()
