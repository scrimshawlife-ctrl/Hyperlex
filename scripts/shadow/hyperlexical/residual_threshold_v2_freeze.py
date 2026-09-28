"""Write the v2 preregistration once. v1 files are read and then rechecked."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from hyperlexical.residual_threshold_v1_calibration import ANCESTORS, PREREGISTRATION, SOURCE, TRACKER
from hyperlexical.residual_threshold_v1_design_closure import CLOSURE_PATH, EXECUTION_SHA256, REVIEW_PATH
from hyperlexical.residual_threshold_v2 import NEXT_TRANSITION, companion_documents, preregistration

CURRENT_TRACKER = "a2a71c5da91d194337b2cc0de55692b712d5568694debf5350ede5ea0554d6c2"
CLOSURE_SHA = "a5dbdb8ae497c25e711a81a880ad26ec7ef1ace917278c807497af5ec37e5002"
REVIEW_SHA = "3a6c967c3542096714e25b59544bd68d89d7a9bc28ee253dec1b9f224b5a0484"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def refuse(message: str) -> None:
    raise SystemExit(message)


def _write_json(path: Path, payload: dict) -> str:
    if path.exists():
        refuse(f"refusing to rewrite {path.name}")
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _expect(path: Path, expected: str) -> None:
    if sha256(path) != expected:
        refuse(f"sealed file changed: {path.name}")


def verify_v1(*, include_tracker: bool = True) -> None:
    for path, expected in PREREGISTRATION.items():
        _expect(path, expected)
    for path, expected in EXECUTION_SHA256.items():
        _expect(path, expected)
    for path, expected in ANCESTORS.items():
        if path == TRACKER:
            continue
        _expect(path, expected)
    _expect(CLOSURE_PATH, CLOSURE_SHA)
    _expect(REVIEW_PATH, REVIEW_SHA)
    if include_tracker:
        _expect(TRACKER, CURRENT_TRACKER)


def freeze() -> dict:
    verify_v1()
    companions = companion_documents()
    for name in companions:
        if (SOURCE / name).exists():
            refuse(f"v2 artifact already exists: {name}")
    if (SOURCE / "RESIDUAL_THRESHOLD_V2_PREREGISTRATION.json").exists():
        refuse("v2 preregistration already exists")
    sibling = {}
    for name, payload in companions.items():
        sibling[name] = _write_json(SOURCE / name, payload)
    prereg_path = SOURCE / "RESIDUAL_THRESHOLD_V2_PREREGISTRATION.json"
    prereg_sha = _write_json(prereg_path, preregistration(sibling))
    tracker = json.loads(TRACKER.read_text(encoding="utf-8"))
    if tracker.get("residual_threshold_state") != "CALIBRATION_INSUFFICIENT_SUPPORT":
        refuse("v1 execution state drifted")
    if tracker.get("residual_threshold_v1_disposition") != "CLOSED_CALIBRATION_DESIGN_INSUFFICIENT":
        refuse("v1 disposition drifted")
    if tracker.get("residual_threshold_value") is not None or tracker.get("residual_threshold_frozen") is not False:
        refuse("v1 threshold drifted")
    tracker["previous_tracker_sha256"] = sha256(TRACKER)
    tracker["residual_threshold_v2_rule"] = "RUNE.SEMANTIC_COMPOSITIONALITY_THRESHOLD.v2"
    tracker["residual_threshold_v2_state"] = "THRESHOLD_PROCEDURE_PREREGISTERED"
    tracker["residual_threshold_v2_value"] = None
    tracker["residual_threshold_v2_frozen"] = False
    tracker["residual_threshold_v2_calibration_draw_size"] = 200
    tracker["residual_threshold_v2_measurement_draw_size"] = 200
    tracker["residual_threshold_v2_calibration_surface_drawn"] = False
    tracker["residual_threshold_v2_measurement_surface_drawn"] = False
    tracker["residual_threshold_v2_redraw_authorized"] = False
    tracker["residual_threshold_v2_preregistration_sha256"] = prereg_sha
    for name, digest in sibling.items():
        key = "residual_threshold_v2_" + name.removeprefix("RESIDUAL_THRESHOLD_V2_").removesuffix(".json").lower() + "_sha256"
        tracker[key] = digest
    tracker["next_legal_transition"] = NEXT_TRANSITION
    tracker["next_transition_authorized"] = False
    tracker["selected_source"] = "none"
    tracker["select_authorized"] = False
    tracker["admitted"] = 0
    tracker["settled"] = 0
    tracker["gold"] = 0
    text = json.dumps(tracker, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    TRACKER.write_text(text, encoding="utf-8")
    TRACKER.chmod(0o600)
    verify_v1(include_tracker=False)
    if tracker["residual_threshold_state"] != "CALIBRATION_INSUFFICIENT_SUPPORT":
        refuse("v1 execution state was overwritten")
    report = {
        "next_legal_transition": NEXT_TRANSITION,
        "next_transition_authorized": False,
        "preregistration_sha256": prereg_sha,
        "sibling_sha256": sibling,
        "tracker_sha256": sha256(TRACKER),
        "v1_execution_state": "CALIBRATION_INSUFFICIENT_SUPPORT",
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


def main() -> None:
    freeze()


if __name__ == "__main__":
    main()
