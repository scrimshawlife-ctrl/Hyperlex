"""Replay and measurement driver for the v6 unbind screen.

This module does not admit, settle, or append the ledger.
The forbidden-surface tuple is a regression probe. The scorer does not import it.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from hyperlexical.holdout_guard import normalized_text_sha256
from hyperlexical.unbind_screen_v3 import gloss_for, screen
from hyperlexical.unbind_screen_v4 import WordNetLexicon as V4Lexicon
from hyperlexical.unbind_screen_v4 import apply_v4, canonical_bucket, normalize_lexical, rule_surface_violations
from hyperlexical.unbind_screen_v4_measure import _stratified_sample
from hyperlexical.unbind_screen_v5 import WordNetLexicon as V5Lexicon
from hyperlexical.unbind_screen_v5 import apply_v5
from hyperlexical.unbind_screen_v6 import RULE_VERSION, apply_v6, assess, measurement_allowed

LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
WORDNET = LEDGER / "acquisition/sources/wordnet-3.0/wordnet"
V5 = LEDGER / "operator-review/HLX-EVAL-UNBIND-SCREEN-V5-001/unbind_screen_v5"
V5H = LEDGER / "operator-review/HLX-EVAL-UNBIND-SCREEN-V5-HYPOTHESIS-001"
HYP = LEDGER / "operator-review/HLX-EVAL-UNBIND-SCREEN-V6-HYPOTHESIS-001"
OUT = LEDGER / "operator-review/HLX-EVAL-UNBIND-SCREEN-V6-001/unbind_screen_v6"
EXPECTED_EVENTS = "96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c"
EXPECTED_V5_SAMPLE = "a462f08307e62b09fdfe1dfb6e9a86ec3ea207db27e917730b0d244c47c73359"
EXPECTED_V5_PREDICTIONS = "51bcf051fb1a4b9bf67a28fe7d1235c8922e3a887bb908de32e5ac0d78a6408f"
EXPECTED_V5_LABELS = "b05dc1c35d3d10eed4b615ca1ee8251a875a450f57560fef4b5a84b3e1fc075f"
EXPECTED_V5_ACCEPTANCE = "752fd459658f636df91a8da9f1a701a0de8e3240d6df12072bbd2b7ac4cc0b7a"
EXPECTED_V6_ACCEPTANCE = "68c60dfe9efaf9f79bc445b974c5436d31b60b77fe7374b17103f3b74865610f"
EXPECTED_V6_DRAFT = "942eeab825d1c89c21e91af84da0d753281a91012e9ff219a633d27fe6648aa5"
PROBE_SURFACES = (
    "hit the roof",
    "get it on",
    "like a shot",
    "fed up",
    "taken for granted",
    "turn on a dime",
    "in the public eye",
    "bonnet monkey",
    "john scott haldane",
    "bearer of the sword",
    "detachment of the retina",
    "three times",
    "one hundred seventy-five",
    "on the go",
    "flat out",
    "in the way",
    "to a t",
    "slip of the tongue",
    "run low",
    ".22 caliber",
    "phi correlation",
    "blue-eyed african daisy",
    "monoamine oxidase inhibitor",
    "air force research laboratory",
    "martin luther king jr's birthday",
    "keep out",
    "on the job",
    "take orders",
    "from nowhere",
    "all told",
    "rolled into one",
    "handle with kid gloves",
    "fleet ballistic missile submarine",
    "rapid eye movement sleep",
    "law of conservation of energy",
    "coronoid process of the mandible",
)
LEAK_KEYS = frozenset({
    "predicted", "predicted_bucket", "bucket", "relation", "rule", "phase",
    "operator", "operator_bucket", "forecast", "diagnostic", "v4", "v3", "v5", "v6",
    "primary_evidence", "supporting_evidence", "evidence", "v3_bucket", "v4_bucket",
    "v5_bucket", "v6_bucket",
})
SCORER = Path(__file__).with_name("unbind_screen_v6.py")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def events_sha256() -> str:
    return file_sha256(LEDGER / "events.jsonl")


def scorer_violations() -> list[str]:
    return rule_surface_violations(SCORER.read_text(encoding="utf-8"), PROBE_SURFACES)


def load_replay_rows() -> list[dict]:
    rows = []
    for line in (V5 / "v5_replay_141_predictions.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        rows.append({
            "surface": raw["surface"],
            "pos": raw["pos"],
            "gloss": raw.get("gloss") or "",
            "v3_bucket": raw["v3_bucket"],
            "v4_bucket": raw["v4_bucket"],
            "v5_bucket": raw["v5_bucket"],
            "operator_bucket": raw["operator_bucket"],
            "split": raw.get("split") or "reviewed_141",
            "row_id": raw["row_id"],
        })
    sample = {
        json.loads(line)["row_id"]: json.loads(line)
        for line in (V5 / "measurement_sample.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    labels = {
        json.loads(line)["row_id"]: json.loads(line)
        for line in (V5 / "measurement_labels.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    predictions = {
        json.loads(line)["row_id"]: json.loads(line)
        for line in (V5 / "measurement_predictions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    if set(sample) != set(labels) or set(sample) != set(predictions):
        raise SystemExit("v5 measurement identities differ")
    seen = {row["row_id"] for row in rows}
    if seen & set(sample):
        raise SystemExit("v5 measurement overlaps the prior reviewed surfaces")
    for row_id, blind in sample.items():
        pred = predictions[row_id]
        rows.append({
            "surface": blind["surface"],
            "pos": blind["pos"],
            "gloss": blind.get("gloss") or "",
            "v3_bucket": pred["v3_bucket"],
            "v4_bucket": pred["v4_bucket"],
            "v5_bucket": pred["v5_bucket"],
            "operator_bucket": labels[row_id]["operator_bucket"],
            "split": "v5_measurement_28",
            "row_id": row_id,
        })
    if len(rows) != 169 or len({row["row_id"] for row in rows}) != 169:
        raise SystemExit(f"reviewed surfaces are {len(rows)}, not 169 unique")
    if len({row["surface"] for row in rows}) != 169:
        raise SystemExit("reviewed surfaces are not unique")
    return rows


def replay(out_dir: Path = OUT) -> dict:
    if (out_dir / "measurement_sample.jsonl").exists():
        raise SystemExit("replay refused: the v6 measurement sample is already frozen")
    _require_frozen_parents()
    lexicon = V5Lexicon(WORDNET)
    predictions = []
    for raw in load_replay_rows():
        decision = apply_v6(raw["v5_bucket"], raw["surface"], raw["gloss"], raw["pos"], lexicon)
        predictions.append({
            "schema": "hyperlex.unbind_screen_v6_replay_row.v1",
            "row_id": raw["row_id"],
            "split": raw["split"],
            "surface": raw["surface"],
            "pos": raw["pos"],
            "gloss": raw["gloss"],
            "operator_bucket": canonical_bucket(raw["operator_bucket"]),
            "v3_bucket": canonical_bucket(raw["v3_bucket"]),
            "v4_bucket": canonical_bucket(raw["v4_bucket"]),
            **decision,
        })
    violations = scorer_violations()
    report = assess(predictions, phrase_specific_rule_fired=bool(violations), expected_rows=169)
    report["phrase_violations"] = violations
    report["acceptance_sha256"] = file_sha256(HYP / "ACCEPTANCE.json")
    report["events_sha256"] = events_sha256()
    if report["replay_rows"] != 169:
        report["failures"].append("replay count is not 169")
        report["assertions"]["replay_count"] = False
        report["regression"] = "REGRESSION_FAILED"
        report["state"] = "ENCODED"
        report["measurement_eligible"] = False
    predictions.sort(key=lambda row: row["row_id"])
    changed = [row for row in predictions if row["v5_bucket"] != row["v6_bucket"]]
    changed.sort(key=lambda row: row["row_id"])
    out_dir.mkdir(parents=True, exist_ok=True)
    out_dir.chmod(0o700)
    prediction_sha = _dump_jsonl(out_dir / "v6_replay_169_predictions.jsonl", predictions)
    diff_sha = _dump_jsonl(out_dir / "v6_replay_169_diff.jsonl", changed)
    report["prediction_sha256"] = prediction_sha
    report["diff_sha256"] = diff_sha
    report["diff_rows"] = len(changed)
    _dump_json(out_dir / "v6_replay_169_gate_report.json", report)
    summary = _error_summary(predictions, report)
    _dump_json(out_dir / "v6_replay_169_error_summary.json", summary)
    receipt = _implementation_receipt(report, prediction_sha, diff_sha)
    _dump_json(out_dir / "v6_implementation_receipt.json", receipt)
    _touch_hypothesis(receipt)
    if events_sha256() != EXPECTED_EVENTS:
        raise SystemExit("ledger events hash changed during replay")
    return receipt


def draw_measurement(out_dir: Path = OUT, per_cell: int = 2) -> dict:
    if (out_dir / "measurement_sample.jsonl").exists():
        raise SystemExit("measurement sample is already frozen")
    report = json.loads((out_dir / "v6_replay_169_gate_report.json").read_text(encoding="utf-8"))
    if not measurement_allowed(report) or report.get("replay_rows") != 169:
        raise SystemExit("measurement draw refused: regression is not verified")
    _require_frozen_parents()
    acceptance = json.loads((HYP / "ACCEPTANCE.json").read_text(encoding="utf-8"))
    criteria = dict(acceptance["success_criteria"])
    if criteria.get("high_precision") != 1.0 or criteria.get("reject_precision") != 1.0:
        raise SystemExit("acceptance bar was amended")
    if criteria.get("false_high_allowed") != 0 or criteria.get("false_reject_allowed") != 0:
        raise SystemExit("acceptance bar was amended")
    if criteria.get("false_secondary_rate_required") is not False or criteria.get("accuracy_gain_required") is not False:
        raise SystemExit("acceptance bar gained a coverage or accuracy target")
    if criteria.get("next_measurement_excludes_reviewed_surfaces") != 169:
        raise SystemExit("acceptance exclusion count changed")
    if "false_secondary_rate_must_be_strictly_below" in criteria:
        raise SystemExit("a false-secondary floor was added after the contract")
    criteria_sha = _dump_json(out_dir / "measurement_criteria.json", criteria)
    reviewed = load_replay_rows()
    blocked_hash = {row["row_id"] for row in reviewed}
    blocked_norm = {normalize_lexical(row["surface"]) for row in reviewed}
    picked, strata = _stratified_sample(blocked_hash, blocked_norm, per_cell=per_cell)
    v5_lexicon = V5Lexicon(WORDNET)
    v4_lexicon = V4Lexicon(WORDNET)
    v6_lexicon = V5Lexicon(WORDNET)
    blind = []
    predictions = []
    for row in picked:
        surface = str(row["text"])
        pos = str(row["source_pos"])
        tokens = [str(tok) for tok in row["fillers"]]
        if " ".join(tokens) != surface:
            raise SystemExit("sample tokens do not reconstruct the surface")
        _pos, gloss = gloss_for(surface, pos, WORDNET)
        v3_bucket, v3_rule, _phase = screen(surface, pos, tokens, gloss)
        v4_decision = apply_v4(v3_bucket, surface, gloss, pos, v4_lexicon)
        v5_decision = apply_v5(v4_decision["v4_bucket"], surface, gloss, pos, v5_lexicon)
        decision = apply_v6(v5_decision["v5_bucket"], surface, gloss, pos, v6_lexicon)
        row_id = normalized_text_sha256(surface)
        blind.append({
            "schema": "hyperlex.unbind_screen_review_row.v1",
            "evaluation_id": "HLX-EVAL-UNBIND-SCREEN-V6-001",
            "sample_id": "measurement-001",
            "row_id": row_id,
            "surface": surface,
            "pos": pos,
            "token_count": len(tokens),
            "gloss": gloss,
            "provenance": {
                "source": "wordnet-3.0",
                "source_pos": pos,
                "excluded_reviewed_surfaces": 169,
            },
        })
        leaked = LEAK_KEYS.intersection(blind[-1])
        if leaked:
            raise SystemExit(f"blind row carries {sorted(leaked)}")
        predictions.append({
            "schema": "hyperlex.unbind_screen_v6_measurement_prediction.v1",
            "evaluation_id": "HLX-EVAL-UNBIND-SCREEN-V6-001",
            "sample_id": "measurement-001",
            "row_id": row_id,
            "v3_rule": v3_rule,
            "application_index": 1,
            "v3_bucket": canonical_bucket(v3_bucket),
            "v4_bucket": v4_decision["v4_bucket"],
            "v5_bucket": v5_decision["v5_bucket"],
            **decision,
        })
    if {row["surface"] for row in blind} & {row["surface"] for row in reviewed}:
        raise SystemExit("measurement sample reuses a reviewed surface")
    if {normalize_lexical(row["surface"]) for row in blind} & blocked_norm:
        raise SystemExit("measurement sample reuses a normalized reviewed identity")
    if {row["row_id"] for row in blind} & blocked_hash:
        raise SystemExit("measurement sample reuses a reviewed row id")
    blind.sort(key=lambda row: row["row_id"])
    predictions.sort(key=lambda row: row["row_id"])
    sample_sha = _dump_jsonl(out_dir / "measurement_sample.jsonl", blind)
    prediction_sha = _dump_jsonl(out_dir / "measurement_predictions.jsonl", predictions)
    freeze = {
        "schema": "hyperlex.unbind_screen_v6_measurement_freeze.v1",
        "rule": RULE_VERSION,
        "state": "SAMPLE_FROZEN",
        "regression": "REGRESSION_VERIFIED",
        "measurement_eligible": True,
        "rows": len(blind),
        "per_cell": per_cell,
        "strata": "source_pos x token_count",
        "stratum_counts": strata,
        "order": "normalized_text_sha256",
        "excluded_reviewed_surfaces": 169,
        "deduplicated_normalized_lexical_identity": True,
        "sample_sha256": sample_sha,
        "prediction_sha256": prediction_sha,
        "criteria_sha256": criteria_sha,
        "v6_application_count": 1,
        "hand_corrections": 0,
        "operator_labels": None,
        "precision": "NOT_COMPUTABLE",
        "confusion": "NOT_COMPUTABLE",
        "inspected_before_freeze": False,
        "false_secondary_rate_required": False,
        "accuracy_gain_required": False,
        "admitted": 0,
        "settled": 0,
        "gold": 0,
        "select_authorized": False,
        "revision_eligible": False,
        "events_sha256": events_sha256(),
    }
    _dump_json(out_dir / "measurement_freeze.json", freeze)
    receipt = json.loads((out_dir / "v6_implementation_receipt.json").read_text(encoding="utf-8"))
    receipt["state"] = "MEASUREMENT_ELIGIBLE"
    receipt["applied_to_measurement"] = True
    receipt["measurement_eligible"] = True
    receipt["measurement_state"] = "SAMPLE_FROZEN"
    receipt["measurement_rows"] = len(blind)
    receipt["measurement_sample_sha256"] = sample_sha
    receipt["measurement_prediction_sha256"] = prediction_sha
    receipt["criteria_sha256"] = criteria_sha
    receipt["v6_application_count"] = 1
    receipt["hand_corrections"] = 0
    receipt["precision"] = "NOT_COMPUTABLE"
    receipt["events_sha256"] = events_sha256()
    _dump_json(out_dir / "v6_implementation_receipt.json", receipt)
    _touch_hypothesis(receipt)
    if events_sha256() != EXPECTED_EVENTS:
        raise SystemExit("ledger events hash changed during the draw")
    if file_sha256(out_dir / "measurement_sample.jsonl") != sample_sha:
        raise SystemExit("sample hash drifted")
    return freeze


def _error_summary(predictions: list[dict], report: dict) -> dict:
    reversals = []
    for row in predictions:
        if row["v5_bucket"] == row["v6_bucket"]:
            continue
        reversals.append({
            "row_id": row["row_id"],
            "surface": row["surface"],
            "v5_bucket": row["v5_bucket"],
            "v6_bucket": row["v6_bucket"],
            "operator_bucket": row["operator_bucket"],
            "primary_evidence": row["primary_evidence"],
            "previously_correct": row["v5_bucket"] == row["operator_bucket"],
        })
    stayed_wrong = sum(
        1 for row in predictions
        if row["v5_bucket"] == row["v6_bucket"] and row["v6_bucket"] != row["operator_bucket"]
    )
    return {
        "schema": "hyperlex.unbind_screen_v6_replay_error_summary.v1",
        "role": "regression_summary",
        "executable_rule_source": False,
        "motivating_cases_are_not_a_required_fit": True,
        "regression": report["regression"],
        "replay_rows": report["replay_rows"],
        "moves": report["moves"],
        "previously_correct": report["previously_correct"],
        "previously_correct_lost": report["previously_correct_lost"],
        "direct_swaps": report["direct_swaps"],
        "reversals": reversals,
        "unchanged_disagreement_count": stayed_wrong,
        "select_authorized": False,
        "admitted": 0,
        "settled": 0,
        "gold": 0,
    }


def _require_frozen_parents() -> None:
    if events_sha256() != EXPECTED_EVENTS:
        raise SystemExit("ledger events hash changed")
    checks = {
        V5 / "measurement_sample.jsonl": EXPECTED_V5_SAMPLE,
        V5 / "measurement_predictions.jsonl": EXPECTED_V5_PREDICTIONS,
        V5 / "measurement_labels.jsonl": EXPECTED_V5_LABELS,
        V5H / "ACCEPTANCE.json": EXPECTED_V5_ACCEPTANCE,
        HYP / "ACCEPTANCE.json": EXPECTED_V6_ACCEPTANCE,
        HYP / "HYPOTHESIS.draft.json": EXPECTED_V6_DRAFT,
    }
    for path, digest in checks.items():
        if file_sha256(path) != digest:
            raise SystemExit(f"frozen parent changed: {path.name}")


def _implementation_receipt(report: dict, prediction_sha: str, diff_sha: str) -> dict:
    verified = report["regression"] == "REGRESSION_VERIFIED"
    return {
        "schema": "hyperlex.unbind_screen_v6_implementation_receipt.v1",
        "rule": RULE_VERSION,
        "state": "REGRESSION_VERIFIED" if verified else "ENCODED",
        "regression": report["regression"],
        "measurement_eligible": verified,
        "authorized": False,
        "encoded": True,
        "applied_to_measurement": False,
        "relation_to_v5": "challengeable_outer_buckets_over_a_frozen_v5_bucket",
        "demotion_stops_for_this_application": True,
        "acceptance_sha256": report["acceptance_sha256"],
        "source_sha256": {SCORER.name: file_sha256(SCORER)},
        "replay_rows": report["replay_rows"],
        "diff_rows": report["diff_rows"],
        "prediction_sha256": prediction_sha,
        "diff_sha256": diff_sha,
        "phrase_specific_rule_fired": report["phrase_specific_rule_fired"],
        "failures": report["failures"],
        "assertions": report["assertions"],
        "moves": report["moves"],
        "previously_correct": report["previously_correct"],
        "previously_correct_lost": report["previously_correct_lost"],
        "direct_swaps": report["direct_swaps"],
        "events_sha256": report["events_sha256"],
        "revision_eligible": False,
        "select_authorized": False,
        "admitted": 0,
        "settled": 0,
        "gold": 0,
        "precision": "NOT_COMPUTABLE",
    }


def _touch_hypothesis(receipt: dict) -> None:
    path = HYP / "HYPOTHESIS.json"
    hypothesis = json.loads(path.read_text(encoding="utf-8"))
    draft = file_sha256(HYP / "HYPOTHESIS.draft.json")
    acceptance = file_sha256(HYP / "ACCEPTANCE.json")
    if draft != EXPECTED_V6_DRAFT or acceptance != EXPECTED_V6_ACCEPTANCE:
        raise SystemExit("v6 draft or acceptance bytes changed")
    if hypothesis.get("draft_hypothesis_sha256") not in (None, EXPECTED_V6_DRAFT):
        raise SystemExit("v6 hypothesis no longer points at the frozen draft")
    if hypothesis.get("acceptance_sha256") != EXPECTED_V6_ACCEPTANCE:
        raise SystemExit("v6 hypothesis no longer points at the frozen acceptance")
    hypothesis["encoded"] = True
    hypothesis["state"] = receipt["state"]
    hypothesis["regression"] = receipt["regression"]
    hypothesis["measurement_eligible"] = receipt["measurement_eligible"]
    hypothesis["applied"] = bool(receipt.get("applied_to_measurement"))
    hypothesis["applied_to_measurement"] = bool(receipt.get("applied_to_measurement"))
    hypothesis["select_authorized"] = False
    hypothesis["authorized"] = False
    hypothesis["revision_eligible"] = False
    hypothesis["previously_correct_lost"] = receipt["previously_correct_lost"]
    hypothesis["direct_swaps"] = receipt["direct_swaps"]
    hypothesis["moves"] = receipt["moves"]
    hypothesis["replay_rows"] = receipt["replay_rows"]
    if receipt.get("measurement_sample_sha256"):
        hypothesis["measurement_sample_sha256"] = receipt["measurement_sample_sha256"]
        hypothesis["measurement_rows"] = receipt["measurement_rows"]
        hypothesis["measurement_state"] = receipt["measurement_state"]
        hypothesis["precision"] = "NOT_COMPUTABLE"
    path.write_text(json.dumps(hypothesis, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)


def _dump_json(path: Path, payload: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, sort_keys=True, ensure_ascii=True, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _dump_jsonl(path: Path, rows: list[dict]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Replay v6 and, if verified, draw the measurement sample")
    parser.add_argument("command", choices=("replay", "draw", "run"))
    args = parser.parse_args()
    if args.command == "replay":
        receipt = replay()
    elif args.command == "draw":
        receipt = draw_measurement()
    else:
        receipt = replay()
        if receipt.get("regression") == "REGRESSION_VERIFIED":
            receipt = draw_measurement()
    print(json.dumps({
        key: receipt.get(key)
        for key in (
            "state", "regression", "measurement_eligible", "measurement_state",
            "replay_rows", "diff_rows", "moves", "previously_correct_lost",
            "direct_swaps", "failures", "rows", "sample_sha256", "precision",
            "v6_application_count", "events_sha256",
        )
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
