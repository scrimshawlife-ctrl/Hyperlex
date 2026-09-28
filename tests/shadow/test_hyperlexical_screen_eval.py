import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.holdout_guard import normalized_text_sha256
from hyperlexical.screen_eval import (
    ScreenEvalError,
    file_sha256,
    freeze_labels,
    materialize,
    score,
)

FROZEN_AT = "2020-01-01T00:00:00Z"
LABELED_AT = "2020-01-02T00:00:00Z"


def _frozen_row(text, predicted, rule, pos="verb"):
    tokens = text.split(" ")
    return {
        "text": text,
        "source_pos": pos,
        "tokens": tokens,
        "predicted": predicted,
        "rule": rule,
        "gloss": f"gloss for {text}",
    }


def _write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _layout(tmp_path):
    frozen = tmp_path / "frozen.jsonl"
    rows = [
        _frozen_row("alpha beta", "HIGH_VALUE", "conventionalized_semantic_shift"),
        _frozen_row("gamma delta", "SECONDARY", "transparent_or_moderate", pos="adj"),
        _frozen_row("epsilon zeta", "REJECT", "proper_person_name", pos="noun"),
    ]
    _write_jsonl(frozen, rows)
    dev = tmp_path / "development.txt"
    dev.write_text("other phrase\n", encoding="utf-8")
    val = tmp_path / "validation.txt"
    val.write_text("another phrase\n", encoding="utf-8")
    return frozen, dev, val


def test_materialize_hides_prediction_and_keeps_source_hash(tmp_path):
    frozen, dev, val = _layout(tmp_path)
    digest = file_sha256(frozen)
    receipt = materialize(
        frozen,
        tmp_path / "eval",
        expected_sha256=digest,
        development=dev,
        validation_development=val,
        frozen_at=FROZEN_AT,
        evaluation_id="HLX-EVAL-TEST",
    )
    assert file_sha256(frozen) == digest
    assert receipt["state"] == "PREDICTIONS_FROZEN"
    assert receipt["held_out_precision"] == "NOT_COMPUTABLE"
    assert receipt["select_authorized"] is False
    assert receipt["admitted"] == 0
    review = [
        json.loads(line)
        for line in (tmp_path / "eval" / "operator" / "heldout-001.review.jsonl").read_text().splitlines()
    ]
    assert len(review) == 3
    for row in review:
        assert "predicted" not in row
        assert "rule" not in row
        assert "bucket" not in row
        assert row["row_id"] == normalized_text_sha256(row["surface"])
        assert row["gloss"].startswith("gloss for ")
    report = score(tmp_path / "eval")
    assert report["status"] == "NOT_COMPUTABLE"
    assert report["confusion_matrix"] == "NOT_COMPUTABLE"
    assert not (tmp_path / "eval" / "reports" / "heldout-001.confusion.csv").exists()


def test_development_overlap_refuses(tmp_path):
    frozen, dev, val = _layout(tmp_path)
    dev.write_text("alpha beta\n", encoding="utf-8")
    with pytest.raises(ScreenEvalError, match="development"):
        materialize(
            frozen,
            tmp_path / "eval",
            expected_sha256=file_sha256(frozen),
            development=dev,
            validation_development=val,
            frozen_at=FROZEN_AT,
        )


def test_score_joins_on_row_id_and_does_not_authorize(tmp_path):
    frozen, dev, val = _layout(tmp_path)
    out = tmp_path / "eval"
    materialize(
        frozen,
        out,
        expected_sha256=file_sha256(frozen),
        development=dev,
        validation_development=val,
        frozen_at=FROZEN_AT,
        evaluation_id="HLX-EVAL-TEST",
    )
    predictions = [
        json.loads(line)
        for line in (out / "predictions" / "heldout-001.predictions.jsonl").read_text().splitlines()
    ]
    by_surface = {
        json.loads(line)["surface"]: json.loads(line)["row_id"]
        for line in (out / "samples" / "heldout-001.jsonl").read_text().splitlines()
    }
    labels = [
        {
            "evaluation_id": "HLX-EVAL-TEST",
            "row_id": by_surface["alpha beta"],
            "operator_bucket": "HIGH",
            "reason_code": "STRONG_IDIOM",
            "note": None,
            "labeled_at": LABELED_AT,
        },
        {
            "evaluation_id": "HLX-EVAL-TEST",
            "row_id": by_surface["gamma delta"],
            "operator_bucket": "REJECT",
            "reason_code": "PRODUCTIVE_NUMBER",
            "note": None,
            "labeled_at": LABELED_AT,
        },
        {
            "evaluation_id": "HLX-EVAL-TEST",
            "row_id": by_surface["epsilon zeta"],
            "operator_bucket": "UNRESOLVED",
            "reason_code": "INSUFFICIENT_SIGNAL",
            "note": None,
            "labeled_at": LABELED_AT,
        },
    ]
    label_path = tmp_path / "labels.jsonl"
    _write_jsonl(label_path, labels)
    freeze_labels(out, label_path)
    # Tampering with the source order must not matter: score reads the frozen label file.
    report = score(out)
    assert report["status"] == "SCORED"
    assert report["select_authorized"] is False
    assert report["revision_eligible"] is False
    assert report["unresolved_count"] == 1
    assert report["per_bucket"]["HIGH"]["precision"] == 1
    assert report["per_bucket"]["SECONDARY"]["precision"] == 0
    assert report["error_classes"]["false_secondary"] == 1
    errors = [
        json.loads(line)
        for line in (out / "reports" / "heldout-001.errors.jsonl").read_text().splitlines()
    ]
    assert errors[0]["surface"] == "gamma delta"
    assert errors[0]["operator_reason"] == "PRODUCTIVE_NUMBER"
    assert errors[0]["error_class"] == "false_secondary"
    assert {row["row_id"] for row in predictions} == set(by_surface.values())


def test_label_before_freeze_refuses(tmp_path):
    frozen, dev, val = _layout(tmp_path)
    out = tmp_path / "eval"
    materialize(
        frozen,
        out,
        expected_sha256=file_sha256(frozen),
        development=dev,
        validation_development=val,
        frozen_at=FROZEN_AT,
        evaluation_id="HLX-EVAL-TEST",
    )
    row_id = json.loads((out / "samples" / "heldout-001.jsonl").read_text().splitlines()[0])["row_id"]
    # Cover all three identities with an early timestamp on the first.
    ids = [
        json.loads(line)["row_id"]
        for line in (out / "samples" / "heldout-001.jsonl").read_text().splitlines()
    ]
    labels = []
    for index, identity in enumerate(ids):
        labels.append({
            "evaluation_id": "HLX-EVAL-TEST",
            "row_id": identity,
            "operator_bucket": "HIGH",
            "reason_code": "STRONG_IDIOM",
            "note": None,
            "labeled_at": "2019-12-31T00:00:00Z" if index == 0 else LABELED_AT,
        })
    path = tmp_path / "early.jsonl"
    _write_jsonl(path, labels)
    with pytest.raises(ScreenEvalError, match="timestamp"):
        freeze_labels(out, path)
    assert row_id in ids


def test_changed_prediction_hash_refuses_score(tmp_path):
    frozen, dev, val = _layout(tmp_path)
    out = tmp_path / "eval"
    materialize(
        frozen,
        out,
        expected_sha256=file_sha256(frozen),
        development=dev,
        validation_development=val,
        frozen_at=FROZEN_AT,
    )
    pred = out / "predictions" / "heldout-001.predictions.jsonl"
    pred.write_text(pred.read_text() + "\n", encoding="utf-8")
    with pytest.raises(ScreenEvalError, match="prediction_artifact_sha256"):
        score(out)
