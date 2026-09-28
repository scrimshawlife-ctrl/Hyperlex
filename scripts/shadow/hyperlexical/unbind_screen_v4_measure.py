"""Replay and measurement driver for the v4 unbind screen.

This module does not admit, settle, or append the ledger.
The forbidden-surface tuple is a regression probe. The scorer does not import it.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from hyperlexical.holdout_guard import normalized_text_sha256
from hyperlexical.unbind_screen_v3 import gloss_for, screen
from hyperlexical.unbind_screen_v4 import (
    RULE_VERSION,
    SUCCESS_CRITERIA,
    WordNetLexicon,
    apply_v4,
    assess,
    canonical_bucket,
    measurement_allowed,
    normalize_lexical,
    rule_surface_violations,
)

LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
WORDNET = LEDGER / "acquisition/sources/wordnet-3.0/wordnet"
TRAIN = Path("/home/morpheus/hlx-private/d1-spark-tree-20260924T213846Z/morph78-train-export.jsonl")
FIT = LEDGER / "operator-review/HLX-EVAL-UNBIND-SCREEN-2026-09-27-004/development_fit.json"
EVAL = LEDGER / "operator-review/HLX-EVAL-UNBIND-SCREEN-V3-001"
OUT = LEDGER / "operator-review/HLX-EVAL-UNBIND-SCREEN-V4-001/unbind_screen_v4"
EXPECTED_EVENTS = "96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c"
EXPECTED_SAMPLE = "8af5644061a7a60fc5620c217e15a4ec8145f170edee9d8ff4e2999e7b86605e"
EXPECTED_LABELS = "4e7bae5986e6345de62086af270a1d1a6902103d69a50d8f0b1e4e0fe01ecde5"
EXPECTED_ACCEPTANCE = "ffb39e38784a56ae15bae51718c61b78fc861e48399936dbed57fb7d0754c55b"
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
)
LEAK_KEYS = frozenset({
    "predicted", "predicted_bucket", "bucket", "relation", "rule", "phase",
    "operator", "operator_bucket", "forecast", "diagnostic", "v4", "v3",
    "primary_evidence", "supporting_evidence", "evidence", "v3_bucket", "v4_bucket",
})
SCORER_FILES = (
    Path(__file__).with_name("unbind_screen_v3.py"),
    Path(__file__).with_name("unbind_screen_v4.py"),
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def events_sha256() -> str:
    return file_sha256(LEDGER / "events.jsonl")


def scorer_violations() -> list[str]:
    found = []
    for path in SCORER_FILES:
        found.extend(rule_surface_violations(path.read_text(encoding="utf-8"), PROBE_SURFACES))
    return found


def load_replay_rows() -> list[dict]:
    fit = json.loads(FIT.read_text(encoding="utf-8"))
    rows = []
    for raw in fit["rows"]:
        rows.append({
            "surface": raw["text"],
            "pos": raw["source_pos"],
            "gloss": raw.get("gloss") or "",
            "v3_bucket": raw["predicted"],
            "operator_bucket": raw["operator"],
            "split": raw.get("split") or "development",
        })
    labels = {
        json.loads(line)["row_id"]: json.loads(line)
        for line in (EVAL / "operator/heldout-001.labels.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    predictions = {
        json.loads(line)["row_id"]: json.loads(line)
        for line in (EVAL / "predictions/heldout-001.predictions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    reviews = {
        json.loads(line)["row_id"]: json.loads(line)
        for line in (EVAL / "operator/heldout-001.review.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    if set(labels) != set(predictions) or set(labels) != set(reviews):
        raise SystemExit("held-out label, prediction, and review identities differ")
    for row_id, review in reviews.items():
        rows.append({
            "surface": review["surface"],
            "pos": review["pos"],
            "gloss": review.get("gloss") or "",
            "v3_bucket": predictions[row_id]["bucket"],
            "operator_bucket": labels[row_id]["operator_bucket"],
            "split": "held_out_29",
        })
    if len(rows) != 113:
        raise SystemExit(f"reviewed surfaces are {len(rows)}, not 113")
    if len({row["surface"] for row in rows}) != 113:
        raise SystemExit("reviewed surfaces are not unique")
    return rows


def replay(out_dir: Path = OUT) -> dict:
    if events_sha256() != EXPECTED_EVENTS:
        raise SystemExit("ledger events hash changed before replay")
    sample_sha = file_sha256(
        LEDGER / "operator-review/HLX-EVAL-UNBIND-SCREEN-2026-09-27-004/held_out_sample.jsonl"
    )
    label_sha = file_sha256(EVAL / "operator/heldout-001.labels.jsonl")
    if sample_sha != EXPECTED_SAMPLE or label_sha != EXPECTED_LABELS:
        raise SystemExit("v3 sample or label hash changed")
    lexicon = WordNetLexicon(WORDNET)
    predictions = []
    assessed_rows = []
    for raw in load_replay_rows():
        decision = apply_v4(raw["v3_bucket"], raw["surface"], raw["gloss"], raw["pos"], lexicon)
        row_id = normalized_text_sha256(raw["surface"])
        record = {
            "schema": "hyperlex.unbind_screen_v4_replay_row.v1",
            "row_id": row_id,
            "split": raw["split"],
            "surface": raw["surface"],
            "pos": raw["pos"],
            "gloss": raw["gloss"],
            "operator_bucket": canonical_bucket(raw["operator_bucket"]),
            **decision,
        }
        predictions.append(record)
        assessed_rows.append(record)
    violations = scorer_violations()
    report = assess(assessed_rows, phrase_specific_rule_fired=bool(violations), expected_rows=113)
    report["phrase_violations"] = violations
    report["acceptance_sha256"] = EXPECTED_ACCEPTANCE
    report["events_sha256"] = events_sha256()
    report["v3_sample_sha256"] = sample_sha
    report["v3_label_sha256"] = label_sha
    predictions.sort(key=lambda row: row["row_id"])
    changed = [row for row in predictions if row["v3_bucket"] != row["v4_bucket"]]
    changed.sort(key=lambda row: row["row_id"])
    out_dir.mkdir(parents=True, exist_ok=True)
    prediction_sha = _dump_jsonl(out_dir / "replay_113_predictions.jsonl", predictions)
    diff_sha = _dump_jsonl(out_dir / "replay_113_diff.jsonl", changed)
    report["prediction_sha256"] = prediction_sha
    report["diff_sha256"] = diff_sha
    report["diff_rows"] = len(changed)
    _dump_json(out_dir / "replay_113_gate_report.json", report)
    receipt = _implementation_receipt(report, prediction_sha, diff_sha)
    _dump_json(out_dir / "implementation_receipt.json", receipt)
    if events_sha256() != EXPECTED_EVENTS:
        raise SystemExit("ledger events hash changed during replay")
    return receipt


def draw_measurement(out_dir: Path = OUT, per_cell: int = 2) -> dict:
    receipt_path = out_dir / "implementation_receipt.json"
    report = json.loads((out_dir / "replay_113_gate_report.json").read_text(encoding="utf-8"))
    if not measurement_allowed(report):
        raise SystemExit("measurement draw refused: regression is not verified")
    if events_sha256() != EXPECTED_EVENTS:
        raise SystemExit("ledger events hash changed before the draw")
    criteria_sha = _dump_json(out_dir / "measurement_criteria.json", dict(SUCCESS_CRITERIA))
    reviewed = load_replay_rows()
    blocked_hash = {normalized_text_sha256(row["surface"]) for row in reviewed}
    blocked_norm = {normalize_lexical(row["surface"]) for row in reviewed}
    picked, strata = _stratified_sample(blocked_hash, blocked_norm, per_cell=per_cell)
    lexicon = WordNetLexicon(WORDNET)
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
        decision = apply_v4(v3_bucket, surface, gloss, pos, lexicon)
        row_id = normalized_text_sha256(surface)
        provenance = {
            "source": "wordnet-3.0",
            "source_pos": pos,
            "excluded_reviewed_surfaces": 113,
        }
        blind.append({
            "schema": "hyperlex.unbind_screen_review_row.v1",
            "evaluation_id": "HLX-EVAL-UNBIND-SCREEN-V4-001",
            "sample_id": "measurement-001",
            "row_id": row_id,
            "surface": surface,
            "pos": pos,
            "token_count": len(tokens),
            "gloss": gloss,
            "provenance": provenance,
        })
        leaked = LEAK_KEYS.intersection(blind[-1])
        if leaked:
            raise SystemExit(f"blind row carries {sorted(leaked)}")
        predictions.append({
            "schema": "hyperlex.unbind_screen_v4_measurement_prediction.v1",
            "evaluation_id": "HLX-EVAL-UNBIND-SCREEN-V4-001",
            "sample_id": "measurement-001",
            "row_id": row_id,
            "v3_rule": v3_rule,
            "application_index": 1,
            **decision,
        })
    if {row["surface"] for row in blind} & {row["surface"] for row in reviewed}:
        raise SystemExit("measurement sample reuses a reviewed surface")
    if {normalize_lexical(row["surface"]) for row in blind} & blocked_norm:
        raise SystemExit("measurement sample reuses a normalized reviewed identity")
    blind.sort(key=lambda row: row["row_id"])
    predictions.sort(key=lambda row: row["row_id"])
    sample_sha = _dump_jsonl(out_dir / "measurement_sample.jsonl", blind)
    prediction_sha = _dump_jsonl(out_dir / "measurement_predictions.jsonl", predictions)
    freeze = {
        "schema": "hyperlex.unbind_screen_v4_measurement_freeze.v1",
        "rule": RULE_VERSION,
        "state": "SAMPLE_FROZEN",
        "regression": "REGRESSION_VERIFIED",
        "measurement_eligible": True,
        "rows": len(blind),
        "per_cell": per_cell,
        "strata": "source_pos x token_count",
        "stratum_counts": strata,
        "order": "normalized_text_sha256",
        "excluded_reviewed_surfaces": 113,
        "deduplicated_normalized_lexical_identity": True,
        "sample_sha256": sample_sha,
        "prediction_sha256": prediction_sha,
        "criteria_sha256": criteria_sha,
        "v4_application_count": 1,
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
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["applied_to_measurement"] = True
    receipt["measurement_eligible"] = True
    receipt["measurement_state"] = "SAMPLE_FROZEN"
    receipt["measurement_rows"] = len(blind)
    receipt["measurement_sample_sha256"] = sample_sha
    receipt["measurement_prediction_sha256"] = prediction_sha
    receipt["criteria_sha256"] = criteria_sha
    receipt["v4_application_count"] = 1
    receipt["hand_corrections"] = 0
    receipt["precision"] = "NOT_COMPUTABLE"
    receipt["events_sha256"] = events_sha256()
    _dump_json(receipt_path, receipt)
    if events_sha256() != EXPECTED_EVENTS:
        raise SystemExit("ledger events hash changed during the draw")
    return freeze


def _implementation_receipt(report: dict, prediction_sha: str, diff_sha: str) -> dict:
    source_sha = {
        path.name: file_sha256(path)
        for path in SCORER_FILES
    }
    return {
        "schema": "hyperlex.unbind_screen_v4_implementation_receipt.v1",
        "rule": RULE_VERSION,
        "state": "ENCODED",
        "regression": report["regression"],
        "measurement_eligible": report["measurement_eligible"],
        "authorized": False,
        "encoded": True,
        "applied_to_measurement": False,
        "relation_to_v3": "proposed_coverage_extension_only",
        "acceptance_sha256": EXPECTED_ACCEPTANCE,
        "source_sha256": source_sha,
        "replay_rows": report["replay_rows"],
        "diff_rows": report["diff_rows"],
        "prediction_sha256": prediction_sha,
        "diff_sha256": diff_sha,
        "phrase_specific_rule_fired": report["phrase_specific_rule_fired"],
        "failures": report["failures"],
        "moves": report["moves"],
        "operator_conflict_on_move": report["operator_conflict_on_move"],
        "assertions": report["assertions"],
        "v3_sample_sha256": report["v3_sample_sha256"],
        "v3_label_sha256": report["v3_label_sha256"],
        "events_sha256": report["events_sha256"],
        "revision_eligible": False,
        "select_authorized": False,
        "admitted": 0,
        "settled": 0,
        "gold": 0,
    }


def _stratified_sample(
    blocked_hash: set[str], blocked_norm: set[str], *, per_cell: int
) -> tuple[list[dict], list[dict]]:
    from hyperlexical.clean_unbind import (
        WORDNET_LICENSE,
        gate_rows,
        load_jsonl,
        read_wordnet_index,
        rows_from_wordnet_atoms,
    )
    from hyperlexical.identity_ledger import IdentityLedger

    atoms = read_wordnet_index(WORDNET)
    rows = rows_from_wordnet_atoms(atoms, license=WORDNET_LICENSE)
    train_rows = load_jsonl(TRAIN)
    ledger = IdentityLedger.load(LEDGER)
    admissible, _rejections, _account = gate_rows(
        rows,
        train_rows=train_rows,
        ledger=ledger,
        require_settlement=False,
    )
    best: dict[str, dict] = {}
    for row in admissible:
        if row.get("role_scheme") != "positional":
            continue
        surface = str(row.get("text") or "")
        identity = normalize_lexical(surface)
        digest = normalized_text_sha256(surface)
        if digest in blocked_hash or identity in blocked_norm:
            continue
        current = best.get(identity)
        if current is None or digest < normalized_text_sha256(str(current.get("text") or "")):
            best[identity] = row
    cells: dict[tuple[str, int], list[dict]] = {}
    for row in best.values():
        fillers = [str(tok) for tok in row.get("fillers") or []]
        cells.setdefault((str(row.get("source_pos") or ""), len(fillers)), []).append(row)
    picked = []
    strata = []
    for key in sorted(cells):
        group = cells[key]
        group.sort(key=lambda row: normalized_text_sha256(str(row.get("text") or "")))
        taken = group[:per_cell]
        picked.extend(taken)
        strata.append({
            "source_pos": key[0],
            "token_count": key[1],
            "available": len(group),
            "taken": len(taken),
        })
    if not picked:
        raise SystemExit("measurement sample is empty")
    return picked, strata


def _dump_json(path: Path, payload: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, sort_keys=True, ensure_ascii=True, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _dump_jsonl(path: Path, rows: list[dict]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Replay v4 and, if verified, draw the measurement sample")
    parser.add_argument("command", choices=("replay", "draw"))
    args = parser.parse_args()
    if args.command == "replay":
        receipt = replay()
    else:
        receipt = draw_measurement()
    summary = {
        key: receipt[key]
        for key in receipt
        if key in {
            "state", "regression", "measurement_eligible", "measurement_state",
            "replay_rows", "diff_rows", "moves", "operator_conflict_on_move",
            "failures", "phrase_specific_rule_fired", "rows", "sample_sha256",
            "precision", "v4_application_count", "events_sha256", "measurement_rows",
            "measurement_sample_sha256",
        }
    }
    print(json.dumps(summary, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
