"""Replay the frozen 225-row development manifest through procedure v2.

The replay is a development experiment. It does not draw a measurement sample,
restore the co-lemma shortcut, or write a class back onto the manifest.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from hyperlexical.screen_eval import _error_class, _metrics
from hyperlexical.unbind_sense_screen_v2 import classify, load_exceptions, load_wordnet

LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
HYPERLEX = Path("/home/morpheus/Hyperlex")
WORDNET = LEDGER / "acquisition/sources/wordnet-3.0/wordnet"
OUT = LEDGER / "operator-review/HLX-EVAL-UNBIND-SENSE-SCREEN-V1-HYPOTHESIS-001"
PREDICTIONS = OUT / "development_replay_v2_predictions.jsonl"
REPORT = OUT / "development_replay_v2_report.json"
TRACKER = OUT / "HYPOTHESIS.json"
EVIDENCE = OUT / "DEVELOPMENT_EVIDENCE.json"
PROCEDURE_V1 = OUT / "CLASSIFICATION_PROCEDURE.json"
PROCEDURE_V2 = OUT / "CLASSIFICATION_PROCEDURE.v2.json"
V1_PREDICTIONS = OUT / "development_replay_predictions.jsonl"
V1_REPORT = OUT / "development_replay_report.json"

EXPECTED = {
    PROCEDURE_V1: "4d9dad77d8d315e810863101041229c53570ed16970074c86abaecd0cc3012ad",
    PROCEDURE_V2: "3f4071640d0c9f29cf56f53969a88ec25c635444b87765e77e1b9158470e5662",
    OUT / "ACCEPTANCE.json": "cff6af0f05ec5e12fb29ddfd2ec321addc94c73258c31860345f6d49960065b0",
    OUT / "HYPOTHESIS.draft.json": "93375446b1f4a1f70c60f747a56b626ae667c8944d0eea54deddb9d57d3d9e38",
    EVIDENCE: "0e9b3c1af9dd573bf6e2034640e468e8ab9074e1e76c90cef1f39f68d607bc03",
    OUT / "LINEAGE_RETIREMENT.json": "fd5d9ebb94d7a6e6ea69609c4e2125ec9914f6705ae256b780223bbea2e26f6f",
    OUT / "LEXEME_STRUCTURE_SCREEN.architecture.json": "529defbc2b56152c3290d5b09f309764128b035906797229dab54857cd249df0",
    OUT / "PROCEDURE_V1_ERROR_ANALYSIS.json": "471bc27b89f550fae36b3471daaad282a6dd8735414846cb18aafe1195e0a52e",
    OUT / "PROCEDURE_V1_TO_V2_CHANGE_NOTE.json": "443ce2964d4e4fcd8257055cb1404965faa70b838264b1f623be192d1cae085c",
    V1_PREDICTIONS: "69ea6b8714f3cb6105222d636af3f17bd5c5caac7b290c3c3d87e4efaeedd0ef",
    V1_REPORT: "38ada8bc32d8b19361cc974346d5972f6020eb0c32c2ca537abff4d17f66c7f0",
    TRACKER: "af11d20ebefec5629718617ebacc07d8b4cc36c61e59e829d153b05b9397ca40",
    LEDGER / "events.jsonl": "96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c",
    HYPERLEX / "scripts/shadow/hyperlexical/unbind_sense_screen_v1.py": "531b58422e6f18b42276c6dde36493c7d0f8841556785b4b8911017879f93ad0",
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
STATES = ("YES", "NO", "UNKNOWN", "CONFLICT")


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
        refuse("procedure v2 replay artifacts already exist")
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    rows = evidence["rows"]
    if len(rows) != 225 or any(row.get("sense_class") is not None for row in rows):
        refuse("development manifest is not the unclassified 225-row inventory")
    tracker = json.loads(TRACKER.read_text(encoding="utf-8"))
    if tracker.get("state") != "DEVELOPMENT_ANALYZED" or tracker.get("procedure_v2_state") != "PROCEDURE_V2_FROZEN":
        refuse("tracker is not waiting at PROCEDURE_V2_FROZEN")
    if tracker.get("procedure_v2_encoded") is not False or tracker.get("measurement_sample_drawn") is not False:
        refuse("procedure v2 is already encoded or a sample exists")
    procedure = json.loads(PROCEDURE_V2.read_text(encoding="utf-8"))
    if procedure.get("encoded") is not False or procedure.get("state") != "PROCEDURE_V2_FROZEN":
        refuse("procedure v2 artifact is not the sealed unencoded freeze")

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
        if decision["sense_class"] not in SENSE_CLASSES or decision["compositional_state"] == "NO":
            refuse(f"classifier left the frozen catalog for {row['row_id']}")
        if decision["bucket"] == "HIGH" or decision["sense_class"] == "LEXICALIZED_NONCOMPOSITIONAL":
            refuse("encoder emitted HIGH from the empty compositional NO catalog")
        classified.append((row, decision))

    by_surface = {row["surface"]: decision for row, decision in classified}
    alternation = by_surface.get("as far as possible")
    if alternation is None or (
        alternation["referential_state"],
        alternation["lexicalized_state"],
        alternation["compositional_state"],
        alternation["sense_class"],
    ) != ("NO", "UNKNOWN", "YES", "AMBIGUOUS"):
        refuse("as far as possible did not follow the frozen v2 illustration")
    damascus = by_surface.get("road to damascus")
    if damascus is None or (
        damascus["referential_state"],
        damascus["lexicalized_state"],
        damascus["compositional_state"],
        damascus["sense_class"],
    ) != ("UNKNOWN", "UNKNOWN", "UNKNOWN", "AMBIGUOUS"):
        refuse("road to damascus did not follow the frozen v2 illustration")

    predictions = []
    for row, decision in sorted(classified, key=lambda item: item[0]["row_id"]):
        predictions.append(
            {
                "schema": "hyperlex.unbind_sense_screen_v2_development_row.v1",
                "rule": "RUNE.UNBIND_SENSE_SCREEN.v1",
                "procedure": "hyperlex.unbind_sense_screen_v1_classification_procedure.v2",
                "application_index": 1,
                "row_id": row["row_id"],
                "surface": row["surface"],
                "pos": row["pos"],
                "synset": f"{row['synset_pos']}:{row['synset_offset']}",
                "synset_offset": row["synset_offset"],
                "synset_pos": row["synset_pos"],
                "referential_state": decision["referential_state"],
                "lexicalized_state": decision["lexicalized_state"],
                "compositional_state": decision["compositional_state"],
                "sense_class": decision["sense_class"],
                "bucket": decision["bucket"],
                "primary_evidence_code": decision["primary_evidence_code"],
                "supporting_evidence_codes": decision["supporting_evidence_codes"],
                "evidence_sources": decision["evidence_sources"],
                "confidence_status": decision["confidence_status"],
            }
        )
    prediction_sha = write_jsonl(PREDICTIONS, predictions)

    by_id = {row["row_id"]: decision for row, decision in classified}
    ordered_rows = sorted(rows, key=lambda row: row["row_id"])
    pairs = []
    sense_by_operator = {op: {sense: 0 for sense in SENSE_CLASSES} for op in OPERATOR_BUCKETS}
    error_rows = {name: [] for name in ("false_high", "false_reject", "false_secondary", "false_quarantine")}
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
                    "referential_state": decision["referential_state"],
                    "lexicalized_state": decision["lexicalized_state"],
                    "compositional_state": decision["compositional_state"],
                    "primary_evidence_code": decision["primary_evidence_code"],
                    "evidence_sources": decision["evidence_sources"],
                }
            )
    metrics = _metrics(pairs)
    sense_counts = Counter(row["sense_class"] for row in predictions)
    bucket_counts = Counter(row["bucket"] for row in predictions)
    evidence_counts = Counter(row["primary_evidence_code"] for row in predictions)
    state_counts = {
        "referential": Counter(row["referential_state"] for row in predictions),
        "lexicalized": Counter(row["lexicalized_state"] for row in predictions),
        "compositional": Counter(row["compositional_state"] for row in predictions),
    }
    triples = Counter(
        f"{row['referential_state']}|{row['lexicalized_state']}|{row['compositional_state']}"
        for row in predictions
    )

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
        "schema": "hyperlex.unbind_sense_screen_v2_development_replay.v1",
        "rule": "RUNE.UNBIND_SENSE_SCREEN.v1",
        "procedure": "hyperlex.unbind_sense_screen_v1_classification_procedure.v2",
        "role": "development experiment, not validation",
        "question": "Can the frozen WordNet-only evidence model instantiate the intended classes, especially LEXICALIZED_NONCOMPOSITIONAL, without the co-lemma shortcut?",
        "not_a_validation_set": True,
        "state": "DEVELOPMENT_ANALYZED_V2",
        "state_path": [
            "PROCEDURE_V2_FROZEN",
            "ENCODE_PROCEDURE_V2_AUTHORIZATION",
            "ENCODED",
            "225_ROW_DEVELOPMENT_REPLAY",
            "DEVELOPMENT_ANALYZED_V2",
        ],
        "analyzed_at": when,
        "rows": 225,
        "applications_per_row": 1,
        "prediction_sha256": prediction_sha,
        "procedure_v2_sha256": EXPECTED[PROCEDURE_V2],
        "procedure_v2_mutated": False,
        "procedure_v1_sha256": EXPECTED[PROCEDURE_V1],
        "procedure_v1_mutated": False,
        "acceptance_sha256": EXPECTED[OUT / "ACCEPTANCE.json"],
        "development_evidence_sha256": EXPECTED[EVIDENCE],
        "development_manifest_sense_classes_written": False,
        "v1_prediction_sha256": EXPECTED[V1_PREDICTIONS],
        "v1_report_sha256": EXPECTED[V1_REPORT],
        "lexeme_architecture_sha256": EXPECTED[OUT / "LEXEME_STRUCTURE_SCREEN.architecture.json"],
        "lexeme_architecture_mutated": False,
        "events_sha256": EXPECTED[LEDGER / "events.jsonl"],
        "sense_class_counts": {name: sense_counts[name] for name in SENSE_CLASSES},
        "bucket_counts": {name: bucket_counts[name] for name in BUCKETS},
        "evidence_state_counts": {
            dimension: {state: counts[state] for state in STATES}
            for dimension, counts in state_counts.items()
        },
        "evidence_state_triples": dict(sorted(triples.items())),
        "operator_vs_bucket_confusion": metrics["confusion_matrix"],
        "operator_vs_sense_class": sense_by_operator,
        "ambiguous_count": sense_counts["AMBIGUOUS"],
        "ambiguous_rate_fraction": fraction(sense_counts["AMBIGUOUS"], 225),
        "ambiguous_rate_is_not_a_success_criterion": True,
        "high_support": bucket_counts["HIGH"],
        "high_support_is_zero": bucket_counts["HIGH"] == 0,
        "lexicalized_noncompositional_support": sense_counts["LEXICALIZED_NONCOMPOSITIONAL"],
        "lexicalized_noncompositional_instantiated": sense_counts["LEXICALIZED_NONCOMPOSITIONAL"] > 0,
        "colemma_shortcut_restored": False,
        "compositional_no_emitted": state_counts["compositional"]["NO"],
        "evidence_code_counts": dict(sorted(evidence_counts.items())),
        "HIGH": bucket_block("HIGH"),
        "SECONDARY": bucket_block("SECONDARY"),
        "REJECT": bucket_block("REJECT"),
        "QUARANTINE": bucket_block("QUARANTINE"),
        "referential_precision_fraction": bucket_block("REJECT")["precision_fraction"],
        "referential_recall_fraction": bucket_block("REJECT")["recall_fraction"],
        "lexicalized_compositional_support": sense_counts["LEXICALIZED_COMPOSITIONAL"],
        "lexicalized_compositional_support_is_a_readiness_signal_only": True,
        "false_high": len(error_rows["false_high"]),
        "false_reject": len(error_rows["false_reject"]),
        "false_secondary": len(error_rows["false_secondary"]),
        "false_quarantine": len(error_rows["false_quarantine"]),
        "false_high_rows": error_rows["false_high"],
        "false_reject_rows": error_rows["false_reject"],
        "diagnostics_are_not_pass_fail": True,
        "measurement_bar_applied": False,
        "measurement_sample_drawn": False,
        "measurement_eligible": False,
        "revision_eligible": False,
        "select_authorized": False,
        "admitted": 0,
        "settled": 0,
        "gold": 0,
        "ledger_appended": False,
        "next_legal_transition": "V2_DEVELOPMENT_RESULT_REVIEW",
        "next_transition_authorized": False,
    }
    report_sha = write_json(REPORT, report)
    if any(row.get("sense_class") is not None for row in json.loads(EVIDENCE.read_text(encoding="utf-8"))["rows"]):
        refuse("replay wrote a sense class onto the development manifest")
    for path, expected in EXPECTED.items():
        if path == TRACKER:
            continue
        if sha256(path) != expected:
            refuse(f"replay mutated {path.name}")

    tracker["previous_state"] = "DEVELOPMENT_ANALYZED"
    tracker["previous_tracker_sha256"] = EXPECTED[TRACKER]
    tracker["v1_screen_state"] = "DEVELOPMENT_ANALYZED"
    tracker["state"] = "DEVELOPMENT_ANALYZED_V2"
    tracker["procedure_v2_state"] = "DEVELOPMENT_ANALYZED_V2"
    tracker["procedure_v2_encoded"] = True
    tracker["procedure_v2_encoding_authorized"] = True
    tracker["procedure_v2_applied"] = True
    tracker["procedure_v2_development_replay_run"] = True
    tracker["procedure_v2_rows_classified"] = 225
    tracker["procedure_v2_prediction_sha256"] = prediction_sha
    tracker["procedure_v2_report_sha256"] = report_sha
    tracker["measurement_sample_drawn"] = False
    tracker["measurement_eligible"] = False
    tracker["revision_eligible"] = False
    tracker["select_authorized"] = False
    tracker["authorized"] = False
    tracker["next_legal_transition"] = "V2_DEVELOPMENT_RESULT_REVIEW"
    tracker["next_transition_authorized"] = False
    tracker["high_support_v2"] = bucket_counts["HIGH"]
    tracker["lexicalized_noncompositional_support_v2"] = sense_counts["LEXICALIZED_NONCOMPOSITIONAL"]
    tracker_sha = write_json(TRACKER, tracker)
    if sha256(PROCEDURE_V2) != EXPECTED[PROCEDURE_V2] or sha256(EVIDENCE) != EXPECTED[EVIDENCE]:
        refuse("tracker update mutated a sealed artifact")
    print(json.dumps({
        "prediction_sha256": prediction_sha,
        "report_sha256": report_sha,
        "tracker_sha256": tracker_sha,
        "sense_class_counts": report["sense_class_counts"],
        "bucket_counts": report["bucket_counts"],
        "evidence_state_counts": report["evidence_state_counts"],
        "ambiguous_rate_fraction": report["ambiguous_rate_fraction"],
        "HIGH": report["HIGH"],
        "SECONDARY": report["SECONDARY"],
        "REJECT": report["REJECT"],
        "false_high": report["false_high"],
        "false_reject": report["false_reject"],
        "false_secondary": report["false_secondary"],
        "lexicalized_compositional_support": report["lexicalized_compositional_support"],
        "lexicalized_noncompositional_instantiated": report["lexicalized_noncompositional_instantiated"],
        "evidence_code_counts": report["evidence_code_counts"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
