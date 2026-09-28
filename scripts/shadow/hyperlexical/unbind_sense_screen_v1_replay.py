"""Replay the frozen 225-row development manifest through the encoded sense screen.

The replay is development evidence. It does not draw a measurement sample,
revise the frozen procedure, or write a sense class back onto the manifest.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from hyperlexical.screen_eval import _error_class, _metrics
from hyperlexical.unbind_sense_screen_v1 import classify, load_exceptions, load_wordnet

LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
HYPERLEX = Path("/home/morpheus/Hyperlex")
WORDNET = LEDGER / "acquisition/sources/wordnet-3.0/wordnet"
OUT = LEDGER / "operator-review/HLX-EVAL-UNBIND-SENSE-SCREEN-V1-HYPOTHESIS-001"
PREDICTIONS = OUT / "development_replay_predictions.jsonl"
REPORT = OUT / "development_replay_report.json"
TRACKER = OUT / "HYPOTHESIS.json"
EVIDENCE = OUT / "DEVELOPMENT_EVIDENCE.json"
PROCEDURE = OUT / "CLASSIFICATION_PROCEDURE.json"

EXPECTED = {
    OUT / "ACCEPTANCE.json": "cff6af0f05ec5e12fb29ddfd2ec321addc94c73258c31860345f6d49960065b0",
    OUT / "HYPOTHESIS.draft.json": "93375446b1f4a1f70c60f747a56b626ae667c8944d0eea54deddb9d57d3d9e38",
    EVIDENCE: "0e9b3c1af9dd573bf6e2034640e468e8ab9074e1e76c90cef1f39f68d607bc03",
    OUT / "LINEAGE_RETIREMENT.json": "fd5d9ebb94d7a6e6ea69609c4e2125ec9914f6705ae256b780223bbea2e26f6f",
    OUT / "LEXEME_STRUCTURE_SCREEN.architecture.json": "529defbc2b56152c3290d5b09f309764128b035906797229dab54857cd249df0",
    PROCEDURE: "4d9dad77d8d315e810863101041229c53570ed16970074c86abaecd0cc3012ad",
    TRACKER: "f9c4757b6eec558b5e1baf644bcf33c27c949807e7f00cd15df869eb6411de31",
    LEDGER / "events.jsonl": "96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c",
    HYPERLEX / "scripts/shadow/hyperlexical/unbind_screen_v3.py": "179d8dcc112214c70566bd3c9a0397e1ebab9131666b0ca1f2a3817973aaccc6",
    HYPERLEX / "scripts/shadow/hyperlexical/unbind_screen_v4.py": "f1e86e2f21544655cda6a136885a186b20885d501cb7ea9c75e18b3dd4a42377",
    HYPERLEX / "scripts/shadow/hyperlexical/unbind_screen_v5.py": "70504574523f2e8fde0fb974e3027205dded2c96213dd997f44475ea6856f948",
    HYPERLEX / "scripts/shadow/hyperlexical/unbind_screen_v6.py": "59699496c15aaedfbe69a7e49b5c6e62d1e543ce5a1e0e9a0255a98a62036fba",
    HYPERLEX / "scripts/shadow/hyperlexical/unbind_screen_v7.py": "73335bde8eec262ebecfedfc0d0ecb0a965da5c6b66e53c16f2aee2f38b061ab",
}
SENSE_CLASSES = (
    "REFERENTIAL",
    "LEXICALIZED_NONCOMPOSITIONAL",
    "LEXICALIZED_COMPOSITIONAL",
    "ORDINARY_COMPOSITIONAL",
    "AMBIGUOUS",
)
BUCKETS = ("HIGH", "SECONDARY", "REJECT", "QUARANTINE")
OPERATOR_BUCKETS = BUCKETS + ("UNRESOLVED",)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def refuse(message: str) -> None:
    raise SystemExit(message)


def write_json(path: Path, payload: dict) -> str:
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_jsonl(path: Path, rows: list[dict]) -> str:
    text = "".join(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fraction(numerator: int, denominator: int) -> str | None:
    if denominator == 0:
        return None
    return f"{numerator}/{denominator}"


def main() -> None:
    for path, expected in EXPECTED.items():
        found = sha256(path)
        if found != expected:
            refuse(f"hash mismatch {path.name}: {found}")
    if PREDICTIONS.exists() or REPORT.exists():
        refuse("development replay artifacts already exist")
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    if evidence.get("sense_classes_assigned") is not False:
        refuse("development manifest already records assigned sense classes")
    rows = evidence["rows"]
    if len(rows) != 225 or evidence.get("row_count") != 225:
        refuse("development manifest is not the frozen 225-row inventory")
    if len({row["row_id"] for row in rows}) != 225:
        refuse("development row ids are not unique")
    if any(row.get("sense_class") is not None for row in rows):
        refuse("a development row already has a sense class")
    tracker = json.loads(TRACKER.read_text(encoding="utf-8"))
    if tracker.get("state") != "PROCEDURE_FROZEN" or tracker.get("encoded") is not False:
        refuse("tracker is not waiting at PROCEDURE_FROZEN")
    procedure = json.loads(PROCEDURE.read_text(encoding="utf-8"))
    if procedure.get("encoded") is not False or procedure.get("development_replay_run") is not False:
        refuse("frozen procedure artifact is not in its sealed unencoded state")

    synsets, glosses = load_wordnet(WORDNET)
    exceptions = load_exceptions(WORDNET)
    targets = {key: synset.lemmas for key, synset in synsets.items()}
    classified = []
    for row in rows:
        key = (row["synset_pos"], row["synset_offset"])
        synset = synsets.get(key)
        gloss = glosses.get(key)
        if synset is None or gloss is None:
            refuse(f"missing synset {row['synset_pos']} {row['synset_offset']}")
        if gloss != row["gloss"]:
            refuse(f"frozen gloss does not match the data-line first clause for {row['row_id']}")
        decision = classify(row["surface"], row["gloss"], synset, exceptions, targets)
        if decision["sense_class"] not in SENSE_CLASSES or decision["bucket"] not in BUCKETS:
            refuse(f"classifier returned an unknown class for {row['row_id']}")
        classified.append((row, decision))

    predictions = []
    for row, decision in sorted(classified, key=lambda item: item[0]["row_id"]):
        predictions.append(
            {
                "schema": "hyperlex.unbind_sense_screen_v1_development_row.v1",
                "rule": "RUNE.UNBIND_SENSE_SCREEN.v1",
                "application_index": 1,
                "row_id": row["row_id"],
                "surface": row["surface"],
                "pos": row["pos"],
                "synset": f"{row['synset_pos']}:{row['synset_offset']}",
                "synset_offset": row["synset_offset"],
                "synset_pos": row["synset_pos"],
                "sense_class": decision["sense_class"],
                "bucket": decision["bucket"],
                "primary_evidence_code": decision["primary_evidence_code"],
                "evidence_source": decision["evidence_source"],
                "confidence_status": decision["confidence_status"],
            }
        )
    if any("operator_bucket" in row or "historical_unbind_screen" in row for row in predictions):
        refuse("prediction rows carry operator or historical fields")
    prediction_sha = write_jsonl(PREDICTIONS, predictions)

    by_id = {row["row_id"]: decision for row, decision in classified}
    ordered_rows = sorted(rows, key=lambda row: row["row_id"])
    pairs = []
    sense_by_operator = {op: {sense: 0 for sense in SENSE_CLASSES} for op in OPERATOR_BUCKETS}
    error_rows = {"false_high": [], "false_reject": [], "false_secondary": [], "false_quarantine": []}
    for row in ordered_rows:
        decision = by_id[row["row_id"]]
        operator = row["operator_bucket"]
        pairs.append((row["row_id"], decision["bucket"], operator, decision["primary_evidence_code"]))
        sense_by_operator[operator][decision["sense_class"]] += 1
        kind = _error_class(decision["bucket"], operator)
        if kind:
            error_rows[kind].append(
                {
                    "row_id": row["row_id"],
                    "surface": row["surface"],
                    "operator_bucket": operator,
                    "bucket": decision["bucket"],
                    "sense_class": decision["sense_class"],
                    "primary_evidence_code": decision["primary_evidence_code"],
                    "evidence_source": decision["evidence_source"],
                }
            )
    metrics = _metrics(pairs)
    sense_counts = Counter(row["sense_class"] for row in predictions)
    bucket_counts = Counter(row["bucket"] for row in predictions)
    evidence_counts = Counter(row["primary_evidence_code"] for row in predictions)
    source_counts = Counter(row["evidence_source"] for row in predictions)
    confidence_counts = Counter(row["confidence_status"] for row in predictions)
    ambiguous = sense_counts["AMBIGUOUS"]

    def bucket_block(name: str) -> dict:
        stats = metrics["per_bucket"][name]
        support = stats["support"]
        predicted = bucket_counts[name]
        true_positive = sum(1 for _i, pred, op, _r in pairs if pred == name and op == name)
        return {
            "precision": stats["precision"],
            "precision_fraction": fraction(true_positive, predicted),
            "recall": stats["recall"],
            "recall_fraction": fraction(true_positive, support),
            "operator_support": support,
            "predicted": predicted,
        }

    when = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    report = {
        "schema": "hyperlex.unbind_sense_screen_v1_development_replay.v1",
        "rule": "RUNE.UNBIND_SENSE_SCREEN.v1",
        "role": "development evidence, not validation",
        "not_a_validation_set": True,
        "tuning_on_these_rows_is_not_validation": True,
        "state": "DEVELOPMENT_ANALYZED",
        "state_path": [
            "PROCEDURE_FROZEN",
            "ENCODE_AUTHORIZED",
            "ENCODED",
            "225_ROW_DEVELOPMENT_REPLAY",
            "DEVELOPMENT_ANALYZED",
        ],
        "analyzed_at": when,
        "rows": 225,
        "application_index": 1,
        "applications_per_row": 1,
        "prediction_sha256": prediction_sha,
        "procedure_sha256": EXPECTED[PROCEDURE],
        "procedure_mutated": False,
        "acceptance_sha256": EXPECTED[OUT / "ACCEPTANCE.json"],
        "acceptance_mutated": False,
        "draft_hypothesis_sha256": EXPECTED[OUT / "HYPOTHESIS.draft.json"],
        "development_evidence_sha256": EXPECTED[EVIDENCE],
        "development_manifest_sense_classes_written": False,
        "lexeme_architecture_sha256": EXPECTED[OUT / "LEXEME_STRUCTURE_SCREEN.architecture.json"],
        "lexeme_architecture_mutated": False,
        "lineage_retirement_sha256": EXPECTED[OUT / "LINEAGE_RETIREMENT.json"],
        "events_sha256": EXPECTED[LEDGER / "events.jsonl"],
        "sense_class_counts": {name: sense_counts[name] for name in SENSE_CLASSES},
        "bucket_counts": {name: bucket_counts[name] for name in BUCKETS},
        "operator_vs_bucket_confusion": metrics["confusion_matrix"],
        "operator_vs_sense_class": sense_by_operator,
        "ambiguous_count": ambiguous,
        "ambiguous_rate": ambiguous / 225,
        "ambiguous_rate_fraction": fraction(ambiguous, 225),
        "ambiguous_rate_is_expected_measurement": True,
        "high_ambiguity_was_not_repaired": True,
        "absence_of_evidence_is_not_secondary": True,
        "evidence_code_counts": dict(sorted(evidence_counts.items())),
        "evidence_source_counts": dict(sorted(source_counts.items())),
        "confidence_status_counts": dict(sorted(confidence_counts.items())),
        "HIGH": bucket_block("HIGH"),
        "SECONDARY": bucket_block("SECONDARY"),
        "REJECT": bucket_block("REJECT"),
        "QUARANTINE": bucket_block("QUARANTINE"),
        "quarantine_support": metrics["per_bucket"]["QUARANTINE"]["support"],
        "false_high": len(error_rows["false_high"]),
        "false_reject": len(error_rows["false_reject"]),
        "false_secondary": len(error_rows["false_secondary"]),
        "false_quarantine": len(error_rows["false_quarantine"]),
        "false_secondary_is_descriptive_only": True,
        "false_high_rows": error_rows["false_high"],
        "false_reject_rows": error_rows["false_reject"],
        "outer_bucket_metrics_are_descriptive": True,
        "measurement_bar_applied": False,
        "measurement_sample_drawn": False,
        "measurement_eligible": False,
        "revision_eligible": False,
        "select_authorized": False,
        "admitted": 0,
        "settled": 0,
        "gold": 0,
        "ledger_appended": False,
        "next_legal_transition": "MEASUREMENT_AUTHORIZATION",
        "next_transition_authorized": False,
    }
    report_sha = write_json(REPORT, report)

    untouched = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    if any(row.get("sense_class") is not None for row in untouched["rows"]):
        refuse("replay wrote a sense class onto the development manifest")
    if sha256(EVIDENCE) != EXPECTED[EVIDENCE] or sha256(PROCEDURE) != EXPECTED[PROCEDURE]:
        refuse("replay mutated a sealed artifact")

    tracker["previous_state"] = "PROCEDURE_FROZEN"
    tracker["previous_tracker_sha256"] = EXPECTED[TRACKER]
    tracker["state"] = "DEVELOPMENT_ANALYZED"
    tracker["encoded"] = True
    tracker["encoding_authorized"] = True
    tracker["applied"] = True
    tracker["development_replay_run"] = True
    tracker["rows_classified"] = 225
    tracker["measurement_sample_drawn"] = False
    tracker["measurement_eligible"] = False
    tracker["revision_eligible"] = False
    tracker["next_legal_transition"] = "MEASUREMENT_AUTHORIZATION"
    tracker["next_transition_authorized"] = False
    tracker["select_authorized"] = False
    tracker["authorized"] = False
    tracker["prediction_sha256"] = prediction_sha
    tracker["report_sha256"] = report_sha
    tracker["ambiguous_rate_fraction"] = report["ambiguous_rate_fraction"]
    tracker["high_ambiguity_was_not_repaired"] = True
    tracker_sha = write_json(TRACKER, tracker)
    print(json.dumps({
        "prediction_sha256": prediction_sha,
        "report_sha256": report_sha,
        "tracker_sha256": tracker_sha,
        "sense_class_counts": report["sense_class_counts"],
        "bucket_counts": report["bucket_counts"],
        "ambiguous_rate_fraction": report["ambiguous_rate_fraction"],
        "HIGH": report["HIGH"],
        "SECONDARY": report["SECONDARY"],
        "REJECT": report["REJECT"],
        "QUARANTINE": report["QUARANTINE"],
        "false_high": report["false_high"],
        "false_reject": report["false_reject"],
        "false_secondary": report["false_secondary"],
        "evidence_code_counts": report["evidence_code_counts"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
