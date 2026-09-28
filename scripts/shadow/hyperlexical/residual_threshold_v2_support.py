"""Join frozen v2 labels to frozen calibration readiness and apply the support gate.

Direction, confound review, and threshold search stay outside this pass.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from hyperlexical.residual_threshold_v2_calibration import (
    MIN_CALIBRATION_HIGH,
    MIN_CALIBRATION_SECONDARY,
    support_passed,
)
from hyperlexical.screen_eval import OPERATOR_BUCKETS

LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
SOURCE = LEDGER / "operator-review/HLX-EVAL-UNBIND-SEMANTIC-EVIDENCE-SOURCE-V1-001"
SENSE = LEDGER / "operator-review/HLX-EVAL-UNBIND-SENSE-SCREEN-V1-HYPOTHESIS-001"
EVENTS = LEDGER / "events.jsonl"
LEDGER_FILE = LEDGER / "ledger.json"
TRACKER = SENSE / "HYPOTHESIS.json"
SPEC = Path("/home/morpheus/Hyperlex/specs/007-hyperlexical-model/evaluation-reserve.md")

CALIBRATION_MANIFEST = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_MANIFEST.jsonl"
MEASUREMENT_MANIFEST = SOURCE / "RESIDUAL_THRESHOLD_V2_MEASUREMENT_MANIFEST.jsonl"
SCORES_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_SCORES.jsonl"
SCORE_RECEIPT = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_SCORE_RECEIPT.json"
RESOLUTION_RECEIPT = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_RESOLUTION_RECEIPT.json"
FAILURE_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_FAILURE.json"
LABELS_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_OPERATOR_LABELS.jsonl"
LABEL_RECEIPT_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_OPERATOR_LABELING_RECEIPT.json"
JOIN_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_SUPPORT_JOIN.jsonl"
RESULT_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_SUPPORT_REASSESSMENT.json"

AUTHORIZATION = "THRESHOLD_V2_CALIBRATION_SUPPORT_REASSESSMENT_AUTHORIZATION"
EXECUTION_ID = "THRESHOLD_V2_CALIBRATION_EXECUTION_001"
REASSESSMENT_ID = "THRESHOLD_V2_CALIBRATION_SUPPORT_REASSESSMENT_001"
PASSED = "SUPPORT_GATE_PASSED"
FAILED = "CALIBRATION_INSUFFICIENT_SUPPORT"
DIRECTION_NEXT = "THRESHOLD_V2_DIRECTION_EVALUATION_AUTHORIZATION"
CLASSES = ("HIGH", "SECONDARY", "REJECT", "QUARANTINE")

EXPECTED_CALIBRATION = "34bc70b93039fc6a5ba4bb58685e0fbfe6f91dd1f86a64fec8326a84013a6465"
EXPECTED_MEASUREMENT = "78ca09ab14912681d028e8b9b1c77a8daf1d0c8c81561434eb9b6ade45a753e5"
EXPECTED_FAILURE = "946a686d46b5a2fc47bb9968bf6e39c643e93c297d5a64de9e0fe88fc6eb33eb"
EXPECTED_SCORES = "01c758af570264c190f4af7805d43d734c9e9a36779f0e0b82675709f213e07c"
EXPECTED_SCORE_RECEIPT = "28ddb23bce8cfcf74b8046ee2cfd0908b5dddefa2a0c04562f9c2f8c912e88d5"
EXPECTED_RESOLUTION = "491b854bcf04d20624e560b63c01823b5634716ec266a4d3a7396d5514defd8d"
EXPECTED_RESOLUTION_RECEIPT = "461ed206ef3abba6b4a8ba79ed5de72305cbee95a61c96981923c89817c17d2d"
EXPECTED_LABELS = "f9901e334543dac2e9bf258208097cf4c9b48af9dc8b497ff42fe4f1f106e1fc"
EXPECTED_LABEL_RECEIPT = "4ce71e88c40cd617b9b6b502db48216c51e8cfa22ecea02347c9becc44c967fa"
EXPECTED_PACKET = "d9d986ec85a1ebea257859af8011758e9c84df270c9547f7b8bd0e34cec970fe"
EXPECTED_PACKET_RECEIPT = "0aff22b3406d9d954a54eabe080e83d2d4cb5e99df279605d9403e614b61dcf0"
EXPECTED_REVIEW = "8826b141468ec0dd674d2c7a253acfaa6e1d364ab5191506b424198419166da9"
EXPECTED_TRACKER = "b40bcb75f152c84d37fc96e834b6d0a23e1f4af562e8ec0225f452c3b000f77a"
EXPECTED_EVENTS = "96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c"
EXPECTED_LEDGER = "77e22433203879b252f7a9e309d2013d7550101d1c4a014b494d2c96df87d0e0"
EXPECTED_V1_FAILURE = "1d3f1f26609c1f1a47790d94730fba50e9f4d888dd8d7d89e6fa698a924fb3a8"
EXPECTED_V1_CLOSURE = "a5dbdb8ae497c25e711a81a880ad26ec7ef1ace917278c807497af5ec37e5002"
EXPECTED_EXECUTION_LABELS = "5cfeab84f16e5ca77d81bda8f1523a3aa20ae70a9828e1ff04a4d64a1930aa1d"
FROZEN_READY = 60
FROZEN_UNKNOWN = 140


def refuse(message: str) -> None:
    raise SystemExit(message)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def render_json(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def render_jsonl(rows: list[dict]) -> str:
    return "".join(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n" for row in rows)


def write_new(path: Path, text: str) -> str:
    if path.exists():
        refuse(f"{path.name} already exists")
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)
    return sha256_text(text)


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def sealed_hashes() -> dict[Path, str]:
    return {
        CALIBRATION_MANIFEST: EXPECTED_CALIBRATION,
        MEASUREMENT_MANIFEST: EXPECTED_MEASUREMENT,
        SCORES_PATH: EXPECTED_SCORES,
        SCORE_RECEIPT: EXPECTED_SCORE_RECEIPT,
        SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_RESOLUTION.jsonl": EXPECTED_RESOLUTION,
        RESOLUTION_RECEIPT: EXPECTED_RESOLUTION_RECEIPT,
        FAILURE_PATH: EXPECTED_FAILURE,
        LABELS_PATH: EXPECTED_LABELS,
        LABEL_RECEIPT_PATH: EXPECTED_LABEL_RECEIPT,
        SOURCE / "RESIDUAL_THRESHOLD_V2_BLIND_OPERATOR_PACKET.jsonl": EXPECTED_PACKET,
        SOURCE / "RESIDUAL_THRESHOLD_V2_BLIND_OPERATOR_PACKET_RECEIPT.json": EXPECTED_PACKET_RECEIPT,
        SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_LABEL_AVAILABILITY_REVIEW.json": EXPECTED_REVIEW,
        SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_LABELS.jsonl": EXPECTED_EXECUTION_LABELS,
        SOURCE / "RESIDUAL_THRESHOLD_V1_CALIBRATION_FAILURE.json": EXPECTED_V1_FAILURE,
        SOURCE / "RESIDUAL_THRESHOLD_V1_CALIBRATION_DESIGN_CLOSURE.json": EXPECTED_V1_CLOSURE,
        EVENTS: EXPECTED_EVENTS,
        LEDGER_FILE: EXPECTED_LEDGER,
    }


def assert_sealed() -> None:
    for path, expected in sealed_hashes().items():
        if sha256_file(path) != expected:
            refuse(f"sealed artifact drifted: {path.name}")


def join_rows(labels: list[dict], scores: list[dict]) -> list[dict]:
    """Attach frozen readiness and the frozen residual to each frozen label."""
    if len(labels) != len(scores):
        refuse("label count and score count differ")
    joined = []
    for label, score in zip(labels, scores):
        if label["row_id"] != score["row_id"]:
            refuse(f"row order differs at {label['row_id']}")
        if label["operator_label"] not in OPERATOR_BUCKETS:
            refuse(f"operator label left the frozen ontology for {label['row_id']}")
        if label["review_status"] != "REVIEWED":
            refuse(f"review status changed for {label['row_id']}")
        status = score["score_status"]
        if status == "SCORED":
            if score.get("surface") != label["surface"] or score.get("pos") != label["pos"]:
                refuse(f"scored identity differs for {label['row_id']}")
            if score.get("synset") != label["pwn30_synset"]:
                refuse(f"scored synset differs for {label['row_id']}")
            residual = score.get("residual_score")
            if not isinstance(residual, str) or not residual:
                refuse(f"scored row is missing its frozen residual for {label['row_id']}")
            readiness = "RESIDUAL_READY"
            abstention = None
        elif status == "UNKNOWN":
            residual = None
            readiness = "UNKNOWN"
            abstention = score.get("abstention_reason")
            if not isinstance(abstention, str) or not abstention:
                refuse(f"unknown row is missing its frozen abstention for {label['row_id']}")
        else:
            refuse(f"score status {status} is outside the frozen vocabulary")
        joined.append({
            "abstention_reason": abstention,
            "calibration_row_id": label["calibration_row_id"],
            "operator_evidence": label["operator_evidence"],
            "operator_label": label["operator_label"],
            "operator_note": label["operator_note"],
            "pos": label["pos"],
            "pwn30_synset": label["pwn30_synset"],
            "readiness": readiness,
            "residual_score": residual,
            "review_status": label["review_status"],
            "row_id": label["row_id"],
            "schema": "hyperlex.residual_threshold_v2_calibration_support_join_row.v1",
            "score_status": status,
            "surface": label["surface"],
        })
    return joined


def _blank_counts() -> dict[str, int]:
    return {name: 0 for name in CLASSES}


def support_inventory(rows: list[dict]) -> dict:
    """Count ready and unknown rows by the frozen operator label.

    The numeric residual is not an input. UNRESOLVED stays outside the four
    comparison classes and does not fill the support floors.
    """
    ready = _blank_counts()
    unknown = _blank_counts()
    unresolved = {"RESIDUAL_READY": 0, "UNKNOWN": 0}
    inventory = {name: 0 for name in OPERATOR_BUCKETS}
    for row in rows:
        label = row["operator_label"]
        readiness = row["readiness"]
        inventory[label] += 1
        if readiness not in {"RESIDUAL_READY", "UNKNOWN"}:
            refuse(f"readiness {readiness} is outside the frozen vocabulary")
        if label == "UNRESOLVED":
            unresolved[readiness] += 1
            continue
        if label not in ready:
            refuse(f"operator label {label} is outside the support classes")
        target = ready if readiness == "RESIDUAL_READY" else unknown
        target[label] += 1
    ready_rows = sum(ready.values()) + unresolved["RESIDUAL_READY"]
    unknown_rows = sum(unknown.values()) + unresolved["UNKNOWN"]
    return {
        "operator_label_inventory": inventory,
        "ready": ready,
        "ready_rows": ready_rows,
        "unknown_by_class": unknown,
        "unknown_rows": unknown_rows,
        "unresolved_ready": unresolved["RESIDUAL_READY"],
        "unresolved_unknown": unresolved["UNKNOWN"],
    }


def gate_state(inventory: dict) -> str:
    if inventory["ready_rows"] != FROZEN_READY or inventory["unknown_rows"] != FROZEN_UNKNOWN:
        refuse("ready split differs from the frozen 60/140 calibration scores")
    passed = support_passed(inventory["ready"]["HIGH"], inventory["ready"]["SECONDARY"])
    return PASSED if passed else FAILED


def reassess() -> dict:
    assert_sealed()
    if sha256_file(TRACKER) != EXPECTED_TRACKER:
        refuse("tracker drifted before the support reassessment")
    if MIN_CALIBRATION_HIGH != 12 or MIN_CALIBRATION_SECONDARY != 8:
        refuse("support floors drifted")
    labels = load_jsonl(LABELS_PATH)
    scores = load_jsonl(SCORES_PATH)
    manifest_ids = [row["row_id"] for row in load_jsonl(CALIBRATION_MANIFEST)]
    measurement_ids = {row["row_id"] for row in load_jsonl(MEASUREMENT_MANIFEST)}
    if [row["row_id"] for row in labels] != manifest_ids:
        refuse("labels are not the frozen calibration manifest")
    if [row["row_id"] for row in scores] != manifest_ids:
        refuse("scores are not the frozen calibration manifest")
    if set(manifest_ids) & measurement_ids:
        refuse("measurement row entered the calibration join")
    failure = json.loads(FAILURE_PATH.read_text(encoding="utf-8"))
    observed = failure["observed_support"]
    if observed["unlabeled_scored"] != FROZEN_READY or observed["unlabeled_unknown"] != FROZEN_UNKNOWN:
        refuse("execution failure split drifted")
    receipt = json.loads(RESOLUTION_RECEIPT.read_text(encoding="utf-8"))
    if receipt["residual_ready_rows"] != FROZEN_READY or receipt["unknown_rows"] != FROZEN_UNKNOWN:
        refuse("resolution receipt split drifted")
    label_receipt = json.loads(LABEL_RECEIPT_PATH.read_text(encoding="utf-8"))
    if label_receipt["labeling_state"] != "LABELS_FROZEN" or label_receipt["joined_to_readiness"] is not False:
        refuse("label receipt is not the pre-join freeze")
    joined = join_rows(labels, scores)
    if [row["operator_label"] for row in joined] != [row["operator_label"] for row in labels]:
        refuse("join relabeled a row")
    inventory = support_inventory(joined)
    if inventory["operator_label_inventory"] != label_receipt["operator_label_inventory"]:
        refuse("label inventory changed during the join")
    state = gate_state(inventory)
    join_sha = write_new(JOIN_PATH, render_jsonl(joined))
    reread = support_inventory(load_jsonl(JOIN_PATH))
    if reread != inventory or gate_state(reread) != state:
        refuse("frozen join does not reproduce the support gate")
    result = {
        "authorization": AUTHORIZATION,
        "confound_analysis_performed": False,
        "direction_analysis_performed": False,
        "execution_id_unchanged": EXECUTION_ID,
        "execution_state_unchanged": FAILED,
        "floors_changed": False,
        "join_sha256": join_sha,
        "json_schema_document": None,
        "json_schema_exists": False,
        "label_sha256": EXPECTED_LABELS,
        "measurement_touched": False,
        "minimum_ready_high": MIN_CALIBRATION_HIGH,
        "minimum_ready_secondary": MIN_CALIBRATION_SECONDARY,
        "ready": inventory["ready"],
        "ready_rows": inventory["ready_rows"],
        "ready_split_unchanged": True,
        "reassessment_id": REASSESSMENT_ID,
        "redraw_authorized": False,
        "resolution_recomputed": False,
        "residual_recomputed": False,
        "rows_relabeled": False,
        "runtime_integration": False,
        "schema": "hyperlex.residual_threshold_v2_calibration_support_reassessment.v1",
        "score_sha256": EXPECTED_SCORES,
        "select_005_authorized": False,
        "selected_source": "none",
        "state": state,
        "support_gate_passed": state == PASSED,
        "threshold_candidates_inspected": False,
        "threshold_frozen": False,
        "threshold_search_performed": False,
        "threshold_value": None,
        "unknown_by_class": inventory["unknown_by_class"],
        "unknown_rows": inventory["unknown_rows"],
        "unresolved_ready": inventory["unresolved_ready"],
        "unresolved_unknown": inventory["unresolved_unknown"],
    }
    result_sha = write_new(RESULT_PATH, render_json(result))
    tracker_sha = update_tracker(state, join_sha, result_sha)
    assert_sealed()
    append_spec(state, inventory, join_sha, result_sha, tracker_sha)
    return {
        "join_sha256": join_sha,
        "ready": inventory["ready"],
        "result_sha256": result_sha,
        "state": state,
        "tracker_sha256": tracker_sha,
        "unknown_by_class": inventory["unknown_by_class"],
    }


def update_tracker(state: str, join_sha: str, result_sha: str) -> str:
    if sha256_file(TRACKER) != EXPECTED_TRACKER:
        refuse("tracker drifted before the support update")
    tracker = json.loads(TRACKER.read_text(encoding="utf-8"))
    if tracker.get("residual_threshold_v2_state") != FAILED:
        refuse("execution state drifted")
    if tracker.get("residual_threshold_v2_blind_operator_labeling_state") != "LABELS_FROZEN":
        refuse("label freeze drifted")
    if tracker.get("residual_threshold_v1_disposition") != "CLOSED_CALIBRATION_DESIGN_INSUFFICIENT":
        refuse("v1 disposition drifted")
    if tracker.get("residual_threshold_v2_value") is not None or tracker.get("residual_threshold_v2_frozen") is not False:
        refuse("threshold drifted")
    tracker["previous_tracker_sha256"] = EXPECTED_TRACKER
    tracker["residual_threshold_v2_calibration_execution_state"] = FAILED
    tracker["residual_threshold_v2_support_reassessment_id"] = REASSESSMENT_ID
    tracker["residual_threshold_v2_support_reassessment_state"] = state
    tracker["residual_threshold_v2_support_join_sha256"] = join_sha
    tracker["residual_threshold_v2_support_reassessment_sha256"] = result_sha
    tracker["residual_threshold_v2_state"] = state
    tracker["residual_threshold_v2_value"] = None
    tracker["residual_threshold_v2_frozen"] = False
    tracker["residual_threshold_v2_redraw_authorized"] = False
    tracker["residual_threshold_v2_measurement_state"] = "SEALED"
    tracker["residual_threshold_v2_measurement_resolved"] = False
    tracker["residual_threshold_v2_measurement_scored"] = False
    tracker["residual_threshold_v2_measurement_labeled"] = False
    tracker["measurement_eligible"] = False
    tracker["selected_source"] = "none"
    tracker["select_authorized"] = False
    tracker["admitted"] = 0
    tracker["settled"] = 0
    tracker["gold"] = 0
    if state == PASSED:
        tracker["next_legal_transition"] = DIRECTION_NEXT
        tracker["residual_threshold_v2_disposition"] = None
    else:
        tracker["next_legal_transition"] = "NONE"
        tracker["residual_threshold_v2_disposition"] = "CLOSED_CALIBRATION_INSUFFICIENT_SUPPORT"
    tracker["next_transition_authorized"] = False
    if tracker["residual_threshold_v2_calibration_execution_state"] != FAILED:
        refuse("reassessment overwrote execution 001")
    text = render_json(tracker)
    TRACKER.write_text(text, encoding="utf-8")
    TRACKER.chmod(0o600)
    return sha256_file(TRACKER)


def append_spec(state: str, inventory: dict, join_sha: str, result_sha: str, tracker_sha: str) -> None:
    marker = "## Threshold v2 support reassessment — 2026-09-28"
    text = SPEC.read_text(encoding="utf-8")
    if marker in text:
        refuse("spec section already exists")
    if not text.endswith("\n"):
        text += "\n"
    ready = inventory["ready"]
    unknown = inventory["unknown_by_class"]
    if state == PASSED:
        outcome = (
            f"The support gate passes. Ready HIGH is {ready['HIGH']} and ready SECONDARY is "
            f"{ready['SECONDARY']}. The floors remain 12 and 8. "
            f"The next named transition is `{DIRECTION_NEXT}`. This pass does not authorize it."
        )
    else:
        outcome = (
            f"The support gate fails. Ready HIGH is {ready['HIGH']} and ready SECONDARY is "
            f"{ready['SECONDARY']}. The floors remain 12 and 8. v2 calibration closes as "
            "`CALIBRATION_INSUFFICIENT_SUPPORT` without a redraw. The threshold value stays null."
        )
    section = (
        f"{marker}\n"
        "\n"
        f"`{AUTHORIZATION}` joins the frozen operator labels to the frozen calibration "
        "readiness and residual scores. It does not relabel a row, recompute resolution, "
        "recompute a residual, or change the 60/140 ready split. "
        f"`{EXECUTION_ID}` stays `CALIBRATION_INSUFFICIENT_SUPPORT` and stays sealed, because "
        "that execution had no operator labels. This reassessment is the successor join.\n"
        "\n"
        f"Ready rows are HIGH {ready['HIGH']}, SECONDARY {ready['SECONDARY']}, "
        f"REJECT {ready['REJECT']}, and QUARANTINE {ready['QUARANTINE']}. "
        f"Unknown rows are HIGH {unknown['HIGH']}, SECONDARY {unknown['SECONDARY']}, "
        f"REJECT {unknown['REJECT']}, and QUARANTINE {unknown['QUARANTINE']}. "
        f"Unresolved ready rows are {inventory['unresolved_ready']} and unresolved unknown rows "
        f"are {inventory['unresolved_unknown']}. The three frozen QUARANTINE labels stay in place. "
        f"The raw label inventory remains HIGH {inventory['operator_label_inventory']['HIGH']}, "
        f"SECONDARY {inventory['operator_label_inventory']['SECONDARY']}, "
        f"REJECT {inventory['operator_label_inventory']['REJECT']}, "
        f"QUARANTINE {inventory['operator_label_inventory']['QUARANTINE']}, "
        f"and UNRESOLVED {inventory['operator_label_inventory']['UNRESOLVED']}.\n"
        "\n"
        f"{outcome} Direction analysis, confound review, and threshold search were not run. "
        f"Join sha256 `{join_sha}`. Support reassessment sha256 `{result_sha}`. "
        f"Tracker sha256 `{tracker_sha}`.\n"
        "\n"
        "The threshold stays unfrozen. Measurement stays `SEALED`, unresolved, unscored, and "
        f"unlabeled. Measurement sha256 remains `{EXPECTED_MEASUREMENT}`. Score sha256 remains "
        f"`{EXPECTED_SCORES}`. Failure sha256 remains `{EXPECTED_FAILURE}`. Label sha256 remains "
        f"`{EXPECTED_LABELS}`. `selected_source` remains `none`. Nothing was integrated into runtime. "
        "SELECT-005 remains unauthorized. Admitted, settled, and gold stay 0. "
        f"Events sha256 remains `{EXPECTED_EVENTS}`. The ledger was not appended. "
        "No JSON Schema document exists for this family. v1 remains "
        "`CLOSED_CALIBRATION_DESIGN_INSUFFICIENT`.\n"
    )
    SPEC.write_text(text + section, encoding="utf-8")


def main() -> None:
    if len(sys.argv) == 2 and sys.argv[1] == "--reassess":
        print(json.dumps(reassess(), sort_keys=True))
        return
    refuse("usage: residual_threshold_v2_support.py --reassess")


if __name__ == "__main__":
    main()
