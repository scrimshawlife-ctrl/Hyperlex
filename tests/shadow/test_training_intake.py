"""Synthetic conversion controls only.

Provenance: Notion Sprint 001 Hub NOT_COMPUTABLE + Loop 805 Slice N/A
+ Hash: versioned with patch.
"""
import copy
import hashlib
import json

import pytest
from scripts.shadow.hyperlexical.training_contracts import digest, validate_dataset
from scripts.shadow.hyperlexical.training_intake import convert, export_new, main


def inputs():
    row = {"text": "blue moon", "class": "OBSERVED", "lineage": "none"}
    source = {"version": "source.v1", "source_id": "s1", "raw_text": row["text"],
              "text_sha256": hashlib.sha256(row["text"].encode()).hexdigest(),
              "source_kind": "synthetic", "rights_status": "approved",
              "rights_reference": "synthetic fixture", "provenance_reference": "synthetic test"}
    annotation = {"version": "annotation.v1", "example_id": "e1", "source_id": "s1",
                  "group_ids": ["g1"], "offset_unit": "unicode_codepoint", "ontology_version": "test-v1",
                  "spans": [], "labels": {"family": {"status": "unreviewed", "values": [],
                                                       "loss_mask": False, "reviewer": None, "method": "unreviewed"}}}
    metadata = {digest(row): {"source": source, "annotation": annotation, "partition": "dev"}}
    return row, metadata


def encode(value):
    return json.dumps(value).encode()


def test_conversion_preserves_declared_metadata_and_does_not_promote():
    row, meta = inputs()
    original = copy.deepcopy(meta)
    result = convert(encode(row), encode(meta))
    assert result["report"]["n_candidates"] == 1
    assert result["candidates"][0]["annotation"]["labels"]["family"]["loss_mask"] is False
    assert meta == original
    assert result["report"]["training_ready"] is False
    assert validate_dataset(result["dataset"])["annotations"] == 1


def test_missing_metadata_never_infers_approval_from_observed():
    row, _ = inputs()
    row["license"] = "MIT"
    result = convert(encode(row))
    assert result["report"]["n_candidates"] == 0
    assert result["quarantine"][0]["reason"] == "MISSING_REVIEW_METADATA"
    assert result["dataset"] is None


@pytest.mark.parametrize("payload", [b'{broken}', b'[]', b'{"text":"a","text":"b"}', b'{"x": NaN}'])
def test_malformed_rows_accounted(payload):
    result = convert(payload)
    assert result["report"]["n_records"] == result["report"]["n_quarantined"] == 1


@pytest.mark.parametrize("metadata", [b'[]', b'{"bad":{}}', b'{"x":1,"x":2}'])
def test_invalid_sidecar_fails(metadata):
    with pytest.raises((TypeError, ValueError)):
        convert(b'{"text":"x"}', metadata)


@pytest.mark.parametrize("alter", ["rights", "source", "reviewer", "extra", "offset"])
def test_bad_metadata_quarantined(alter):
    row, meta = inputs()
    entry = next(iter(meta.values()))
    if alter == "rights":
        entry["source"]["rights_status"] = "unreviewed"
    elif alter == "source":
        entry["source"]["raw_text"] = "different"
    elif alter == "reviewer":
        entry["annotation"]["labels"]["family"]["status"] = "reviewed"
    elif alter == "extra":
        entry["invented"] = True
    else:
        entry["annotation"]["spans"] = [{"occurrence_id": "o1", "start": 0, "end": 99, "text": "blue", "role": "pos_0"}]
    result = convert(encode(row), encode(meta))
    assert result["report"]["n_quarantined"] == 1


def test_duplicate_row_and_unused_metadata():
    row, meta = inputs()
    meta["0" * 64] = {}
    result = convert(encode(row) + b'\n' + encode(row), encode(meta))
    assert result["report"]["n_candidates"] == 1
    assert result["report"]["unused_metadata_entries"] == 1
    assert result["quarantine"][0]["reason"] == "DUPLICATE_ROW"


def test_group_conflict_quarantines_whole_candidate_batch():
    row, meta = inputs()
    row2 = {"text": "red moon"}
    entry = copy.deepcopy(next(iter(meta.values())))
    entry["source"].update(source_id="s2", raw_text=row2["text"], text_sha256=hashlib.sha256(b'red moon').hexdigest())
    entry["annotation"].update(source_id="s2", example_id="e2")
    entry["partition"] = "train"
    meta[digest(row2)] = entry
    result = convert(encode(row) + b'\n' + encode(row2), encode(meta))
    assert result["report"]["n_candidates"] == 0
    assert result["report"]["reasons"] == {"BATCH_CONTRACT_CONFLICT": 2}


def test_export_preserves_bytes_and_never_overwrites(tmp_path):
    row, meta = inputs()
    payload = b'\xef\xbb\xbf' + encode(row) + b'\r\n\r\n'
    metadata = encode(meta)
    result = convert(payload, metadata)
    out = tmp_path / "fresh"
    export_new(out, result, payload, metadata)
    assert (out / "original.jsonl").read_bytes() == payload
    assert (out / "metadata.json").read_bytes() == metadata
    assert json.loads((out / "receipt.json").read_text())["export_complete"]
    with pytest.raises(FileExistsError):
        export_new(out, result, payload, metadata)
    assert (out / "original.jsonl").read_bytes() == payload


def test_cli_default_no_writes_and_nonzero_quarantine(tmp_path, capsys):
    row, _ = inputs()
    src = tmp_path / "input.jsonl"
    src.write_bytes(encode(row))
    assert main(["--input", str(src)]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["n_quarantined"] == 1
    assert list(tmp_path.iterdir()) == [src]
    assert src.read_bytes() == encode(row)


def test_empty_and_bad_utf8():
    for payload in (b'\n', b'\xff'):
        with pytest.raises(ValueError):
            convert(payload)


def test_residual_cannot_become_training_row():
    row, meta = inputs()
    entry = next(iter(meta.values()))
    entry["partition"] = "train"
    row.update(gold=["blue", "moon"], pred=["red", "moon"])
    result = convert(encode(row), encode({digest(row): entry}))
    assert result["report"]["reasons"] == {"RESIDUAL_PARTITION": 1}
