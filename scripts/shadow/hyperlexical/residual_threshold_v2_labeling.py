"""Blind operator labeling for the frozen threshold v2 calibration surface.

This pass writes a label-availability review, a blind packet, and operator
labels. It does not join those labels to readiness or residual scores, and it
does not search for a threshold.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from hyperlexical.screen_eval import OPERATOR_BUCKETS, REASONS

LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
SOURCE = LEDGER / "operator-review/HLX-EVAL-UNBIND-SEMANTIC-EVIDENCE-SOURCE-V1-001"
SENSE = LEDGER / "operator-review/HLX-EVAL-UNBIND-SENSE-SCREEN-V1-HYPOTHESIS-001"
EVENTS = LEDGER / "events.jsonl"
LEDGER_FILE = LEDGER / "ledger.json"
TRACKER = SENSE / "HYPOTHESIS.json"
SPEC = Path("/home/morpheus/Hyperlex/specs/007-hyperlexical-model/evaluation-reserve.md")

CALIBRATION_MANIFEST = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_MANIFEST.jsonl"
MEASUREMENT_MANIFEST = SOURCE / "RESIDUAL_THRESHOLD_V2_MEASUREMENT_MANIFEST.jsonl"
FAILURE_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_FAILURE.json"
V1_CLOSURE = SOURCE / "RESIDUAL_THRESHOLD_V1_CALIBRATION_DESIGN_CLOSURE.json"

REVIEW_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_LABEL_AVAILABILITY_REVIEW.json"
PACKET_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_BLIND_OPERATOR_PACKET.jsonl"
PACKET_RECEIPT_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_BLIND_OPERATOR_PACKET_RECEIPT.json"
LABELS_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_OPERATOR_LABELS.jsonl"
LABEL_RECEIPT_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_OPERATOR_LABELING_RECEIPT.json"

AUTHORIZATION = "THRESHOLD_V2_BLIND_OPERATOR_LABELING_AUTHORIZATION"
EXECUTION_ID = "THRESHOLD_V2_CALIBRATION_EXECUTION_001"
LABELING_ID = "THRESHOLD_V2_BLIND_OPERATOR_LABELING_001"
NEXT_TRANSITION = "THRESHOLD_V2_CALIBRATION_SUPPORT_REASSESSMENT_AUTHORIZATION"

EXPECTED_CALIBRATION = "34bc70b93039fc6a5ba4bb58685e0fbfe6f91dd1f86a64fec8326a84013a6465"
EXPECTED_MEASUREMENT = "78ca09ab14912681d028e8b9b1c77a8daf1d0c8c81561434eb9b6ade45a753e5"
EXPECTED_FAILURE = "946a686d46b5a2fc47bb9968bf6e39c643e93c297d5a64de9e0fe88fc6eb33eb"
EXPECTED_SCORES = "01c758af570264c190f4af7805d43d734c9e9a36779f0e0b82675709f213e07c"
EXPECTED_SCORE_RECEIPT = "28ddb23bce8cfcf74b8046ee2cfd0908b5dddefa2a0c04562f9c2f8c912e88d5"
EXPECTED_TRACKER = "50ee4bd40063c57f1f39e466d298d6c08486d0134184da459b9e1ef5de47bea8"
EXPECTED_EVENTS = "96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c"
EXPECTED_LEDGER = "77e22433203879b252f7a9e309d2013d7550101d1c4a014b494d2c96df87d0e0"
EXPECTED_V1_FAILURE = "1d3f1f26609c1f1a47790d94730fba50e9f4d888dd8d7d89e6fa698a924fb3a8"
EXPECTED_V1_CLOSURE = "a5dbdb8ae497c25e711a81a880ad26ec7ef1ace917278c807497af5ec37e5002"
EXPECTED_RESOLUTION = "491b854bcf04d20624e560b63c01823b5634716ec266a4d3a7396d5514defd8d"
EXPECTED_RESOLUTION_RECEIPT = "461ed206ef3abba6b4a8ba79ed5de72305cbee95a61c96981923c89817c17d2d"
EXPECTED_EXECUTION_LABELS = "5cfeab84f16e5ca77d81bda8f1523a3aa20ae70a9828e1ff04a4d64a1930aa1d"
EXPECTED_PREREG = "1c962703e12c5c48fd279dc766fd4d1d3108c40486a10789fdda112926e98261"

PACKET_KEYS = frozenset({
    "calibration_row_id",
    "frozen_gloss",
    "pos",
    "pwn30_synset",
    "row_id",
    "schema",
    "surface",
    "token_count",
})
LABEL_KEYS = frozenset({
    "calibration_row_id",
    "operator_evidence",
    "operator_label",
    "operator_note",
    "pos",
    "pwn30_synset",
    "review_status",
    "row_id",
    "schema",
    "surface",
})
FORBIDDEN_KEY_PARTS = (
    "auc",
    "candidate",
    "confidence",
    "constituent",
    "cosine",
    "embedding",
    "floor",
    "glossbert",
    "lesk",
    "margin",
    "minilm",
    "ready",
    "residual",
    "resolution",
    "score",
    "support",
    "threshold",
    "tier",
    "unknown",
    "wsd",
)
MIN_READY_HIGH = 12
MIN_READY_SECONDARY = 8
MIN_COMBINED = 20


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
        FAILURE_PATH: EXPECTED_FAILURE,
        SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_SCORES.jsonl": EXPECTED_SCORES,
        SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_SCORE_RECEIPT.json": EXPECTED_SCORE_RECEIPT,
        SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_RESOLUTION.jsonl": EXPECTED_RESOLUTION,
        SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_RESOLUTION_RECEIPT.json": EXPECTED_RESOLUTION_RECEIPT,
        SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_LABELS.jsonl": EXPECTED_EXECUTION_LABELS,
        SOURCE / "RESIDUAL_THRESHOLD_V1_CALIBRATION_FAILURE.json": EXPECTED_V1_FAILURE,
        V1_CLOSURE: EXPECTED_V1_CLOSURE,
        SOURCE / "RESIDUAL_THRESHOLD_V2_PREREGISTRATION.json": EXPECTED_PREREG,
        EVENTS: EXPECTED_EVENTS,
        LEDGER_FILE: EXPECTED_LEDGER,
    }


def assert_sealed() -> None:
    for path, expected in sealed_hashes().items():
        found = sha256_file(path)
        if found != expected:
            refuse(f"sealed artifact drifted: {path.name}")


def forbidden_key(key: str) -> str | None:
    lowered = key.casefold()
    for part in FORBIDDEN_KEY_PARTS:
        if part in lowered:
            return part
    return None


def assert_packet_blind(rows: list[dict]) -> None:
    if len(rows) != 200:
        refuse(f"packet row count is {len(rows)}")
    seen: set[str] = set()
    for row in rows:
        if set(row) != PACKET_KEYS:
            refuse(f"packet keys left the permitted set: {sorted(set(row) - PACKET_KEYS)}")
        for key in row:
            part = forbidden_key(key)
            if part is not None:
                refuse(f"packet key exposes {part}")
        row_id = row["row_id"]
        if row_id in seen:
            refuse(f"duplicate packet row {row_id}")
        seen.add(row_id)
        if not isinstance(row["frozen_gloss"], str) or not row["frozen_gloss"]:
            refuse(f"missing frozen gloss for {row_id}")
        if not isinstance(row["surface"], str) or not row["surface"]:
            refuse(f"missing surface for {row_id}")


def packet_rows(manifest: list[dict]) -> list[dict]:
    rows = []
    for row in manifest:
        rows.append({
            "calibration_row_id": row["global_draw_order"],
            "frozen_gloss": row["frozen_gloss"],
            "pos": row["pos"],
            "pwn30_synset": row["pwn30_synset"],
            "row_id": row["row_id"],
            "schema": "hyperlex.residual_threshold_v2_blind_operator_row.v1",
            "surface": row["surface"],
            "token_count": row["token_count"],
        })
    return rows


def availability_review(failure: dict, closure: dict) -> dict:
    support = failure["observed_support"]
    if support["unlabeled"] != 200 or support["unlabeled_scored"] != 60 or support["unlabeled_unknown"] != 140:
        refuse("frozen failure support is not the recorded 0-label split")
    if closure["residual_ready"] != 6 or closure["minimum_required_target_ready_rows"] != MIN_COMBINED:
        refuse("v1 closure counts drifted")
    v1_possible = closure["residual_ready"] >= MIN_COMBINED
    v2_possible = support["unlabeled_scored"] >= MIN_COMBINED
    if v1_possible or not v2_possible:
        refuse("design-support comparison does not separate v1 from v2")
    return {
        "admitted": 0,
        "authorization": AUTHORIZATION,
        "because": "residual_ready_rows 60 >= minimum_combined_target_ready 20",
        "calibration_rows": 200,
        "design_support_possible": True,
        "execution_id": EXECUTION_ID,
        "execution_state_unchanged": "CALIBRATION_INSUFFICIENT_SUPPORT",
        "existing_operator_labels": 0,
        "gold": 0,
        "json_schema_document": None,
        "json_schema_exists": False,
        "minimum_combined_target_ready": MIN_COMBINED,
        "minimum_ready_HIGH": MIN_READY_HIGH,
        "minimum_ready_SECONDARY": MIN_READY_SECONDARY,
        "redraw_authorized": False,
        "redraw_required": False,
        "residual_ready_rows": 60,
        "same_surface_blind_labeling_eligible": True,
        "schema": "hyperlex.residual_threshold_v2_calibration_label_availability_review.v1",
        "select_005_authorized": False,
        "selected_source": "none",
        "settled": 0,
        "unknown_rows": 140,
        "v1_comparison": {
            "design_support_possible": False,
            "disposition_unchanged": "CLOSED_CALIBRATION_DESIGN_INSUFFICIENT",
            "minimum_combined_target_ready": MIN_COMBINED,
            "residual_ready": 6,
        },
        "v1_modified": False,
    }


def freeze_packet() -> dict:
    assert_sealed()
    if sha256_file(TRACKER) != EXPECTED_TRACKER:
        refuse("tracker drifted before the packet freeze")
    manifest = load_jsonl(CALIBRATION_MANIFEST)
    measurement = load_jsonl(MEASUREMENT_MANIFEST)
    if len(manifest) != 200 or len(measurement) != 200:
        refuse("manifest row count is not 200")
    rows = packet_rows(manifest)
    assert_packet_blind(rows)
    manifest_ids = [row["row_id"] for row in manifest]
    packet_ids = [row["row_id"] for row in rows]
    if packet_ids != manifest_ids:
        refuse("packet order or identity diverged from the calibration manifest")
    measurement_ids = {row["row_id"] for row in measurement}
    if set(packet_ids) & measurement_ids:
        refuse("measurement row entered the operator packet")
    failure = json.loads(FAILURE_PATH.read_text(encoding="utf-8"))
    closure = json.loads(V1_CLOSURE.read_text(encoding="utf-8"))
    review = availability_review(failure, closure)
    review_text = render_json(review)
    packet_text = render_jsonl(rows)
    review_sha = write_new(REVIEW_PATH, review_text)
    packet_sha = write_new(PACKET_PATH, packet_text)
    receipt = {
        "authorization": AUTHORIZATION,
        "glossbert_scores_exposed": False,
        "json_schema_document": None,
        "json_schema_exists": False,
        "measurement_rows_included": False,
        "packet_rows": 200,
        "packet_sha256": packet_sha,
        "readiness_exposed": False,
        "residual_scores_exposed": False,
        "resolver_tiers_exposed": False,
        "review_sha256": review_sha,
        "schema": "hyperlex.residual_threshold_v2_blind_operator_packet_receipt.v1",
        "source_manifest_hash": EXPECTED_CALIBRATION,
        "threshold_information_exposed": False,
    }
    receipt_sha = write_new(PACKET_RECEIPT_PATH, render_json(receipt))
    assert_sealed()
    if sha256_file(TRACKER) != EXPECTED_TRACKER:
        refuse("tracker changed during the packet freeze")
    return {
        "packet_sha256": packet_sha,
        "receipt_sha256": receipt_sha,
        "review_sha256": review_sha,
    }


def label_rows(packet: list[dict], decisions: list[dict]) -> list[dict]:
    if len(decisions) != len(packet):
        refuse("decision count does not match the packet")
    by_id = {}
    for decision in decisions:
        row_id = decision.get("row_id")
        if row_id in by_id:
            refuse(f"duplicate decision {row_id}")
        by_id[row_id] = decision
    labels = []
    for row in packet:
        decision = by_id.get(row["row_id"])
        if decision is None:
            refuse(f"missing decision for {row['row_id']}")
        if decision.get("calibration_row_id") != row["calibration_row_id"]:
            refuse(f"calibration row id mismatch for {row['row_id']}")
        label = decision.get("operator_label")
        evidence = decision.get("operator_evidence")
        note = decision.get("operator_note")
        if label not in OPERATOR_BUCKETS:
            refuse(f"operator label {label!r} is outside the canonical ontology")
        if evidence not in REASONS[label]:
            refuse(f"evidence {evidence!r} is not canonical for {label}")
        if not isinstance(note, str) or not note.strip():
            refuse(f"missing operator note for {row['row_id']}")
        for key in decision:
            part = forbidden_key(key)
            if part is not None:
                refuse(f"decision key exposes {part}")
        labels.append({
            "calibration_row_id": row["calibration_row_id"],
            "operator_evidence": evidence,
            "operator_label": label,
            "operator_note": note,
            "pos": row["pos"],
            "pwn30_synset": row["pwn30_synset"],
            "review_status": "REVIEWED",
            "row_id": row["row_id"],
            "schema": "hyperlex.residual_threshold_v2_operator_label.v1",
            "surface": row["surface"],
        })
    return labels


def inventory(labels: list[dict]) -> dict[str, int]:
    counts = {name: 0 for name in OPERATOR_BUCKETS}
    for row in labels:
        counts[row["operator_label"]] += 1
    if sum(counts.values()) != len(labels):
        refuse("label inventory does not cover every row")
    return counts


def freeze_labels(decisions_path: Path) -> dict:
    assert_sealed()
    if sha256_file(TRACKER) != EXPECTED_TRACKER:
        refuse("tracker drifted before the label freeze")
    if not PACKET_RECEIPT_PATH.exists() or not PACKET_PATH.exists():
        refuse("packet receipt was not frozen before labels")
    packet = load_jsonl(PACKET_PATH)
    assert_packet_blind(packet)
    manifest = load_jsonl(CALIBRATION_MANIFEST)
    measurement_ids = {row["row_id"] for row in load_jsonl(MEASUREMENT_MANIFEST)}
    if [row["row_id"] for row in packet] != [row["row_id"] for row in manifest]:
        refuse("packet identity set does not match the calibration manifest")
    if {row["row_id"] for row in packet} & measurement_ids:
        refuse("measurement row present in the packet")
    receipt_sha = sha256_file(PACKET_RECEIPT_PATH)
    stored = json.loads(PACKET_RECEIPT_PATH.read_text(encoding="utf-8"))
    if stored.get("packet_sha256") != sha256_file(PACKET_PATH):
        refuse("packet receipt does not bind the frozen packet")
    if stored.get("readiness_exposed") is not False or stored.get("residual_scores_exposed") is not False:
        refuse("packet receipt does not deny readiness and residual exposure")
    if stored.get("resolver_tiers_exposed") is not False or stored.get("glossbert_scores_exposed") is not False:
        refuse("packet receipt does not deny resolver exposure")
    if stored.get("threshold_information_exposed") is not False or stored.get("measurement_rows_included") is not False:
        refuse("packet receipt does not deny threshold and measurement exposure")
    decisions = load_jsonl(decisions_path)
    labels = label_rows(packet, decisions)
    for row in labels:
        if set(row) != LABEL_KEYS:
            refuse("label keys left the permitted set")
        for key in row:
            part = forbidden_key(key)
            if part is not None:
                refuse(f"label key exposes {part}")
    counts = inventory(labels)
    label_text = render_jsonl(labels)
    label_sha = write_new(LABELS_PATH, label_text)
    labeling_receipt = {
        "authorization": AUTHORIZATION,
        "confound_analysis_performed": False,
        "direction_analysis_performed": False,
        "duplicate_labels": 0,
        "execution_id_unchanged": EXECUTION_ID,
        "execution_state_unchanged": "CALIBRATION_INSUFFICIENT_SUPPORT",
        "identity_set_matches_manifest": True,
        "joined_to_readiness": False,
        "joined_to_scores": False,
        "json_schema_document": None,
        "json_schema_exists": False,
        "label_count": 200,
        "label_sha256": label_sha,
        "labeling_id": LABELING_ID,
        "labeling_state": "LABELS_FROZEN",
        "measurement_rows": 0,
        "measurement_state": "SEALED",
        "measurement_unlabeled": True,
        "measurement_unresolved": True,
        "measurement_unscored": True,
        "missing_rows": 0,
        "operator_label_inventory": counts,
        "packet_receipt_sha256": receipt_sha,
        "packet_sha256": stored["packet_sha256"],
        "review_status": "REVIEWED",
        "runtime_integration": False,
        "schema": "hyperlex.residual_threshold_v2_operator_labeling_receipt.v1",
        "select_005_authorized": False,
        "selected_source": "none",
        "support_reassessment_performed": False,
        "threshold_frozen": False,
        "threshold_search_performed": False,
        "threshold_value": None,
        "unique_row_ids": 200,
    }
    labeling_sha = write_new(LABEL_RECEIPT_PATH, render_json(labeling_receipt))
    tracker_sha = update_tracker(label_sha, labeling_sha, stored["packet_sha256"], receipt_sha, stored["review_sha256"])
    assert_sealed()
    append_spec(tracker_sha, stored, receipt_sha, label_sha, labeling_sha, counts)
    return {
        "label_sha256": label_sha,
        "labeling_receipt_sha256": labeling_sha,
        "operator_label_inventory": counts,
        "tracker_sha256": tracker_sha,
    }


def update_tracker(label_sha: str, labeling_sha: str, packet_sha: str, receipt_sha: str, review_sha: str) -> str:
    if sha256_file(TRACKER) != EXPECTED_TRACKER:
        refuse("tracker drifted before the labeling update")
    tracker = json.loads(TRACKER.read_text(encoding="utf-8"))
    if tracker.get("residual_threshold_v2_state") != "CALIBRATION_INSUFFICIENT_SUPPORT":
        refuse("v2 execution state drifted")
    if tracker.get("residual_threshold_state") != "CALIBRATION_INSUFFICIENT_SUPPORT":
        refuse("v1 execution state drifted")
    if tracker.get("residual_threshold_v1_disposition") != "CLOSED_CALIBRATION_DESIGN_INSUFFICIENT":
        refuse("v1 disposition drifted")
    if tracker.get("residual_threshold_v2_value") is not None or tracker.get("residual_threshold_v2_frozen") is not False:
        refuse("v2 threshold drifted")
    if tracker.get("selected_source") != "none" or tracker.get("select_authorized") is not False:
        refuse("source selection drifted")
    tracker["previous_tracker_sha256"] = EXPECTED_TRACKER
    tracker["residual_threshold_v2_calibration_execution_id"] = EXECUTION_ID
    tracker["residual_threshold_v2_calibration_execution_sealed"] = True
    tracker["residual_threshold_v2_blind_operator_labeling_id"] = LABELING_ID
    tracker["residual_threshold_v2_blind_operator_labeling_state"] = "LABELS_FROZEN"
    tracker["residual_threshold_v2_operator_labels_frozen"] = True
    tracker["residual_threshold_v2_calibration_label_availability_review_sha256"] = review_sha
    tracker["residual_threshold_v2_blind_operator_packet_sha256"] = packet_sha
    tracker["residual_threshold_v2_blind_operator_packet_receipt_sha256"] = receipt_sha
    tracker["residual_threshold_v2_operator_labels_sha256"] = label_sha
    tracker["residual_threshold_v2_operator_labeling_receipt_sha256"] = labeling_sha
    tracker["residual_threshold_v2_measurement_state"] = "SEALED"
    tracker["residual_threshold_v2_measurement_resolved"] = False
    tracker["residual_threshold_v2_measurement_scored"] = False
    tracker["residual_threshold_v2_measurement_labeled"] = False
    tracker["residual_threshold_v2_redraw_authorized"] = False
    tracker["measurement_eligible"] = False
    tracker["selected_source"] = "none"
    tracker["select_authorized"] = False
    tracker["admitted"] = 0
    tracker["settled"] = 0
    tracker["gold"] = 0
    tracker["next_legal_transition"] = NEXT_TRANSITION
    tracker["next_transition_authorized"] = False
    if tracker["residual_threshold_v2_state"] != "CALIBRATION_INSUFFICIENT_SUPPORT":
        refuse("labeling overwrote the calibration execution state")
    text = render_json(tracker)
    TRACKER.write_text(text, encoding="utf-8")
    TRACKER.chmod(0o600)
    return sha256_file(TRACKER)


def append_spec(tracker_sha: str, packet_receipt: dict, receipt_sha: str, label_sha: str, labeling_sha: str, counts: dict[str, int]) -> None:
    marker = "## Threshold v2 blind operator labeling — 2026-09-28"
    text = SPEC.read_text(encoding="utf-8")
    if marker in text:
        refuse("spec section already exists")
    if not text.endswith("\n"):
        text += "\n"
    unresolved = counts["UNRESOLVED"]
    section = (
        f"{marker}\n"
        "\n"
        "`THRESHOLD_V2_BLIND_OPERATOR_LABELING_AUTHORIZATION` freezes operator labels "
        "for the same 200-row calibration manifest. "
        "`THRESHOLD_V2_CALIBRATION_EXECUTION_001` stays `CALIBRATION_INSUFFICIENT_SUPPORT` "
        "and stays sealed. That execution observed ready HIGH 0 and ready SECONDARY 0 "
        "because no operator labels existed. This labeling is a successor event. "
        "It does not join the new labels to readiness or to residual scores.\n"
        "\n"
        "The label-availability review separates v2 from v1. v1 had 6 residual-ready rows, "
        "below the combined target-ready floor of 20, so design support was impossible and "
        "that closure stays `CLOSED_CALIBRATION_DESIGN_INSUFFICIENT`. v2 has 60 residual-ready "
        "rows and 140 unknown rows. Sixty is at least 20, so design support is possible and "
        "the missing evidence is the operator labels. Existing labels on these rows were 0. "
        "Redraw is not required and is not authorized. The same frozen surface is eligible "
        f"for blind labeling. Review sha256 `{packet_receipt['review_sha256']}`.\n"
        "\n"
        "The operator packet contains all 200 calibration rows, in manifest order. Membership "
        "does not depend on readiness, residual score, resolution tier, or threshold eligibility. "
        "Each row exposes the calibration row id, row id, surface, POS, PWN 3.0 synset, frozen "
        "first-sense gloss, and token count. Readiness, residual scores, MiniLM representations, "
        "resolver tiers, Extended Lesk, GlossBERT outputs, candidate counts, and threshold floors "
        "are absent. No measurement row is included. Measurement sha256 remains "
        f"`{EXPECTED_MEASUREMENT}`. Packet sha256 `{packet_receipt['packet_sha256']}`. "
        f"Packet receipt sha256 `{receipt_sha}`. The receipt was hashed before the labels were written.\n"
        "\n"
        "All 200 rows received a canonical review outcome under the existing operator ontology: "
        "HIGH, SECONDARY, REJECT, QUARANTINE, and UNRESOLVED. The label inventory is "
        f"HIGH {counts['HIGH']}, SECONDARY {counts['SECONDARY']}, REJECT {counts['REJECT']}, "
        f"QUARANTINE {counts['QUARANTINE']}, and UNRESOLVED {unresolved}. "
        "Those counts are not joined to residual-ready rows. No support reassessment, direction "
        "analysis, confound analysis, or threshold search was run. "
        f"Label sha256 `{label_sha}`. Labeling receipt sha256 `{labeling_sha}`. "
        f"Tracker sha256 `{tracker_sha}`.\n"
        "\n"
        "The threshold value stays null and the threshold stays unfrozen. Measurement stays "
        "`SEALED`, unresolved, unscored, and unlabeled. `selected_source` remains `none`. "
        "Nothing was integrated into runtime. SELECT-005 remains unauthorized. Admitted, settled, "
        "and gold stay 0. Calibration manifest sha256 remains "
        f"`{EXPECTED_CALIBRATION}`. Failure sha256 remains `{EXPECTED_FAILURE}`. "
        f"Score sha256 remains `{EXPECTED_SCORES}`. Score receipt sha256 remains "
        f"`{EXPECTED_SCORE_RECEIPT}`. Events sha256 remains `{EXPECTED_EVENTS}`. "
        "The ledger was not appended. No JSON Schema document exists for this labeling family.\n"
        "\n"
        f"The next named transition is `{NEXT_TRANSITION}`. This pass does not authorize it.\n"
    )
    SPEC.write_text(text + section, encoding="utf-8")


def main() -> None:
    if len(sys.argv) == 2 and sys.argv[1] == "--packet":
        print(json.dumps(freeze_packet(), sort_keys=True))
        return
    if len(sys.argv) == 3 and sys.argv[1] == "--labels":
        print(json.dumps(freeze_labels(Path(sys.argv[2])), sort_keys=True))
        return
    refuse("usage: residual_threshold_v2_labeling.py --packet | --labels DECISIONS.jsonl")


if __name__ == "__main__":
    main()
