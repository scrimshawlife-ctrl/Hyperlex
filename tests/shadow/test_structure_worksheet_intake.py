"""Tests for fail-closed structure worksheet intake."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.shadow.hyperlexical.structure_worksheet_intake import (
    promote_structure_row,
    run_intake,
)
from scripts.shadow.hyperlexical.training_contracts import digest


def _meta(text: str) -> dict:
    return {
        "source": {
            "raw_text": text,
            "source_id": "src-test",
            "rights_status": "approved",
            "rights_reference": "file:///tmp/rights-memo.md#anchor",
        },
        "annotation": {
            "example_id": "ex-test",
            "source_id": "src-test",
            "group_ids": ["grp-test"],
            "offset_unit": "unicode_codepoint",
            "ontology_version": "proposal-v1",
            "spans": [],
            "version": "annotation.v1",
            "labels": {
                "family": {
                    "status": "reviewed",
                    "values": ["ai-native"],
                    "loss_mask": True,
                    "method": "human",
                    "reviewer": "tester",
                },
                "structure": {
                    "status": "unreviewed",
                    "values": [],
                    "loss_mask": False,
                    "method": "unreviewed",
                    "reviewer": None,
                },
            },
        },
        "partition": "train",
    }


def _original(text: str) -> dict:
    return {
        "text": text,
        "class": "OBSERVED",
        "license": "operator-attested",
        "lineage": "ai-native",
        "split": "train",
        "roles": [],
        "fillers": [],
        "task": "structure",
        "provenance": {"note": "fixture"},
    }


def test_pending_when_unconfirmed():
    text = "l rizz"
    row = {
        "canonical_row_sha256": "x",
        "text": text,
        "confirm_labels": False,
        "confirm_rights": False,
        "structure": {"status": "unreviewed", "loss_mask": False, "spans": []},
    }
    patched, audit = promote_structure_row(worksheet_row=row, metadata_entry=_meta(text))
    assert patched is None
    assert audit["status"] == "PENDING"


def test_rejects_bad_span_bounds():
    text = "l rizz"
    row = {
        "canonical_row_sha256": "x",
        "text": text,
        "confirm_labels": True,
        "confirm_rights": True,
        "structure": {
            "status": "reviewed",
            "loss_mask": True,
            "reviewer": "tester",
            "values": ["mod"],
            "spans": [{"start": 0, "end": 9, "text": "nope", "role": "mod"}],
        },
    }
    patched, audit = promote_structure_row(worksheet_row=row, metadata_entry=_meta(text))
    assert patched is None
    assert audit["status"] == "REJECTED"


def test_promotes_valid_confirmed_row(tmp_path: Path):
    text = "l rizz"
    original = _original(text)
    key = digest(original)
    filled = {
        "canonical_row_sha256": key,
        "text": text,
        "confirm_labels": True,
        "confirm_rights": True,
        "structure": {
            "status": "reviewed",
            "loss_mask": True,
            "reviewer": "tester",
            "method": "human-structure",
            "values": ["mod", "head"],
            "offset_unit": "unicode_codepoint",
            "spans": [
                {"occurrence_id": "sp0", "start": 0, "end": 1, "text": "l", "role": "mod"},
                {"occurrence_id": "sp1", "start": 2, "end": 6, "text": "rizz", "role": "head"},
            ],
        },
    }
    pending = {
        "canonical_row_sha256": key,
        "text": text,
        "confirm_labels": False,
        "confirm_rights": False,
        "structure": {"status": "unreviewed", "loss_mask": False, "spans": []},
    }
    ws = tmp_path / "ws.jsonl"
    ws.write_text(json.dumps(pending) + "\n" + json.dumps(filled) + "\n")
    original_path = tmp_path / "original.jsonl"
    original_path.write_text(json.dumps(original) + "\n")
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(json.dumps({key: _meta(text)}))
    out = tmp_path / "out"
    report = run_intake(
        worksheet_path=ws,
        original_path=original_path,
        metadata_path=metadata_path,
        out_dir=out,
    )
    assert report["n_promoted"] == 1
    assert report["counts"]["PENDING"] == 1
    assert report["counts"]["PROMOTED"] == 1
    patched = json.loads((out / "metadata.json").read_text())[key]
    assert patched["annotation"]["labels"]["structure"]["status"] == "reviewed"
    assert len(patched["annotation"]["spans"]) == 2
    with pytest.raises(FileExistsError):
        run_intake(
            worksheet_path=ws,
            original_path=original_path,
            metadata_path=metadata_path,
            out_dir=out,
        )
