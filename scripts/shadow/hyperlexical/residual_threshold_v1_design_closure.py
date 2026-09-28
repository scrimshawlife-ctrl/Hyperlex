"""Close threshold v1 after the frozen calibration execution.

The execution outcome stays CALIBRATION_INSUFFICIENT_SUPPORT. This module
does not redraw, relabel, or select a threshold. It records why that
outcome cannot be repaired on the frozen 27-row surface.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from hyperlexical.residual_threshold_v1 import MIN_CALIBRATION_HIGH, MIN_CALIBRATION_SECONDARY
from hyperlexical.residual_threshold_v1_calibration import (
    ANALYSIS_PATH,
    ANCESTORS,
    DRAW_RECEIPT,
    EVENTS,
    FAILURE_PATH,
    ISOLATION_PATH,
    LABELS_PATH,
    LEDGER_FILE,
    MANIFEST_PATH,
    PREREGISTRATION,
    RESOLUTION_PATH,
    SCORE_RECEIPT,
    SCORES_PATH,
    SEARCH_PATH,
    SOURCE,
    TRACKER,
)

EXECUTION_ID = "RESIDUAL_THRESHOLD_V1_CALIBRATION_EXECUTION_001"
EXECUTION_STATE = "CALIBRATION_INSUFFICIENT_SUPPORT"
REVIEW_ID = "CALIBRATION_LABEL_AVAILABILITY_REVIEW"
LABEL_CAUSE = "NOVEL_SURFACE_UNLABELED"
FINDING = "CALIBRATION_DESIGN_SUPPORT_MISMATCH_CONFIRMED"
DISPOSITION = "CLOSED_CALIBRATION_DESIGN_INSUFFICIENT"
NEXT_TRANSITION = "THRESHOLD_V2_PREREGISTRATION_AUTHORIZATION"
RULE = "RUNE.SEMANTIC_COMPOSITIONALITY_THRESHOLD.v1"
DRAWN_ROWS = 27
RESIDUAL_READY = 6
CURRENT_TRACKER = "07b911497c4e95d1b251c7bb98f78224f804b857fd61dffd7c198eecdf21636f"

EXECUTION_SHA256 = {
    DRAW_RECEIPT: "7448adb8c9448c3737a7b7c2c9a3116ced23d2bab7e432d011bc41229c3ef283",
    MANIFEST_PATH: "ba561935cff5f9f0a36af0b8b24e4b69bce5fb2c61b5ea2236f0a664c56bcf5d",
    ISOLATION_PATH: "8743c864ed9e7152a5bccb5d6304b62aff8ffed5e894fb1d40ab270d696da9a5",
    RESOLUTION_PATH: "fde102faa317c2bdfd374bc2b2ddda680434bb1847f93b3991e1532da2764dc2",
    SCORES_PATH: "f775849b3bb8cdec2ac8eeeea0100e51853fefcebbd88d6b3b4efb33fa8a3895",
    SCORE_RECEIPT: "44cd2a9b57587d5330d830e5dda49fdbbc9b17d95553f030b3884feec46c9c29",
    LABELS_PATH: "b4c93faed22d3c294d46768a510eb9695c5159f2f84bfb8c4f7ab15b7f2332c2",
    ANALYSIS_PATH: "ac17d7e3c634cb5f984251e6a4f4090eecd0ff7e0d809947a48b689d454db625",
    SEARCH_PATH: "f92c5aded6822747811da2b18c796e59974de1e673db55b3f7a481a71be89a3c",
    FAILURE_PATH: "1d3f1f26609c1f1a47790d94730fba50e9f4d888dd8d7d89e6fa698a924fb3a8",
}

REVIEW_PATH = SOURCE / "RESIDUAL_THRESHOLD_V1_CALIBRATION_LABEL_AVAILABILITY_REVIEW.json"
CLOSURE_PATH = SOURCE / "RESIDUAL_THRESHOLD_V1_CALIBRATION_DESIGN_CLOSURE.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def refuse(message: str) -> None:
    raise SystemExit(message)


def combined_ready_floor(high_floor: int = MIN_CALIBRATION_HIGH, secondary_floor: int = MIN_CALIBRATION_SECONDARY) -> int:
    return high_floor + secondary_floor


def threshold_eligibility(ready_rows: int, high_floor: int = MIN_CALIBRATION_HIGH, secondary_floor: int = MIN_CALIBRATION_SECONDARY) -> str:
    """Ready-row count alone. Operator labels cannot raise this count."""
    if ready_rows < combined_ready_floor(high_floor, secondary_floor):
        return "mathematically_impossible"
    return "not_ruled_out_by_ready_count"


def _write_json(path: Path, payload: dict) -> str:
    if path.exists():
        refuse(f"refusing to rewrite {path.name}")
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _verify_frozen() -> None:
    for path, expected in PREREGISTRATION.items():
        if sha256(path) != expected:
            refuse(f"preregistration changed: {path.name}")
    for path, expected in ANCESTORS.items():
        if path == TRACKER:
            continue
        if sha256(path) != expected:
            refuse(f"sealed ancestor changed: {path.name}")
    for path, expected in EXECUTION_SHA256.items():
        if sha256(path) != expected:
            refuse(f"calibration execution artifact changed: {path.name}")
    if sha256(TRACKER) != CURRENT_TRACKER:
        refuse("tracker hash drifted before the design closure")
    if sha256(EVENTS) != ANCESTORS[EVENTS] or sha256(LEDGER_FILE) != ANCESTORS[LEDGER_FILE]:
        refuse("events or ledger changed")


def _observe() -> dict:
    manifest = [json.loads(line) for line in MANIFEST_PATH.read_text(encoding="utf-8").splitlines() if line]
    scores = [json.loads(line) for line in SCORES_PATH.read_text(encoding="utf-8").splitlines() if line]
    labels = [json.loads(line) for line in LABELS_PATH.read_text(encoding="utf-8").splitlines() if line]
    if len(manifest) != DRAWN_ROWS or len(scores) != DRAWN_ROWS or len(labels) != DRAWN_ROWS:
        refuse("frozen calibration row count drifted")
    ready = sum(1 for row in scores if row.get("score_status") == "SCORED")
    unknown = sum(1 for row in scores if row.get("score_status") != "SCORED")
    labeled = sum(1 for row in labels if row.get("operator_label_present") is True or row.get("operator_bucket") is not None)
    if ready != RESIDUAL_READY or unknown != DRAWN_ROWS - RESIDUAL_READY or labeled != 0:
        refuse("frozen ready or label counts drifted")
    failure = json.loads(FAILURE_PATH.read_text(encoding="utf-8"))
    if failure.get("failure_state") != EXECUTION_STATE or failure.get("threshold_value") is not None or failure.get("threshold_frozen") is not False:
        refuse("execution failure artifact was reinterpreted")
    return {"labeled": labeled, "ready": ready, "unknown": unknown}


def seal() -> dict:
    if REVIEW_PATH.exists() or CLOSURE_PATH.exists():
        refuse("design closure already exists")
    _verify_frozen()
    observed = _observe()
    eligibility = threshold_eligibility(observed["ready"])
    if eligibility != "mathematically_impossible":
        refuse("ready count does not rule out the support gate")
    review = {
        "admitted": 0,
        "blind_labeling_authorized": False,
        "cause": LABEL_CAUSE,
        "execution_failure_sha256": EXECUTION_SHA256[FAILURE_PATH],
        "execution_id": EXECUTION_ID,
        "execution_state_unchanged": EXECUTION_STATE,
        "gold": 0,
        "json_schema_document": None,
        "json_schema_exists": False,
        "manifest_rows": DRAWN_ROWS,
        "manifest_sha256": EXECUTION_SHA256[MANIFEST_PATH],
        "measurement_surface_drawn": False,
        "observed_existing_labels": f"{observed['labeled']}/{DRAWN_ROWS}",
        "operator_packet_created": False,
        "redraw_authorized": False,
        "relabel_can_rescue_support_gate": False,
        "relabel_existing_surface": "potentially_eligible",
        "review_id": REVIEW_ID,
        "schema": "hyperlex.residual_threshold_v1_calibration_label_availability_review.v1",
        "score_sha256": EXECUTION_SHA256[SCORES_PATH],
        "select_005_authorized": False,
        "selected_source": "none",
        "settled": 0,
        "threshold_frozen": False,
        "threshold_search_authorized": False,
        "threshold_value": None,
    }
    review_sha = _write_json(REVIEW_PATH, review)
    closure = {
        "admitted": 0,
        "disposition": DISPOSITION,
        "drawn_rows": DRAWN_ROWS,
        "execution_id": EXECUTION_ID,
        "execution_state": EXECUTION_STATE,
        "finding": FINDING,
        "gold": 0,
        "independent_of_operator_labels": True,
        "json_schema_document": None,
        "json_schema_exists": False,
        "label_availability_review_sha256": review_sha,
        "measurement_authorized": False,
        "measurement_surface_drawn": False,
        "minimum_ready_high": MIN_CALIBRATION_HIGH,
        "minimum_ready_secondary": MIN_CALIBRATION_SECONDARY,
        "minimum_required_target_ready_rows": combined_ready_floor(),
        "next_legal_transition": NEXT_TRANSITION,
        "next_transition_authorized": False,
        "observed_existing_labels": observed["labeled"],
        "observed_total_ready_rows": observed["ready"],
        "observed_unknown_rows": observed["unknown"],
        "preserved_execution_sha256": {path.name: digest for path, digest in sorted(EXECUTION_SHA256.items(), key=lambda item: item[0].name)},
        "redraw_authorized": False,
        "residual_ready": observed["ready"],
        "rule": RULE,
        "schema": "hyperlex.residual_threshold_v1_calibration_design_closure.v1",
        "select_005_authorized": False,
        "selected_source": "none",
        "settled": 0,
        "threshold_eligibility": eligibility,
        "threshold_frozen": False,
        "threshold_search_authorized": False,
        "threshold_value": None,
        "v2_preregistration_authorized": False,
    }
    closure_sha = _write_json(CLOSURE_PATH, closure)
    _update_tracker(review_sha, closure_sha)
    preserved = list(PREREGISTRATION.items()) + list(EXECUTION_SHA256.items())
    preserved.extend((path, digest) for path, digest in ANCESTORS.items() if path != TRACKER)
    for path, expected in preserved:
        if sha256(path) != expected:
            refuse(f"frozen file changed during closure: {path.name}")
    if sha256(EVENTS) != ANCESTORS[EVENTS] or sha256(LEDGER_FILE) != ANCESTORS[LEDGER_FILE]:
        refuse("events or ledger changed during closure")
    report = {
        "closure_sha256": closure_sha,
        "disposition": DISPOSITION,
        "execution_state": EXECUTION_STATE,
        "finding": FINDING,
        "review_sha256": review_sha,
        "threshold_eligibility": eligibility,
        "threshold_value": None,
        "tracker_sha256": sha256(TRACKER),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


def _update_tracker(review_sha: str, closure_sha: str) -> None:
    tracker = json.loads(TRACKER.read_text(encoding="utf-8"))
    if tracker.get("residual_threshold_state") != EXECUTION_STATE:
        refuse("tracker execution state is not the frozen failure")
    if tracker.get("residual_threshold_value") is not None or tracker.get("residual_threshold_frozen") is not False:
        refuse("tracker threshold is not null")
    prior = sha256(TRACKER)
    tracker["previous_tracker_sha256"] = prior
    tracker["residual_threshold_execution_id"] = EXECUTION_ID
    tracker["residual_threshold_v1_disposition"] = DISPOSITION
    tracker["residual_threshold_design_finding"] = FINDING
    tracker["residual_threshold_label_availability_cause"] = LABEL_CAUSE
    tracker["residual_threshold_existing_operator_labels"] = 0
    tracker["residual_threshold_manifest_rows"] = DRAWN_ROWS
    tracker["residual_threshold_residual_ready_rows"] = RESIDUAL_READY
    tracker["residual_threshold_redraw_authorized"] = False
    tracker["residual_threshold_blind_labeling_authorized"] = False
    tracker["residual_threshold_relabel_existing_surface"] = "potentially_eligible"
    tracker["residual_threshold_label_availability_review_sha256"] = review_sha
    tracker["residual_threshold_design_closure_sha256"] = closure_sha
    tracker["next_legal_transition"] = NEXT_TRANSITION
    tracker["next_transition_authorized"] = False
    tracker["selected_source"] = "none"
    tracker["select_authorized"] = False
    tracker["admitted"] = 0
    tracker["settled"] = 0
    tracker["gold"] = 0
    tracker["measurement_sample_drawn"] = False
    tracker["measurement_eligible"] = False
    tracker["residual_threshold_measurement_surface_drawn"] = False
    tracker["residual_threshold_json_schema_document"] = None
    text = json.dumps(tracker, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    TRACKER.write_text(text, encoding="utf-8")
    TRACKER.chmod(0o600)


def main() -> None:
    seal()


if __name__ == "__main__":
    main()
