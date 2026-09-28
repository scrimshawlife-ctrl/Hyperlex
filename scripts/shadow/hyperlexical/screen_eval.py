"""Evaluation lane for a frozen unbind screen.

Prediction, operator judgment, gold, admission, and settlement stay separate.
This module does not settle a target, admit an identity, or authorize SELECT-005.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from hyperlexical.holdout_guard import normalized_text_sha256

SAMPLE_SCHEMA = "hyperlex.unbind_screen_sample_row.v1"
PREDICTION_SCHEMA = "hyperlex.unbind_screen_prediction.v1"
REVIEW_SCHEMA = "hyperlex.unbind_screen_review_row.v1"
LABEL_SCHEMA = "hyperlex.unbind_screen_operator_label.v1"
REPORT_SCHEMA = "hyperlex.unbind_screen_report.v1"
RECEIPT_SCHEMA = "hyperlex.unbind_screen_evaluation_receipt.v1"

RULE_VERSION = "RUNE.UNBIND_SCREEN.v3"
BUCKETS = ("HIGH", "SECONDARY", "REJECT", "QUARANTINE")
OPERATOR_BUCKETS = BUCKETS + ("UNRESOLVED",)
RAW_BUCKETS = {"HIGH_VALUE": "HIGH", "HIGH": "HIGH", "SECONDARY": "SECONDARY", "REJECT": "REJECT", "QUARANTINE": "QUARANTINE"}
REASONS = {
    "HIGH": frozenset({"STRONG_IDIOM", "PHRASAL_BINDING", "FIXED_NONLITERAL", "VARIABLE_SLOT", "CONVENTIONALIZED_SHIFT"}),
    "SECONDARY": frozenset({"LEXICALIZED_TRANSPARENT", "FIXED_COMPOSITIONAL", "DOMAIN_LEXICALIZED"}),
    "REJECT": frozenset({
        "PERSON_NAME", "ORGANIZATION", "TITLE_OR_DESIGNATION", "TAXONOMY",
        "SPECIES_COMMON_NAME", "TECHNICAL_PROCEDURE", "TECHNICAL_MEASUREMENT",
        "PRODUCTIVE_NUMBER", "FREE_COMPOSITION", "REFERENTIAL_DOMINANCE",
    }),
    "QUARANTINE": frozenset({"DIALECTAL", "ARCHAIC", "AMBIGUOUS_SENSE", "PROVENANCE_UNCLEAR"}),
    "UNRESOLVED": frozenset({"INSUFFICIENT_SIGNAL"}),
}
STATES = (
    "DRAFT",
    "SAMPLE_FROZEN",
    "PREDICTIONS_FROZEN",
    "OPERATOR_LABELING",
    "LABELS_FROZEN",
    "SCORED",
    "ERROR_ANALYZED",
    "REVISION_ELIGIBLE",
)
LEAK_KEYS = frozenset({
    "predicted", "predicted_bucket", "bucket", "relation", "rule", "phase",
    "operator", "operator_bucket", "forecast", "diagnostic", "v4",
})


class ScreenEvalError(ValueError):
    pass


def refuse(message: str) -> None:
    raise ScreenEvalError(message)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bucket(raw: str) -> str:
    bucket = RAW_BUCKETS.get(str(raw or ""))
    if bucket is None:
        refuse(f"prediction bucket {raw!r} is not a screen bucket")
    return bucket


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _dump_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _parse_time(value: str) -> datetime:
    text = str(value or "").strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        refuse(f"timestamp {value!r} is not ISO-8601")
        raise exc
    if parsed.tzinfo is None:
        refuse(f"timestamp {value!r} needs a timezone")
    return parsed


def _surfaces(path: Path) -> set[str]:
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def _train_ids(path: Path) -> set[str]:
    found = set()
    for row in _load_jsonl(path):
        text = str(row.get("text") or row.get("surface") or "")
        if text:
            found.add(normalized_text_sha256(text))
    return found


def _identity_rows(frozen: Sequence[Mapping[str, Any]], *, evaluation_id: str, sample_id: str, sample_sha: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    samples, predictions, reviews = [], [], []
    seen: set[str] = set()
    for raw in frozen:
        surface = str(raw.get("text") or "")
        tokens = list(raw.get("tokens") or [])
        if " ".join(str(tok) for tok in tokens) != surface:
            refuse(f"tokens do not reconstruct {surface!r}")
        row_id = normalized_text_sha256(surface)
        if row_id in seen:
            refuse(f"duplicate row identity {row_id}")
        seen.add(row_id)
        provenance = {"source": "wordnet-3.0", "sample_sha256": sample_sha}
        samples.append({
            "schema": SAMPLE_SCHEMA,
            "evaluation_id": evaluation_id,
            "sample_id": sample_id,
            "row_id": row_id,
            "surface": surface,
            "pos": raw.get("source_pos"),
            "token_count": len(tokens),
            "provenance": provenance,
        })
        predictions.append({
            "schema": PREDICTION_SCHEMA,
            "evaluation_id": evaluation_id,
            "sample_id": sample_id,
            "row_id": row_id,
            "bucket": canonical_bucket(str(raw.get("predicted") or "")),
            "bucket_raw": raw.get("predicted"),
            "relation": raw.get("rule"),
            "rule_version": RULE_VERSION,
            "provenance": provenance,
        })
        reviews.append({
            "schema": REVIEW_SCHEMA,
            "evaluation_id": evaluation_id,
            "sample_id": sample_id,
            "row_id": row_id,
            "surface": surface,
            "pos": raw.get("source_pos"),
            "token_count": len(tokens),
            "gloss": raw.get("gloss") or "",
            "provenance": provenance,
        })
    samples.sort(key=lambda row: row["row_id"])
    predictions.sort(key=lambda row: row["row_id"])
    reviews.sort(key=lambda row: row["row_id"])
    return samples, predictions, reviews


def _assert_blind(rows: Sequence[Mapping[str, Any]]) -> None:
    for row in rows:
        leaked = LEAK_KEYS.intersection(row)
        if leaked:
            refuse(f"blind review carries {sorted(leaked)}")


def _assert_disjoint(heldout: Iterable[str], blocked: set[str], name: str) -> None:
    overlap = sorted(set(heldout) & blocked)
    if overlap:
        refuse(f"held-out row is also in {name}")


def materialize(
    frozen_sample: Path,
    out_dir: Path,
    *,
    expected_sha256: str,
    development: Path,
    validation_development: Path,
    train_jsonl: Path | None = None,
    evaluation_id: str = "HLX-EVAL-UNBIND-SCREEN-V3-001",
    sample_id: str = "heldout-001",
    frozen_at: str = "2026-09-27T22:57:17Z",
) -> dict[str, Any]:
    """Copy a frozen prediction file into separate sample, prediction, and blind review artifacts."""
    digest = file_sha256(frozen_sample)
    if digest != expected_sha256:
        refuse("frozen sample hash does not match the expected seal")
    frozen = _load_jsonl(frozen_sample)
    samples, predictions, reviews = _identity_rows(
        frozen, evaluation_id=evaluation_id, sample_id=sample_id, sample_sha=digest,
    )
    _assert_blind(reviews)
    held_ids = {row["row_id"] for row in samples}
    dev_ids = {normalized_text_sha256(text) for text in _surfaces(development)}
    val_ids = {normalized_text_sha256(text) for text in _surfaces(validation_development)}
    _assert_disjoint(held_ids, dev_ids, "development")
    _assert_disjoint(held_ids, val_ids, "validation_development")
    train_checked = train_jsonl is not None
    if train_jsonl is not None:
        _assert_disjoint(held_ids, _train_ids(train_jsonl), "training_gold")
    out = Path(out_dir)
    sample_sha = _dump_jsonl(out / "samples" / f"{sample_id}.jsonl", samples)
    prediction_sha = _dump_jsonl(out / "predictions" / f"{sample_id}.predictions.jsonl", predictions)
    review_sha = _dump_jsonl(out / "operator" / f"{sample_id}.review.jsonl", reviews)
    if file_sha256(frozen_sample) != digest:
        refuse("frozen sample changed during materialize")
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "evaluation_id": evaluation_id,
        "sample_id": sample_id,
        "state": "PREDICTIONS_FROZEN",
        "rule_version": RULE_VERSION,
        "sample_sha256": digest,
        "sample_artifact_sha256": sample_sha,
        "prediction_artifact_sha256": prediction_sha,
        "blind_review_sha256": review_sha,
        "operator_label_sha256": None,
        "sample_frozen_at": frozen_at,
        "development_rows": len(dev_ids),
        "validation_development_rows": len(val_ids),
        "held_out_rows": len(samples),
        "v3_application_count": 1,
        "hand_corrections": 0,
        "operator_labels": "pending",
        "held_out_precision": "NOT_COMPUTABLE",
        "confusion_matrix": "NOT_COMPUTABLE",
        "train_gold_checked": train_checked,
        "admitted": 0,
        "settled": 0,
        "gold": 0,
        "select_authorized": False,
        "revision_eligible": False,
    }
    (out / "reports").mkdir(parents=True, exist_ok=True)
    _write_json(out / "reports" / f"{sample_id}.receipt.json", receipt)
    return receipt


def _write_json(path: Path, body: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _receipt(out_dir: Path, sample_id: str) -> dict[str, Any]:
    path = out_dir / "reports" / f"{sample_id}.receipt.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _check_hashes(out_dir: Path, receipt: Mapping[str, Any]) -> None:
    sample_id = str(receipt["sample_id"])
    pairs = {
        "sample_artifact_sha256": out_dir / "samples" / f"{sample_id}.jsonl",
        "prediction_artifact_sha256": out_dir / "predictions" / f"{sample_id}.predictions.jsonl",
        "blind_review_sha256": out_dir / "operator" / f"{sample_id}.review.jsonl",
    }
    for field, path in pairs.items():
        if file_sha256(path) != receipt[field]:
            refuse(f"{field} changed after freeze")
    _assert_blind(_load_jsonl(pairs["blind_review_sha256"]))


def validate_label(row: Mapping[str, Any], *, frozen_at: str) -> dict[str, Any]:
    bucket = str(row.get("operator_bucket") or "")
    if bucket not in OPERATOR_BUCKETS:
        refuse(f"operator bucket {bucket!r} is not allowed")
    reason = str(row.get("reason_code") or "")
    if reason not in REASONS[bucket]:
        refuse(f"reason {reason!r} is not valid for {bucket}")
    row_id = str(row.get("row_id") or "")
    if len(row_id) != 64:
        refuse("operator label row_id must be the immutable identity")
    labeled_at = str(row.get("labeled_at") or "")
    if _parse_time(labeled_at) <= _parse_time(frozen_at):
        refuse("operator label timestamp is not after the sample freeze")
    return {
        "schema": LABEL_SCHEMA,
        "evaluation_id": row.get("evaluation_id"),
        "row_id": row_id,
        "operator_bucket": bucket,
        "reason_code": reason,
        "note": row.get("note"),
        "labeled_at": labeled_at,
    }


def freeze_labels(out_dir: Path, labels_path: Path, *, sample_id: str = "heldout-001") -> dict[str, Any]:
    """Store operator labels beside the frozen predictions. Does not score or settle."""
    out_dir = Path(out_dir)
    receipt = _receipt(out_dir, sample_id)
    if receipt.get("state") not in {"PREDICTIONS_FROZEN", "OPERATOR_LABELING", "LABELS_FROZEN"}:
        refuse(f"cannot freeze labels from state {receipt.get('state')}")
    _check_hashes(out_dir, receipt)
    predictions = _load_jsonl(out_dir / "predictions" / f"{sample_id}.predictions.jsonl")
    expected = {row["row_id"] for row in predictions}
    cleaned = [validate_label(row, frozen_at=str(receipt["sample_frozen_at"])) for row in _load_jsonl(labels_path)]
    got = [row["row_id"] for row in cleaned]
    if len(got) != len(set(got)):
        refuse("operator labels repeat a row identity")
    if set(got) != expected:
        refuse("operator labels do not cover the frozen rows exactly once")
    cleaned.sort(key=lambda row: row["row_id"])
    label_sha = _dump_jsonl(out_dir / "operator" / f"{sample_id}.labels.jsonl", cleaned)
    receipt["operator_label_sha256"] = label_sha
    receipt["operator_labels"] = "frozen"
    receipt["state"] = "LABELS_FROZEN"
    receipt["held_out_precision"] = "NOT_COMPUTABLE"
    receipt["confusion_matrix"] = "NOT_COMPUTABLE"
    receipt["select_authorized"] = False
    _write_json(out_dir / "reports" / f"{sample_id}.receipt.json", receipt)
    return receipt


def _metrics(pairs: Sequence[tuple[str, str, str, str]]) -> dict[str, Any]:
    """pairs are (row_id, predicted, operator, reason)."""
    resolved = [item for item in pairs if item[2] != "UNRESOLVED"]
    unresolved = [item for item in pairs if item[2] == "UNRESOLVED"]
    matrix = {op: {pred: 0 for pred in BUCKETS} for op in OPERATOR_BUCKETS}
    for _row_id, pred, op, _reason in pairs:
        matrix[op][pred] += 1
    per_bucket = {}
    for bucket in BUCKETS:
        tp = sum(1 for _i, pred, op, _r in resolved if pred == bucket and op == bucket)
        fp = sum(1 for _i, pred, op, _r in resolved if pred == bucket and op != bucket)
        fn = sum(1 for _i, pred, op, _r in resolved if op == bucket and pred != bucket)
        precision = None if tp + fp == 0 else tp / (tp + fp)
        recall = None if tp + fn == 0 else tp / (tp + fn)
        f1 = None
        if precision is not None and recall is not None and precision + recall:
            f1 = 2 * precision * recall / (precision + recall)
        per_bucket[bucket] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": tp + fn,
        }
    accuracy = None if not resolved else sum(1 for _i, pred, op, _r in resolved if pred == op) / len(resolved)
    reasons: dict[str, int] = {}
    for _i, _p, _o, reason in pairs:
        reasons[reason] = reasons.get(reason, 0) + 1
    return {
        "overall_accuracy": accuracy,
        "per_bucket": per_bucket,
        "confusion_matrix": matrix,
        "reason_code_distribution": reasons,
        "unresolved_count": len(unresolved),
        "resolved_count": len(resolved),
    }


def _error_class(predicted: str, operator: str) -> str | None:
    if operator == "UNRESOLVED" or predicted == operator:
        return None
    return {
        "HIGH": "false_high",
        "SECONDARY": "false_secondary",
        "REJECT": "false_reject",
        "QUARANTINE": "false_quarantine",
    }[predicted]


def score(out_dir: Path, *, sample_id: str = "heldout-001") -> dict[str, Any]:
    """Join labels to predictions on row_id. Pending labels stay NOT_COMPUTABLE."""
    out_dir = Path(out_dir)
    receipt = _receipt(out_dir, sample_id)
    _check_hashes(out_dir, receipt)
    label_path = out_dir / "operator" / f"{sample_id}.labels.jsonl"
    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "evaluation_id": receipt["evaluation_id"],
        "sample_id": sample_id,
        "rule_version": RULE_VERSION,
        "select_authorized": False,
        "revision_eligible": False,
        "admitted": 0,
        "settled": 0,
        "gold": 0,
    }
    if receipt.get("operator_labels") != "frozen" or not label_path.is_file():
        report["status"] = "NOT_COMPUTABLE"
        report["held_out_precision"] = "NOT_COMPUTABLE"
        report["confusion_matrix"] = "NOT_COMPUTABLE"
        report["overall_accuracy"] = "NOT_COMPUTABLE"
        _write_json(out_dir / "reports" / f"{sample_id}.metrics.json", report)
        return report
    if file_sha256(label_path) != receipt.get("operator_label_sha256"):
        refuse("operator artifact hash changed after label freeze")
    predictions = {row["row_id"]: row for row in _load_jsonl(out_dir / "predictions" / f"{sample_id}.predictions.jsonl")}
    samples = {row["row_id"]: row for row in _load_jsonl(out_dir / "samples" / f"{sample_id}.jsonl")}
    labels = {row["row_id"]: row for row in _load_jsonl(label_path)}
    if set(labels) != set(predictions):
        refuse("join row identities do not match")
    pairs = []
    errors = []
    classes = {name: 0 for name in ("false_high", "false_secondary", "false_reject", "false_quarantine")}
    for row_id in sorted(predictions):
        pred = predictions[row_id]
        label = labels[row_id]
        kind = _error_class(pred["bucket"], label["operator_bucket"])
        pairs.append((row_id, pred["bucket"], label["operator_bucket"], label["reason_code"]))
        if kind:
            classes[kind] += 1
            errors.append({
                "row_id": row_id,
                "surface": samples[row_id]["surface"],
                "predicted_bucket": pred["bucket"],
                "operator_bucket": label["operator_bucket"],
                "prediction_relation": pred["relation"],
                "operator_reason": label["reason_code"],
                "error_class": kind,
            })
    metrics = _metrics(pairs)
    report.update(metrics)
    report["status"] = "SCORED"
    report["error_classes"] = classes
    report["select_authorized"] = False
    _write_json(out_dir / "reports" / f"{sample_id}.metrics.json", report)
    _dump_jsonl(out_dir / "reports" / f"{sample_id}.errors.jsonl", errors)
    with (out_dir / "reports" / f"{sample_id}.confusion.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["operator_bucket", "predicted_bucket", "count"])
        for operator, cols in metrics["confusion_matrix"].items():
            for predicted, count in cols.items():
                writer.writerow([operator, predicted, count])
    receipt["state"] = "SCORED"
    receipt["held_out_precision"] = "SCORED"
    receipt["confusion_matrix"] = "SCORED"
    receipt["select_authorized"] = False
    receipt["revision_eligible"] = False
    _write_json(out_dir / "reports" / f"{sample_id}.receipt.json", receipt)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Score a frozen unbind screen without settling it.")
    sub = parser.add_subparsers(dest="command", required=True)
    mat = sub.add_parser("materialize")
    mat.add_argument("--frozen-sample", type=Path, required=True)
    mat.add_argument("--expected-sha", required=True)
    mat.add_argument("--development", type=Path, required=True)
    mat.add_argument("--validation-development", type=Path, required=True)
    mat.add_argument("--train-jsonl", type=Path)
    mat.add_argument("--out", type=Path, required=True)
    mat.add_argument("--evaluation-id", default="HLX-EVAL-UNBIND-SCREEN-V3-001")
    mat.add_argument("--frozen-at", default="2026-09-27T22:57:17Z")
    sc = sub.add_parser("score")
    sc.add_argument("--evaluation", type=Path, required=True)
    fr = sub.add_parser("freeze-labels")
    fr.add_argument("--evaluation", type=Path, required=True)
    fr.add_argument("--labels", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "materialize":
            receipt = materialize(
                args.frozen_sample,
                args.out,
                expected_sha256=args.expected_sha,
                development=args.development,
                validation_development=args.validation_development,
                train_jsonl=args.train_jsonl,
                evaluation_id=args.evaluation_id,
                frozen_at=args.frozen_at,
            )
        elif args.command == "freeze-labels":
            receipt = freeze_labels(args.evaluation, args.labels)
        else:
            receipt = score(args.evaluation)
    except ScreenEvalError as exc:
        raise SystemExit(f"REFUSE: {exc}") from exc
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
