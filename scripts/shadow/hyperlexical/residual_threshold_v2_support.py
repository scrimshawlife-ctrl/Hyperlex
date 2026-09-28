"""Join frozen v2 labels to frozen calibration readiness and apply the support gate.

Direction, confound review, and threshold search stay outside this pass.
The join records only the frozen identity, label, row resolution status, and residual.
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
RESOLUTION_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_RESOLUTION.jsonl"
RESOLUTION_RECEIPT = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_RESOLUTION_RECEIPT.json"
FAILURE_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_FAILURE.json"
LABELS_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_OPERATOR_LABELS.jsonl"
LABEL_RECEIPT_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_OPERATOR_LABELING_RECEIPT.json"
JOIN_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_SUPPORT_JOIN.jsonl"
JOIN_RECEIPT_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_SUPPORT_JOIN_RECEIPT.json"
RESULT_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_SUPPORT_REASSESSMENT.json"

AUTHORIZATION = "THRESHOLD_V2_CALIBRATION_SUPPORT_REASSESSMENT_AUTHORIZATION"
EXECUTION_ID = "THRESHOLD_V2_CALIBRATION_EXECUTION_001"
REASSESSMENT_ID = "THRESHOLD_V2_CALIBRATION_SUPPORT_REASSESSMENT_001"
PASSED = "SUPPORT_GATE_PASSED"
FAILED = "CALIBRATION_INSUFFICIENT_SUPPORT"
INTEGRITY_FAILURE = "SUPPORT_REASSESSMENT_INTEGRITY_FAILURE"
DIRECTION_NEXT = "THRESHOLD_V2_DIRECTION_EVALUATION_AUTHORIZATION"
CLASSES = ("HIGH", "SECONDARY", "REJECT", "QUARANTINE")
JOIN_KEYS = frozenset({
    "calibration_row_id",
    "operator_label",
    "pos",
    "pwn30_synset",
    "residual_score",
    "row_id",
    "row_resolution_status",
    "surface",
})

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
EXPECTED_TRACKER = "ae73f1b6926cf86a2add088ad99c200f0341aa28c7ecb8b67e6a824cf1ee01d5"
EXPECTED_EVENTS = "96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c"
EXPECTED_LEDGER = "77e22433203879b252f7a9e309d2013d7550101d1c4a014b494d2c96df87d0e0"
EXPECTED_V1_FAILURE = "1d3f1f26609c1f1a47790d94730fba50e9f4d888dd8d7d89e6fa698a924fb3a8"
EXPECTED_V1_CLOSURE = "a5dbdb8ae497c25e711a81a880ad26ec7ef1ace917278c807497af5ec37e5002"
EXPECTED_EXECUTION_LABELS = "5cfeab84f16e5ca77d81bda8f1523a3aa20ae70a9828e1ff04a4d64a1930aa1d"
PRIOR_JOIN = "19457ab6ea99ee8feefe5eb1e62da97f348c1c31a26519f3e01da0cdef8b879a"
PRIOR_RESULT = "dafd4c8242dc08eaad21ae85cacd508eaa672608d3391eb7f828c391ec2a4780"
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
        RESOLUTION_PATH: EXPECTED_RESOLUTION,
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


def assert_measurement_sealed() -> None:
    if sha256_file(MEASUREMENT_MANIFEST) != EXPECTED_MEASUREMENT:
        refuse("measurement manifest drifted")
    for name in (
        "RESIDUAL_THRESHOLD_V2_MEASUREMENT_RESOLUTION.jsonl",
        "RESIDUAL_THRESHOLD_V2_MEASUREMENT_SCORES.jsonl",
        "RESIDUAL_THRESHOLD_V2_MEASUREMENT_LABELS.jsonl",
        "RESIDUAL_THRESHOLD_V2_MEASUREMENT_PREDICTIONS.jsonl",
    ):
        if (SOURCE / name).exists():
            refuse(f"measurement artifact exists: {name}")


def join_rows(manifest: list[dict], labels: list[dict], parents: list[dict], scores: list[dict]) -> list[dict]:
    """Copy frozen identity, label, parent resolution status, and residual."""
    if not (len(manifest) == len(labels) == len(parents) == len(scores)):
        refuse("frozen row counts differ")
    joined = []
    for source, label, parent, score in zip(manifest, labels, parents, scores):
        row_id = source["row_id"]
        if label["row_id"] != row_id or parent["row_id"] != row_id or score["row_id"] != row_id:
            refuse(f"row_id join failed for {row_id}")
        if source["normalized_text_sha256"] != row_id:
            refuse(f"normalized text hash is not the row id for {row_id}")
        if label["calibration_row_id"] != source["global_draw_order"]:
            refuse(f"calibration row id differs for {row_id}")
        if label["pwn30_synset"] != source["pwn30_synset"] or parent["synset"] != source["pwn30_synset"]:
            refuse(f"synset differs for {row_id}")
        if label["surface"] != source["surface"] or parent["surface"] != source["surface"]:
            refuse(f"surface differs for {row_id}")
        if label["pos"] != source["pos"] or parent["pos"] != source["pos"]:
            refuse(f"pos differs for {row_id}")
        if label["operator_label"] not in OPERATOR_BUCKETS:
            refuse(f"operator label left the frozen ontology for {row_id}")
        status = parent["row_resolution_status"]
        if status == "RESIDUAL_READY":
            if score.get("score_status") != "SCORED" or not isinstance(score.get("residual_score"), str):
                refuse(f"ready row lacks its frozen residual for {row_id}")
            residual = score["residual_score"]
        elif status == "UNKNOWN":
            if score.get("score_status") != "UNKNOWN" or "residual_score" in score:
                refuse(f"unknown row carries a residual for {row_id}")
            residual = None
        else:
            refuse(f"row resolution status {status} is outside the frozen vocabulary")
        joined.append({
            "calibration_row_id": label["calibration_row_id"],
            "operator_label": label["operator_label"],
            "pos": source["pos"],
            "pwn30_synset": source["pwn30_synset"],
            "residual_score": residual,
            "row_id": row_id,
            "row_resolution_status": status,
            "surface": source["surface"],
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
        if set(row) != JOIN_KEYS:
            refuse("joined row left the authorized field set")
        label = row["operator_label"]
        status = row["row_resolution_status"]
        inventory[label] += 1
        if status not in {"RESIDUAL_READY", "UNKNOWN"}:
            refuse(f"row resolution status {status} is outside the frozen vocabulary")
        if label == "UNRESOLVED":
            unresolved[status] += 1
            continue
        if label not in ready:
            refuse(f"operator label {label} is outside the support classes")
        target = ready if status == "RESIDUAL_READY" else unknown
        target[label] += 1
    ready_rows = sum(ready.values()) + unresolved["RESIDUAL_READY"]
    unknown_rows = sum(unknown.values()) + unresolved["UNKNOWN"]
    return {
        "operator_label_inventory": inventory,
        "ready": ready,
        "ready_rows": ready_rows,
        "ready_unresolved": unresolved["RESIDUAL_READY"],
        "unknown_by_class": unknown,
        "unknown_rows": unknown_rows,
        "unknown_unresolved": unresolved["UNKNOWN"],
    }


def gate_state(inventory: dict) -> str:
    if inventory["ready_rows"] != FROZEN_READY or inventory["unknown_rows"] != FROZEN_UNKNOWN:
        refuse("ready split differs from the frozen 60/140 calibration scores")
    if inventory["ready_rows"] + inventory["unknown_rows"] != 200:
        refuse("joined rows are not 200")
    passed = support_passed(inventory["ready"]["HIGH"], inventory["ready"]["SECONDARY"])
    return PASSED if passed else FAILED


def _retire_prior(path: Path, expected: str) -> None:
    if not path.exists():
        return
    found = sha256_file(path)
    if found != expected:
        refuse(f"{path.name} is not the prior support artifact")
    path.unlink()


def _integrity_failure(reason: str) -> dict:
    payload = {
        "authorization": AUTHORIZATION,
        "json_schema_document": None,
        "json_schema_exists": False,
        "measurement_touched": False,
        "reason": reason,
        "schema": "hyperlex.residual_threshold_v2_support_reassessment_integrity_failure.v1",
        "state": INTEGRITY_FAILURE,
    }
    digest = write_new(SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_SUPPORT_INTEGRITY_FAILURE.json", render_json(payload))
    return {"integrity_sha256": digest, "state": INTEGRITY_FAILURE}


def reassess() -> dict:
    assert_sealed()
    assert_measurement_sealed()
    if sha256_file(TRACKER) != EXPECTED_TRACKER:
        refuse("tracker drifted before the support reassessment")
    if MIN_CALIBRATION_HIGH != 12 or MIN_CALIBRATION_SECONDARY != 8:
        refuse("support floors drifted")
    manifest = load_jsonl(CALIBRATION_MANIFEST)
    labels = load_jsonl(LABELS_PATH)
    scores = load_jsonl(SCORES_PATH)
    constituents = load_jsonl(RESOLUTION_PATH)
    resolution = json.loads(RESOLUTION_RECEIPT.read_text(encoding="utf-8"))
    parents = resolution["parent_rows"]
    if len(manifest) != 200 or len(labels) != 200 or len(parents) != 200 or len(scores) != 200:
        return _integrity_failure("frozen row count is not 200")
    manifest_ids = [row["row_id"] for row in manifest]
    if [row["row_id"] for row in labels] != manifest_ids:
        return _integrity_failure("label identity set differs from the manifest")
    if [row["row_id"] for row in parents] != manifest_ids:
        return _integrity_failure("resolution parent identity set differs from the manifest")
    if [row["row_id"] for row in scores] != manifest_ids:
        return _integrity_failure("score identity set differs from the manifest")
    constituent_parents = {row["parent_row_id"] for row in constituents}
    if not constituent_parents <= set(manifest_ids):
        return _integrity_failure("resolution constituent names a row outside the manifest")
    failure = json.loads(FAILURE_PATH.read_text(encoding="utf-8"))
    observed = failure["observed_support"]
    if observed["unlabeled_scored"] != FROZEN_READY or observed["unlabeled_unknown"] != FROZEN_UNKNOWN:
        refuse("execution failure split drifted")
    if resolution["residual_ready_rows"] != FROZEN_READY or resolution["unknown_rows"] != FROZEN_UNKNOWN:
        refuse("resolution receipt split drifted")
    label_receipt = json.loads(LABEL_RECEIPT_PATH.read_text(encoding="utf-8"))
    if label_receipt["labeling_state"] != "LABELS_FROZEN" or label_receipt["joined_to_readiness"] is not False:
        refuse("label receipt is not the pre-join freeze")
    if label_receipt["label_sha256"] != EXPECTED_LABELS:
        refuse("label receipt does not bind the frozen labels")
    joined = join_rows(manifest, labels, parents, scores)
    if [row["operator_label"] for row in joined] != [row["operator_label"] for row in labels]:
        refuse("join relabeled a row")
    inventory = support_inventory(joined)
    if inventory["operator_label_inventory"] != label_receipt["operator_label_inventory"]:
        refuse("label inventory changed during the join")
    if RESULT_PATH.exists():
        prior = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
        if prior.get("ready") != inventory["ready"] or prior.get("unknown_by_class") != inventory["unknown_by_class"]:
            refuse("compliant join changed the frozen support counts")
        if prior.get("state") != gate_state(inventory):
            refuse("compliant join changed the support gate")
    state = gate_state(inventory)
    _retire_prior(JOIN_PATH, PRIOR_JOIN)
    _retire_prior(RESULT_PATH, PRIOR_RESULT)
    join_sha = write_new(JOIN_PATH, render_jsonl(joined))
    reread = support_inventory(load_jsonl(JOIN_PATH))
    if reread != inventory or gate_state(reread) != state:
        refuse("frozen join does not reproduce the support gate")
    join_receipt = {
        "authorization": AUTHORIZATION,
        "join_identity": "row_id",
        "join_sha256": join_sha,
        "joined_rows": 200,
        "json_schema_document": None,
        "json_schema_exists": False,
        "labels_modified": False,
        "manifest_hash": EXPECTED_CALIBRATION,
        "measurement_touched": False,
        "operator_label_hash": EXPECTED_LABELS,
        "resolution_hash": EXPECTED_RESOLUTION,
        "resolution_parent_rows": 200,
        "resolution_recomputed": False,
        "schema": "hyperlex.residual_threshold_v2_calibration_support_join_receipt.v1",
        "score_hash": EXPECTED_SCORES,
        "scores_recomputed": False,
    }
    receipt_sha = write_new(JOIN_RECEIPT_PATH, render_json(join_receipt))
    result = {
        "authorization": AUTHORIZATION,
        "confound_analysis_performed": False,
        "direction_analysis_performed": False,
        "execution_id_unchanged": EXECUTION_ID,
        "execution_state_unchanged": FAILED,
        "floors_changed": False,
        "high_floor_passed": inventory["ready"]["HIGH"] >= MIN_CALIBRATION_HIGH,
        "join_receipt_sha256": receipt_sha,
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
        "ready_unresolved": inventory["ready_unresolved"],
        "reassessment_id": REASSESSMENT_ID,
        "redraw_authorized": False,
        "resolution_recomputed": False,
        "residual_recomputed": False,
        "rows_relabeled": False,
        "runtime_integration": False,
        "schema": "hyperlex.residual_threshold_v2_calibration_support_reassessment.v1",
        "score_sha256": EXPECTED_SCORES,
        "secondary_floor_passed": inventory["ready"]["SECONDARY"] >= MIN_CALIBRATION_SECONDARY,
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
        "unknown_unresolved": inventory["unknown_unresolved"],
    }
    result_sha = write_new(RESULT_PATH, render_json(result))
    tracker_sha = update_tracker(state, join_sha, receipt_sha, result_sha)
    assert_sealed()
    assert_measurement_sealed()
    append_spec(state, inventory, join_sha, receipt_sha, result_sha, tracker_sha)
    return {
        "join_receipt_sha256": receipt_sha,
        "join_sha256": join_sha,
        "ready": inventory["ready"],
        "ready_unresolved": inventory["ready_unresolved"],
        "result_sha256": result_sha,
        "state": state,
        "tracker_sha256": tracker_sha,
        "unknown_by_class": inventory["unknown_by_class"],
        "unknown_unresolved": inventory["unknown_unresolved"],
    }


def update_tracker(state: str, join_sha: str, receipt_sha: str, result_sha: str) -> str:
    if sha256_file(TRACKER) != EXPECTED_TRACKER:
        refuse("tracker drifted before the support update")
    tracker = json.loads(TRACKER.read_text(encoding="utf-8"))
    if tracker.get("residual_threshold_v2_calibration_execution_state") != FAILED:
        refuse("execution 001 state drifted")
    if tracker.get("residual_threshold_v2_blind_operator_labeling_state") != "LABELS_FROZEN":
        refuse("label freeze drifted")
    if tracker.get("residual_threshold_v1_disposition") != "CLOSED_CALIBRATION_DESIGN_INSUFFICIENT":
        refuse("v1 disposition drifted")
    if tracker.get("residual_threshold_v2_value") is not None or tracker.get("residual_threshold_v2_frozen") is not False:
        refuse("threshold drifted")
    tracker["previous_tracker_sha256"] = EXPECTED_TRACKER
    tracker["residual_threshold_v2_support_reassessment_id"] = REASSESSMENT_ID
    tracker["residual_threshold_v2_support_reassessment_state"] = state
    tracker["residual_threshold_v2_support_join_sha256"] = join_sha
    tracker["residual_threshold_v2_support_join_receipt_sha256"] = receipt_sha
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


def append_spec(state: str, inventory: dict, join_sha: str, receipt_sha: str, result_sha: str, tracker_sha: str) -> None:
    marker = "## Threshold v2 support reassessment — 2026-09-28"
    text = SPEC.read_text(encoding="utf-8")
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
        "parent resolution status and residual scores by `row_id`. It checks calibration row id, "
        "normalized text hash, and PWN 3.0 synset for equality. It does not relabel a row, "
        "recompute resolution, recompute a residual, or change the 60/140 ready split. "
        f"`{EXECUTION_ID}` stays `CALIBRATION_INSUFFICIENT_SUPPORT` and stays sealed. "
        "The resolution file stores constituent lines. Its 200 parent rows are the row identity, "
        "and that set matches the manifest and the labels.\n"
        "\n"
        "Each joined row records only the calibration row id, row id, surface, POS, synset, "
        "operator label, row resolution status, and residual score. An unknown row has a null residual. "
        f"Ready rows are HIGH {ready['HIGH']}, SECONDARY {ready['SECONDARY']}, "
        f"REJECT {ready['REJECT']}, QUARANTINE {ready['QUARANTINE']}, and UNRESOLVED "
        f"{inventory['ready_unresolved']}. Unknown rows are HIGH {unknown['HIGH']}, "
        f"SECONDARY {unknown['SECONDARY']}, REJECT {unknown['REJECT']}, QUARANTINE {unknown['QUARANTINE']}, "
        f"and UNRESOLVED {inventory['unknown_unresolved']}. "
        f"The raw label inventory remains HIGH {inventory['operator_label_inventory']['HIGH']}, "
        f"SECONDARY {inventory['operator_label_inventory']['SECONDARY']}, "
        f"REJECT {inventory['operator_label_inventory']['REJECT']}, "
        f"QUARANTINE {inventory['operator_label_inventory']['QUARANTINE']}, "
        f"and UNRESOLVED {inventory['operator_label_inventory']['UNRESOLVED']}.\n"
        "\n"
        f"{outcome} Direction analysis, confound review, and threshold search were not run. "
        f"Join sha256 `{join_sha}`. Join receipt sha256 `{receipt_sha}`. "
        f"Support reassessment sha256 `{result_sha}`. Tracker sha256 `{tracker_sha}`.\n"
        "\n"
        "The threshold stays unfrozen. Measurement stays `SEALED`, unresolved, unscored, and "
        f"unlabeled. Measurement sha256 remains `{EXPECTED_MEASUREMENT}`. Score sha256 remains "
        f"`{EXPECTED_SCORES}`. Resolution sha256 remains `{EXPECTED_RESOLUTION}`. "
        f"Failure sha256 remains `{EXPECTED_FAILURE}`. Label sha256 remains `{EXPECTED_LABELS}`. "
        "`selected_source` remains `none`. Nothing was integrated into runtime. "
        "SELECT-005 remains unauthorized. Admitted, settled, and gold stay 0. "
        f"Events sha256 remains `{EXPECTED_EVENTS}`. The ledger was not appended. "
        "No JSON Schema document exists for this reassessment family. v1 remains "
        "`CLOSED_CALIBRATION_DESIGN_INSUFFICIENT`.\n"
    )
    if marker in text:
        start = text.index(marker)
        SPEC.write_text(text[:start] + section, encoding="utf-8")
        return
    if not text.endswith("\n"):
        text += "\n"
    SPEC.write_text(text + section, encoding="utf-8")


def main() -> None:
    if len(sys.argv) == 2 and sys.argv[1] == "--reassess":
        print(json.dumps(reassess(), sort_keys=True))
        return
    refuse("usage: residual_threshold_v2_support.py --reassess")


if __name__ == "__main__":
    main()
