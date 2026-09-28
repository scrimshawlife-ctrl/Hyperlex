"""Replay and measurement driver for the v5 unbind screen.

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
from hyperlexical.unbind_screen_v5 import (
    RULE_VERSION,
    WordNetLexicon,
    apply_v5,
    assess,
    measurement_allowed,
)

LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
WORDNET = LEDGER / "acquisition/sources/wordnet-3.0/wordnet"
EVAL3 = LEDGER / "operator-review/HLX-EVAL-UNBIND-SCREEN-V3-001"
V4 = LEDGER / "operator-review/HLX-EVAL-UNBIND-SCREEN-V4-001/unbind_screen_v4"
HYP = LEDGER / "operator-review/HLX-EVAL-UNBIND-SCREEN-V5-HYPOTHESIS-001"
OUT = LEDGER / "operator-review/HLX-EVAL-UNBIND-SCREEN-V5-001/unbind_screen_v5"
EXPECTED_EVENTS = "96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c"
EXPECTED_V4_SAMPLE = "dae8851134aa960a13e072ae017428054c68b988c8d7e6f86d8cab2d16c2586b"
EXPECTED_V4_PREDICTIONS = "a854847e516fbcd37fbb221456e8caf8c420552795ac7fc6225960bb5434084f"
EXPECTED_V4_LABELS = "023691f8349f0dda12c234691f235ae109289fcf9eab86ec20be1e23bfed9463"
EXPECTED_V4_ACCEPTANCE = "ffb39e38784a56ae15bae51718c61b78fc861e48399936dbed57fb7d0754c55b"
EXPECTED_V3_SAMPLE = "8af5644061a7a60fc5620c217e15a4ec8145f170edee9d8ff4e2999e7b86605e"
EXPECTED_V3_LABELS = "4e7bae5986e6345de62086af270a1d1a6902103d69a50d8f0b1e4e0fe01ecde5"
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
)
LEAK_KEYS = frozenset({
    "predicted", "predicted_bucket", "bucket", "relation", "rule", "phase",
    "operator", "operator_bucket", "forecast", "diagnostic", "v4", "v3", "v5",
    "primary_evidence", "supporting_evidence", "evidence", "v3_bucket", "v4_bucket", "v5_bucket",
})
SCORER = Path(__file__).with_name("unbind_screen_v5.py")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def events_sha256() -> str:
    return file_sha256(LEDGER / "events.jsonl")


def scorer_violations() -> list[str]:
    return rule_surface_violations(SCORER.read_text(encoding="utf-8"), PROBE_SURFACES)


def load_replay_rows() -> list[dict]:
    rows = []
    for line in (V4 / "replay_113_predictions.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        rows.append({
            "surface": raw["surface"],
            "pos": raw["pos"],
            "gloss": raw.get("gloss") or "",
            "v3_bucket": raw["v3_bucket"],
            "v4_bucket": raw["v4_bucket"],
            "operator_bucket": raw["operator_bucket"],
            "split": raw.get("split") or "reviewed_113",
            "row_id": raw["row_id"],
        })
    sample = {
        json.loads(line)["row_id"]: json.loads(line)
        for line in (V4 / "measurement_sample.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    labels = {
        json.loads(line)["row_id"]: json.loads(line)
        for line in (V4 / "measurement_labels.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    predictions = {
        json.loads(line)["row_id"]: json.loads(line)
        for line in (V4 / "measurement_predictions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    if set(sample) != set(labels) or set(sample) != set(predictions):
        raise SystemExit("v4 measurement identities differ")
    for row_id, blind in sample.items():
        rows.append({
            "surface": blind["surface"],
            "pos": blind["pos"],
            "gloss": blind.get("gloss") or "",
            "v3_bucket": predictions[row_id]["v3_bucket"],
            "v4_bucket": predictions[row_id]["v4_bucket"],
            "operator_bucket": labels[row_id]["operator_bucket"],
            "split": "v4_measurement_28",
            "row_id": row_id,
        })
    if len(rows) != 141 or len({row["surface"] for row in rows}) != 141:
        raise SystemExit(f"reviewed surfaces are {len(rows)}, not 141 unique")
    if len({row["row_id"] for row in rows}) != 141:
        raise SystemExit("reviewed row ids are not unique")
    return rows


def replay(out_dir: Path = OUT) -> dict:
    if (out_dir / "measurement_sample.jsonl").exists():
        raise SystemExit("replay refused: the v5 measurement sample is already frozen")
    _require_frozen_parents()
    lexicon = WordNetLexicon(WORDNET)
    predictions = []
    for raw in load_replay_rows():
        decision = apply_v5(raw["v4_bucket"], raw["surface"], raw["gloss"], raw["pos"], lexicon)
        record = {
            "schema": "hyperlex.unbind_screen_v5_replay_row.v1",
            "row_id": raw["row_id"],
            "split": raw["split"],
            "surface": raw["surface"],
            "pos": raw["pos"],
            "gloss": raw["gloss"],
            "operator_bucket": canonical_bucket(raw["operator_bucket"]),
            "v3_bucket": canonical_bucket(raw["v3_bucket"]),
            **decision,
        }
        predictions.append(record)
    violations = scorer_violations()
    report = assess(predictions, phrase_specific_rule_fired=bool(violations), expected_rows=141)
    report["phrase_violations"] = violations
    report["acceptance_sha256"] = file_sha256(HYP / "ACCEPTANCE.json")
    report["events_sha256"] = events_sha256()
    report["v4_sample_sha256"] = EXPECTED_V4_SAMPLE
    report["v4_prediction_sha256"] = EXPECTED_V4_PREDICTIONS
    report["v4_label_sha256"] = EXPECTED_V4_LABELS
    predictions.sort(key=lambda row: row["row_id"])
    changed = [row for row in predictions if row["v4_bucket"] != row["v5_bucket"]]
    changed.sort(key=lambda row: row["row_id"])
    out_dir.mkdir(parents=True, exist_ok=True)
    out_dir.chmod(0o700)
    prediction_sha = _dump_jsonl(out_dir / "v5_replay_141_predictions.jsonl", predictions)
    diff_sha = _dump_jsonl(out_dir / "v5_replay_141_diff.jsonl", changed)
    report["prediction_sha256"] = prediction_sha
    report["diff_sha256"] = diff_sha
    report["diff_rows"] = len(changed)
    _dump_json(out_dir / "v5_replay_141_gate_report.json", report)
    receipt = _implementation_receipt(report, prediction_sha, diff_sha)
    _dump_json(out_dir / "v5_implementation_receipt.json", receipt)
    _touch_hypothesis(receipt)
    if events_sha256() != EXPECTED_EVENTS:
        raise SystemExit("ledger events hash changed during replay")
    return receipt


def draw_measurement(out_dir: Path = OUT, per_cell: int = 2) -> dict:
    if (out_dir / "measurement_sample.jsonl").exists():
        raise SystemExit("measurement sample is already frozen")
    report = json.loads((out_dir / "v5_replay_141_gate_report.json").read_text(encoding="utf-8"))
    if not measurement_allowed(report):
        raise SystemExit("measurement draw refused: regression is not verified")
    _require_frozen_parents()
    acceptance = json.loads((HYP / "ACCEPTANCE.json").read_text(encoding="utf-8"))
    criteria = dict(acceptance["success_criteria"])
    if criteria.get("false_secondary_rate_must_be_strictly_below") != "12/28":
        raise SystemExit("acceptance bar is not the frozen false-secondary rate")
    if criteria.get("accuracy_gain_required") is not False or criteria.get("high_precision") != 1.0:
        raise SystemExit("acceptance bar was amended")
    if criteria.get("reject_precision") != 1.0:
        raise SystemExit("acceptance bar was amended")
    criteria_sha = _dump_json(out_dir / "measurement_criteria.json", criteria)
    reviewed = load_replay_rows()
    blocked_hash = {row["row_id"] for row in reviewed}
    blocked_norm = {normalize_lexical(row["surface"]) for row in reviewed}
    picked, strata = _stratified_sample(blocked_hash, blocked_norm, per_cell=per_cell)
    lexicon = WordNetLexicon(WORDNET)
    v4_lexicon = V4Lexicon(WORDNET)
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
        decision = apply_v5(v4_decision["v4_bucket"], surface, gloss, pos, lexicon)
        row_id = normalized_text_sha256(surface)
        blind.append({
            "schema": "hyperlex.unbind_screen_review_row.v1",
            "evaluation_id": "HLX-EVAL-UNBIND-SCREEN-V5-001",
            "sample_id": "measurement-001",
            "row_id": row_id,
            "surface": surface,
            "pos": pos,
            "token_count": len(tokens),
            "gloss": gloss,
            "provenance": {
                "source": "wordnet-3.0",
                "source_pos": pos,
                "excluded_reviewed_surfaces": 141,
            },
        })
        leaked = LEAK_KEYS.intersection(blind[-1])
        if leaked:
            raise SystemExit(f"blind row carries {sorted(leaked)}")
        predictions.append({
            "schema": "hyperlex.unbind_screen_v5_measurement_prediction.v1",
            "evaluation_id": "HLX-EVAL-UNBIND-SCREEN-V5-001",
            "sample_id": "measurement-001",
            "row_id": row_id,
            "v3_rule": v3_rule,
            "application_index": 1,
            "v3_bucket": canonical_bucket(v3_bucket),
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
        "schema": "hyperlex.unbind_screen_v5_measurement_freeze.v1",
        "rule": RULE_VERSION,
        "state": "SAMPLE_FROZEN",
        "regression": "REGRESSION_VERIFIED",
        "measurement_eligible": True,
        "rows": len(blind),
        "per_cell": per_cell,
        "strata": "source_pos x token_count",
        "stratum_counts": strata,
        "order": "normalized_text_sha256",
        "excluded_reviewed_surfaces": 141,
        "deduplicated_normalized_lexical_identity": True,
        "sample_sha256": sample_sha,
        "prediction_sha256": prediction_sha,
        "criteria_sha256": criteria_sha,
        "v5_application_count": 1,
        "hand_corrections": 0,
        "operator_labels": None,
        "precision": "NOT_COMPUTABLE",
        "confusion": "NOT_COMPUTABLE",
        "inspected_before_freeze": False,
        "admitted": 0,
        "settled": 0,
        "gold": 0,
        "select_authorized": False,
        "revision_eligible": False,
        "events_sha256": events_sha256(),
    }
    _dump_json(out_dir / "measurement_freeze.json", freeze)
    receipt = json.loads((out_dir / "v5_implementation_receipt.json").read_text(encoding="utf-8"))
    receipt["state"] = "MEASUREMENT_ELIGIBLE"
    receipt["applied_to_measurement"] = True
    receipt["measurement_eligible"] = True
    receipt["measurement_state"] = "SAMPLE_FROZEN"
    receipt["measurement_rows"] = len(blind)
    receipt["measurement_sample_sha256"] = sample_sha
    receipt["measurement_prediction_sha256"] = prediction_sha
    receipt["criteria_sha256"] = criteria_sha
    receipt["v5_application_count"] = 1
    receipt["hand_corrections"] = 0
    receipt["precision"] = "NOT_COMPUTABLE"
    receipt["events_sha256"] = events_sha256()
    _dump_json(out_dir / "v5_implementation_receipt.json", receipt)
    _touch_hypothesis(receipt)
    if events_sha256() != EXPECTED_EVENTS:
        raise SystemExit("ledger events hash changed during the draw")
    if file_sha256(out_dir / "measurement_sample.jsonl") != sample_sha:
        raise SystemExit("sample hash drifted")
    return freeze


def _require_frozen_parents() -> None:
    if events_sha256() != EXPECTED_EVENTS:
        raise SystemExit("ledger events hash changed")
    checks = {
        V4 / "measurement_sample.jsonl": EXPECTED_V4_SAMPLE,
        V4 / "measurement_predictions.jsonl": EXPECTED_V4_PREDICTIONS,
        V4 / "measurement_labels.jsonl": EXPECTED_V4_LABELS,
        LEDGER / "operator-review/HLX-EVAL-UNBIND-SCREEN-V4-HYPOTHESIS-001/ACCEPTANCE.json": EXPECTED_V4_ACCEPTANCE,
        LEDGER / "operator-review/HLX-EVAL-UNBIND-SCREEN-2026-09-27-004/held_out_sample.jsonl": EXPECTED_V3_SAMPLE,
        EVAL3 / "operator/heldout-001.labels.jsonl": EXPECTED_V3_LABELS,
    }
    for path, digest in checks.items():
        if file_sha256(path) != digest:
            raise SystemExit(f"frozen parent changed: {path.name}")


def _implementation_receipt(report: dict, prediction_sha: str, diff_sha: str) -> dict:
    return {
        "schema": "hyperlex.unbind_screen_v5_implementation_receipt.v1",
        "rule": RULE_VERSION,
        "state": "REGRESSION_VERIFIED" if report["measurement_eligible"] else "ENCODED",
        "regression": report["regression"],
        "measurement_eligible": report["measurement_eligible"],
        "authorized": False,
        "encoded": True,
        "applied_to_measurement": False,
        "relation_to_v4": "pure_wrapper_over_a_frozen_v4_bucket",
        "acceptance_sha256": report["acceptance_sha256"],
        "source_sha256": {SCORER.name: file_sha256(SCORER)},
        "replay_rows": report["replay_rows"],
        "diff_rows": report["diff_rows"],
        "prediction_sha256": prediction_sha,
        "diff_sha256": diff_sha,
        "phrase_specific_rule_fired": report["phrase_specific_rule_fired"],
        "failures": report["failures"],
        "moves": report["moves"],
        "operator_conflict_on_move": report["operator_conflict_on_move"],
        "high_unchanged": report["high_unchanged"],
        "reject_unchanged": report["reject_unchanged"],
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
    if hypothesis.get("draft_hypothesis_sha256") != draft or hypothesis.get("acceptance_sha256") != acceptance:
        raise SystemExit("v5 hypothesis no longer points at the frozen draft and acceptance")
    hypothesis["encoded"] = True
    hypothesis["state"] = receipt["state"]
    hypothesis["regression"] = receipt["regression"]
    hypothesis["measurement_eligible"] = receipt["measurement_eligible"]
    hypothesis["applied"] = bool(receipt.get("applied_to_measurement"))
    hypothesis["applied_to_measurement"] = bool(receipt.get("applied_to_measurement"))
    hypothesis["select_authorized"] = False
    hypothesis["authorized"] = False
    hypothesis["revision_eligible"] = False
    hypothesis["operator_conflict_on_move"] = receipt["operator_conflict_on_move"]
    hypothesis["moves"] = receipt["moves"]
    hypothesis["replay_rows"] = receipt["replay_rows"]
    if receipt.get("measurement_sample_sha256"):
        hypothesis["measurement_sample_sha256"] = receipt["measurement_sample_sha256"]
        hypothesis["measurement_rows"] = receipt["measurement_rows"]
        hypothesis["measurement_state"] = receipt["measurement_state"]
        hypothesis["precision"] = "NOT_COMPUTABLE"
    text = json.dumps(hypothesis, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")
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

    parser = argparse.ArgumentParser(description="Replay v5 and, if verified, draw the measurement sample")
    parser.add_argument("command", choices=("replay", "draw"))
    args = parser.parse_args()
    receipt = replay() if args.command == "replay" else draw_measurement()
    summary = {
        key: receipt[key]
        for key in (
            "state", "regression", "measurement_eligible", "measurement_state",
            "replay_rows", "diff_rows", "moves", "operator_conflict_on_move",
            "failures", "phrase_specific_rule_fired", "rows", "sample_sha256",
            "precision", "v5_application_count", "events_sha256", "measurement_rows",
            "measurement_sample_sha256", "high_unchanged", "reject_unchanged",
        )
        if key in receipt
    }
    print(json.dumps(summary, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
