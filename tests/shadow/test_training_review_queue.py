"""Review queue build/apply controls. Never invents rights or label approval.

Provenance: Hyperlex Spec 007 WF-002 review queue helper tests.
"""
from __future__ import annotations

import copy
import hashlib
import json

import pytest

from scripts.shadow.hyperlexical.training_contracts import digest
from scripts.shadow.hyperlexical.training_intake import convert
from scripts.shadow.hyperlexical.training_review_queue import (
    apply_confirmed_decisions,
    build_review_queue,
    main,
    materialize_sidecar_entry,
)


def _row(**extra):
    row = {
        "text": "blue moon rises",
        "class": "OBSERVED",
        "license": "operator-local",
        "lineage": "ai-native",
        "split": "train",
        "roles": ["mod", "head"],
        "fillers": ["blue", "moon"],
        "task": "structure",
        "provenance": {"note": "synthetic fixture"},
    }
    row.update(extra)
    return row


def _encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def test_build_queue_never_auto_approves_observed():
    row = _row()
    result = build_review_queue(_encode(row))
    assert result["report"]["status"] == "QUEUE_BUILT"
    assert result["report"]["training_ready"] is False
    assert result["report"]["n_queue"] == 1
    item = result["queue"][0]
    assert item["canonical_row_sha256"] == digest(row)
    assert item["confirm_rights"] is False
    assert item["confirm_labels"] is False
    assert item["draft"]["source"]["rights_status"] == "unreviewed"
    assert item["draft"]["source"]["rights_reference"] == "operator-local"
    assert item["draft"]["annotation"]["labels"]["family"]["status"] == "unreviewed"
    assert item["draft"]["annotation"]["labels"]["family"]["loss_mask"] is False
    assert item["auto_approve_forbidden"] is True
    assert item["observed_is_not_rights"] is True


def test_build_quarantines_malformed_and_duplicates():
    good = _encode(_row())
    payload = b"{broken}\n" + good + b"\n" + good + b"\n[]\n"
    result = build_review_queue(payload)
    assert result["report"]["n_queue"] == 1
    assert result["report"]["n_quarantined"] == 3
    reasons = result["report"]["quarantine_reasons"]
    assert reasons["MALFORMED_JSON"] == 1
    assert reasons["NOT_AN_OBJECT"] == 1
    assert reasons["DUPLICATE_ROW"] == 1


def test_apply_rejects_unconfirmed_and_operator_local_rights():
    row = _row()
    built = build_review_queue(_encode(row))
    item = built["queue"][0]
    key = item["canonical_row_sha256"]

    unconfirmed = apply_confirmed_decisions(built["queue"], [{"canonical_row_sha256": key}])
    assert unconfirmed["metadata"] == {}
    assert "unconfirmed" in unconfirmed["skipped"][0]["reason"]

    bad = copy.deepcopy(item)
    bad["confirm_rights"] = True
    bad["confirm_labels"] = True
    bad["draft"]["source"]["rights_status"] = "approved"
    bad["draft"]["source"]["rights_reference"] = "operator-local"
    fam = bad["draft"]["annotation"]["labels"]["family"]
    fam.update(status="reviewed", loss_mask=True, values=["ai-native"], reviewer="reviewer-a", method="human")
    with pytest.raises(ValueError, match="not authoritative"):
        materialize_sidecar_entry(bad)


def test_apply_confirmed_sidecar_passes_intake():
    row = _row()
    built = build_review_queue(_encode(row))
    item = copy.deepcopy(built["queue"][0])
    key = item["canonical_row_sha256"]
    draft = item["draft"]
    draft["source"]["rights_status"] = "approved"
    draft["source"]["rights_reference"] = "fixture-corpus-license.md#clause-1"
    draft["annotation"]["labels"]["family"].update(
        status="reviewed",
        loss_mask=True,
        values=["ai-native"],
        reviewer="reviewer-a",
        method="human-review",
    )
    # Keep structure suggestion inactive until spans are human-confirmed.
    draft["annotation"]["labels"]["structure"].update(
        status="unreviewed", loss_mask=False, values=[], reviewer=None, method="unreviewed"
    )
    draft["annotation"]["spans"] = []
    decision = {
        "canonical_row_sha256": key,
        "confirm_rights": True,
        "confirm_labels": True,
        "draft": draft,
    }
    applied = apply_confirmed_decisions(built["queue"], [decision])
    assert applied["report"]["n_sidecar_entries"] == 1
    assert applied["skipped"] == []
    meta = applied["metadata"]
    assert set(meta[key]) == {"source", "annotation", "partition"}
    converted = convert(_encode(row), json.dumps(meta).encode())
    assert converted["report"]["n_candidates"] == 1
    assert converted["report"]["n_quarantined"] == 0
    assert converted["dataset"] is not None
    assert converted["report"]["training_ready"] is False


def test_cli_build_and_apply(tmp_path, capsys):
    src = tmp_path / "legacy.jsonl"
    row = _row()
    src.write_bytes(_encode(row))
    out = tmp_path / "queue-pkg"
    assert main(["build", "--input", str(src), "--out-dir", str(out)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["n_queue"] == 1
    assert (out / "queue.json").is_file()
    assert (out / "decisions_template_first20.jsonl").is_file()
    assert (out / "original.jsonl").read_bytes() == src.read_bytes()

    queue = json.loads((out / "queue.json").read_text(encoding="utf-8"))
    draft = copy.deepcopy(queue[0]["draft"])
    draft["source"]["rights_status"] = "approved"
    draft["source"]["rights_reference"] = "authoritative-rights-memo.md"
    draft["annotation"]["labels"]["family"].update(
        status="reviewed",
        loss_mask=True,
        values=["ai-native"],
        reviewer="reviewer-b",
        method="human-review",
    )
    draft["annotation"]["labels"]["structure"].update(
        status="unreviewed", loss_mask=False, values=[], reviewer=None, method="unreviewed"
    )
    draft["annotation"]["spans"] = []
    decisions = tmp_path / "decisions.jsonl"
    decisions.write_text(
        json.dumps(
            {
                "canonical_row_sha256": queue[0]["canonical_row_sha256"],
                "confirm_rights": True,
                "confirm_labels": True,
                "draft": draft,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    meta_path = tmp_path / "metadata.json"
    assert (
        main(
            [
                "apply",
                "--queue",
                str(out / "queue.json"),
                "--decisions",
                str(decisions),
                "--out-metadata",
                str(meta_path),
            ]
        )
        == 0
    )
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert len(meta) == 1
    assert hashlib.sha256(draft["source"]["raw_text"].encode()).hexdigest() == draft["source"]["text_sha256"]
