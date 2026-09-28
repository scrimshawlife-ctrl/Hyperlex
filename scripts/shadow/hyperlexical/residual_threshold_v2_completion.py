"""Finish the remaining preregistered v2 calibration gates in one pass.

Confound evaluation uses the frozen stop flags. Threshold search runs only
after those flags pass, and it calls the frozen precision-gated selector.
Measurement rows are not read.
"""

from __future__ import annotations

import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path

from hyperlexical.residual_model_resolved_replay_v1 import (
    TIER3_GLOSSBERT,
    confound_report,
)
from hyperlexical.residual_threshold_v1 import (
    ALGORITHM_ID,
    CONFOUND_REVIEW,
    MIN_PREDICTED_YES,
    NO_THRESHOLD,
    PRECISION_FLOOR,
    THRESHOLD_FROZEN,
    WILSON_LOWER_FLOOR,
    _candidate_thresholds,
    _comparison,
    _high_recall,
    _metrics,
    _passes_candidate,
    _precision_terms,
    _quantize_rate,
    _ready_rows,
    _residual_text,
    _safety_counts,
    _stable,
    select_threshold,
    wilson_interval,
)
from hyperlexical.residual_threshold_v2_calibration import MEASUREMENT_NEXT

LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
SOURCE = LEDGER / "operator-review/HLX-EVAL-UNBIND-SEMANTIC-EVIDENCE-SOURCE-V1-001"
SENSE = LEDGER / "operator-review/HLX-EVAL-UNBIND-SENSE-SCREEN-V1-HYPOTHESIS-001"
EVENTS = LEDGER / "events.jsonl"
LEDGER_FILE = LEDGER / "ledger.json"
TRACKER = SENSE / "HYPOTHESIS.json"
SPEC = Path("/home/morpheus/Hyperlex/specs/007-hyperlexical-model/evaluation-reserve.md")

JOIN_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_SUPPORT_JOIN.jsonl"
SCORES_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_SCORES.jsonl"
LABELS_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_OPERATOR_LABELS.jsonl"
MANIFEST_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_MANIFEST.jsonl"
RESOLUTION_RECEIPT = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_RESOLUTION_RECEIPT.json"
MEASUREMENT_MANIFEST = SOURCE / "RESIDUAL_THRESHOLD_V2_MEASUREMENT_MANIFEST.jsonl"
DIRECTION_ANALYSIS = SOURCE / "RESIDUAL_THRESHOLD_V2_DIRECTION_ANALYSIS.json"
DIRECTION_DECISION = SOURCE / "RESIDUAL_THRESHOLD_V2_DIRECTION_DECISION.json"
EXECUTION_CONFOUND = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_CONFOUND_ANALYSIS.json"
EXECUTION_SEARCH = SOURCE / "RESIDUAL_THRESHOLD_V2_THRESHOLD_SEARCH.json"
EXECUTION_FAILURE = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_FAILURE.json"
EXECUTION_ANALYSIS = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_ANALYSIS.json"

CONFOUND_ANALYSIS_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_CONFOUND_ANALYSIS.json"
CONFOUND_DECISION_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_CONFOUND_DECISION.json"
COMPLETION_SEARCH_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_COMPLETION_THRESHOLD_SEARCH.json"
FROZEN_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_THRESHOLD_FROZEN.json"
COMPLETION_FAILURE_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_COMPLETION_FAILURE.json"
RECEIPT_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_COMPLETION_RECEIPT.json"

AUTHORIZATION = "THRESHOLD_V2_CALIBRATION_COMPLETION_AUTHORIZATION"
EXECUTION_ID = "THRESHOLD_V2_CALIBRATION_EXECUTION_001"
STOP_FLAGS = ("extreme_driven", "pos_partitioned", "tier3_concentrated")
CLASSES = ("HIGH", "SECONDARY", "REJECT", "QUARANTINE", "UNRESOLVED")
READY_COUNTS = {"HIGH": 13, "SECONDARY": 22, "REJECT": 24, "QUARANTINE": 1, "UNRESOLVED": 0}
UNKNOWN_COUNTS = {"HIGH": 31, "SECONDARY": 60, "REJECT": 47, "QUARANTINE": 2, "UNRESOLVED": 0}
TRAINING_BLOCKED = "BLOCKED_BY_THRESHOLD_V2_CALIBRATION"
TRAINING_PENDING = "CALIBRATION_COMPLETE_MEASUREMENT_PENDING"

EXPECTED_JOIN = "02088379b5ebe0f26106e830a730e8a90b2281d83c37bf1e750e1846bffa128b"
EXPECTED_SCORES = "01c758af570264c190f4af7805d43d734c9e9a36779f0e0b82675709f213e07c"
EXPECTED_LABELS = "f9901e334543dac2e9bf258208097cf4c9b48af9dc8b497ff42fe4f1f106e1fc"
EXPECTED_MANIFEST = "34bc70b93039fc6a5ba4bb58685e0fbfe6f91dd1f86a64fec8326a84013a6465"
EXPECTED_MEASUREMENT = "78ca09ab14912681d028e8b9b1c77a8daf1d0c8c81561434eb9b6ade45a753e5"
EXPECTED_DIRECTION_ANALYSIS = "b68483acab29fe5918a81281798974fb85000a18af30ec3411c2e30500292783"
EXPECTED_DIRECTION_DECISION = "d408c81ff5766d40ece5c18c2c971ce2e05c23b8163fa9a809f2eded58a852eb"
EXPECTED_EXECUTION_CONFOUND = "3695640fd649aab2e077028aae302c7c59578e2085b0d7de16127c948f19e954"
EXPECTED_EXECUTION_SEARCH = "701ab0858a46490a6df4cf0ba8c41c0b16dc1f6738a0f9b76044812a3bdfb44c"
EXPECTED_EXECUTION_FAILURE = "946a686d46b5a2fc47bb9968bf6e39c643e93c297d5a64de9e0fe88fc6eb33eb"
EXPECTED_EXECUTION_ANALYSIS = "46a8ecb371ec8dfe6ab38875a1500b463fda3db533cffb05129b4d8070963f2a"
EXPECTED_RESOLUTION = "491b854bcf04d20624e560b63c01823b5634716ec266a4d3a7396d5514defd8d"
EXPECTED_RESOLUTION_RECEIPT = "461ed206ef3abba6b4a8ba79ed5de72305cbee95a61c96981923c89817c17d2d"
EXPECTED_REASSESSMENT = "fe5d1061c1f9aed9cad4a1ad8e1dbabc5f76d13d4b13eacb88cef12c347e560d"
EXPECTED_JOIN_RECEIPT = "05748f812491be4ebe215a9a88224073bb2349b465c09dd2598f98d60e02947d"
EXPECTED_V1_FAILURE = "1d3f1f26609c1f1a47790d94730fba50e9f4d888dd8d7d89e6fa698a924fb3a8"
EXPECTED_V1_CLOSURE = "a5dbdb8ae497c25e711a81a880ad26ec7ef1ace917278c807497af5ec37e5002"
EXPECTED_PREREGISTRATION = "1c962703e12c5c48fd279dc766fd4d1d3108c40486a10789fdda112926e98261"
EXPECTED_TRACKER = "7a2e3eb6265ddb90624f2ef5034d77f486d1cec83e2c2792d7659a56bd076abe"
EXPECTED_EVENTS = "96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c"
EXPECTED_LEDGER = "77e22433203879b252f7a9e309d2013d7550101d1c4a014b494d2c96df87d0e0"


def refuse(message: str) -> None:
    raise SystemExit(message)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def render_json(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def write_new(path: Path, text: str) -> str:
    if path.exists():
        refuse(f"{path.name} already exists")
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)
    return sha256_text(text)


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def confound_stop(flags: dict) -> bool:
    """The frozen stop is only tier-3 concentration, extreme-driven separation, or a POS partition."""
    return bool(flags["extreme_driven"] or flags["pos_partitioned"] or flags["tier3_concentrated"])


def itemized_gate_counts(ready: list[dict], comparison: list[dict], candidates: list[str]) -> dict[str, int]:
    """Count each frozen criterion on its own. Selection still uses the combined rule."""
    counts = {
        "all_gates": 0,
        "candidates": 0,
        "leave_one_out": 0,
        "precision_floor": 0,
        "predicted_yes_support": 0,
        "quarantine_veto": 0,
        "reject_veto": 0,
        "wilson_lower": 0,
    }
    for threshold in candidates:
        true_high, support = _precision_terms(comparison, threshold)
        safety = _safety_counts(ready, threshold)
        interval = wilson_interval(true_high, support) if support > 0 else None
        precision_ok = False
        if support > 0:
            precision_ok = _quantize_rate(Decimal(true_high) / Decimal(support)) >= PRECISION_FLOOR
        wilson_ok = interval is not None and interval[0] >= WILSON_LOWER_FLOOR
        counts["candidates"] += 1
        counts["predicted_yes_support"] += int(support >= MIN_PREDICTED_YES)
        counts["precision_floor"] += int(precision_ok)
        counts["wilson_lower"] += int(wilson_ok)
        counts["leave_one_out"] += int(
            _stable(
                comparison,
                threshold,
                minimum_yes=MIN_PREDICTED_YES,
                precision_floor=PRECISION_FLOOR,
                wilson_floor=WILSON_LOWER_FLOOR,
            )
        )
        counts["reject_veto"] += int(safety["reject_predicted_yes"] == 0)
        counts["quarantine_veto"] += int(safety["quarantine_predicted_yes"] == 0)
        counts["all_gates"] += int(_passes_candidate(ready, comparison, threshold))
    return counts


def _sealed() -> dict[Path, str]:
    return {
        JOIN_PATH: EXPECTED_JOIN,
        SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_SUPPORT_JOIN_RECEIPT.json": EXPECTED_JOIN_RECEIPT,
        SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_SUPPORT_REASSESSMENT.json": EXPECTED_REASSESSMENT,
        SCORES_PATH: EXPECTED_SCORES,
        LABELS_PATH: EXPECTED_LABELS,
        MANIFEST_PATH: EXPECTED_MANIFEST,
        MEASUREMENT_MANIFEST: EXPECTED_MEASUREMENT,
        DIRECTION_ANALYSIS: EXPECTED_DIRECTION_ANALYSIS,
        DIRECTION_DECISION: EXPECTED_DIRECTION_DECISION,
        EXECUTION_CONFOUND: EXPECTED_EXECUTION_CONFOUND,
        EXECUTION_SEARCH: EXPECTED_EXECUTION_SEARCH,
        EXECUTION_FAILURE: EXPECTED_EXECUTION_FAILURE,
        EXECUTION_ANALYSIS: EXPECTED_EXECUTION_ANALYSIS,
        SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_RESOLUTION.jsonl": EXPECTED_RESOLUTION,
        RESOLUTION_RECEIPT: EXPECTED_RESOLUTION_RECEIPT,
        SOURCE / "RESIDUAL_THRESHOLD_V1_CALIBRATION_FAILURE.json": EXPECTED_V1_FAILURE,
        SOURCE / "RESIDUAL_THRESHOLD_V1_CALIBRATION_DESIGN_CLOSURE.json": EXPECTED_V1_CLOSURE,
        SOURCE / "RESIDUAL_THRESHOLD_V2_PREREGISTRATION.json": EXPECTED_PREREGISTRATION,
        EVENTS: EXPECTED_EVENTS,
        LEDGER_FILE: EXPECTED_LEDGER,
    }


def assert_sealed() -> None:
    for path, expected in _sealed().items():
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


def _index(rows: list[dict]) -> dict[str, dict]:
    found = {}
    for row in rows:
        row_id = row["row_id"]
        if row_id in found:
            refuse(f"duplicate row_id {row_id}")
        found[row_id] = row
    return found


def assemble(join_rows: list[dict], scores: list[dict], labels: list[dict], manifest: list[dict], parents: list[dict]) -> dict:
    """Copy frozen labels, residuals, tier flags, and the nuisance fields that were stored."""
    if not (len(join_rows) == len(scores) == len(labels) == len(manifest) == len(parents) == 200):
        refuse("frozen calibration tables are not 200 rows")
    by_score = _index(scores)
    by_label = _index(labels)
    by_manifest = _index(manifest)
    by_parent = _index(parents)
    selectable = []
    confound_rows = []
    ready_counts = {name: 0 for name in CLASSES}
    unknown_counts = {name: 0 for name in CLASSES}
    for joined in join_rows:
        row_id = joined["row_id"]
        score = by_score[row_id]
        label = by_label[row_id]
        source = by_manifest[row_id]
        parent = by_parent[row_id]
        bucket = joined["operator_label"]
        if bucket not in ready_counts or label["operator_label"] != bucket:
            refuse("operator label drifted from the support join")
        if joined["surface"] != source["surface"] or joined["surface"] != score.get("surface", joined["surface"]):
            refuse("surface drifted")
        if joined["pos"] != source["pos"] or joined["pos"] != parent["pos"]:
            refuse("pos drifted")
        if joined["pwn30_synset"] != parent["synset"] or joined["pwn30_synset"] != source["pwn30_synset"]:
            refuse("synset drifted")
        status = joined["row_resolution_status"]
        if status == "RESIDUAL_READY":
            if score.get("score_status") != "SCORED" or parent["row_resolution_status"] != "RESIDUAL_READY":
                refuse("readiness drifted")
            residual = joined["residual_score"]
            if residual != score["residual_score"]:
                refuse("residual string drifted from the score file")
            if _residual_text(Decimal(residual)) != residual:
                refuse("residual string is not already the frozen quantum")
            tiers = list(score["constituent_resolution_tiers"])
            uses_tier3 = score["uses_tier3"]
            if uses_tier3 is not (TIER3_GLOSSBERT in tiers):
                refuse("frozen uses_tier3 disagrees with frozen tiers")
            if len(score["content_constituents"]) != len(parent["selected_constituent_synsets"]):
                refuse("frozen constituent count disagrees")
            if str(source["token_count"]) != str(len(source["surface"].split())):
                refuse("frozen token_count disagrees with the frozen surface")
            ready_counts[bucket] += 1
            selectable.append(
                {
                    "development_row": False,
                    "operator_bucket": bucket,
                    "pos": joined["pos"],
                    "residual_score": residual,
                    "score_status": "SCORED",
                    "uses_tier3": uses_tier3,
                }
            )
            confound_rows.append(
                {
                    "bucket": bucket,
                    "character_length": str(len(source["surface"])),
                    "content_count": str(len(score["content_constituents"])),
                    "max_candidate_senses": None,
                    "min_glossbert_confidence": None,
                    "min_glossbert_margin": None,
                    "pos": joined["pos"],
                    "residual_score": residual,
                    "row_id": row_id,
                    "surface": source["surface"],
                    "synset": joined["pwn30_synset"],
                    "tiers": tiers,
                    "token_count": str(source["token_count"]),
                    "uses_tier3": uses_tier3,
                }
            )
        elif status == "UNKNOWN":
            if score.get("score_status") != "UNKNOWN" or joined["residual_score"] is not None:
                refuse("unknown row changed")
            if parent["row_resolution_status"] != "UNKNOWN":
                refuse("parent readiness drifted")
            unknown_counts[bucket] += 1
        else:
            refuse("unexpected resolution status")
    if ready_counts != READY_COUNTS or unknown_counts != UNKNOWN_COUNTS:
        refuse("support counts drifted")
    return {"confound_rows": confound_rows, "selectable": selectable}


def _flags_from_report(report: dict) -> dict:
    return {
        "extreme_driven": report["extreme_driven"],
        "pos_partitioned": report["pos_partitioned"],
        "tier3_concentrated": bool(report["tier3"]["concentrated"]),
    }


def _nuisance_provenance() -> dict:
    return {
        "character_length": "FROZEN_SURFACE_LENGTH",
        "content_count": "FROZEN_CONTENT_CONSTITUENT_COUNT",
        "max_candidate_senses": "NOT_PERSISTED",
        "min_glossbert_confidence": "NOT_PERSISTED",
        "min_glossbert_margin": "NOT_PERSISTED",
        "token_count": "FROZEN_MANIFEST_TOKEN_COUNT",
        "uses_tier3": "FROZEN_SCORE_FIELD",
    }


def _search_body(selectable: list[dict], selection: dict) -> dict:
    ready = _ready_rows(selectable)
    comparison = _comparison(ready)
    candidates = _candidate_thresholds(ready)
    counts = itemized_gate_counts(ready, comparison, candidates)
    passing = [
        (str(_high_recall(comparison, threshold)), threshold)
        for threshold in candidates
        if _passes_candidate(ready, comparison, threshold)
    ]
    selected = selection.get("threshold_value")
    if passing:
        best = max(passing, key=lambda item: (Decimal(item[0]), Decimal(item[1])))
        if selected != best[1]:
            refuse("threshold search disagrees with select_threshold")
    elif selected is not None:
        refuse("select_threshold returned a value with no passing candidate")
    if counts["all_gates"] != len(passing):
        refuse("combined gate count disagrees with the passing candidates")
    return {
        "algorithm_id": ALGORITHM_ID,
        "candidate_count": len(candidates),
        "candidates_evaluated": True,
        "execution_001_search_sha256": EXPECTED_EXECUTION_SEARCH,
        "execution_001_search_unchanged": True,
        "gate_pass_counts": counts,
        "json_schema_document": None,
        "json_schema_exists": False,
        "precision_denominator": "HIGH positive, SECONDARY negative",
        "schema": "hyperlex.residual_threshold_v2_completion_threshold_search.v1",
        "search_executed": True,
        "selected_threshold": selected,
        "selection_algorithm_id": ALGORITHM_ID,
    }


def _receipt(confound_result: str, threshold_state: str, threshold_value, threshold_frozen: bool, training: str, measurement_eligible: bool) -> dict:
    return {
        "calibration_redraw": False,
        "confound_gate": confound_result,
        "direction_gate": "SUPPORTED_DIRECTION",
        "json_schema_document": None,
        "json_schema_exists": False,
        "measurement_eligible": measurement_eligible,
        "measurement_state": "SEALED",
        "operator_labeling": "LABELS_FROZEN",
        "runtime_integration": False,
        "select_005_authorized": False,
        "selected_source": "none",
        "support_gate": "SUPPORT_GATE_PASSED",
        "surface_draw": "SURFACES_FROZEN",
        "threshold_frozen": threshold_frozen,
        "threshold_search": threshold_state,
        "threshold_value": threshold_value,
        "training_authorized": False,
        "training_readiness": training,
    }


def update_tracker(state: str, threshold_value, threshold_frozen: bool, training: str, measurement_eligible: bool, next_transition: str, digests: dict) -> str:
    if sha256_file(TRACKER) != EXPECTED_TRACKER:
        refuse("tracker drifted before the completion update")
    tracker = json.loads(TRACKER.read_text(encoding="utf-8"))
    if tracker.get("residual_threshold_v2_calibration_execution_state") != "CALIBRATION_INSUFFICIENT_SUPPORT":
        refuse("execution 001 drifted")
    if tracker.get("residual_threshold_v2_direction_evaluation_state") != "SUPPORTED_DIRECTION":
        refuse("direction state drifted")
    if tracker.get("residual_threshold_v2_support_reassessment_state") != "SUPPORT_GATE_PASSED":
        refuse("support state drifted")
    if tracker.get("residual_threshold_v1_disposition") != "CLOSED_CALIBRATION_DESIGN_INSUFFICIENT":
        refuse("v1 disposition drifted")
    tracker["previous_tracker_sha256"] = EXPECTED_TRACKER
    tracker["residual_threshold_v2_state"] = state
    tracker["residual_threshold_v2_value"] = threshold_value
    tracker["residual_threshold_v2_frozen"] = threshold_frozen
    tracker["residual_threshold_v2_redraw_authorized"] = False
    tracker["residual_threshold_v2_measurement_state"] = "SEALED"
    tracker["residual_threshold_v2_measurement_resolved"] = False
    tracker["residual_threshold_v2_measurement_scored"] = False
    tracker["residual_threshold_v2_measurement_labeled"] = False
    tracker["residual_threshold_v2_training_readiness"] = training
    tracker["residual_threshold_v2_training_authorized"] = False
    tracker["measurement_eligible"] = measurement_eligible
    tracker["selected_source"] = "none"
    tracker["select_authorized"] = False
    tracker["admitted"] = 0
    tracker["settled"] = 0
    tracker["gold"] = 0
    tracker["next_legal_transition"] = next_transition
    tracker["next_transition_authorized"] = False
    for key, digest in digests.items():
        tracker[key] = digest
    if tracker["residual_threshold_v2_calibration_execution_state"] != "CALIBRATION_INSUFFICIENT_SUPPORT":
        refuse("completion changed execution 001")
    if tracker["residual_threshold_v2_calibration_failure_sha256"] != EXPECTED_EXECUTION_FAILURE:
        refuse("completion changed the execution failure hash")
    if tracker["residual_threshold_v2_calibration_search_sha256"] != EXPECTED_EXECUTION_SEARCH:
        refuse("completion changed the execution search hash")
    text = render_json(tracker)
    TRACKER.write_text(text, encoding="utf-8")
    TRACKER.chmod(0o600)
    return sha256_file(TRACKER)


def _spearman_line(report: dict) -> str:
    parts = []
    for field, body in report["nuisance"].items():
        high = body["HIGH"].get("spearman_with_residual")
        secondary = body["SECONDARY"].get("spearman_with_residual")
        high_status = body["HIGH"].get("status")
        secondary_status = body["SECONDARY"].get("status")
        parts.append(
            f"{field} HIGH {high_status or high}, SECONDARY {secondary_status or secondary}"
        )
    return "; ".join(parts)


def append_spec(summary: dict) -> None:
    marker = "## Threshold v2 calibration completion — 2026-09-28"
    text = SPEC.read_text(encoding="utf-8")
    flags = summary["flags"]
    section = (
        f"{marker}\n"
        "\n"
        f"`{AUTHORIZATION}` runs the remaining preregistered calibration gates in order on the "
        "frozen support join. It does not recompute residuals, labels, readiness, GlossBERT, "
        "MiniLM, or the resolver. It does not redraw. The frozen confound stop remains "
        "tier-3 concentration, extreme-driven separation, or a POS partition. Nuisance "
        "associations do not add a stop. "
        f"Extreme-driven is {flags['extreme_driven']}. POS-partitioned is {flags['pos_partitioned']}. "
        f"Tier-3 concentrated is {flags['tier3_concentrated']}. "
        f"Confound result is `{summary['confound_result']}`.\n"
        "\n"
        "Token count, character length, and content-constituent count are copied from the frozen "
        "manifest, surface, and score constituents. Candidate-sense count and GlossBERT confidence "
        "and margin were not stored on the calibration artifacts, so those associations are "
        f"`NOT_COMPUTABLE` and GlossBERT was not rerun. Nuisance Spearman results: {_spearman_line(summary['report'])}.\n"
        "\n"
        f"{summary['spec_outcome']} "
        f"Analysis sha256 `{summary['confound_analysis_sha256']}`. "
        f"Decision sha256 `{summary['confound_decision_sha256']}`. "
        f"Completion search sha256 `{summary['search_sha256']}`. "
        f"Threshold artifact sha256 `{summary['threshold_artifact_sha256']}`. "
        f"Receipt sha256 `{summary['receipt_sha256']}`. "
        f"Tracker sha256 `{summary['tracker_sha256']}`.\n"
        "\n"
        f"Training readiness is `{summary['training_readiness']}`. Training stays unauthorized. "
        "A frozen threshold does not authorize SELECT-005, BEST replacement, or model promotion. "
        f"Measurement stays `SEALED`. Measurement sha256 remains `{EXPECTED_MEASUREMENT}`. "
        f"The next named transition is `{summary['next_legal_transition']}`. This pass does not authorize it. "
        f"`selected_source` remains `none`. Admitted, settled, and gold stay 0. "
        f"Events sha256 remains `{EXPECTED_EVENTS}`. The ledger was not appended. "
        "No JSON Schema document exists for this completion family. "
        "Execution 001, the direction artifacts, and v1 stay sealed. "
        f"`{EXECUTION_ID}` remains `CALIBRATION_INSUFFICIENT_SUPPORT`.\n"
    )
    if marker in text:
        start = text.index(marker)
        SPEC.write_text(text[:start] + section, encoding="utf-8")
        return
    if not text.endswith("\n"):
        text += "\n"
    SPEC.write_text(text + section, encoding="utf-8")


def _outcome_sentence(selection: dict, search: dict | None, frozen: dict | None) -> str:
    state = selection["calibration_state"]
    if state == CONFOUND_REVIEW:
        return (
            "The confound stop fired. Threshold search did not run. The threshold value stays null. "
            f"Training readiness is `{TRAINING_BLOCKED}` because of `{CONFOUND_REVIEW}`."
        )
    if state == NO_THRESHOLD:
        counts = search["gate_pass_counts"]
        return (
            f"Threshold search evaluated {search['candidate_count']} unique ready residuals. "
            f"Predicted-YES support passed for {counts['predicted_yes_support']}. "
            f"The precision floor passed for {counts['precision_floor']}. "
            f"The Wilson lower bound passed for {counts['wilson_lower']}. "
            f"Leave-one-out passed for {counts['leave_one_out']}. "
            f"The REJECT veto passed for {counts['reject_veto']}. "
            f"The QUARANTINE veto passed for {counts['quarantine_veto']}. "
            f"Candidates passing every frozen gate: {counts['all_gates']}. "
            "No candidate passed. The threshold value stays null. "
            f"Training readiness is `{TRAINING_BLOCKED}` because of `{NO_THRESHOLD}`."
        )
    metrics = frozen
    return (
        f"Threshold search evaluated {search['candidate_count']} unique ready residuals and froze "
        f"`T_HIGH` at `{metrics['threshold_value']}`. Predicted YES support is {metrics['predicted_yes_support']}. "
        f"True HIGH is {metrics['true_high']}. False HIGH is {metrics['false_high']}. "
        f"Precision is {metrics['precision']}. The Wilson interval is {metrics['wilson_lower']} to {metrics['wilson_upper']}. "
        f"HIGH recall is {metrics['high_recall']}. Ready REJECT YES is {metrics['reject_predicted_yes']}. "
        f"Ready QUARANTINE YES is {metrics['quarantine_predicted_yes']}. Leave-one-out is PASS. "
        "Measurement execution is a separate authorization. "
        f"`{MEASUREMENT_NEXT}` is required before measurement is resolved, scored, or labeled. "
        f"Training readiness is `{TRAINING_PENDING}`."
    )


def complete() -> dict:
    assert_sealed()
    assert_measurement_sealed()
    if sha256_file(TRACKER) != EXPECTED_TRACKER:
        refuse("tracker drifted before completion")
    if MEASUREMENT_NEXT != "THRESHOLD_V2_MEASUREMENT_EXECUTION_AUTHORIZATION":
        refuse("measurement handoff name drifted")
    join_rows = load_jsonl(JOIN_PATH)
    scores = load_jsonl(SCORES_PATH)
    labels = load_jsonl(LABELS_PATH)
    manifest = load_jsonl(MANIFEST_PATH)
    parents = json.loads(RESOLUTION_RECEIPT.read_text(encoding="utf-8"))["parent_rows"]
    built = assemble(join_rows, scores, labels, manifest, parents)
    report = confound_report(built["confound_rows"])
    flags = _flags_from_report(report)
    selection = select_threshold(built["selectable"])
    if selection.get("direction") != "SUPPORTED_DIRECTION":
        refuse("selector direction disagrees with the frozen direction decision")
    if selection.get("high_support") != 13 or selection.get("secondary_support") != 22:
        refuse("selector support disagrees with the frozen counts")
    selector_flags = selection.get("confound")
    stopped = confound_stop(flags)
    if stopped:
        if selection["calibration_state"] != CONFOUND_REVIEW or selector_flags != flags:
            refuse("confound report disagrees with select_threshold")
    elif selection["calibration_state"] == CONFOUND_REVIEW or selector_flags is not None or any(flags.values()):
        refuse("confound report disagrees with select_threshold")
    analysis = {
        "analysis_scope": "CONFOUND_THEN_THRESHOLD_IF_PASS",
        "confound_gate_executed": True,
        "confound_result": "STOP" if stopped else "PASS",
        "direction_analysis_sha256": EXPECTED_DIRECTION_ANALYSIS,
        "direction_result": "SUPPORTED_DIRECTION",
        "frozen_stop_conditions": flags,
        "json_schema_document": None,
        "json_schema_exists": False,
        "nuisance_changes_stop_decision": False,
        "nuisance_field_provenance": _nuisance_provenance(),
        "report": report,
        "residual_recomputed": False,
        "rows_excluded": 0,
        "schema": "hyperlex.residual_threshold_v2_confound_analysis.v1",
        "source_label_hash": EXPECTED_LABELS,
        "source_score_hash": EXPECTED_SCORES,
        "source_support_join_hash": EXPECTED_JOIN,
        "threshold_search_run": False if stopped else True,
    }
    decision = {
        "confound_result": analysis["confound_result"],
        "evaluation_id": "THRESHOLD_V2_CONFOUND_EVALUATION_001",
        "frozen_stop_conditions": list(STOP_FLAGS),
        "json_schema_document": None,
        "json_schema_exists": False,
        "next_stage_authorized_by_this_pass": not stopped,
        "state": CONFOUND_REVIEW if stopped else "PASS",
        "threshold_search_run": not stopped,
    }
    analysis_sha = write_new(CONFOUND_ANALYSIS_PATH, render_json(analysis))
    decision["analysis_sha256"] = analysis_sha
    decision_sha = write_new(CONFOUND_DECISION_PATH, render_json(decision))
    search = None
    search_sha = None
    frozen = None
    failure_sha = None
    threshold_value = None
    threshold_frozen = False
    if stopped:
        state = CONFOUND_REVIEW
        training = TRAINING_BLOCKED
        measurement_eligible = False
        next_transition = "NONE"
        threshold_search_state = "NOT_RUN"
        spec_outcome = _outcome_sentence(selection, None, None)
    else:
        search = _search_body(built["selectable"], selection)
        search_sha = write_new(COMPLETION_SEARCH_PATH, render_json(search))
        state = selection["calibration_state"]
        if state == NO_THRESHOLD:
            failure = {
                "failed_gate": "precision_gate",
                "failure_state": NO_THRESHOLD,
                "gate_pass_counts": search["gate_pass_counts"],
                "json_schema_document": None,
                "json_schema_exists": False,
                "measurement_touched": False,
                "schema": "hyperlex.residual_threshold_v2_calibration_completion_failure.v1",
                "search_sha256": search_sha,
                "threshold_frozen": False,
                "threshold_value": None,
            }
            failure_sha = write_new(COMPLETION_FAILURE_PATH, render_json(failure))
            training = TRAINING_BLOCKED
            measurement_eligible = False
            next_transition = "NONE"
            threshold_search_state = NO_THRESHOLD
            spec_outcome = _outcome_sentence(selection, search, None)
        elif state == THRESHOLD_FROZEN:
            metrics = selection["selection_metrics"]
            frozen = {
                "algorithm_id": ALGORITHM_ID,
                "confound_result": "PASS",
                "confound_sha256": analysis_sha,
                "direction_result": "SUPPORTED_DIRECTION",
                "false_high": metrics["false_high"],
                "high_recall": metrics["high_recall"],
                "json_schema_document": None,
                "json_schema_exists": False,
                "leave_one_out_result": "PASS",
                "measurement_execution_authorized": False,
                "measurement_eligible": True,
                "measurement_state": "SEALED",
                "precision": metrics["precision"],
                "predicted_yes_support": metrics["predicted_yes_support"],
                "quarantine_predicted_yes": metrics["quarantine_predicted_yes"],
                "reject_predicted_yes": metrics["reject_predicted_yes"],
                "schema": "hyperlex.residual_threshold_v2_threshold_frozen.v1",
                "search_sha256": search_sha,
                "select_005_authorized": False,
                "selected_source": "none",
                "selection_algorithm_id": ALGORITHM_ID,
                "threshold_frozen": True,
                "threshold_id": "T_HIGH",
                "threshold_value": selection["threshold_value"],
                "true_high": metrics["true_high"],
                "wilson_lower": metrics["precision_interval"][0],
                "wilson_upper": metrics["precision_interval"][1],
            }
            frozen_sha = write_new(FROZEN_PATH, render_json(frozen))
            frozen["artifact_sha256"] = frozen_sha
            threshold_value = selection["threshold_value"]
            threshold_frozen = True
            training = TRAINING_PENDING
            measurement_eligible = True
            next_transition = MEASUREMENT_NEXT
            threshold_search_state = THRESHOLD_FROZEN
            spec_outcome = _outcome_sentence(selection, search, frozen)
        else:
            refuse(f"unexpected selector state {state}")
    receipt = _receipt(
        analysis["confound_result"],
        threshold_search_state,
        threshold_value,
        threshold_frozen,
        training,
        measurement_eligible,
    )
    receipt_sha = write_new(RECEIPT_PATH, render_json(receipt))
    digests = {
        "residual_threshold_v2_confound_analysis_sha256": analysis_sha,
        "residual_threshold_v2_confound_decision_sha256": decision_sha,
        "residual_threshold_v2_calibration_completion_receipt_sha256": receipt_sha,
        "residual_threshold_v2_confound_evaluation_state": analysis["confound_result"],
    }
    if search_sha is not None:
        digests["residual_threshold_v2_completion_threshold_search_sha256"] = search_sha
    if failure_sha is not None:
        digests["residual_threshold_v2_calibration_completion_failure_sha256"] = failure_sha
    if frozen is not None:
        digests["residual_threshold_v2_threshold_frozen_sha256"] = frozen["artifact_sha256"]
    tracker_sha = update_tracker(
        state,
        threshold_value,
        threshold_frozen,
        training,
        measurement_eligible,
        next_transition,
        digests,
    )
    summary = {
        "confound_analysis_sha256": analysis_sha,
        "confound_decision_sha256": decision_sha,
        "confound_result": analysis["confound_result"],
        "flags": flags,
        "next_legal_transition": next_transition,
        "receipt_sha256": receipt_sha,
        "report": report,
        "search_sha256": search_sha or "not-run",
        "spec_outcome": spec_outcome,
        "threshold_artifact_sha256": failure_sha or (None if frozen is None else frozen["artifact_sha256"]) or "not-run",
        "tracker_sha256": tracker_sha,
        "training_readiness": training,
    }
    append_spec(summary)
    assert_sealed()
    assert_measurement_sealed()
    if sha256_file(EXECUTION_SEARCH) != EXPECTED_EXECUTION_SEARCH:
        refuse("execution 001 search artifact changed")
    return {
        "calibration_state": state,
        "confound_analysis_sha256": analysis_sha,
        "confound_decision_sha256": decision_sha,
        "confound_result": analysis["confound_result"],
        "failure_sha256": failure_sha,
        "flags": flags,
        "frozen_sha256": None if frozen is None else frozen["artifact_sha256"],
        "gate_pass_counts": None if search is None else search["gate_pass_counts"],
        "measurement_eligible": measurement_eligible,
        "next_legal_transition": next_transition,
        "receipt_sha256": receipt_sha,
        "search_sha256": search_sha,
        "threshold_frozen": threshold_frozen,
        "threshold_search_ran": search is not None,
        "threshold_value": threshold_value,
        "tracker_sha256": tracker_sha,
        "training_readiness": training,
    }


def main() -> None:
    if len(sys.argv) == 2 and sys.argv[1] == "--complete":
        print(json.dumps(complete(), sort_keys=True))
        return
    refuse("usage: residual_threshold_v2_completion.py --complete")


if __name__ == "__main__":
    main()
