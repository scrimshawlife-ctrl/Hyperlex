"""Apply the frozen direction rule to the sealed v2 support join.

This pass reads residual strings that are already on the join. It does not
recompute a residual, change a label, or continue into confound review or
threshold search.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from hyperlexical.residual_model_resolved_replay_v1 import (
    INVERTED,
    NO_SEPARATION,
    SUPPORTED,
    direction_result,
    pair_comparison,
)

LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
SOURCE = LEDGER / "operator-review/HLX-EVAL-UNBIND-SEMANTIC-EVIDENCE-SOURCE-V1-001"
SENSE = LEDGER / "operator-review/HLX-EVAL-UNBIND-SENSE-SCREEN-V1-HYPOTHESIS-001"
EVENTS = LEDGER / "events.jsonl"
LEDGER_FILE = LEDGER / "ledger.json"
TRACKER = SENSE / "HYPOTHESIS.json"
SPEC = Path("/home/morpheus/Hyperlex/specs/007-hyperlexical-model/evaluation-reserve.md")

JOIN_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_SUPPORT_JOIN.jsonl"
JOIN_RECEIPT_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_SUPPORT_JOIN_RECEIPT.json"
REASSESSMENT_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_SUPPORT_REASSESSMENT.json"
ANALYSIS_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_DIRECTION_ANALYSIS.json"
DECISION_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_DIRECTION_DECISION.json"
CALIBRATION_MANIFEST = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_MANIFEST.jsonl"
MEASUREMENT_MANIFEST = SOURCE / "RESIDUAL_THRESHOLD_V2_MEASUREMENT_MANIFEST.jsonl"
SCORES_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_SCORES.jsonl"
SCORE_RECEIPT = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_SCORE_RECEIPT.json"
RESOLUTION_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_RESOLUTION.jsonl"
RESOLUTION_RECEIPT = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_RESOLUTION_RECEIPT.json"
FAILURE_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_FAILURE.json"
LABELS_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_OPERATOR_LABELS.jsonl"
LABEL_RECEIPT_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_OPERATOR_LABELING_RECEIPT.json"
PREREGISTRATION = SOURCE / "RESIDUAL_THRESHOLD_V2_PREREGISTRATION.json"
SELECTION_PROCEDURE = SOURCE / "RESIDUAL_THRESHOLD_V2_SELECTION_PROCEDURE.json"

AUTHORIZATION = "THRESHOLD_V2_DIRECTION_EVALUATION_AUTHORIZATION"
EVALUATION_ID = "THRESHOLD_V2_DIRECTION_EVALUATION_001"
EXECUTION_ID = "THRESHOLD_V2_CALIBRATION_EXECUTION_001"
SUPPORT_STATE = "SUPPORT_GATE_PASSED"
ANALYSIS_SCOPE = "DIRECTION_ONLY"
UNCERTAINTY = "UNCERTAINTY_INTERVAL_NOT_COMPUTED"
CONFOUND_NEXT = "THRESHOLD_V2_CONFOUND_EVALUATION_AUTHORIZATION"
READY = "RESIDUAL_READY"
CLASSES = ("HIGH", "SECONDARY", "REJECT", "QUARANTINE", "UNRESOLVED")
DIRECTION_RESULTS = frozenset({SUPPORTED, INVERTED, NO_SEPARATION})
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

FROZEN_READY = {
    "HIGH": 13,
    "SECONDARY": 22,
    "REJECT": 24,
    "QUARANTINE": 1,
    "UNRESOLVED": 0,
}
FROZEN_UNKNOWN = {
    "HIGH": 31,
    "SECONDARY": 60,
    "REJECT": 47,
    "QUARANTINE": 2,
    "UNRESOLVED": 0,
}

EXPECTED_JOIN = "02088379b5ebe0f26106e830a730e8a90b2281d83c37bf1e750e1846bffa128b"
EXPECTED_JOIN_RECEIPT = "05748f812491be4ebe215a9a88224073bb2349b465c09dd2598f98d60e02947d"
EXPECTED_REASSESSMENT = "fe5d1061c1f9aed9cad4a1ad8e1dbabc5f76d13d4b13eacb88cef12c347e560d"
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
EXPECTED_EXECUTION_LABELS = "5cfeab84f16e5ca77d81bda8f1523a3aa20ae70a9828e1ff04a4d64a1930aa1d"
EXPECTED_V1_FAILURE = "1d3f1f26609c1f1a47790d94730fba50e9f4d888dd8d7d89e6fa698a924fb3a8"
EXPECTED_V1_CLOSURE = "a5dbdb8ae497c25e711a81a880ad26ec7ef1ace917278c807497af5ec37e5002"
EXPECTED_PREREGISTRATION = "1c962703e12c5c48fd279dc766fd4d1d3108c40486a10789fdda112926e98261"
EXPECTED_SELECTION = "1c8a82ef939a33bbbb327f0f760439113432645438361176de36159a8f56c55c"
EXPECTED_TRACKER = "170e4b66cfa6764034367ffef685cff67c88367833eb75b46d05f7b3f10f867c"
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
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def sealed_hashes() -> dict[Path, str]:
    return {
        JOIN_PATH: EXPECTED_JOIN,
        JOIN_RECEIPT_PATH: EXPECTED_JOIN_RECEIPT,
        REASSESSMENT_PATH: EXPECTED_REASSESSMENT,
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
        PREREGISTRATION: EXPECTED_PREREGISTRATION,
        SELECTION_PROCEDURE: EXPECTED_SELECTION,
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


def ready_residuals(rows: list[dict], *, expect_frozen_counts: bool) -> dict[str, list[str]]:
    """Copy frozen residual strings for ready rows. Order follows the join."""
    if len(rows) != 200:
        refuse("support join row count drifted")
    ready = {label: [] for label in CLASSES}
    unknown = {label: 0 for label in CLASSES}
    seen = set()
    for row in rows:
        if set(row) != JOIN_KEYS:
            refuse("support join keys drifted")
        row_id = row["row_id"]
        if row_id in seen:
            refuse("support join repeats a row")
        seen.add(row_id)
        label = row["operator_label"]
        if label not in ready:
            refuse("support join has an unknown operator label")
        status = row["row_resolution_status"]
        score = row["residual_score"]
        if status == READY:
            if not isinstance(score, str) or score == "":
                refuse("ready row is missing its frozen residual string")
            ready[label].append(score)
        elif status == "UNKNOWN":
            if score is not None:
                refuse("unknown row carries a residual")
            unknown[label] += 1
        else:
            refuse("support join has an unexpected resolution status")
    if expect_frozen_counts and (ready_counts(ready) != FROZEN_READY or unknown != FROZEN_UNKNOWN):
        refuse("support class counts drifted")
    return ready


def ready_counts(ready: dict[str, list[str]]) -> dict[str, int]:
    return {label: len(ready[label]) for label in CLASSES}


def compare_direction(high_scores: list[str], secondary_scores: list[str]) -> dict:
    """Apply pair_comparison and direction_result to the two comparison classes."""
    if not high_scores or not secondary_scores:
        refuse("direction comparison requires ready HIGH and ready SECONDARY")
    comparison = pair_comparison(high_scores, secondary_scores)
    result = direction_result(comparison)
    if result not in DIRECTION_RESULTS:
        refuse(f"direction rule returned an unfrozen state: {result}")
    if comparison["status"] != "DESCRIPTIVE":
        refuse("direction comparison is not descriptive")
    return {
        "direction_result": result,
        "high_distribution": comparison["high"],
        "high_larger_pairs": comparison["favorable_pairs"],
        "mann_whitney_u": comparison["u_high"],
        "mean_difference": comparison["mean_difference"],
        "median_difference": comparison["median_difference"],
        "rank_biserial": comparison["rank_biserial"],
        "roc_auc": comparison["auc"],
        "secondary_distribution": comparison["secondary"],
        "secondary_larger_pairs": comparison["unfavorable_pairs"],
        "ties": comparison["ties"],
    }


def _analysis(comparison: dict) -> dict:
    high = comparison["high_distribution"]
    secondary = comparison["secondary_distribution"]
    return {
        "analysis_scope": ANALYSIS_SCOPE,
        "confound_analysis_run": False,
        "direction_result": comparison["direction_result"],
        "direction_rule": "residual_model_resolved_replay_v1.direction_result",
        "high_distribution": high,
        "high_larger_pairs": comparison["high_larger_pairs"],
        "json_schema_document": None,
        "json_schema_exists": False,
        "labels_changed": False,
        "mann_whitney_u": comparison["mann_whitney_u"],
        "mean_difference": comparison["mean_difference"],
        "median_difference": comparison["median_difference"],
        "precision_wilson_run": False,
        "rank_biserial": comparison["rank_biserial"],
        "readiness_changed": False,
        "ready_high_count": high["count"],
        "ready_quarantine_count": FROZEN_READY["QUARANTINE"],
        "ready_reject_count": FROZEN_READY["REJECT"],
        "ready_secondary_count": secondary["count"],
        "reject_quarantine_comparison_run": False,
        "residual_recomputed": False,
        "roc_auc": comparison["roc_auc"],
        "rows_excluded": 0,
        "secondary_distribution": secondary,
        "secondary_larger_pairs": comparison["secondary_larger_pairs"],
        "source_label_hash": EXPECTED_LABELS,
        "source_score_hash": EXPECTED_SCORES,
        "source_support_join_hash": EXPECTED_JOIN,
        "source_support_join_receipt_hash": EXPECTED_JOIN_RECEIPT,
        "source_support_reassessment_hash": EXPECTED_REASSESSMENT,
        "threshold_search_run": False,
        "ties": comparison["ties"],
        "uncertainty": UNCERTAINTY,
    }


def _decision(result: str, analysis_sha: str) -> dict:
    supported = result == SUPPORTED
    return {
        "admitted": 0,
        "analysis_scope": ANALYSIS_SCOPE,
        "analysis_sha256": analysis_sha,
        "confound_analysis_run": False,
        "direction_result": result,
        "evaluation_id": EVALUATION_ID,
        "gold": 0,
        "json_schema_document": None,
        "json_schema_exists": False,
        "measurement_state": "SEALED",
        "next_legal_transition": CONFOUND_NEXT if supported else "NONE",
        "next_transition_authorized": False,
        "redraw_authorized": False,
        "runtime_integration": False,
        "select_005_authorized": False,
        "selected_source": "none",
        "settled": 0,
        "state": result,
        "threshold_frozen": False,
        "threshold_search_run": False,
        "threshold_value": None,
        "uncertainty": UNCERTAINTY,
    }


def update_tracker(result: str, analysis_sha: str, decision_sha: str) -> str:
    if sha256_file(TRACKER) != EXPECTED_TRACKER:
        refuse("tracker drifted before the direction update")
    tracker = json.loads(TRACKER.read_text(encoding="utf-8"))
    if tracker.get("residual_threshold_v2_calibration_execution_state") != "CALIBRATION_INSUFFICIENT_SUPPORT":
        refuse("execution 001 is no longer the sealed insufficient-support record")
    if tracker.get("residual_threshold_v2_blind_operator_labeling_state") != "LABELS_FROZEN":
        refuse("operator labels are no longer frozen")
    if tracker.get("residual_threshold_v2_support_reassessment_state") != SUPPORT_STATE:
        refuse("support reassessment is no longer passed")
    if tracker.get("residual_threshold_v2_support_join_sha256") != EXPECTED_JOIN:
        refuse("tracker join hash drifted")
    if tracker.get("residual_threshold_v1_disposition") != "CLOSED_CALIBRATION_DESIGN_INSUFFICIENT":
        refuse("v1 disposition drifted")
    if tracker.get("residual_threshold_v2_value") is not None or tracker.get("residual_threshold_v2_frozen") is not False:
        refuse("threshold is no longer null and unfrozen")
    tracker["previous_tracker_sha256"] = EXPECTED_TRACKER
    tracker["residual_threshold_v2_direction_evaluation_id"] = EVALUATION_ID
    tracker["residual_threshold_v2_direction_evaluation_state"] = result
    tracker["residual_threshold_v2_direction_analysis_sha256"] = analysis_sha
    tracker["residual_threshold_v2_direction_decision_sha256"] = decision_sha
    tracker["residual_threshold_v2_state"] = result
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
    tracker["residual_threshold_v2_disposition"] = None
    if result == SUPPORTED:
        tracker["next_legal_transition"] = CONFOUND_NEXT
    else:
        tracker["next_legal_transition"] = "NONE"
    tracker["next_transition_authorized"] = False
    if tracker["residual_threshold_v2_calibration_execution_state"] != "CALIBRATION_INSUFFICIENT_SUPPORT":
        refuse("direction update changed execution 001")
    if tracker["residual_threshold_v2_support_reassessment_state"] != SUPPORT_STATE:
        refuse("direction update changed the support gate")
    text = render_json(tracker)
    TRACKER.write_text(text, encoding="utf-8")
    return sha256_file(TRACKER)


def _distribution_sentence(name: str, distribution: dict) -> str:
    return (
        f"{name} count {distribution['count']}, min {distribution['min']}, "
        f"p10 {distribution['p10']}, p25 {distribution['p25']}, median {distribution['median']}, "
        f"p75 {distribution['p75']}, p90 {distribution['p90']}, max {distribution['max']}, "
        f"mean {distribution['mean']}, std {distribution['std']}"
    )


def append_spec(analysis: dict, analysis_sha: str, decision_sha: str, tracker_sha: str) -> None:
    marker = "## Threshold v2 direction evaluation — 2026-09-28"
    text = SPEC.read_text(encoding="utf-8")
    result = analysis["direction_result"]
    if result == SUPPORTED:
        outcome = (
            f"`{EVALUATION_ID}` is `{SUPPORTED}`. The next named transition is "
            f"`{CONFOUND_NEXT}`. This pass does not authorize it."
        )
    else:
        outcome = (
            f"`{EVALUATION_ID}` is `{result}`. The threshold value stays null. "
            "Confound review, threshold search, and a redraw were not run."
        )
    section = (
        f"{marker}\n"
        "\n"
        f"`{AUTHORIZATION}` reads residual strings already stored on the frozen support join. "
        "The only directional comparison is ready HIGH against ready SECONDARY. "
        f"Ready HIGH is {analysis['ready_high_count']} and ready SECONDARY is "
        f"{analysis['ready_secondary_count']}. Ready REJECT {analysis['ready_reject_count']} "
        f"and ready QUARANTINE {analysis['ready_quarantine_count']} are context counts and are "
        "not part of the comparison. No row was trimmed, winsorized, or removed. "
        "Residuals, labels, readiness, constituent senses, GlossBERT outputs, and Extended Lesk "
        f"decisions were not recomputed. `{EXECUTION_ID}` stays "
        "`CALIBRATION_INSUFFICIENT_SUPPORT` and stays sealed. Support reassessment 001 stays "
        f"`{SUPPORT_STATE}`.\n"
        "\n"
        "The distributions use the frozen `full_distribution` convention: linear interpolation "
        "on the sorted residuals, rank `(n - 1) * (percent / 100)`, then the residual quantum "
        "with round-half-even. "
        f"{_distribution_sentence('HIGH', analysis['high_distribution'])}. "
        f"{_distribution_sentence('SECONDARY', analysis['secondary_distribution'])}.\n"
        "\n"
        f"HIGH mean minus SECONDARY mean is {analysis['mean_difference']}. "
        f"HIGH median minus SECONDARY median is {analysis['median_difference']}. "
        f"Mann-Whitney U for HIGH is {analysis['mann_whitney_u']}. "
        f"HIGH-larger pairs are {analysis['high_larger_pairs']}. "
        f"SECONDARY-larger pairs are {analysis['secondary_larger_pairs']}. "
        f"Ties are {analysis['ties']}. Rank-biserial correlation is {analysis['rank_biserial']}. "
        f"Descriptive ROC AUC, with HIGH positive, is {analysis['roc_auc']}. "
        "AUC is descriptive and is not a threshold. "
        f"Uncertainty is `{UNCERTAINTY}`: the v2 preregistration and the v2 selection procedure "
        "do not define a calibration-direction interval, and `direction_result` does not require one. "
        f"The frozen rule returns `{result}`.\n"
        "\n"
        f"{outcome} Direction scope is `{ANALYSIS_SCOPE}`. Confound analysis did not run. "
        "Threshold search did not run. No precision or Wilson calculation ran. "
        f"Analysis sha256 `{analysis_sha}`. Decision sha256 `{decision_sha}`. "
        f"Tracker sha256 `{tracker_sha}`. Support join sha256 remains `{EXPECTED_JOIN}`.\n"
        "\n"
        "The threshold stays null and unfrozen. Measurement stays `SEALED`, unresolved, "
        f"unscored, and unlabeled. Measurement sha256 remains `{EXPECTED_MEASUREMENT}`. "
        f"Score sha256 remains `{EXPECTED_SCORES}`. Label sha256 remains `{EXPECTED_LABELS}`. "
        f"Resolution sha256 remains `{EXPECTED_RESOLUTION}`. Failure sha256 remains "
        f"`{EXPECTED_FAILURE}`. `selected_source` remains `none`. Nothing was integrated into "
        "runtime. SELECT-005 remains unauthorized. Admitted, settled, and gold stay 0. "
        f"Events sha256 remains `{EXPECTED_EVENTS}`. The ledger was not appended. "
        "No JSON Schema document exists for this direction family. v1 remains "
        "`CLOSED_CALIBRATION_DESIGN_INSUFFICIENT`.\n"
    )
    if marker in text:
        start = text.index(marker)
        SPEC.write_text(text[:start] + section, encoding="utf-8")
        return
    if not text.endswith("\n"):
        text += "\n"
    SPEC.write_text(text + section, encoding="utf-8")


def evaluate() -> dict:
    assert_sealed()
    assert_measurement_sealed()
    if sha256_file(TRACKER) != EXPECTED_TRACKER:
        refuse("tracker drifted before the direction evaluation")
    if sha256_file(JOIN_PATH) != EXPECTED_JOIN:
        refuse("support join drifted")
    rows = load_jsonl(JOIN_PATH)
    ready = ready_residuals(rows, expect_frozen_counts=True)
    if ready_counts(ready)["HIGH"] != 13 or ready_counts(ready)["SECONDARY"] != 22:
        refuse("directional class counts are not the frozen support counts")
    comparison = compare_direction(ready["HIGH"], ready["SECONDARY"])
    if comparison["high_distribution"]["count"] != 13:
        refuse("HIGH distribution count drifted")
    if comparison["secondary_distribution"]["count"] != 22:
        refuse("SECONDARY distribution count drifted")
    analysis = _analysis(comparison)
    analysis_text = render_json(analysis)
    analysis_sha = write_new(ANALYSIS_PATH, analysis_text)
    decision_text = render_json(_decision(comparison["direction_result"], analysis_sha))
    decision_sha = write_new(DECISION_PATH, decision_text)
    tracker_sha = update_tracker(comparison["direction_result"], analysis_sha, decision_sha)
    append_spec(analysis, analysis_sha, decision_sha, tracker_sha)
    if sha256_file(JOIN_PATH) != EXPECTED_JOIN:
        refuse("support join changed during direction evaluation")
    assert_sealed()
    assert_measurement_sealed()
    if sha256_file(ANALYSIS_PATH) != analysis_sha or sha256_file(DECISION_PATH) != decision_sha:
        refuse("direction artifact hash drifted after write")
    return {
        "analysis_sha256": analysis_sha,
        "decision_sha256": decision_sha,
        "direction_result": comparison["direction_result"],
        "tracker_sha256": tracker_sha,
    }


def main() -> None:
    if len(sys.argv) == 2 and sys.argv[1] == "--evaluate":
        print(json.dumps(evaluate(), sort_keys=True))
        return
    refuse("usage: residual_threshold_v2_direction.py --evaluate")


if __name__ == "__main__":
    main()
